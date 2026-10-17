"use strict";
// The developer's world (S12 to S16b), dark-warm, with the manager's cut-ins of S13 to S16. Real code from data.code.
const DACC = "#6fc3dd", DTEXT = "#f4eee6", DMUTED = "#8a7f70", DLINE = "#36302a", AMBER = "#e8b45a";

function devWindow(root, title) {
  const win = mk("div", "win", root, { left: "50px", top: "100px", width: "1820px", height: "840px" });
  const bar = mk("div", "bar", win);
  for (let i = 0; i < 3; i++) mk("span", "dot", bar);
  const tt = mk("span", "", bar, { marginLeft: "16px" }); tt.textContent = title;
  const tree = mk("div", "tree", win, { width: "420px" });
  const main = mk("div", "abs", win, { left: "420px", top: "50px", right: 0, bottom: 0, overflow: "hidden" });
  const tabs = mk("div", "abs", main, { left: 0, top: 0, right: 0, height: "50px", background: "#191614", borderBottom: `2px solid ${DLINE}`, whiteSpace: "nowrap" });
  const body = mk("div", "abs", main, { left: 0, top: "50px", right: 0, bottom: 0, overflow: "hidden" });
  return { win, tree, tabs, body, main };
}
function buildTree(el, entries) {
  return entries.map(e => {
    const r = mk("div", "", el, { paddingLeft: (e.d * 24) + "px", whiteSpace: "pre", height: "38px", overflow: "hidden", opacity: 0 });
    r.textContent = e.t;
    return r;
  });
}
function updTree(rows, entries, t) {
  rows.forEach((r, i) => {
    const e = entries[i], at = e.at || 0;
    r.style.opacity = ease(t, at, at + 0.3);
    r.className = (e.cls || "") + (e.on && t >= e.on[0] && t < e.on[1] ? " on" : "");
  });
}
function buildTabs(el, spec) { return spec.map(() => mk("span", "tab", el)); }
function updTabs(els, spec, t) {
  els.forEach((e, i) => {
    const s = spec[i];
    e.style.display = t >= (s.at === undefined ? s.a : s.at) ? "inline-block" : "none";
    e.className = "tab" + (t >= s.a && t < s.b ? " on" : "");
    e.textContent = s.name + (s.dirty && t >= s.dirty[0] && t < s.dirty[1] ? "  ●" : "");
  });
}
// A code pane: the lines of a real file, revealed as if typed, scrolled, with rows that can be marked.
function codePane(parent, lang, text, o = {}) {
  const fs = o.fs || 24, lh = Math.round(fs * 1.5);
  const el = mk("div", "abs", parent, { left: (o.x || 0) + "px", top: (o.y || 0) + "px", right: (o.r || 0) + "px", bottom: (o.b || 0) + "px", overflow: "hidden", font: `${fs}px/${lh}px var(--mono)`, color: DTEXT, paddingTop: "10px" });
  const inner = mk("div", "abs", el, { left: 0, top: "10px", width: "100%" });
  const all = text.split("\n"), html = highlightBlock(lang, text);
  const from = o.from || 1, to = o.to || all.length;
  const rows = [];
  for (let i = from; i <= to; i++) {
    const r = mk("div", "", inner, { height: lh + "px", whiteSpace: "pre", visibility: "hidden", paddingRight: "20px" });
    r.innerHTML = `<span class="ln" style="width:${fs * 2.2}px;margin-right:${fs * 0.9}px">${i}</span>${(o.fix ? o.fix(i, html[i - 1]) : html[i - 1]) || ""}`;
    rows.push(r);
  }
  const api = {
    el, rows, lh, n: rows.length, from,
    reveal(k) {
      const f = Math.floor(k);
      rows.forEach((r, i) => { r.style.visibility = i < f ? "visible" : "hidden"; r.style.clipPath = ""; });
      if (f < rows.length && k > f) { rows[f].style.visibility = "visible"; rows[f].style.clipPath = `inset(0 ${(1 - (k - f)) * 100}% 0 0)`; }
    },
    scroll(line) { inner.style.transform = `translateY(${-line * lh}px)`; },
    follow(k, visible) { api.scroll(Math.max(0, k - visible + 1)); },
    mark(a, b, on) { for (let i = a; i <= b; i++) if (rows[i - from]) rows[i - from].classList.toggle("hlrow", on); },
    show(v) { el.style.display = v ? "block" : "none"; },
  };
  return api;
}
// A terminal: lines that appear at a time, a prompt line typed at cps characters per second.
function termPane(parent, h) {
  const el = mk("div", "term", parent, { height: h + "px" });
  return el;
}
function buildTerm(el, lines) {
  return lines.map(() => mk("div", "", el, { height: "36px", whiteSpace: "pre", opacity: 0 }));
}
function updTerm(els, lines, t) {
  els.forEach((e, i) => {
    const l = lines[i];
    if (t < l.at) { e.style.opacity = 0; return; }
    e.style.opacity = 1;
    let str = l.text;
    if (l.cps) str = l.text.slice(0, clamp(Math.floor((t - l.at) * l.cps), 0, l.text.length));
    const caret = l.cps && t - l.at < l.text.length / l.cps + 0.5 && Math.floor(t * 2) % 2 === 0 ? "▍" : "";
    e.innerHTML = (l.prompt ? `<span class="prompt">&gt; </span>` : "") + `<span style="color:${l.color || "#cfc6b8"}">${esc(str)}</span>${caret}`;
  });
}
const RECENCY = () => D.code["backend/app/decision/strategies/recency_boost.py"].text;

