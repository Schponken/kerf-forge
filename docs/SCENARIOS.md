# From a problem to a decision

In **New design**, choose **I have a problem to solve**. Explain what needs to change, what success looks like,
what matters most and how much hands-on work you can give it. The existing optional budget, power, environment,
parts-on-hand and use-story questions still apply. Leave unknown answers blank.

**Compare ways to solve it** uses the same signed-in Claude Code research job as architecture quotes; it uses your
Claude plan. It asks for 2–3 alternatives, including a ready-made solution and an adaptation or custom build.
Each alternative carries original research links, what those sources establish, fit to your goal, risks,
hands-on effort, next steps and the basis for cost and print-time estimates. Unknown costs/times display as unknown,
not zero. Delivery and setup effort belong in the explanation; print hours alone are not time to a working solution.

An unanswered question that could change the design appears under **Before choosing**. Add the answer above and
compare again. Assumptions remain visible but do not count as engineering evidence. Editing the request clears the
old selection; the server also checks the saved request before accepting an option. Reopening a finished quote
restores its original answers into an empty form without overwriting edits already entered.

A buy-only option has research links and next steps, with no design button. Kerf does not order anything. Adapting
or building starts the existing full design workflow with the selected evidence and risks included in its brief.
The server reads the saved option rather than trusting the card data sent by the browser. Printer actions still
require the separate, explicit Ship it flow.

## Quote files and compatibility

Quotes remain in `.cache/studio/quotes/<name>.json`. The original request/answers are saved beside them as
`<name>.request.json`, under the same job lock, so a duplicate click cannot erase an active quote. Older architecture
quotes remain readable. Scenario quotes use the additional contract in `.claude/skills/kerf/SKILL.md` and are checked
by `kerf.quotes.validate`: valid recommendation, both routes, finite nonnegative numbers or explained unknowns,
whole printed-part counts, fit/effort/risks/next steps, and HTTP(S) research links without embedded credentials.
Validation checks structure, not whether the model actually researched a page or whether a solution works.

## E8 status

The automated scenario fixture starts with **“my plants die when I travel”** and exercises intake, comparison,
unknown estimates, source links, selected-option handoff and decision guards. Its alternatives and `example.com`
links are clearly labelled illustrative test data. It is not a researched product recommendation or an E8 pass.

Still needed for full E8: run the real scenario research, settle trip duration/plant demand/location/water/power
constraints with the user, choose an evidence-backed solution, then complete its project checks, build, independent
review and scenario acceptance (including measured or sourced water demand, capacity and duty-cycle power).
The [scenario quantity checks](SCENARIO_CHECKS.md) cover modeled internal capacity, explicit electrical duty and
geometric sensor coverage; their synthetic examples do not complete E8.
Neither that run nor the separate scenario-requirement engine item is completed by the intake change.
