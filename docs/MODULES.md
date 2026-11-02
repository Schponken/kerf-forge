# Reusable assemblies

Start from an existing assembly with its interfaces, sourcing, wiring and requirements intact:

```sh
.venv/bin/kerf modules
.venv/bin/kerf modules servo_joint
.venv/bin/kerf new my_joint "My bench joint" --module servo_joint
.venv/bin/kerf check my_joint
```

`kerf modules [name] --json` returns the same contract for tools. The first module, `servo_joint`, includes the
bench base, bracket, MG996R servo, horn and arm from `servo_link`, plus the off-board supply, jack and controller.
Its mount is the base in its own frame, its output is `arm.tip`, and its motion is the `swing` joint. It is a complete
starting assembly; attaching it to another design needs a new interface and checks for that assembled system.

The new folder is a normal Kerf project. The source's parameters, materials, purchased parts, load cases, safety
factors, fasteners, wiring and checks are preserved. Part helpers and the shared layout are copied too. Change the
new files normally; no symlinks or shared writable files tie them to the source. Existing projects are never replaced.

`MODULE.md` records the interfaces, limits and next steps. `module.json` records source hashes, source review status
at creation and the full historical review, including unresolved findings. `DESIGN.md` and `REFERENCES.md` are the
source documents. Review freshness in `kerf modules` is computed from the current source using the same rule as
`kerf review-status`; a historical PASS is not presented as current approval when its fingerprint has changed.

The copy excludes build output, caches, feedback, catalog-dependency records and `review.json`. An instance starts
unchecked and unreviewed even when its source has a current PASS. Run the complete check and build, inspect the
renders, and obtain a new independent review before calling it finished. Changes to a load, material, parameter,
attachment or surrounding assembly can invalidate the source's engineering assumptions.

## Adding a library entry

`catalog/modules.yaml` declares an entry's source project, title, description, file list, ports and limits. Extract
only from an existing reviewed design, and retain the complete contract needed for its use. List `project.yaml`,
the part files and every sibling helper, `DESIGN.md`, `REFERENCES.md`, and any referenced model assets in `imports/`
or `meshes/`. File paths must stay inside the source and cannot be symlinks. The loader rejects omitted part/layout
files or sibling Python helpers; the entry's integration test must exercise any other file dependencies.

Every entry needs a test that instantiates, builds and resolves its declared interfaces, and evaluates its relevant
requirements. Published limits must agree with the source design and its checks. Avoid copying only an attractive
part while dropping its support, fastening, power or strength assumptions.

Additional module families and combining multiple assemblies in one project remain future work; the initial
library does not claim arbitrary subassembly composition or approval of the current source geometry.
