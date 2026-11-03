/* Kerf Studio "How Kerf decided": the story of a design job, told as a calm trail you can read top to bottom
   (kerf/thoughtweb.py builds the data from the job's visible actions and notes; this file only draws it).
     1 You asked  ->  2 What it looked into (each question, what it found, where)  ->  3 What it decided (options, chosen
     and set aside, and why)  ->  4 What it's building.
   Fixed layout: nothing moves except new items fading in, labels wrap instead of being cut or overlapping.
   TW.mount(el, url, {mode: "full" | "strip", job, onOpen, onResearch}) -> {stop(), refresh()}
     full : the whole trail; on a running job, questions can be steered (focus / skip) and a note sent (kerf/steer.py)
     strip: one compact line for the job panel (current step, counts, latest finding) with a button to open the trail */
(function () {
  const css = `
.twv{--tw-bg:var(--panel2,#1a1d23);--tw-card:var(--panel,#15171c);--tw-line:var(--line,#262a31);--tw-ink:var(--ink,#ecebe7);
  --tw-muted:var(--muted,#8d929b);--tw-info:var(--info,#6cb4ff);--tw-ok:var(--ok,#3ddc84);--tw-acc:var(--accent,#ff6a2b);
  color:var(--tw-ink);font:13.5px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif}
.twv.full{height:100%;display:flex;flex-direction:column;min-height:0}
.twv .twnow{display:flex;gap:9px;align-items:flex-start;padding:9px 12px;border-radius:10px;background:var(--tw-bg);border:1px solid var(--tw-line);margin-bottom:10px}
.twv .dot{width:9px;height:9px;border-radius:50%;background:var(--tw-info);flex:none;margin-top:5px}
.twv.live .dot{box-shadow:0 0 0 0 var(--tw-info);animation:twbeat 2s ease-out infinite}
.twv.over .dot{background:var(--tw-ok)}
.twv .scroll{flex:1;min-height:0;overflow:auto;padding-right:4px}
.twv ol.trail{list-style:none;margin:0;padding:0}
.twv .st{display:grid;grid-template-columns:30px minmax(0,1fr);gap:12px;position:relative;padding-bottom:16px}
.twv .st:not(:last-child)::before{content:"";position:absolute;left:14px;top:30px;bottom:0;width:2px;background:var(--tw-line)}
.twv .st.done:not(:last-child)::before{background:color-mix(in srgb,var(--tw-ok) 55%,transparent)}
.twv .num{width:30px;height:30px;border-radius:50%;display:grid;place-items:center;font-weight:700;font-size:13px;border:2px solid var(--tw-line);background:var(--tw-card);color:var(--tw-muted)}
.twv .st.done .num{border-color:var(--tw-ok);color:var(--tw-ok)}
.twv .st.cur .num{border-color:var(--tw-info);color:var(--tw-info)}
.twv .st.next{opacity:.62}
.twv h4{margin:4px 0 2px;font-size:15px}.twv h4 .cnt{font-weight:500;font-size:12.5px;color:var(--tw-muted);margin-left:6px}
.twv .hint{margin:0 0 8px;color:var(--tw-muted);font-size:12.5px}
.twv .ask{margin:2px 0 0;font-size:14px}
.twv .twc{background:var(--tw-card);border:1px solid var(--tw-line);border-radius:11px;padding:10px 12px;margin:0 0 8px}
.twv .twc.s-active{border-color:color-mix(in srgb,var(--tw-info) 60%,var(--tw-line))}
.twv .twc.s-set_aside,.twv .opt.aside{opacity:.72}
.twv .qh{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}.twv .qt{font-weight:600;overflow-wrap:anywhere}
.twv .badge{font-size:11px;font-weight:600;padding:1px 7px;border-radius:20px;white-space:nowrap;border:1px solid var(--tw-line);color:var(--tw-muted)}
.twv .b-active{color:var(--tw-info);border-color:color-mix(in srgb,var(--tw-info) 50%,transparent)}
.twv .b-pursued{color:var(--tw-acc);border-color:color-mix(in srgb,var(--tw-acc) 50%,transparent)}
.twv .b-chosen{color:var(--tw-ok);border-color:color-mix(in srgb,var(--tw-ok) 55%,transparent)}
.twv .found{margin:6px 0 0;font-size:13px}.twv .found span{color:var(--tw-muted)}
.twv .why{margin:5px 0 0;font-size:12.5px;color:var(--tw-muted)}
.twv .srcs{display:flex;flex-wrap:wrap;gap:5px;margin-top:7px}
.twv .src{font-size:11.5px;padding:2px 8px;border-radius:7px;background:var(--tw-bg);border:1px solid var(--tw-line);color:var(--tw-ink);text-decoration:none;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.twv a.src:hover{border-color:var(--tw-info)}
.twv .more{font-size:11.5px;padding:2px 8px;border-radius:7px}
.twv .fups{margin:8px 0 0;padding-left:10px;border-left:2px solid var(--tw-line)}
.twv .fu{margin:0 0 6px}.twv .fu .lead{color:var(--tw-muted);font-size:12px}
.twv .opt{border-left:3px solid var(--tw-line)}.twv .opt.chosen{border-left-color:var(--tw-ok)}
.twv .from{margin-top:5px;font-size:12px;color:var(--tw-muted)}.twv .from a{color:var(--tw-info);cursor:pointer}
.twv .st>div{min-width:0}.twv .steps{list-style:none;margin:0;padding:0}.twv .steps .srcs{margin-top:4px}.twv .steps li{padding:3px 0;display:grid;grid-template-columns:16px minmax(0,1fr);gap:8px}.twv .steps .ic{width:16px;text-align:center;color:var(--tw-ok)}
.twv .steps li.active .ic{color:var(--tw-info)}
.twv .pending{color:var(--tw-muted);font-size:12.5px;margin:2px 0 0}
.twv .steer{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-top:8px}
.twv .steer button{font-size:12px;padding:3px 10px;border-radius:8px}
.twv .steer button.on{border-color:var(--tw-acc);color:var(--tw-acc)}
.twv .sd{font-size:11.5px;color:var(--tw-muted)}
.twv .tell{display:flex;gap:6px;margin-top:8px}.twv .tell input{flex:1;min-width:0;font:inherit;padding:7px 10px;border-radius:9px;border:1px solid var(--tw-line);background:var(--tw-card);color:var(--tw-ink)}
.twv .foot{font-size:11px;color:var(--tw-muted);margin-top:6px;display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;align-items:center}
.twv .flash{outline:2px solid var(--tw-info);outline-offset:2px}
.twv .new{animation:twin .5s ease-out both}
.twv.strip{display:flex;gap:10px;align-items:center;padding:8px 12px;border-radius:11px;background:var(--tw-bg);border:1px solid var(--tw-line);cursor:pointer}
.twv.strip .sl{flex:1;min-width:0}.twv.strip .l1{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.twv.strip .l2{font-size:12px;color:var(--tw-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.twv.strip button{flex:none;font-size:12.5px;padding:5px 11px}
@keyframes twin{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
@keyframes twbeat{0%{box-shadow:0 0 0 0 color-mix(in srgb,var(--tw-info) 60%,transparent)}100%{box-shadow:0 0 0 9px transparent}}
@media (prefers-reduced-motion:reduce){.twv .new,.twv.live .dot{animation:none}}`;
  if (!document.getElementById("twcss")) { const s = document.createElement("style"); s.id = "twcss"; s.textContent = css; document.head.appendChild(s); }

  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const KNOWN = "What Kerf already knows";
  const STATE = {active: ["Looking now", "b-active"], pursued: ["Kept coming back to it", "b-pursued"], explored: ["Looked at", ""],
                 set_aside: ["Not pursued", ""], chosen: ["Chosen", "b-chosen"]};
  const VERB = {idea: "Looking into", source: "Reading", decision: "Deciding", option: "Weighing", build: "Building", trunk: "Building", core: "Starting on"};
  const SHOW_SRC = 6;

  /* the job's graph -> the four steps of the story */
  function model(d, limit) {
    const nodes = (d.nodes || []).filter(n => n.t <= limit), by = new Map(nodes.map(n => [n.id, n]));
    const kids = new Map(); for (const n of nodes) { if (!kids.has(n.parent)) kids.set(n.parent, []); kids.get(n.parent).push(n); }
    const of = (id, kind) => (kids.get(id) || []).filter(n => n.kind === kind);
    const core = nodes.find(n => n.kind === "core");
    const top = core ? of(core.id, "idea") : [];
    const known = top.find(n => n.label === KNOWN);
    const questions = top.filter(n => n !== known).map(q => {
      const fups = [], stack = of(q.id, "idea");
      while (stack.length) { const f = stack.shift(); fups.push(f); stack.push(...of(f.id, "idea")); }
      return {q, fups, srcs: of(q.id, "source")};
    });
    const decision = nodes.find(n => n.kind === "decision");
    const options = nodes.filter(n => n.kind === "option").sort((a, b) => (b.state === "chosen") - (a.state === "chosen") || a.t - b.t);
    const trunk = nodes.find(n => n.kind === "trunk"), builds = trunk ? of(trunk.id, "build") : [];
    const nsrc = nodes.filter(n => n.kind === "source").length;
    const stage = !d.live ? "over" : builds.length || trunk ? "build" : decision ? "decide" : "research";
    const last = [...nodes].filter(n => n.kind !== "core").sort((a, b) => b.touched - a.touched || b.t - a.t)[0];
    const finding = [...nodes].filter(n => (n.notes || []).length).sort((a, b) => b.touched - a.touched)[0];
    return {nodes, by, of, core, known, questions, decision, options, trunk, builds, nsrc, stage, last, finding};
  }
  const plural = (n, w) => `${n} ${w}${n === 1 ? "" : "s"}`;

  function mount(el, url, opt = {}) {
    const strip = opt.mode === "strip";
    el.innerHTML = strip ? `<div class="twv strip" title="See how Kerf is researching and deciding"><span class="dot"></span><div class="sl"><div class="l1">Getting ready…</div><div class="l2"></div></div><button class="open">How it's deciding ⤢</button></div>`
      : `<div class="twv full"><div class="twnow"><span class="dot"></span><div class="nowt">Loading…</div></div><div class="scroll"><ol class="trail"></ol>
         <div class="tellbox" hidden><div class="tell"><input maxlength="500" placeholder="Tell Kerf something, e.g. “keep it under 200 g” or “look at folding-wing gliders”"><button class="send">Send</button></div>
         <div class="foot"><span>Kerf reads it at its next step. It doesn't pause, restart or cost an extra turn.</span></div></div>
         <div class="foot"><span>Built only from what Kerf did and wrote down (searches, pages, its notes and its plan), not hidden thinking.</span><span class="rp" hidden><button class="play">▶ Replay</button></span></div></div></div>`;
    const root = el.querySelector(".twv");
    let data = {nodes: [], steps: 0}, sig = "", stopped = false, timer = null, limit = Infinity, researched = false;
    const seen = new Set(), open = new Set();
    let first = true;

    function steerOf(id) { const e = (data.steer || []).filter(x => x.node === id && x.action !== "note").pop(); return e; }
    function steerUi(n) {
      if (!data.steerable) return "";
      const e = steerOf(n.id), st = e ? `<span class="sd">You: ${e.action === "focus" ? "focus on this" : "skip this"} · ${e.delivered ? "Kerf has it ✓" : "it reads this at its next step"}</span>` : "";
      return `<div class="steer"><button data-steer="focus" data-node="${n.id}" class="${e && e.action === "focus" ? "on" : ""}">Focus on this</button>` +
        `<button data-steer="skip" data-node="${n.id}" class="${e && e.action === "skip" ? "on" : ""}">Skip this</button>${st}</div>`;
    }
    const nw = n => { const f = !first && !seen.has(n.id); seen.add(n.id); return f ? " new" : ""; };
    function srcs(list, key) {
      if (!list.length) return "";
      const all = open.has(key), shown = all ? list : list.slice(0, SHOW_SRC);
      return `<div class="srcs">${shown.map(s => /^https?:\/\//.test(s.url || "") ?
        `<a class="src${nw(s)}" href="${esc(s.url)}" target="_blank" rel="noopener" title="${esc(s.url)}">${esc(s.label)}</a>` :
        `<span class="src${nw(s)}" title="${esc(s.label)}">${esc(s.label)}</span>`).join("")}` +
        (list.length > SHOW_SRC ? `<button class="more" data-more="${key}">${all ? "show fewer" : `+${list.length - SHOW_SRC} more`}</button>` : "") + `</div>`;
    }
    let cur = null;   // the one question it is on right now; other recent ones read "looked at"
    const st = n => n.state === "active" && !(data.live && n.id === cur) ? "explored" : n.state;
    function badge(n) { const [t, c] = STATE[st(n)] || ["", ""]; return t ? `<span class="badge ${c}">${t}</span>` : ""; }
    function found(n) {
      const notes = (n.notes || []).slice(-2);
      const why = n.state === "set_aside" && n.reason ? `<div class="why">Why not: ${esc(n.reason)}</div>` : "";
      return notes.map(t => `<div class="found"><span>Found:</span> ${esc(t)}</div>`).join("") + why;
    }
    function question({q, fups, srcs: s}, m) {
      const fu = fups.map(f => `<div class="fu${nw(f)}"><div class="qh"><span class="lead">↳ then asked</span><span class="qt">${esc(f.label)}</span>${badge(f)}</div>${found(f)}${srcs(m.of(f.id, "source"), f.id)}</div>`).join("");
      return `<div class="twc q s-${[q, ...fups].some(f => st(f) === "active") ? "active" : st(q)}${nw(q)}" data-id="${q.id}"><div class="qh">${badge(q)}<span class="qt">${esc(q.label)}</span>` +
        `<span class="badge">${plural(s.length + fups.reduce((a, f) => a + m.of(f.id, "source").length, 0), "source")}</span></div>` +
        `${found(q)}${srcs(s, q.id)}${fu ? `<div class="fups">${fu}</div>` : ""}${m.decision ? "" : steerUi(q)}</div>`;
    }
    function render(m) {
      const live = !!data.live;
      root.classList.toggle("live", live); root.classList.toggle("over", !live);
      const ideas = m.nodes.filter(n => n.kind === "idea" && n.label !== KNOWN).sort((a, b) => b.touched - a.touched || b.t - a.t);
      cur = live && m.stage === "research" && ideas[0] ? ideas[0].id : null;
      const nowt = live ? (m.last ? `<b>Now · ${VERB[m.last.kind] || "Working on"}:</b> ${esc(m.last.label)}` : "<b>Starting…</b>")
        : `<b>How this design was decided.</b> Read it top to bottom: what you asked, what it researched, what it chose and why, what it built.`;
      if (strip) {
        const word = {research: "Researching", decide: "Deciding", build: "Building", over: "Finished"}[m.stage];
        root.querySelector(".l1").innerHTML = `<b>${word}</b> · ${esc(m.last ? m.last.label : "starting")}`;
        root.querySelector(".l1").title = m.last ? m.last.label : "";
        const chosen = m.options.find(o => o.state === "chosen");
        root.querySelector(".l2").textContent = [plural(m.questions.length, "question"), plural(m.nsrc, "source"),
          chosen ? `chose: ${chosen.label}` : m.finding ? `found: ${m.finding.notes[m.finding.notes.length - 1]}` : ""].filter(Boolean).join(" · ");
        return;
      }
      root.querySelector(".nowt").innerHTML = nowt;
      const cls = k => { const order = ["research", "decide", "build", "over"], i = order.indexOf(m.stage), j = order.indexOf(k);
        return i === 3 || j < i ? "done" : j === i ? "cur" : "next"; };
      const opts = m.options.map(o => {
        const from = o.based_on && m.by.get(o.based_on);
        return `<div class="twc opt ${o.state === "chosen" ? "chosen" : "aside"}${nw(o)}"><div class="qh">${o.state === "chosen" ? `<span class="badge b-chosen">✓ Chosen</span>` : `<span class="badge">Set aside</span>`}<span class="qt">${esc(o.label)}</span></div>` +
          (o.reason ? `<div class="why">${o.state === "chosen" ? "Why: " : "Why not: "}${esc(o.reason)}</div>` : "") +
          (from ? `<div class="from">Came out of: <a data-goto="${from.id}">${esc(from.label)}</a></div>` : "") + `</div>`;
      }).join("");
      const research = m.questions.map(x => question(x, m)).join("") +
        (m.known ? `<div class="twc q${nw(m.known)}" data-id="${m.known.id}"><div class="qh"><span class="qt">Checked what Kerf already knows</span><span class="badge">${plural(m.of(m.known.id, "source").length, "source")}</span></div>` +
          `<div class="why">Its past builds, the parts catalog with real sizes, and its engineering rule books.</div>${srcs(m.of(m.known.id, "source"), m.known.id)}</div>` : "");
      const lastB = m.builds[m.builds.length - 1], groups = [];   // parts drawn one after another read as one step
      for (const b of m.builds) { const part = /^Drawing the /.test(b.label), g = groups[groups.length - 1];
        if (part && g && g.parts) g.items.push(b); else groups.push({parts: part, items: [b]}); }
      const stepLi = g => { const act = live && g.items.includes(lastB), ic = `<span class="ic">${act ? "●" : "✓"}</span>`;
        if (!g.parts) return `<li class="${act ? "active" : ""}${nw(g.items[0])}">${ic}<span>${esc(g.items[0].label)}</span></li>`;
        g.items.forEach(nw);
        return `<li class="${act ? "active" : ""}">${ic}<span>${act ? "Drawing" : "Drew"} ${plural(g.items.length, "part")}<div class="srcs">${g.items.map(b =>
          `<span class="src">${esc(b.label.replace(/^Drawing the /, ""))}</span>`).join("")}</div></span></li>`; };
      root.querySelector(".trail").innerHTML = `
        <li class="st done"><div class="num">1</div><div><h4>You asked</h4><p class="ask">${esc((m.core ? m.core.detail || m.core.label : data.label || "").replace(/^New design:\s*/, ""))}</p></div></li>
        <li class="st ${cls("research")}"><div class="num">2</div><div><h4>What it looked into<span class="cnt">${plural(m.questions.length, "question")} · ${plural(m.nsrc, "source")}</span></h4>
          <p class="hint">Each card is one question it researched: what it found, and the pages and past builds it read.${data.steerable && !m.decision ? " Steer it with Focus / Skip while it is still researching." : ""}</p>
          ${research || `<p class="pending">${live ? "Starting the research…" : "No research was recorded for this design."}</p>`}</div></li>
        <li class="st ${cls("decide")}"><div class="num">3</div><div><h4>What it decided${m.options.length ? `<span class="cnt">${plural(m.options.length, "option")} weighed</span>` : ""}</h4>
          ${opts || (m.decision ? `<p class="pending">It wrote its plan (DESIGN.md) without listing alternatives.</p>` :
            `<p class="pending">Comes after the research: it weighs a few ways to build it and says why it picks one.</p>`)}</div></li>
        <li class="st ${cls("build")}"><div class="num">4</div><div><h4>What it's building${groups.length ? `<span class="cnt">${plural(groups.length, "step")}</span>` : ""}</h4>
          ${m.builds.length ? `<ul class="steps">${groups.map(stepLi).join("")}</ul>`
            : `<p class="pending">Comes after the plan: it draws each part, then tests that everything fits, moves and holds.</p>`}</div></li>`;
      root.querySelector(".tellbox").hidden = !data.steerable;
      root.querySelector(".rp").hidden = live || !(data.steps > 1);
    }
    function draw(force) {
      const s = JSON.stringify([data, limit === Infinity ? -1 : limit, [...open]]);
      if (s === sig && !force) return;
      sig = s;
      const m = model(data, limit);
      if (!researched && (m.questions.length || m.known || m.decision || m.trunk)) { researched = true; opt.onResearch && opt.onResearch(); }
      render(m); first = false;
    }
    async function load() {
      try {
        const r = await fetch(url), d = await r.json();
        if (d.error) throw new Error(d.error);
        data = d; draw();
        if (d.live && !stopped) timer = setTimeout(load, strip ? 2500 : 1500);
      } catch (e) { if (!stopped) timer = setTimeout(load, 4000); }
    }
    async function steer(body) {
      try {
        const r = await fetch("/api/steer", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({job: opt.job, ...body})});
        const d = await r.json(); if (d.error) throw new Error(d.error);
        clearTimeout(timer); load(); return true;
      } catch (e) { (window.toast || alert)("Couldn't steer", e.message, "bad"); return false; }
    }
    root.addEventListener("click", ev => {
      const b = ev.target.closest("button, a[data-goto]");
      if (strip) { if (opt.onOpen) opt.onOpen(); return; }
      if (!b) return;
      if (b.dataset.more) { open.has(b.dataset.more) ? open.delete(b.dataset.more) : open.add(b.dataset.more); draw(true); }
      else if (b.dataset.steer) { const n = data.nodes.find(x => x.id === b.dataset.node); if (n) steer({action: b.dataset.steer, node: n.id, label: n.label}); }
      else if (b.dataset.goto) { const c = root.querySelector(`[data-id="${b.dataset.goto}"]`); if (c) { c.scrollIntoView({block: "center", behavior: "smooth"}); c.classList.add("flash"); setTimeout(() => c.classList.remove("flash"), 1400); } }
      else if (b.classList.contains("send")) sendNote();
      else if (b.classList.contains("play")) replay();
    });
    async function sendNote() {
      const i = root.querySelector(".tell input"), t = i.value.trim(); if (!t) return;
      if (await steer({action: "note", text: t})) { i.value = ""; (window.toast || (() => {}))("Sent to Kerf", "It reads this at its next step.", "ok"); }
    }
    if (!strip) root.querySelector(".tell input").addEventListener("keydown", e => { if (e.key === "Enter") sendNote(); });
    function replay() {   // grow the finished story again, one recorded step at a time
      const ts = [...new Set(data.nodes.map(n => n.t))].sort((a, b) => a - b); let i = 0; seen.clear(); first = false;
      const tick = () => { if (stopped) return; limit = i < ts.length - 1 ? ts[i] : Infinity; draw(); i += 1; if (i < ts.length) setTimeout(tick, 380); };
      tick();
    }
    load();
    return {stop() { stopped = true; clearTimeout(timer); }, refresh: load};
  }
  window.TW = {mount};
})();
