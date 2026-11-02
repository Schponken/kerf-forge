# Kerf: the end vision (Spencer, 2026-11-01)

**Describe the problem. Choose your depth. Print the solution.**

Kerf takes a scenario ("my plants die when I travel", "aerial shots of my trail runs", "a fun FPV wing I can crash")
or a direct design request and delivers a physical thing that works: real parts, simulated against how it will be
used, designed to break well, with its electronics, firmware and assembly guide, at whatever depth the user asks for.
Every PLAN.md item under "Kerf vision" moves toward this; pick work that closes the biggest gap first.

## 1. Selectable modes: run only what was asked

One project, one pipeline, different depths. A mode switches stages on or off; finishing a mode never throws work
away, and any result can be upgraded to a deeper mode later (the cache keeps what's done).

| Mode | Gives | Skips |
|---|---|---|
| Sketch | a 3D model to look at and tweak (viewer) | most checks, print prep, BOM |
| Print it | printable STL/3MF + A2L plates, fit checks | FEA, wiring, review |
| Check it | a fit / strength / balance / wiring report on a design the user brings (STEP or STL + a short yaml) | designing |
| Simulate it | motion, loads, flight / balance run through the use story | print files, BOM |
| Build kit | everything: files, priced BOM, wiring guide, assembly steps, firmware | nothing |
| Ship it | Build kit + independent review + printer loop (coupons -> measure -> adjust -> send to the A2L) | nothing |

**Ship it is opt-in only.** It is never the default, never chosen by Kerf on its own, and Studio asks for an explicit
click (it prints on the user's printer). Every mode states its usual time and cost before it starts.

## 2. Design from the use story, not the shape

- **Use story first**: who uses it, where, how often, what goes wrong (crashes, drops, heat, rain, gloves) - written
  into project.yaml and turned into requirements.
- **Simulate it moving**: dynamic load cases from the use story (crash / drop impulses, hard stops, vibration and
  resonance), not one static pose.
- **Know how it breaks**: per-part failure modes, designed weak links (the cheap part fails first), repair time.
- **Design for life**: fatigue of flexing parts, creep of loaded plastic, screws loosening under vibration, heat.
- **Optimise, then explain**: search the params for lighter / cheaper / faster within the checks; report trade-offs.
- **The person using it**: reach and access (battery swap with gloves), carrying, repair.
- **Learn from results**: flight logs, failure photos and notes feed back into the rules (`kerf feedback`).

## 3. Scenario in, solution out

- **Intake** asks only what changes the design (indoor/outdoor, life, budget, parts on hand, effort).
- **Options**, including buy-vs-build ("buy this, print one adapter" is a valid answer; check for existing / free
  designs first), compared on cost, build time, risk and fit to the scenario; one recommended, with reasons.
- **Proven modules** (power systems, servo joints, grippers, wing panels, motor mounts, enclosures, drive trains)
  extracted from finished projects, so a new scenario is mostly assembly of known-good pieces.
- **Whole system**: mechanics + electronics + firmware / controller tuned in sim + setup guide.
- **Checked against the scenario itself** ("away 10 days, 1 L tank" -> the water and battery last 10 days).

## 4. Wider reach

Conventional planes (tail sizing, landing gear) and VTOL; ground robots (wheels / tracks, tip-over on slopes,
self-balancing); strength-checked gearboxes (planetary, worm); mixed manufacturing (laser-cut / CNC / carbon plate
DXF for order services); watertight and thermal checks; a self-growing catalog (research a part, validate against the
vendor's STEP, add it with sources).

## Ground rules that do not change

Real numbers with sources, never a faked pass, every engine feature tested, finished and verified work over roadmaps
(CLAUDE.md). Budget: Spencer's cap is **60 % of the weekly usage**; see CLAUDE.md "Budget".
