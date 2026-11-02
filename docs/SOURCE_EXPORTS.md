# Design sources in Studio downloads

Studio's project ZIP keeps the generated maker files at the top level and puts the editable project under
`<project>/design/`. The design folder contains `project.yaml`, optional `DESIGN.md` / `REFERENCES.md`, every Python
helper under `parts/`, and the part, layout, imported STEP/STL/3MF and Meshy files declared by the project.

List additional project-local inputs explicitly in `project.yaml`:

```yaml
source_files:
  - parts/helpers/profile.csv
  - data/calibration.json
  - code/shared_geometry.py
  - meshes/shell.bin
```

Use paths relative to the project folder. Files keep that structure in the archive, so code can continue reading
them relative to its own location. This is a **declared dependency closure**, not static proof of every file Python
could read: list data files, helpers outside `parts/`, and sidecar files required by a mesh format. The download does
not execute code to discover dependencies or include an entire data directory automatically.

Every selected file must exist and remain inside the project, without symlink components. Absolute/escaping paths,
hidden files, output/cache folders, review approval and known credential/key filenames are refused. Keep credentials
out of design sources. Missing required inputs fail the download with the filename instead of returning an incomplete
ZIP. Unlisted files are left out; the original project is never modified.

The extracted design has no `review.json` or previous build cache. Put it in a Kerf checkout to rebuild it with the
engine and catalog, then run its checks and obtain its own current review. The existing maker outputs in the ZIP
remain the saved outputs from the original project; exporting does not rebuild or approve either copy.

## Generated maker files

Selected maker files must be regular files within the project's real `out/` directory. The download refuses
symlinks in that root, selected folders or their descendants, and refuses special files such as pipes or sockets.
Unreadable folders fail the download instead of silently omitting their files. The error names the invalid input;
no partial ZIP is returned. Remove the invalid output and regenerate the expected maker files before retrying.

Missing optional output files/folders remain okay, so a project can still export its design before its first build.
Valid nested maker paths are preserved; generated `.glb` previews remain excluded. Supplier files and generated
reports continue to follow Studio's additive output lists.
