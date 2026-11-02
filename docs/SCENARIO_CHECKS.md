# Check the scenario's quantities

Use ordinary `requirements:` entries so scenario checks appear in the same report, CLI and Studio cards as the
rest of the design. `reservoir_capacity` and `sensor_coverage` run with the early concept checks; `run_time` reuses
the existing electrical power tree. Neither new check requires a stress simulation.

```yaml
requirements:
  - id: trip_water
    check: reservoir_capacity
    volume: water_space       # a keep-out solid modeling the INTERNAL fluid volume
    daily_ml: 100             # replace with measured/sourced demand; illustrative here
    days: 14
    usable_fraction: 0.9      # explicitly allow for headspace/unpumpable water
    reserve_ml: 200
  - id: trip_power
    check: run_time
    min_min: 20160            # 14 days × 24 hours × 60 minutes
  - id: target_coverage
    check: sensor_coverage
    view: sensor_view         # an assembled view_cone keep-out, using the real sensor's field of view/range
    target: required_region   # a separate, nonzero-volume keep-out region
    min_fraction: 1           # every part of that region must be within the modeled frustum
    # pose: {pan: 20}         # optional named assembly joint pose
```

Run `.venv/bin/kerf req my_project trip_water trip_power target_coverage` while sizing; run the normal full check
before calling the assembly checked. A plastic tank's material volume or outer bounding box cannot be supplied as
its capacity: model the fluid space separately. One valid keep-out solid is required. Source the declared demand
and sensor dimensions/range; absent evidence cannot be inferred from the geometry.

For intermittent loads, replace `avg_a` with a duty description in the existing electrical draw override:

```yaml
electrical:
  draw:
    pump:
      duty: {active_a: 1, idle_a: 0.1, on_s: 15, period_s: 60}
      peak_a: 2
      why: "Replace these illustrative numbers with measurement/source and the intended operating schedule"
```

The average is `active_a × on_s / period_s + idle_a × (1 − on_s / period_s)`. The required explicit peak remains
in the supply/wire checks. Include the controller's standby current and all other loads: the power tree already
adds them and regulator losses. Inputs must be finite and nonnegative, the period positive, on-time no greater
than the period, and peak at least both active and idle current. Duty and an explicit average cannot both be set.

The following are **synthetic arithmetic examples**, not measurements or a completed E8 watering design:

| Quantity | Given | Result |
|---|---|---|
| Water | Internal region 100 × 100 × 200 mm; 90% usable; 200 mL reserve; 100 mL/day | 2000 × 0.9 − 200 = 1600 mL; lasts 16 days, exceeding 14 |
| Increased demand | Same region at 125 mL/day | Lasts 12.8 days; fails a 14-day trip |
| Duty current | 1 A active for 15 of every 60 s; 0.1 A idle; 2 A peak | Average 0.325 A, peak remains 2 A; this alone does not establish total runtime |
| Coverage | A 20 mm target cube extends from z=190 to 210; a wide-enough view cone ends at z=200 | 50% covered; fails the default requirement for the whole region |

Coverage is geometric volume intersection at the stated pose. It does not establish unobstructed visibility,
resolution, illumination, sensing range in real conditions, or detection probability. Normal fit checks catch
modeled objects inside the view cone; a real sensor still needs validation. Capacity does not prove pump delivery,
water tightness or actual plant demand. The real E8 remains open until its requirements, hardware, assembly and
independent review are complete; these synthetic tests are engine validation only.