// the manager's cut-in: a linen layer over the dark window from time `at` on (hard cut), shots relative to the scene
function managerPart(root, at, shots, extra) {
  const m = mk("div", "abs", root, { left: 0, top: 0, width: "1920px", height: "1080px", background: LINEN, display: "none" });
  const upd = shotScene(m, null, shots, extra, true);
  return (T, t) => { const on = t >= at; m.style.display = on ? "block" : "none"; if (on) upd(T, t); };
}

// ---------------------------------------------------------------- S12 · behind the screens
defScene("S12", "dark", 0, (root, s) => {
  const lab = text(root, "The developer", { left: "90px", top: "40px", font: "600 36px var(--font)", color: DACC, letterSpacing: ".04em" });
  const w = devWindow(root, "repository");
  const entries = [
    { t: "storage/", d: 0, at: 0.2 }, { t: "modules/email/", d: 1, at: 0.3 },
    { t: "backend/app/", d: 0, at: 0.4 }, { t: "ai/tasks/", d: 1, at: 0.5 }, { t: "decision/strategies/", d: 1, at: 0.6 },
    { t: "recipient_top_score.py", d: 2, at: 0.7 }, { t: "top_score.py", d: 2, at: 0.7 },
    { t: "recency_boost.py", d: 2, at: 4.2, cls: "new", on: [4.2, 6.2] }, { t: "delivery/providers/", d: 1, at: 0.8 },
    { t: "docs/architecture/ADR/", d: 0, at: 0.9 },
  ];
  const rows = buildTree(w.tree, entries);
  const tabSpec = [{ name: "recency_boost.py", a: 4.3, b: 99, at: 4.3, dirty: [4.3, 10.4] }];
  const tabEls = buildTabs(w.tabs, tabSpec);
  const term = termPane(w.body, 250);
  const tl = [
    { at: 0.7, text: "add a decision strategy that favours recent content", cps: 20, prompt: true, color: DTEXT },
    { at: 3.6, text: "writing backend/app/decision/strategies/recency_boost.py", color: DMUTED },
    { at: 10.6, text: "1 file changed. A person reviews it, then merges.", color: DACC },
  ];
  const tl_els = buildTerm(term, tl);
  const code = codePane(w.body, "python", RECENCY(), { from: 1, to: 56, b: 262, fs: 22 });
  return (T, t) => {
    updTree(rows, entries, t); updTabs(tabEls, tabSpec, t); updTerm(tl_els, tl, t);
    const k = clamp((t - 4.3) / 6.0, 0, 1) * 56;
    code.reveal(k); code.follow(k, 14);
    code.el.style.opacity = t >= 4.3 ? 1 : 0;
  };
});

