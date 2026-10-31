# Teardown: Adam-CAD/CADAM

Method as in text-to-cad.md. 2026-10-31, commit of 2026-10-14.

**What it is.** A hosted web app (Vite/React + Supabase, vercel.json) where a chat with an LLM (src/server/aiChat.ts,
1,726 lines, Anthropic models via @ai-sdk/anthropic at line 1) writes OpenSCAD-style parametric models shown in a
browser mesh viewer (src/server/mesh.ts 1,638 lines, src/utils/meshPrintProcessUtils.ts 1,291).
**Weight: medium tool**, ~42k code lines. **Licence: GPL-3.0**, copyleft: no code can be copied into Kerf.

**Verdict: SKIP.** One part at a time, no assemblies, fasteners, motion, strength or review; Kerf already does more, and
the licence blocks reuse. Worth taking regardless: nothing new; its parameter sliders are what Kerf Studio's Tune tab
already does.
