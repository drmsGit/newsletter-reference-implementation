"use strict";
// Framework, the hook (S01), the idea (S02 to S04). Loaded after lib.js.
const PET = "#1a5d74", INK = "#1f1b16", MUTED = "#62594e", LINE = "#e4daca", LINEN = "#fcf8f2";
const DEFS = [];
const defScene = (id, cls, fade, build) => DEFS.push({ id, cls, fade, build });
const fadeWin = (T, a, b, fi = 0.3, fo = 0.3) => ease(T, a, a + fi) * (1 - ease(T, b - fo, b));
const text = (parent, str, css, cls = "") => { const e = mk("div", "abs " + cls, parent, css); e.textContent = str; return e; };

// ---------------------------------------------------------------- shots: one capture, a camera move, a cursor, rings
function mkShot(root, o) {
  const box = mk("div", "abs", root, { left: 0, top: 0, width: "1920px", height: "1080px" });
  const L = layer(box, o.id, { shadow: o.shadow !== false && !o.crop });
  if (o.crop) crop(L, ...o.crop);
  const rings = (o.rings || []).map(r => Object.assign({}, r, { el: ring(L, r.x, r.y, r.w, r.h) }));
  if (o.draw) o.draw(L.wrap);
  const cur = o.cursor ? cursorEl(box) : null;
  if (o.cursor && CUR) for (const q of o.cursor) if (q[3]) EVENTS.push(CUR.start + q[0]);
  return { o, box, L, rings, cur };
}
function updShot(sh, t) {
  const o = sh.o, hold = o.hold === undefined ? 0.4 : o.hold;
  const vis = t >= o.a && t < o.b + hold;
  sh.box.style.display = vis ? "block" : "none";
  if (!vis) return;
  sh.box.style.opacity = o.fade === 0 ? 1 : ease(t, o.a, o.a + (o.fade === undefined ? 0.35 : o.fade));
  const f = o.from, e = o.to || o.from, k = (o.lin ? prog : ease)(t, o.a, o.b);
  const syv = lerp(o.sy || 540, o.sy2 !== undefined ? o.sy2 : (o.sy || 540), k);
  cam(sh.L, lerp(f[0], e[0], k), lerp(f[1], e[1], k), lerp(f[2], e[2], k), o.sx || 960, syv, o.clamp !== false && !o.crop);
  for (const r of sh.rings) r.el.set(ease(t, r.a, r.a + 0.25) * (1 - ease(t, r.b, r.b + 0.25)));
  if (sh.cur) {
    const p = o.cursor, t0 = p[0][0], t1 = p[p.length - 1][0];
    if (t < t0 || t > t1 + 0.6) { sh.cur.style.opacity = 0; return; }
    let i = 0;
    while (i < p.length - 2 && t > p[i + 1][0]) i++;
    const A = p[i], B = p[Math.min(i + 1, p.length - 1)];
    const kk = B[0] > A[0] ? ease(t, A[0], B[0]) : 1;
    const x = lerp(A[1], B[1], kk), y = lerp(A[2], B[2], kk);
    const [sx, sy] = toStage(sh.L, x, y);
    // a press: the cursor dips for 0.18 s at every key that carries a 4th value of 1
    let down = 0;
    for (const q of p) if (q[3] && t > q[0] && t < q[0] + 0.18) down = 1 - Math.abs((t - q[0]) / 0.09 - 1);
    sh.cur.style.opacity = t > t1 + 0.3 ? 1 - ease(t, t1 + 0.3, t1 + 0.6) : 1;
    sh.cur.at(sx, sy, down);
  }
}
// A scene made of shots (the manager's screens). o.extra(root) may add overlays; returns update(T, t).
function shotScene(root, s, shots, extra, cutFirst = false) {
  const list = shots.map(o => mkShot(root, o));
  shots.forEach((o, i) => { if (CUR && (i ? o.id !== shots[i - 1].id : cutFirst)) EVENTS.push(CUR.start + o.a); });
  const ex = extra ? extra(root, s) : null;
  return (T, t) => { for (const sh of list) updShot(sh, t); if (ex) ex(T, t); };
}
// A burned-in label on a manager screen: a white pill with a petrol rule, top centre.
function pill(root, str, a, b, css = {}) {
  const e = mk("div", "abs", root, Object.assign({ left: 0, right: 0, top: "56px", textAlign: "center", pointerEvents: "none", opacity: 0 }, css));
  const i = mk("span", "", e, { display: "inline-block", background: "#fff", border: `2px solid ${PET}`, borderRadius: "999px", padding: "12px 34px",
    font: "600 40px var(--font)", color: INK, boxShadow: "0 10px 30px rgba(40,30,20,.18)" });
  i.textContent = str;
  return T => { e.style.opacity = fadeWin(T, a, b, 0.35, 0.35); };
}