// ---------------------------------------------------------------- S13 · drop a content block
defScene("S13", "dark", 0, (root, s) => {
  const lab = text(root, "The developer", { left: "90px", top: "40px", font: "600 36px var(--font)", color: DACC, letterSpacing: ".04em" });
  const w = devWindow(root, "repository");
  const entries = [
    { t: "storage/", d: 0 }, { t: "modules/email/", d: 1 },
    { t: "cta.json", d: 2 }, { t: "cta.mjml", d: 2 }, { t: "cta.html", d: 2 },
    { t: "hero.json", d: 2 }, { t: "hero.mjml", d: 2 }, { t: "hero.html", d: 2 },
    { t: "quote.json", d: 2, at: 0.3, cls: "new", on: [0.3, 1.3] }, { t: "quote.mjml", d: 2, at: 1.2, cls: "new", on: [1.2, 2.3] },
    { t: "quote.html", d: 2, at: 3.0, cls: "new", on: [3.0, 4.2] },
  ];
  const rows = buildTree(w.tree, entries);
  const tabSpec = [{ name: "quote.json", a: 0.3, b: 1.25, dirty: [0.3, 1.25] }, { name: "quote.mjml", a: 1.25, b: 99, dirty: [1.25, 2.4] }];
  const tabEls = buildTabs(w.tabs, tabSpec);
  const term = termPane(w.body, 210);
  const tl = [
    { at: 1.6, text: "npm run build:modules", cps: 30, prompt: true, color: DTEXT },
    { at: 2.6, text: "Wrote 11 files to storage/modules/email.", color: "#cfc6b8" },
    { at: 3.0, text: "built in 0.58 s", color: DMUTED },
  ];
  const tlEls = buildTerm(term, tl);
  const j = D.code["storage/modules/email/quote.json"], x = D.code["storage/modules/email/quote.mjml"];
  const cj = codePane(w.body, "json", j.text, { b: 222 }), cx = codePane(w.body, "xml", x.text, { b: 222 });
  const mgr = managerPart(root, 4.2, [
    { id: "c27-add-module-quote", a: 4.2, b: 8.4, fade: 0, from: [720, 405, 1.0], to: [500, 560, 1.4], rings: [{ x: 246, y: 704, w: 156, h: 32, a: 6.0, b: 8.4 }],
      cursor: [[4.6, 300, 790], [6.2, 320, 719, 1], [7.4, 436, 788, 1]] },
    { id: "c28-quote-fields", a: 8.2, b: 12, crop: [0, 0, 1440, 766], shadow: false, from: [720, 405, 1.0], to: [740, 410, 1.05],
      rings: [{ x: 246, y: 616, w: 364, h: 68, a: 8.5, b: 9.8 }, { x: 650, y: 574, w: 752, h: 92, a: 9.6, b: 12 }] },
  ]);
  return (T, t) => {
    updTree(rows, entries, t); updTabs(tabEls, tabSpec, t); updTerm(tlEls, tl, t);
    const k1 = clamp((t - 0.3) / 0.9, 0, 1) * cj.n, k2 = clamp((t - 1.25) / 1.0, 0, 1) * cx.n;
    cj.reveal(k1); cx.reveal(k2);
    cj.show(t < 1.25); cx.show(t >= 1.25);
    term.style.opacity = t >= 1.5 ? 1 : 0;
    mgr(T, t);
  };
});

