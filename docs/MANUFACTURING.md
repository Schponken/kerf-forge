# Custom stock parts beside printed parts

A project may contain a laser-cut panel, a CNC carbon plate or a machined solid alongside its printed parts.
Declare it under `parts:` with the usual `file: parts/panel.py` and `build(ctx)`, or `import: imports/panel.step`.
Its joints, fastener sites, collisions, motion, assembly placement, viewer and URDF work through the same assembly.

Add a `manufacturing` map to that part:

| Key | Meaning |
|---|---|
| `process` | `laser_cut` or `cnc`. Choose the process the supplier actually supports for this stock. |
| `stock` | Exact material, grade and stock description, including laminate layup where relevant. |
| `density_g_cm3` | Positive density from the stock's datasheet. Mass is the current solid's volume × this density; geometry changes update it. |
| `density_source` | HTTP(S) link to that density evidence. Kerf records the source; it does not verify the supplier's data automatically. |
| `thickness_mm` | Required for `laser_cut`; optional for `cnc`. When present, the part must be a flat, constant-section XY plate of this thickness. |
| `price_key` | Optional key for an exact, dated supplier quote in `catalog/prices.json`, using its normal `buy`, `source`, `checked`, `pack_qty` and `pack_usd` fields. |
| `quote_fingerprint` | Geometry/stock/process/quantity identity from the generated `manufacturing/order.json`. Save this only after receiving a quote for those exact files and quantity. |

The part's `qty` must be a positive integer. Do not put FDM `material`, `print_rot`, `infill`, `walls`, `modifiers` or
`supports` on it. Measured printer fit offsets are disabled during its build. The designer still specifies actual
machined hole sizes and clearances; printing-oriented interface helpers do not become machining standards.
Do not substitute a printed carbon-filled polymer's properties for a carbon laminate.

`kerf build` exports:

- `manufacturing/<part>.step`: the finished exact solid, in its own coordinate frame, in millimetres.
- `manufacturing/<part>.dxf`: 1:1 XY through-cut outline and holes, only for a proven constant-section plate.
  Kerf reconstructs the solid by extruding its bottom face and compares both directions. Pockets, chamfers, bevels,
  bent sheets, non-XY plates and thickness mismatches fail that route. Use `cnc` without `thickness_mm` for a 3D STEP
  solid instead. No kerf compensation, nesting or toolpaths are generated.
- `manufacturing/ORDER.md` and `order.json`: stock, quantity, density evidence, current estimated mass and file list.
  Rebuilding removes obsolete STEP/DXF files listed in the previous generated manifest; other files are kept.
- Drawings, assembly STEP/GLB, the viewer, assembly steps, the priced BOM and Studio's download ZIP include the stock
  parts. Print STL/3MF, slicer plates, filament totals and Studio's filament picker include printed parts only.

Missing or outdated quotes appear as **unpriced**. A change to geometry, stock, process or quantity invalidates the
saved quote fingerprint; this also prevents a quote for one quantity from silently pricing another. The geometry
identity is conservative, so changes to tessellation may require reconfirming a quote too. Taxes and shipping follow
the existing BOM exclusions. No automatic supplier search, quote request, purchase or order is made.

This is a manufacturing handoff, not stock engineering certification. Geometry, mass, assembly fit and motion can
be checked now. Stock-specific strength, laminate properties and thermal models, supplier minimum feature sizes,
tool access, surface finish and tolerances require separate evidence. `structural: true`, strength requirements
targeting stock (including derived strength cases), and heat requirements covering stock fail explicitly as
unverified. Kerf never runs them with a default FDM polymer. A fixture test proves the software route; it is not a
production design or a supplier qualification. The broader PLAN item remains open for those models and a fully
engineered mixed-manufacturing project.
