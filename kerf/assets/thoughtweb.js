/* Kerf Studio thought web: a growing map of how a design job explores (kerf/thoughtweb.py builds the graph from the
   job's visible actions and notes; this file only draws it). TW.mount(el, url, {live}) -> {stop()}.
   Core = your request; ideas branch off ideas they share words with; sources hang off the idea they serve; the plan's
   options glow when chosen and fade when set aside; the build trunk grows parts and tests. */
(function () {
  const css = `
.tw{position:relative;height:100%;min-height:300px;border-radius:12px;overflow:hidden;
  background:radial-gradient(ellipse at 50% 45%,rgba(60,130,255,.13),transparent 65%),#070b14;color:#cfe3ff;font:12px/1.3 system-ui,-apple-system,sans-serif}
.tw svg{position:absolute;inset:0;width:100%;height:100%}
.tw .grid{position:absolute;inset:0;background-image:linear-gradient(rgba(120,170,255,.06) 1px,transparent 1px),linear-gradient(90deg,rgba(120,170,255,.06) 1px,transparent 1px);background-size:28px 28px}
.tw .e{fill:none;stroke:#3d6fb8;stroke-opacity:.55;stroke-width:1.4}
.tw .e.set_aside{stroke:#5b6170;stroke-dasharray:3 4;stroke-opacity:.45}
.tw .e.chosen{stroke:#ffcf5a;stroke-opacity:.9;stroke-width:2.4}
.tw .e.build{stroke:#4fd18b;stroke-opacity:.7}
.tw .n circle{stroke-width:1.5;transition:r .4s}
.tw .n.core circle{fill:#1b4fd6;stroke:#9cc2ff;filter:url(#twglow)}
.tw .n.idea circle{fill:#123a7a;stroke:#6aa8ff}
.tw .n.source circle{fill:#0c1b33;stroke:#79e0ff}
.tw .n.decision circle,.tw .n.trunk circle{fill:#2a2150;stroke:#c7a6ff}
.tw .n.option circle{fill:#3a2f10;stroke:#ffcf5a}
.tw .n.build circle{fill:#0f3a26;stroke:#4fd18b}
.tw .n.active circle{animation:twpulse 1.6s ease-in-out infinite}
.tw .n.pursued circle{stroke-width:2.6}
.tw .n.chosen circle{fill:#5a4512;stroke:#ffdf7a;filter:url(#twglow)}
.tw .n.set_aside{opacity:.42}
.tw .n.set_aside circle{fill:#1a1d24;stroke:#6b7080;stroke-dasharray:2 2}
.tw .n text{fill:#d7e8ff;font-size:11px;paint-order:stroke;stroke:#070b14;stroke-width:3px;stroke-linejoin:round;pointer-events:none}
.tw .n.source text{fill:#9fdcf0;font-size:10px}
.tw .n.core text{font-size:13px;font-weight:700}
.tw .n.set_aside text{fill:#8d93a3;text-decoration:line-through}
.tw .n .why{fill:#9aa1b2;font-size:9.5px;text-decoration:none}
.tw.many .n.source:not(.active) text,.tw.many .n.build:not(.active) text{display:none}
.tw .n:hover text{display:inline}
.tw .n.new{animation:twgrow .7s cubic-bezier(.2,1.6,.4,1)}
.tw .pulse{fill:#bfe1ff;filter:url(#twglow)}
.tw .now{position:absolute;left:12px;right:12px;bottom:10px;padding:7px 10px;border-radius:9px;background:rgba(10,20,40,.78);
  border:1px solid rgba(110,160,255,.25);backdrop-filter:blur(4px);font-size:12.5px;display:flex;gap:8px;align-items:center}
.tw .now b{color:#fff}.tw .now .dot{width:8px;height:8px;border-radius:50%;background:#6aa8ff;box-shadow:0 0 10px #6aa8ff;flex:none}
.tw .legend{position:absolute;top:8px;left:10px;display:flex;gap:10px;flex-wrap:wrap;font-size:10.5px;color:#9db6d8}
.tw .legend i{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:4px;vertical-align:-1px}
.tw .tip{position:absolute;max-width:260px;padding:8px 10px;border-radius:9px;background:#0d1730;border:1px solid #2c4f8c;
  font-size:12px;pointer-events:none;opacity:0;transition:opacity .15s;z-index:3}
.tw .tip.on{opacity:1}.tw .tip small{display:block;color:#93a9c8;margin-top:4px}
.tw .replay{position:absolute;top:6px;right:10px;display:flex;gap:6px;align-items:center;font-size:11px;color:#9db6d8}
.tw .replay input{width:120px}.tw .replay button{background:#132648;color:#cfe3ff;border:1px solid #2c4f8c;border-radius:6px;padding:2px 8px;cursor:pointer}
.tw .empty{position:absolute;inset:0;display:grid;place-items:center;color:#7f97bb;font-size:13px}
.tw .disclaimer{position:absolute;right:10px;bottom:46px;font-size:9.5px;color:#61789b}
@keyframes twpulse{0%,100%{stroke-opacity:1}50%{stroke-opacity:.35}}
@keyframes twgrow{from{transform:scale(.1);opacity:0}to{transform:scale(1);opacity:1}}
@media (prefers-reduced-motion:reduce){.tw .n.active circle,.tw .n.new{animation:none}}`;
  if (!document.getElementById("twcss")) { const s = document.createElement("style"); s.id = "twcss"; s.textContent = css; document.head.appendChild(s); }

  const R = {core: 15, idea: 8, decision: 10, trunk: 9, option: 8, source: 4.5, build: 6};
  const LEN = {idea: 95, decision: 105, trunk: 105, option: 70, source: 52, build: 58};
  const VERB = {idea: "Exploring", source: "Looking at", decision: "Deciding", option: "Weighing", build: "Building", trunk: "Building", core: "Starting on"};
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
  const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;

  function mount(el, url, opt = {}) {
    el.innerHTML = `<div class="tw"><div class="grid"></div><svg><defs><filter id="twglow" x="-80%" y="-80%" width="260%" height="260%">
      <feGaussianBlur stdDeviation="3.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
      <g class="cam"><g class="edges"></g><g class="pulses"></g><g class="nodes"></g></g></svg>
      <div class="legend"><span><i style="background:#6aa8ff"></i>exploring</span><span><i style="background:#79e0ff"></i>reference</span>
      <span><i style="background:#ffcf5a"></i>chosen</span><span><i style="background:#6b7080"></i>set aside</span><span><i style="background:#4fd18b"></i>building</span></div>
      <div class="replay" hidden><button class="play">▶ Replay</button><input type="range" min="0" value="0"></div>
      <div class="tip"></div><div class="empty">Waiting for the first idea…</div>
      <div class="disclaimer">a simplified map of what it looked at and decided</div>
      <div class="now"><span class="dot"></span><span class="txt">Getting ready…</span></div></div>`;
    const root = el.querySelector(".tw"), svg = root.querySelector("svg"), cam = root.querySelector(".cam");
    const gE = root.querySelector(".edges"), gN = root.querySelector(".nodes"), gP = root.querySelector(".pulses");
    const tip = root.querySelector(".tip"), now = root.querySelector(".now .txt"), empty = root.querySelector(".empty");
    const rp = root.querySelector(".replay"), slider = rp.querySelector("input"), play = rp.querySelector(".play");
    const P = new Map();            // id -> {x,y,vx,vy,n,el,edge,touched}
    let data = {nodes: [], steps: 0}, stopped = false, timer = null, view = {x: -300, y: -200, w: 600, h: 400}, limit = Infinity;
    let pulses = [];

    function place(n) {
      const par = P.get(n.parent);
      if (!par) return {x: 0, y: 0};
      const gp = P.get(par.n.parent), base = gp ? Math.atan2(par.y - gp.y, par.x - gp.x) : Math.random() * 6.28;
      const a = base + (Math.random() - .5) * 1.6, d = (LEN[n.kind] || 70) * .6;
      return {x: par.x + Math.cos(a) * d, y: par.y + Math.sin(a) * d};
    }
    function sync() {
      const shown = data.nodes.filter(n => n.t <= limit);
      empty.style.display = shown.length > 1 ? "none" : "";
      const keep = new Set(shown.map(n => n.id));
      for (const [id, p] of P) if (!keep.has(id)) { p.el.remove(); p.edge && p.edge.remove(); P.delete(id); }
      for (const n of shown) {
        let p = P.get(n.id);
        if (!p) {
          const xy = place(n);
          p = {x: xy.x, y: xy.y, vx: 0, vy: 0, n, touched: n.touched};
          if (n.parent) { p.edge = document.createElementNS("http://www.w3.org/2000/svg", "path"); gE.appendChild(p.edge); }
          p.el = document.createElementNS("http://www.w3.org/2000/svg", "g");
          gN.appendChild(p.el);
          p.el.addEventListener("mouseenter", ev => showTip(p, ev)); p.el.addEventListener("mouseleave", () => tip.classList.remove("on"));
          p.fresh = true; P.set(n.id, p);
          if (n.parent) pulse(n.parent, n.id);
        } else if (n.touched > p.touched && n.parent) { pulse(n.parent, n.id); }
        p.touched = n.touched; p.n = n;
        const r = (R[n.kind] || 6) + Math.min(5, Math.log2(1 + (n.touches || 1)) * (n.kind === "idea" ? 1.3 : .4));
        const lab = n.kind === "source" ? n.label.slice(0, 34) : n.label.slice(0, 46);
        p.el.setAttribute("class", `n ${n.kind} ${n.state}${p.fresh ? " new" : ""}`);
        p.el.innerHTML = `<circle r="${r.toFixed(1)}"/><text x="${r + 4}" y="4">${esc(lab)}</text>` +
          (n.state === "set_aside" && n.reason ? `<text class="why" x="${r + 4}" y="16">set aside: ${esc(n.reason.slice(0, 50))}</text>` : "");
        if (p.edge) p.edge.setAttribute("class", `e ${n.state} ${n.kind === "build" || n.kind === "trunk" ? "build" : ""}`);
        setTimeout(() => { p.fresh = false; }, 800);
      }
      const last = [...shown].sort((a, b) => b.touched - a.touched || b.t - a.t)[0];
      if (last) now.innerHTML = `<b>${VERB[last.kind] || "Working on"}:</b> ${esc(last.label)}${last.notes && last.notes.length ? ` — <span style="color:#9fb6d6">${esc(last.notes[last.notes.length - 1])}</span>` : ""}`;
    }
    function pulse(from, to) { if (!calm) pulses.push({from, to, t: 0}); }
    function showTip(p, ev) {
      const n = p.n, b = root.getBoundingClientRect();
      tip.innerHTML = `<b>${esc(n.label)}</b>${n.url ? `<small>${esc(n.url)}</small>` : ""}${(n.notes || []).map(t => `<small>“${esc(t)}”</small>`).join("")}` +
        `<small>${{active: "being explored now", pursued: "pursued: it kept coming back to this", explored: "looked at", set_aside: "set aside" + (n.reason ? ": " + esc(n.reason) : ""), chosen: "chosen"}[n.state] || ""}</small>`;
      tip.style.left = Math.min(ev.clientX - b.left + 12, b.width - 270) + "px"; tip.style.top = (ev.clientY - b.top + 12) + "px";
      tip.classList.add("on");
    }
    function step() {
      const arr = [...P.values()];
      for (let i = 0; i < arr.length; i++) {                     // repulsion
        const a = arr[i];
        for (let k = i + 1; k < arr.length; k++) {
          const b = arr[k]; let dx = a.x - b.x, dy = a.y - b.y; const d2 = dx * dx + dy * dy + 0.01;
          if (d2 > 160000) continue;
          const f = 2200 / d2; a.vx += dx * f; a.vy += dy * f; b.vx -= dx * f; b.vy -= dy * f;
        }
      }
      for (const p of arr) {                                      // springs to the parent, core held at the centre
        const par = P.get(p.n.parent);
        if (par) { const dx = p.x - par.x, dy = p.y - par.y, d = Math.hypot(dx, dy) || 1, k = (d - (LEN[p.n.kind] || 70)) * .03;
          p.vx -= dx / d * k; p.vy -= dy / d * k; par.vx += dx / d * k * .3; par.vy += dy / d * k * .3; }
        else { p.vx -= p.x * .05; p.vy -= p.y * .05; }
      }
      let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9; const zoom = view.w / (svg.clientWidth || 600);
      root.classList.toggle("many", arr.length > 28);
      for (const p of arr) {
        p.vx *= .82; p.vy *= .82; p.x += Math.max(-8, Math.min(8, p.vx)); p.y += Math.max(-8, Math.min(8, p.vy));
        x0 = Math.min(x0, p.x); y0 = Math.min(y0, p.y); x1 = Math.max(x1, p.x + (p.n.kind === "source" ? 40 : 150) * zoom); y1 = Math.max(y1, p.y + 14 * zoom);
        p.el.setAttribute("transform", `translate(${p.x.toFixed(1)},${p.y.toFixed(1)}) scale(${zoom.toFixed(3)})`);   // same size on screen at any zoom
        const par = P.get(p.n.parent);
        if (p.edge && par) { const mx = (p.x + par.x) / 2 + (p.y - par.y) * .12, my = (p.y + par.y) / 2 - (p.x - par.x) * .12;
          p.edge.setAttribute("d", `M${par.x.toFixed(1)},${par.y.toFixed(1)} Q${mx.toFixed(1)},${my.toFixed(1)} ${p.x.toFixed(1)},${p.y.toFixed(1)}`); }
      }
      if (arr.length) {                                            // camera eases to fit everything
        const bw = svg.clientWidth || 600, bh = svg.clientHeight || 360, pad = 30 * zoom + 20;
        y1 += 40 * zoom;                                           // room above the caption bar
        let w = Math.max(320, x1 - x0 + pad * 2), h = Math.max(220, y1 - y0 + pad * 2);
        if (w / h > bw / bh) h = w * bh / bw; else w = h * bw / bh;
        const tx = (x0 + x1) / 2 - w / 2, ty = (y0 + y1) / 2 - h / 2;
        view.x += (tx - view.x) * .1; view.y += (ty - view.y) * .1; view.w += (w - view.w) * .1; view.h += (h - view.h) * .1;
        svg.setAttribute("viewBox", `${view.x.toFixed(1)} ${view.y.toFixed(1)} ${view.w.toFixed(1)} ${view.h.toFixed(1)}`);
      }
      gP.innerHTML = ""; const pr = (3 * zoom).toFixed(2);
      pulses = pulses.filter(q => q.t < 1);
      for (const q of pulses) {
        const a = P.get(q.from), b = P.get(q.to); q.t += .035; if (!a || !b) { q.t = 1; continue; }
        gP.insertAdjacentHTML("beforeend", `<circle class="pulse" r="${pr}" cx="${(a.x + (b.x - a.x) * q.t).toFixed(1)}" cy="${(a.y + (b.y - a.y) * q.t).toFixed(1)}"/>`);
      }
      if (!stopped) requestAnimationFrame(step);
    }
    async function load() {
      try {
        const r = await fetch(url); const d = await r.json();
        if (d.error) throw new Error(d.error);
        data = d;
        if (!d.live) { rp.hidden = false; slider.max = d.steps; if (limit === Infinity) slider.value = d.steps; }
        sync();
        if (d.live && !stopped) timer = setTimeout(load, 1500);
      } catch (e) { if (!stopped) timer = setTimeout(load, 4000); }
    }
    slider.oninput = () => { limit = +slider.value >= data.steps ? Infinity : +slider.value; sync(); };
    play.onclick = () => {
      let s = 0; limit = 0; P.forEach(p => { p.el.remove(); p.edge && p.edge.remove(); }); P.clear();
      const tick = () => { if (stopped) return; s += 1; slider.value = s; limit = s >= data.steps ? Infinity : s; sync(); if (s < data.steps) setTimeout(tick, 420); };
      tick();
    };
    requestAnimationFrame(step);
    load();
    return {stop() { stopped = true; clearTimeout(timer); }, refresh: load};
  }
  window.TW = {mount};
})();