// ---------------------------------------------------------------- S14 · drop a decision strategy
defScene("S14", "dark", 0, (root, s) => {
  const lab = text(root, "The developer", { left: "90px", top: "40px", font: "600 36px var(--font)", color: DACC, letterSpacing: ".04em" });
  const w = devWindow(root, "repository");
  const entries = [
    { t: "backend/app/decision/strategies/", d: 0 }, { t: "base.py", d: 1 }, { t: "recipient_top_score.py", d: 1 },
    { t: "recency_boost.py", d: 1, at: 1.0, cls: "new", on: [1.0, 3.6] }, { t: "registry.py", d: 1 }, { t: "top_score.py", d: 1 },
  ];
  const rows = buildTree(w.tree, entries);
  const tabSpec = [{ name: "top_score.py", a: 0, b: 1.0 }, { name: "recency_boost.py", a: 1.0, b: 99, at: 1.0, dirty: [1.0, 3.0] }];
  const tabEls = buildTabs(w.tabs, tabSpec);
  const ts = codePane(w.body, "python", D.files.top_score_head, { from: 12, to: 38, fs: 22 });
  const rb = codePane(w.body, "python", RECENCY(), { from: 13, to: 80, fs: 22 });
  const mgr = managerPart(root, 5.6, [
    { id: "c29-strategy-list", a: 5.6, b: 9.2, fade: 0, from: [960, 300, 1.2], to: [960, 270, 1.5], rings: [{ x: 655, y: 185, w: 742, h: 26, a: 6.4, b: 9.2 }] },
    { id: "c30-strategy-chosen", a: 9.0, b: 10.5, from: [1020, 520, 1.35], to: [1020, 520, 1.4], rings: [{ x: 652, y: 462, w: 746, h: 30, a: 9.2, b: 10.5 }] },
    { id: "c30-strategy-chosen", a: 10.3, b: 12, from: [1020, 1760, 1.35], to: [1020, 1900, 1.4], rings: [{ x: 650, y: 1960, w: 750, h: 52, a: 10.9, b: 12 }] },
  ]);
  return (T, t) => {
    updTree(rows, entries, t); updTabs(tabEls, tabSpec, t);
    ts.show(t < 1.0); rb.show(t >= 1.0);
    const k = clamp((t - 1.0) / 2.0, 0, 1) * rb.n;
    rb.reveal(k);
    // before the save the new file follows the typing; after it, a slow scroll from `meta` to `rank`
    rb.scroll(t < 3.0 ? Math.max(0, k - 14) : lerp(Math.max(0, rb.n - 14), 30, ease(t, 3.0, 5.4)));
    rb.mark(24, 24, t > 3.3 && t < 4.4); rb.mark(55, 55, t > 4.4 && t < 5.6);
    mgr(T, t);
  };
});

