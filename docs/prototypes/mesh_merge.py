import time, numpy as np, trimesh, manifold3d as mf
def organic(sub):
    m = trimesh.creation.icosphere(subdivisions=sub, radius=30); v=m.vertices; r=np.linalg.norm(v,axis=1,keepdims=True)
    m.vertices = v/r*30*(1+0.12*np.sin(3*v[:,[0]]/10)*np.cos(2*v[:,[1]]/10)); m.vertices[:,2]*=0.7; return m
def to_manifold(m):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices,np.float32), tri_verts=np.asarray(m.faces,np.uint32)))
def repair(m):
    """Cheap repair ladder: merge verts -> fill holes -> if still bad, voxel remesh (always watertight)."""
    m = m.copy(); m.merge_vertices(); m.update_faces(m.nondegenerate_faces()); trimesh.repair.fill_holes(m); trimesh.repair.fix_normals(m)
    if m.is_watertight and to_manifold(m).status().name == "NoError": return m, "fill_holes"
    v = m.voxelized(pitch=0.4).fill(); return v.marching_cubes.apply_transform(v.transform), "voxel_remesh"
def merge(M):
    mount = mf.Manifold.cube([40,40,6],True).translate([0,0,-20])
    out = (M - mf.Manifold.cube([80,80,20],True).translate([0,0,-30])) + mount
    for x in (-15,15):
        for y in (-15,15): out = out - mf.Manifold.cylinder(40,1.6,1.6,64,True).translate([x,y,-20])
    mm = out.to_mesh(); return trimesh.Trimesh(mm.vert_properties[:,:3], mm.tri_verts)
def probe_hole(tm):   # is the M3 hole really 3.2 mm and open? sample a ray down the hole axis
    pts = np.array([[15,15,z] for z in np.linspace(-23,-17,7)]); inside = tm.contains(pts)
    edge = tm.contains(np.array([[15+1.5,15,-20],[15+1.7,15,-20]]))
    return (not inside.any()), list(edge)
for sub,label in ((6,"clean 80k tris"),(7,"clean 330k tris")):
    m=organic(sub); t=time.time(); tm=merge(to_manifold(m)); print(f"{label}: watertight={tm.is_watertight} bodies={len(tm.split())} {time.time()-t:.2f}s hole_open,edge(in@1.5,in@1.7)={probe_hole(tm)}")
m=organic(5); rng=np.random.default_rng(1)
broken = trimesh.Trimesh(m.vertices, np.delete(m.faces, rng.choice(len(m.faces),40,replace=False),0))  # 40 missing triangles
broken = trimesh.util.concatenate([broken, trimesh.creation.box((10,10,10)).apply_translation([0,0,18])])  # overlapping junk body
print("broken: watertight", broken.is_watertight, "manifold status", to_manifold(broken).status().name)
t=time.time(); fixed, how = repair(broken); tm = merge(to_manifold(fixed))
print(f"repaired via {how}: watertight={tm.is_watertight} bodies={len(tm.split())} {time.time()-t:.1f}s hole={probe_hole(tm)}")
def repair_union(m):
    parts=[]; how=set()
    for c in m.split(only_watertight=False):
        f,h = repair(c); how.add(h); M=to_manifold(f)
        if M.status().name=="NoError" and M.volume()>1: parts.append(M)
    return mf.Manifold.batch_boolean(parts, mf.OpType.Add), how
t=time.time(); U,how = repair_union(broken); tm = merge(U)
print(f"repair per piece + union via {how}: watertight={tm.is_watertight} bodies={len(tm.split())} {time.time()-t:.1f}s hole={probe_hole(tm)}")