// ---------------------------------------------------------------- S01 · the question (black)
defScene("S01", "black", 0, (root, s) => {
  const shots = shotScene(root, s, [
    { id: "c01-deliveries-list", a: 0, b: 3.9, fade: 0, from: [420, 99, 2.0], to: [420, 99, 2.18], sy: 450, crop: [244, 64, 602, 136], shadow: false,
      rings: [{ x: 286, y: 106, w: 30, h: 22, a: 2.8, b: 3.7 }] },
    { id: "c02-slot-list", a: 3.7, b: 6.8, fade: 0.15, from: [420, 425, 2.0], to: [420, 425, 2.18], sy: 450, crop: [244, 394, 602, 460], shadow: false,
      rings: [{ x: 528, y: 432, w: 68, h: 26, a: 5.6, b: 6.6 }] },
    { id: "c04-as-sent", a: 6.6, b: 8.6, fade: 0.15, from: [1025, 806, 1.12], to: [1025, 806, 1.22], crop: [650, 484, 1400, 1129], shadow: false, hold: 0.05 },
  ]);
  const lines = [
    ["One campaign.", 1.15, 2.95], ["123 readers.", 2.95, 5.75], ["369 choices.", 5.75, 6.65],
  ].map(([str, a, b]) => ({ a, b, el: text(root, str, { left: 0, right: 0, top: "700px", textAlign: "center", font: "650 76px var(--font)", color: "#f4eee6", letterSpacing: "-.01em" }) }));
  lines.forEach(l => (l.el.style.opacity = 0));
  const q = text(root, "Could you say why?", { left: 0, right: 0, top: "470px", textAlign: "center", font: "650 112px var(--font)", color: "#f4eee6", letterSpacing: "-.015em", opacity: 0 });
  const flash = mk("div", "abs", root, { left: 0, top: 0, width: "1920px", height: "1080px", background: "#fff", opacity: 0, pointerEvents: "none" });
  const hits = [3.0, 5.8, 8.6];
  return (T, t) => {
    shots(T, t);
    lines.forEach(l => (l.el.style.opacity = fadeWin(t, l.a, l.b, 0.2, 0.15)));
    q.style.opacity = fadeWin(t, 8.6, 13.4, 0.5, 0.6);
    let f = 0;
    for (const h of hits) if (t >= h) f = Math.max(f, 0.10 * Math.exp(-(t - h) * 9));
    flash.style.opacity = f;
  };
});

// ---------------------------------------------------------------- S02 · two ends of the market (linen)
const lockSvg = (w, col) => `<svg width="${w}" height="${w}" viewBox="0 0 24 24" fill="none" stroke="${col}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>`;
const keySvg = (w, col) => `<svg width="${w}" height="${w}" viewBox="0 0 24 24" fill="none" stroke="${col}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M16 7l3 3M14 9l2 2"/></svg>`;