// ---------------------------------------------------------------- S15 · drop an AI task
defScene("S15", "dark", 0, (root, s) => {
  const lab = text(root, "The developer", { left: "90px", top: "40px", font: "600 36px var(--font)", color: DACC, letterSpacing: ".04em" });
  const w = devWindow(root, "repository");
  const entries = [
    { t: "backend/app/ai/tasks/", d: 0 }, { t: "base.py", d: 1 }, { t: "content_draft.py", d: 1 }, { t: "content_translate.py", d: 1 },
    { t: "headline_polish.py", d: 1, at: 0.4, cls: "new", on: [0.4, 3.6] }, { t: "registry.py", d: 1 }, { t: "subject_preheader.py", d: 1 }, { t: "variant_from_topic.py", d: 1 },
  ];
  const rows = buildTree(w.tree, entries);
  const tabSpec = [{ name: "headline_polish.py", a: 0.4, b: 99, at: 0.4, dirty: [0.4, 3.0] }];
  const tabEls = buildTabs(w.tabs, tabSpec);
  const code = codePane(w.body, "python", D.code["backend/app/ai/tasks/headline_polish.py"].text, { fs: 24 });
  const mgr = managerPart(root, 4.6, [
    { id: "c31-ai-prompts-list", a: 4.6, b: 8.0, fade: 0, from: [720, 405, 1.0], to: [480, 330, 1.5], rings: [{ x: 246, y: 283, w: 360, h: 68, a: 5.4, b: 8.0 }],
      cursor: [[4.9, 700, 600], [6.2, 400, 315, 1]] },
    { id: "c32-ai-prompt-detail", a: 7.8, b: 12, crop: [630, 495, 1420, 880], shadow: false, from: [1025, 688, 1.4], to: [1025, 688, 1.48],
      rings: [{ x: 650, y: 570, w: 750, h: 200, a: 8.3, b: 10.2 }, { x: 650, y: 788, w: 152, h: 34, a: 10.5, b: 12 }],
      cursor: [[8.4, 1300, 520], [9.3, 1000, 680, 1], [10.9, 725, 805, 1]] },
  ]);
  return (T, t) => {
    updTree(rows, entries, t); updTabs(tabEls, tabSpec, t);
    const k = clamp((t - 0.4) / 2.6, 0, 1) * code.n;
    code.reveal(k);
    code.scroll(t < 3.0 ? Math.max(0, k - 21) : lerp(Math.max(0, code.n - 21), 25, ease(t, 3.0, 3.9)));
    code.mark(4, 5, t > 1.5 && t < 3.0); code.mark(33, 43, t > 3.9 && t < 4.7);
    mgr(T, t);
  };
});

// ---------------------------------------------------------------- S16 · swap the delivery provider
defScene("S16", "dark", 0, (root, s) => {
  const lab = text(root, "The developer", { left: "90px", top: "40px", font: "600 36px var(--font)", color: DACC, letterSpacing: ".04em" });
  const w = devWindow(root, "repository");
  const entries = [
    { t: "backend/app/delivery/providers/", d: 0 }, { t: "base.py", d: 1 },
    { t: "example_mail.py", d: 1, at: 0.4, cls: "new", on: [0.4, 3.2] }, { t: "example_push.py", d: 1, at: 3.2, cls: "new", on: [3.2, 5.4] },
    { t: "factory.py", d: 1, at: 0, on: [5.6, 9.2] }, { t: "mock.py", d: 1 }, { t: "resend.py", d: 1 },
  ];
  const rows = buildTree(w.tree, entries);
  const tabSpec = [
    { name: "example_mail.py", a: 0.4, b: 3.2, at: 0.4, dirty: [0.4, 3.0] }, { name: "example_push.py", a: 3.2, b: 5.6, at: 3.2, dirty: [3.2, 5.4] },
    { name: "factory.py", a: 5.6, b: 99, at: 5.6, dirty: [5.6, 9.0] },
  ];
  const tabEls = buildTabs(w.tabs, tabSpec);
  const mail = codePane(w.body, "python", D.code["backend/app/delivery/providers/example_mail.py"].text, { fs: 23, b: 0 });
  const push = codePane(w.body, "python", D.code["backend/app/delivery/providers/example_push.py"].text, { fs: 23, b: 0 });
  const diff = codePane(w.body, "diff", D.code["backend/app/delivery/providers/factory.py"].text, { fs: 22, b: 0 });
  const term = termPane(w.body, 230);
  const tl = [
    { at: 9.1, text: "WARNING:  StatReload detected changes in 'app/delivery/providers/factory.py'. Reloading...", color: AMBER },
    { at: 9.7, text: "INFO:main:channels: email (12 modules, max unbounded), push (1 modules, max 1)", color: "#cfc6b8" },
    { at: 10.3, text: "INFO:     Application startup complete.", color: "#cfc6b8" },
    { at: 10.6, text: "ready in 1.4 s", color: DACC },
  ];
  const tlEls = buildTerm(term, tl);
  const mgr = managerPart(root, 11.6, [
    { id: "c33-send-picker-email", a: 11.6, b: 14.0, fade: 0, crop: [620, 30, 1440, 800], shadow: false, from: [1030, 415, 0.9], to: [1030, 415, 0.95], sy: 500, rings: [{ x: 655, y: 676, w: 742, h: 28, a: 12.4, b: 14.0 }] },
    { id: "c34-send-picker-push", a: 13.8, b: 16, crop: [620, 336, 1440, 740], shadow: false, from: [1030, 538, 1.2], to: [1030, 538, 1.26], rings: [{ x: 655, y: 592, w: 742, h: 26, a: 14.4, b: 16 }] },
  ]);
  const sw = pill(root, "A file. A few lines. Any sender.", 11.7, 15.9);
  return (T, t) => {
    updTree(rows, entries, t); updTabs(tabEls, tabSpec, t); updTerm(tlEls, tl, t);
    mail.show(t < 3.2); push.show(t >= 3.2 && t < 5.6); diff.show(t >= 5.6);
    mail.reveal(clamp((t - 0.4) / 2.4, 0, 1) * mail.n);
    mail.mark(19, 19, t > 2.0 && t < 3.0); mail.mark(21, 21, t > 2.3 && t < 3.0);
    push.reveal(clamp((t - 3.2) / 1.8, 0, 1) * push.n);
    push.mark(20, 20, t > 4.4 && t < 5.4);
    diff.reveal(clamp((t - 5.6) / 1.2, 0, 1) * diff.n);
    diff.scroll(ease(t, 6.2, 9.0) * (diff.n - 17));
    term.style.opacity = t >= 9.0 ? 1 : 0;
    mgr(T, t);
    sw(t);
  };
});

