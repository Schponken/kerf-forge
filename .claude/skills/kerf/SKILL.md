---
name: kerf
description: Design a complete 3D-printable mechanical assembly (drones, robot arms, brackets, grippers, enclosures, mechanisms) from a plain-language description, with verified fits, motion, strength and print files. Use when Spencer asks to design, model, make or print a part or a multi-part device.
argument-hint: "<what to build, in plain words>"
---

# kerf: description → engineered, printable assembly

You are the systems engineer. Turn the request into a finished Kerf project that passes `kerf build` and the
design-reviewer. Ask Spencer only about real choices that change the design (budget class, which actuators he
already owns, size limits), at most once, up front; otherwise decide and write down why.

## 0. Research first (design-researcher subagent → `projects/<name>/REFERENCES.md`)
Find proven open designs of the same kind of device, datasheets and vendor drawings for every purchased part, free
vendor STEP models, and the engineering rules of thumb that apply. Start from what works: borrow architecture,
proportions and known-good dimensions (with credit and license respect), avoid failure points others reported.
Every purchased-part number goes into the catalog with its source.

## 1. Understand and size (write `projects/<name>/DESIGN.md`)
- **Requirements** in numbers: what it does, loads/payloads, motion ranges, size limits, mass budget, environment.
- **Architecture options** (2-3 one-liners) and the pick with the reason.
- **Purchased parts** chosen from `catalog/hardware.json` with the sizing math shown (torque at worst pose with
  safety factor, thrust/weight, reach, speed). Missing hardware: research it, add it to the catalog with a source URL.
- **Part list**: each printed part, its job, material, print orientation, rough envelope.
- **Interface table**: every connection — part A, part B, interface type (bolt pattern / insert / nut trap / bearing
  seat / servo mount / horn mount / motor mount / pin), group name, screw size and count.
- **Joint tree** with ranges, and the coupled poses worth checking.
- **Requirements list** that will go into project.yaml (all numeric), including an `fea_static` check for every
  structural part (frames, arms, links, brackets, mounts that carry load) with the real load case and safety factor.
- **Assembly order**, step by step.

## 2. Contract (`projects/<name>/project.yaml`)
Write params, parts, purchased (catalog proxies), keepouts (prop discs, camera view, hands/fingers zones), the
assembly joint tree, allowed overlaps with reasons, sweeps/poses, and requirements. See docs/ARCHITECTURE.md.
Run `kerf check <name> --quick` with stub parts (simple blocks with the right joints) to prove the tree and the
interfaces line up before detailed geometry.

## 3. Parts in parallel
Launch one `part-designer` subagent per independent printed part in a single message, each with its contract:
envelope, interfaces (exact iface call + group + location), loads, print orientation. Parts that depend on each
other's geometry go to the same subagent.

## 4. Integrate
`kerf check <name>` until PASS. Fix every problem at the part that owns it. Never widen an allowed overlap or a
limit to make a check pass unless the physics says so (write why in DESIGN.md).

## 4b. Detail pass (once everything is green)
Turn a working design into a well-made one, re-checking after each change: fillets on every inside corner of a load
path, chamfered bed edges, cable routes and zip-tie points, weight-reduction pockets only where FEA shows margin,
part name/version embossed, screw access confirmed in assembly order, cosmetic shaping. Complex shapes are fine
(sweeps, lofts, shells, gears, threads, snap-fits via `kerf/features.py`); organic/cosmetic surfaces that CAD can't
reasonably express are noted for Spencer to generate with Meshy on his Mac.

## 5. Build and look
`kerf build <name>`. Read the assembly sheet, exploded sheet, keep-out render, every joint pose and every part sheet.
Fix anything that looks wrong even if the checks pass.

## 6. Independent review
Run the `design-reviewer` subagent on the project. Fix all blocker/major findings, rebuild, and review again until
PASS. `kerf review-status <name>` must be ok.

## 7. Deliver
Commit and push. Tell Spencer in plain words: what it is, the key numbers (mass, reach/thrust, margins), the BOM to
buy, the plates to print (`out/plates/*.3mf` — open in Bambu Studio), the assembly steps, and the known limits.