defScene("S02", "light", 0.9, (root, s) => {
  const left = mk("div", "abs", root, { left: 0, top: 0, width: "1000px", height: "1080px" });
  const right = mk("div", "abs", root, { left: "960px", top: 0, width: "960px", height: "1080px" });
  // the box of locked slots: 3 x 3, centred at (500, 540)
  const box = mk("div", "abs", left, { left: "340px", top: "380px", width: "320px", height: "320px", border: `3px solid ${LINE}`, borderRadius: "26px", background: "#fff" });
  const slots = [];
  for (let i = 0; i < 9; i++) {
    const r = Math.floor(i / 3), c = i % 3;
    const e = mk("div", "abs", box, { left: (22 + c * 98) + "px", top: (22 + r * 98) + "px", width: "82px", height: "82px", borderRadius: "14px", background: "#f3ecdf", border: `2px solid ${LINE}`, opacity: 0 });
    if (i === 4) e.innerHTML = `<div style="position:absolute;left:19px;top:19px">${lockSvg(44, PET)}</div>`;
    slots.push(e);
  }
  const lt = text(left, "Easy, until you outgrow it.", { left: "140px", width: "720px", top: "800px", textAlign: "center", font: "500 40px var(--font)", color: INK, opacity: 0 });
  // the tower: blocks that climb out of the top
  const greys = ["#d6cebf", "#c4baa8", "#b0a592", "#cdc4b3", "#a89d8a", "#bdb2a0"];
  const blocks = [];
  for (let i = 0; i < 13; i++) {
    const w = [260, 200, 300, 220, 280, 190][i % 6], dx = [0, 26, -20, 40, -34, 14][i % 6];
    blocks.push(mk("div", "abs", right, { left: (480 - w / 2 + dx) + "px", top: (730 - i * 72) + "px", width: w + "px", height: "66px", borderRadius: "10px", background: greys[i % 6], opacity: 0 }));
  }
  const rt = text(right, "Powerful, until you try to change it.", { left: "60px", width: "840px", top: "800px", textAlign: "center", font: "500 40px var(--font)", color: INK, opacity: 0 });
  return (T, t) => {
    const pull = ease(T, 16, 30) * 50;
    left.style.transform = `translateX(${-pull}px)`;
    right.style.transform = `translateX(${pull}px)`;
    box.style.opacity = ease(T, 15.0, 15.6);
    slots.forEach((e, i) => { const a = 15.4 + i * 0.22; e.style.opacity = ease(T, a, a + 0.3); e.style.transform = `scale(${0.85 + 0.15 * ease(T, a, a + 0.3)})`; });
    lt.style.opacity = ease(T, 18.3, 18.9);
    blocks.forEach((e, i) => { const a = 21.3 + i * 0.16; const k = easeOut(T, a, a + 0.5); e.style.opacity = k > 0 ? 1 : 0; e.style.transform = `translateY(${(1 - k) * 90}px)`; });
    rt.style.opacity = ease(T, 22.6, 23.4);
    // the hit on "Powerful": the tower shudders once
    const h = T >= 23.5 ? Math.exp(-(T - 23.5) * 8) : 0;
    blocks.forEach((e, i) => { if (T >= 23.5) e.style.transform += ` translateX(${Math.sin((T - 23.5) * 60 + i) * 5 * h}px)`; });
  };
});