// ---------------------------------------------------------------- S16b · the reasons stay with the code
defScene("S16b", "dark", 0, (root, s) => {
  const w = devWindow(root, "repository");
  // (a) factory.py: its own docstring names the decision
  const fix = (i, h) => (i === 1 ? h.replace("ADR-101", `<span style="outline:2px solid ${DACC};border-radius:4px;background:rgba(111,195,221,.22)">ADR-101</span>`) : h);
  const fac = codePane(w.body, "python", D.files.factory_head, { fs: 30, fix });
  const entries = [{ t: "factory.py", d: 0, on: [0, 2.6] }, { t: "ADR-101 — Provider", d: 0, at: 2.4, on: [2.6, 5.3] }, { t: "ADR-143 — AI-Assisted", d: 0, at: 5.0, on: [5.3, 12] }];
  const rows = buildTree(w.tree, entries);
  const tabSpec = [{ name: "factory.py", a: 0, b: 2.6 }, { name: D.files.adr101_name, a: 2.6, b: 5.3, at: 2.6 }, { name: D.files.adr143_name, a: 5.3, b: 7.8, at: 5.3 }];
  const tabEls = buildTabs(w.tabs, tabSpec);
  // (b) the two ADRs as a plain markdown reader
  const doc = (title, status, bodyHtml) => {
    const d = mk("div", "abs", w.body, { left: "60px", top: "36px", right: "60px", bottom: "20px", fontFamily: "var(--font)", display: "none" });
    d.innerHTML = `<div style="font:650 44px var(--font);color:${DTEXT};letter-spacing:-.01em">${esc(title)}</div>
      <div style="margin-top:18px;font:26px var(--mono);color:${DMUTED}">status: <span style="color:${DACC}">${status}</span></div>
      <div style="margin-top:44px;font:600 34px var(--font);color:${DTEXT}">${bodyHtml}</div>`;
    return d;
  };
  const d101 = doc("ADR-101 — Provider Capabilities Are Explicit", "accepted",
    `<div style="color:${DMUTED};font:600 28px var(--mono)">## Decision</div><div style="margin-top:22px;font:400 38px/1.4 var(--font)">Provider capabilities must be explicitly defined.</div><div style="margin-top:22px;font:400 38px/1.4 var(--font);color:${DMUTED}">Core capabilities:</div>`);
  const d143 = doc("ADR-143 — AI-Assisted Development Boundary", "accepted",
    `<div style="font:400 40px/1.45 var(--font)">1. Mode C is ADR-140's philosophy pointed at the repo: <span id="proposal" style="background:rgba(111,195,221,.22);outline:2px solid ${DACC};border-radius:6px;padding:0 6px">the AI's output is a proposal, never a deployment.</span></div>`);
  // (c) the pull-back: the repository's four folders and four lines of its history
  const pull = mk("div", "abs", w.body, { left: "50px", top: "30px", right: "50px", bottom: "20px", display: "none" });
  const cols = [["backend/", ["app", "scripts", "tests"]], ["frontend/", ["src", "scripts"]], ["storage/", ["channels", "modules"]], ["docs/", ["architecture", "business", "design", "implementation", "models", "queue"]]];
  cols.forEach(([h, kids], i) => {
    const c = mk("div", "abs", pull, { left: (i * 330) + "px", top: 0, width: "300px", font: "26px/1.6 var(--mono)", color: DMUTED });
    c.innerHTML = `<div style="color:${DACC};font-weight:600;font-size:30px">${h}</div>` + kids.map(k => `<div>  ${k}/</div>`).join("");
  });
  const commits = [
    ["d0bcb51", "docs: ADR-166 addendum — the key expiry's final-design pass (task-344)"],
    ["40cc737", "feat(integrations): a key may expire, set in days when issued (task-344)"],
    ["cc9fb6d", "feat(signals): a link names its content, and a click credits it only if it was sent (task-240, ADR-182)"],
    ["420921f", "fix(ui): a catalogue field's switch and Change in catalogue share one line (task-392 item 3)"],
  ].map(([h, m], i) => text(pull, "", { left: 0, top: (280 + i * 76) + "px", width: "1300px", font: "22px/32px var(--mono)", color: "#cfc6b8", whiteSpace: "pre-wrap", opacity: 0 }));
  const cm = [
    ["d0bcb51", "docs: ADR-166 addendum — the key expiry's final-design pass (task-344)"],
    ["40cc737", "feat(integrations): a key may expire, set in days when issued (task-344)"],
    ["cc9fb6d", "feat(signals): a link names its content, and a click credits it only if it was sent (task-240, ADR-182)"],
    ["420921f", "fix(ui): a catalogue field's switch and Change in catalogue share one line (task-392 item 3)"],
  ];
  commits.forEach((e, i) => (e.innerHTML = `<span style="color:${AMBER}">${cm[i][0]}</span>  ${esc(cm[i][1])}`));
  const words = ["The decision.", "The task.", "The change.", "One repository."].map((str, i) =>
    text(root, str, { left: [90, 520, 860, 1190][i] + "px", top: "872px", font: "650 54px var(--font)", color: DTEXT, opacity: 0 }));
  const wt = [8.4, 9.1, 9.8, 10.7];
  return (T, t) => {
    updTree(rows, entries, t); updTabs(tabEls, tabSpec, t);
    fac.show(t < 2.6); fac.reveal(clamp(t / 0.8, 0, 1) * fac.n);
    d101.style.display = t >= 2.6 && t < 5.3 ? "block" : "none";
    d143.style.display = t >= 5.3 && t < 7.8 ? "block" : "none";
    pull.style.display = t >= 7.8 ? "block" : "none";
    commits.forEach((e, i) => (e.style.opacity = ease(t, 8.0 + i * 0.3, 8.4 + i * 0.3)));
    words.forEach((e, i) => (e.style.opacity = ease(t, wt[i], wt[i] + 0.4)));
    w.win.style.height = t >= 7.8 ? "740px" : "840px";
  };
});
