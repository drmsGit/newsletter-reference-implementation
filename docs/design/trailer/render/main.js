"use strict";
// Boot and the single entry point the renderer calls: render(T) draws the film at time T (seconds) and nothing else.
let STAGE, CAP, BLACK;
const CAPTIONS_ON = !/caps=0/.test(location.search);
async function boot() {
  D = await (await fetch("data/timeline.json")).json();
  await Promise.all([...new Set([...Object.keys(FALLBACK), ...EXTRA])].map(loadCapture));
  DEFS.sort((x, y) => scene(x.id).start - scene(y.id).start);
  STAGE = document.getElementById("stage");
  CAP = document.getElementById("cap");
  for (const def of DEFS) {
    def.s = scene(def.id);
    def.root = mk("div", "scene " + def.cls, null);
    STAGE.insertBefore(def.root, CAP);
    CUR = def.s;
    def.upd = def.build(def.root, def.s);
  }
  BLACK = mk("div", "abs", STAGE, { left: 0, top: 0, width: "1920px", height: "1080px", background: "#000", opacity: 0, zIndex: 60, pointerEvents: "none" });
  await Promise.all([...document.images].map(i => (i.decode ? i.decode().catch(() => {}) : null)));
  return true;
}
function render(T) {
  DEFS.forEach((def, i) => {
    const s = def.s, next = DEFS[i + 1];
    const endVis = next ? next.s.start + next.fade : s.end + 1;
    const vis = T >= s.start && T < endVis;
    def.root.style.display = vis ? "block" : "none";
    if (!vis) return;
    def.root.style.opacity = def.fade > 0 ? ease(T, s.start, s.start + def.fade) : 1;
    def.upd(T, T - s.start);
  });
  const c = CAPTIONS_ON ? D.cues.find(c => T >= c.s && T < c.e) : null;
  CAP.innerHTML = c ? `<span>${esc(c.t)}</span>` : "";
  BLACK.style.opacity = ease(T, D.total - 0.6, D.total);
}
window.__ready = boot();
window.render = render;