// ---------------------------------------------------------------- the diagram of S03, S03b and S04: one function of state
const CORE = { x: 540, y: 330, w: 380, h: 380 };
const SOCK = [
  { key: "Delivery", y: 380, a: "Sender A", b: "Sender B" },
  { key: "AI", y: 520, a: "Model A", b: "Model B" },
  { key: "Channels", y: 660, a: "Email", b: "Push" },
];
const DOORS = [{ key: "CRM", y: 340 }, { key: "Shop", y: 460 }, { key: "Data warehouse", y: 580 }, { key: "Analytics", y: 700 }];
function buildDiagram(root) {
  const o = {};
  o.core = mk("div", "abs", root, { left: CORE.x + "px", top: CORE.y + "px", width: CORE.w + "px", height: CORE.h + "px", border: `3px solid ${PET}`, borderRadius: "22px", background: "#fff", boxShadow: "0 14px 40px rgba(40,30,20,.10)" });
  o.lines = ["content", "campaigns", "rules", "consent log"].map((str, i) => text(o.core, str, { left: "44px", top: (50 + i * 76) + "px", font: "600 40px var(--font)", color: INK, opacity: 0 }));
  o.your = text(root, "Your core.", { left: CORE.x + "px", top: (CORE.y - 84) + "px", font: "650 52px var(--font)", color: PET, opacity: 0 });
  o.sock = SOCK.map(sk => {
    const g = mk("div", "abs", root, { left: 0, top: 0, width: "1920px", height: "1080px", opacity: 0 });
    mk("div", "abs", g, { left: (CORE.x + CORE.w) + "px", top: (sk.y - 1) + "px", width: (1200 - CORE.x - CORE.w) + "px", height: "3px", background: "#cfc5b5" });
    const b = mk("div", "abs", g, { left: "1200px", top: (sk.y - 48) + "px", width: "500px", height: "96px", border: `2px solid ${LINE}`, borderRadius: "16px", background: "#fff", overflow: "hidden" });
    text(b, sk.key, { left: "26px", top: "26px", font: "650 32px var(--font)", color: INK });
    const mkPlug = (label, bg) => {
      const p = mk("div", "abs", b, { left: "236px", top: "16px", width: "240px", height: "62px", borderRadius: "12px", background: bg, display: "flex", alignItems: "center", justifyContent: "center", font: "600 30px var(--font)", color: INK });
      p.textContent = label; return p;
    };
    const rep = text(g, "replaceable", { left: "1200px", top: (sk.y + 52) + "px", font: "400 22px var(--font)", color: MUTED, opacity: 0 });
    return { g, rep, A: mkPlug(sk.a, "#e4daca"), B: mkPlug(sk.b, "#cfe0e7") };
  });
  o.doors = DOORS.map(d => {
    const g = mk("div", "abs", root, { left: 0, top: 0, width: "1920px", height: "1080px", opacity: 0 });
    const b = mk("div", "abs", g, { left: "60px", top: (d.y - 46) + "px", width: "300px", height: "92px", border: `2px solid ${LINE}`, borderRadius: "16px", background: "#fff" });
    const k = mk("div", "abs", b, { left: "20px", top: "24px" }); k.innerHTML = keySvg(44, PET);
    text(b, d.key, { left: "82px", top: "28px", font: "650 30px var(--font)", color: INK, whiteSpace: "nowrap" });
    const sub = text(g, "own key · own permissions", { left: "60px", top: (d.y + 50) + "px", font: "400 23px var(--font)", color: MUTED, opacity: 0 });
    const ar = mk("div", "abs", g, { left: "360px", top: (d.y - 1) + "px", width: (CORE.x - 360 - 10) + "px", height: "3px", background: PET, transformOrigin: "0 50%", transform: "scaleX(0)" });
    const hd = mk("div", "abs", g, { left: (CORE.x - 18) + "px", top: (d.y - 9) + "px", width: 0, height: 0, borderTop: "9px solid transparent", borderBottom: "9px solid transparent", borderLeft: `14px solid ${PET}`, opacity: 0 });
    return { g, sub, ar, hd };
  });
  o.api = text(root, "Connect through the API.", { left: "60px", top: "222px", font: "650 36px var(--font)", color: PET, opacity: 0 });
  // p: {core, lines:[4], your, sock:[3], repl, swap:[3], doors:[4], arrows:[4], sub, api, collapse}
  o.set = p => {
    const c = p.collapse || 0;
    o.core.style.opacity = p.core;
    o.core.style.transform = `translate(${(960 - (CORE.x + CORE.w / 2)) * c}px, ${(557 - (CORE.y + CORE.h / 2)) * c}px) scale(${1 - 0.97 * c})`;
    o.core.style.borderRadius = (22 + 160 * c) + "px";
    o.lines.forEach((e, i) => (e.style.opacity = p.lines[i] * (1 - Math.min(1, c * 4))));
    o.your.style.opacity = p.your * (1 - Math.min(1, c * 4));
    const keep = 1 - Math.min(1, c * 2.5);
    o.sock.forEach((s, i) => {
      s.g.style.opacity = p.sock[i] * keep;
      s.g.style.transform = `translateX(${(1 - p.sock[i]) * 60}px)`;
      s.rep.style.opacity = p.repl;
      const k = p.swap[i];
      const out = ease(k, 0, 0.5), inn = ease(k, 0.5, 1);
      s.A.style.transform = `translateX(${out * 300}px)`; s.A.style.opacity = 1 - out;
      s.B.style.transform = `translateX(${(1 - inn) * 300}px)`; s.B.style.opacity = inn > 0 ? 1 : 0;
    });
    o.doors.forEach((d, i) => {
      d.g.style.opacity = p.doors[i] * keep;
      d.g.style.transform = `translateX(${(1 - p.doors[i]) * -60}px)`;
      d.ar.style.transform = `scaleX(${p.arrows[i]})`;
      d.hd.style.opacity = p.arrows[i] >= 0.999 ? 1 : 0;
      d.sub.style.opacity = p.sub;
    });
    o.api.style.opacity = p.api * keep;
  };
  return o;
}
const blank = n => Array(n).fill(0);
const staticState = () => ({ core: 1, lines: [1, 1, 1, 1], your: 1, sock: [1, 1, 1], repl: 1, swap: [1, 1, 1], doors: blank(4), arrows: blank(4), sub: 0, api: 0 });

// ---------------------------------------------------------------- S03 · the owned core
defScene("S03", "light", 1.0, (root, s) => {
  const d = buildDiagram(root);
  EVENTS.push(36.2, 40.5, 42.0, 44.5, 46.2, 47.8);
  return T => {
    const p = { core: ease(T, 31.6, 32.8), lines: [0, 1, 2, 3].map(i => ease(T, [36.2, 37.4, 38.6, 40.5][i], [36.2, 37.4, 38.6, 40.5][i] + 0.4)), your: ease(T, 35.8, 36.4),
      sock: [0, 1, 2].map(i => ease(T, 42.0 + i * 0.35, 42.0 + i * 0.35 + 0.6)), repl: ease(T, 44.0, 44.6),
      swap: [prog(T, 44.5, 45.8), prog(T, 46.2, 47.5), prog(T, 47.8, 49.1)], doors: blank(4), arrows: blank(4), sub: 0, api: 0, collapse: 0 };
    d.set(p);
  };
});

// ---------------------------------------------------------------- S03b · other systems reach the core
defScene("S03b", "light", 0, (root, s) => {
  const d = buildDiagram(root);
  EVENTS.push(51.0, 51.7, 52.4, 53.1, 54.3, 59.4);
  const card = mk("div", "abs", root, { left: 0, top: 0, width: "1920px", height: "1080px", opacity: 0 });
  const dim = mk("div", "abs", card, { left: 0, top: 0, width: "1920px", height: "1080px", background: "rgba(252,248,242,.86)" });
  const m = mkShot(card, { id: "c45-integration-matrix", a: 0, b: 99, from: [1025, 207, 1.125], crop: [630, 20, 1420, 395], shadow: false, fade: 0, hold: 0, rings: [{ x: 1153, y: 306, w: 32, h: 32, a: 0, b: 99 }] });
  return T => {
    const p = staticState();
    p.doors = [0, 1, 2, 3].map(i => ease(T, 51.0 + i * 0.7, 51.0 + i * 0.7 + 0.5));
    p.arrows = [0, 1, 2, 3].map(i => ease(T, 54.3 + i * 0.35, 54.3 + i * 0.35 + 0.8));
    p.api = ease(T, 55.0, 55.7);
    p.sub = ease(T, 57.0, 57.7);
    d.set(p);
    card.style.opacity = fadeWin(T, 59.4, 61.9, 0.3, 0.4);
    cam(m.L, 1025, 207, 1.125, 960, 540, false);
    m.rings[0].el.set(ease(T, 60.3, 60.6));
  };
});

// ---------------------------------------------------------------- S04 · the title
defScene("S04", "light", 0, (root, s) => {
  const d = buildDiagram(root);
  const dot = mk("div", "abs", root, { left: "951px", top: "548px", width: "18px", height: "18px", borderRadius: "50%", background: PET, opacity: 0 });
  const rule = mk("div", "abs", root, { left: "760px", top: "555px", width: "400px", height: "3px", background: PET, transform: "scaleX(0)", opacity: 0 });
  const name = text(root, D.name, { left: 0, right: 0, top: "400px", textAlign: "center", font: "650 78px var(--font)", color: INK, letterSpacing: "-.015em", opacity: 0 });
  const tag = text(root, "Building a communication system you control.", { left: 0, right: 0, top: "590px", textAlign: "center", font: "400 40px var(--font)", color: MUTED, opacity: 0 });
  const by = text(root, "By Diede Slembrouck", { left: 0, right: 0, top: "672px", textAlign: "center", font: "500 30px var(--font)", color: MUTED, letterSpacing: ".04em", opacity: 0 });
  return T => {
    const p = staticState();
    p.collapse = ease(T, 64.0, 64.9);
    d.set(p);
    dot.style.opacity = ease(T, 64.7, 64.95);
    const grow = ease(T, 65.0, 65.6);
    rule.style.opacity = grow > 0 ? 1 : 0;
    rule.style.transform = `scaleX(${grow})`;
    dot.style.transform = `scale(${1 - grow})`;
    name.style.opacity = ease(T, 65.2, 65.9);
    name.style.transform = `translateY(${(1 - ease(T, 65.2, 65.9)) * 14}px)`;
    tag.style.opacity = ease(T, 66.4, 67.1);
    by.style.opacity = ease(T, 68.0, 68.7);
    // the diagram is gone once the collapse has finished
    d.core.style.display = T < 65.0 ? "block" : "none";
  };
});
