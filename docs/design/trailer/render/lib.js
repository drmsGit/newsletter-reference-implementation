"use strict";
// Helpers for the trailer scenes. Every animation is a pure function of the time T (seconds on the film's timeline).
const W = 1920, H = 1080;
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const lerp = (a, b, k) => a + (b - a) * k;
const smooth = k => k * k * (3 - 2 * k);
const prog = (T, a, b) => clamp((T - a) / (b - a), 0, 1);
const ease = (T, a, b) => smooth(prog(T, a, b));
const easeOut = (T, a, b) => 1 - Math.pow(1 - prog(T, a, b), 3);
const mk = (tag, cls, parent, css) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (css) Object.assign(e.style, css);
  if (parent) parent.appendChild(e);
  return e;
};
const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

let D = null;            // timeline data (data/timeline.json)
const SC = {};           // scene registry: id -> {id, start, end, world, fadeIn, root, update(T, t)}
const EVENTS = [];       // times (film seconds) of presses and cuts: where the mix puts a tick
let CUR = null;          // the scene being built
const IMG = {};          // image registry: id -> {src, real}

const scene = id => D.scenes.find(s => s.id === id);
const voice = id => D.voice[id];                       // {start, dur}
const part = (id, i) => D.parts[id][i];                // {start, dur}
const cueTime = (id, text) => {                        // start of the caption cue of a scene that contains `text`
  const s = scene(id);
  const c = D.cues.find(c => c.s >= s.start - 0.01 && c.s <= s.end && c.t.toLowerCase().includes(text.toLowerCase()));
  return c ? c.s : s.start;
};

// ---------------------------------------------------------------- captures of the real app (layers)
// A capture is captures/<id>.png (1440x810 CSS px at 2x, or taller). Until it exists, an older audit capture or a
// design render stands in, so the pipeline can be tested; the final render must use only real captures.
const AUDIT = "../../ux-audit-2026-10-17/screenshots/";
const REND = "../../renders/";
const FALLBACK = {
  "c01-deliveries-list": AUDIT + "29-deliveries.jpg", "c02-slot-list": AUDIT + "32-slots.jpg", "c03-slot-detail": AUDIT + "33-slot-detail.jpg",
  "c04-as-sent": AUDIT + "31-as-sent.jpg", "c05-slot-reasons": AUDIT + "33-slot-detail.jpg",
  "c06-content-search": AUDIT + "14-records.jpg", "c07-record-categories": AUDIT + "15-record-detail.jpg",
  "c08-editor-chips": AUDIT + "05-variant-editor.jpg", "c09-override-before": AUDIT + "05-variant-editor.jpg", "c10-override-after": AUDIT + "05-variant-editor.jpg",
  "c11-slot-settings": AUDIT + "05-variant-editor.jpg", "c12-preview-reader-a": AUDIT + "06-preview.jpg", "c12-preview-reader-b": AUDIT + "06-preview.jpg", "c12-preview-reader-c": AUDIT + "06-preview.jpg",
  "c13-new-record-dialog": AUDIT + "16-new-record.jpg", "c14-record-draft-source": AUDIT + "15-record-detail.jpg", "c15-draft-proposal": AUDIT + "15-record-detail.jpg",
  "c16-record-saved": AUDIT + "15-record-detail.jpg", "c17-new-blank-variant": AUDIT + "04-campaign-detail.jpg", "c18-prepare-from-topic": AUDIT + "05-variant-editor.jpg",
  "c19-topic-review": AUDIT + "05-variant-editor.jpg", "c20-built-stack": AUDIT + "05-variant-editor.jpg", "c21-approvals-request": REND + "01-approvals-light.png",
  "c22-approvals-approved": REND + "01-approvals-light.png", "c23-send-step1": AUDIT + "11-send.jpg", "c24-send-plan": AUDIT + "11-send.jpg", "c25-send-ready": REND + "26-send-ready.png",
  "c26-results": REND + "20-campaigns.png", "c27-add-module-quote": AUDIT + "05-variant-editor.jpg", "c28-quote-fields": AUDIT + "05-variant-editor.jpg",
  "c29-strategy-list": REND + "23-editor-slot.png", "c30-strategy-chosen": REND + "23-editor-slot.png", "c31-ai-prompts-list": AUDIT + "41-ai-prompts.jpg",
  "c32-ai-prompt-detail": AUDIT + "42-ai-prompt-detail.jpg", "c33-send-picker-email": AUDIT + "11-send.jpg", "c34-send-picker-push": AUDIT + "11-send.jpg",
  "c35-campaign-two-variants": AUDIT + "04-campaign-detail.jpg", "c36-push-editor": AUDIT + "58-push-editor.jpg", "c37-push-preview": AUDIT + "60-push-preview.jpg",
  "c38-approvals-history": REND + "40-decision-history.png", "c39-monitoring": AUDIT + "12-monitoring.jpg", "c40-audiences-rules": AUDIT + "21-audiences.jpg",
  "c41-recipients-list": AUDIT + "27-recipients.jpg", "c42-brand-profile": AUDIT + "35-profiles.jpg", "c43-personalisation": AUDIT + "38-personalisation.jpg",
  "c44-roles": AUDIT + "46-roles.jpg", "c45-integration-matrix": AUDIT + "50-integration-detail.jpg", "c46-ai-prompts": AUDIT + "41-ai-prompts.jpg",
  "drawn-stranded-send": REND + "30-delivery-stranded.png",
};
function probe(src) {
  return new Promise(res => { const i = new Image(); i.onload = () => res(i); i.onerror = () => res(null); i.src = src; });
}
// until a capture of a scene's id is final, a named variant of it stands in
const ALIAS = {};
const EXTRA = ["c04-as-sent-127", "c44-roles-list", "c40-audiences-rules"];   // captures used that no fallback exists for
async function loadCapture(id) {
  let i = await probe(`captures/${ALIAS[id] || id}.png`);
  let real = true;
  if (!i && FALLBACK[id]) { i = await probe(FALLBACK[id]); real = false; }
  if (i) { try { await i.decode(); } catch (e) { /* decoded lazily */ } }
  IMG[id] = i ? { src: i.src, real, w: i.naturalWidth, h: i.naturalHeight } : null;
}
// A layer: a wrapper of 1440 css px width holding the capture, moved and scaled as a whole (the camera).
function layer(parent, id, opts = {}) {
  const wrap = mk("div", "layer" + (opts.shadow === false ? "" : " shadow"), parent);
  const info = IMG[id];
  let h = 810;
  if (info) {
    const img = mk("img", "", wrap);
    img.src = info.src;
    h = Math.round(1440 * info.h / info.w);
  } else {
    const ph = mk("div", "ph", wrap);
    ph.textContent = id + " (not captured)";
  }
  return { wrap, id, h, real: !!(info && info.real) };
}
// Show the layer's point (x, y) at the screen position (sx, sy), at zoom z (1 = the 1440 px wide layer exactly fills the
// stage's width). With clamp the view never leaves the layer, so no edge or background shows.
const BASE = 1920 / 1440;
function cam(L, x, y, z, sx = 960, sy = 540, clampTo = true) {
  const s = BASE * z;
  if (clampTo && sx === 960 && sy === 540) {
    x = clamp(x, 960 / s, 1440 - 960 / s);
    y = L.h * s >= 1080 ? clamp(y, 540 / s, L.h - 540 / s) : L.h / 2;
  }
  L.wrap.style.transform = `translate(${sx - x * s}px, ${sy - y * s}px) scale(${s})`;
  L.s = s; L.tx = sx - x * s; L.ty = sy - y * s;
}
// Crop a layer to a region (layer px): everything outside is invisible.
function crop(L, x0, y0, x1, y1) {
  L.wrap.style.clipPath = `inset(${y0}px ${1440 - x1}px ${L.h - y1}px ${x0}px)`;
}
const toStage = (L, x, y) => [L.tx + x * L.s, L.ty + y * L.s];   // layer point -> stage position (after cam)
function ring(L, x, y, w, h, a) {                                  // a highlight ring in layer space, a = 0..1
  const r = mk("div", "abs", L.wrap, { left: x + "px", top: y + "px", width: w + "px", height: h + "px", border: "3px solid #1a5d74",
    borderRadius: "10px", boxShadow: "0 0 0 6px rgba(26,93,116,.18)", opacity: 0, pointerEvents: "none" });
  r.set = v => { r.style.opacity = v; };
  return r;
}
function cursorEl(parent) {
  const c = mk("div", "abs", parent, { left: 0, top: 0, width: "44px", height: "44px", zIndex: 40, transformOrigin: "6px 4px" });
  c.innerHTML = '<svg width="44" height="44" viewBox="0 0 24 24"><path d="M3 2l7 18 2.6-7.4L20 10z" fill="#1f1b16" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  c.at = (x, y, down = 0) => { c.style.transform = `translate(${x}px, ${y}px) scale(${1 - 0.14 * down})`; };
  return c;
}
// Typewriter: how much of `text` is shown at time T, starting at t0, at cps characters per second.
const typed = (text, T, t0, cps = 28) => text.slice(0, clamp(Math.floor((T - t0) * cps), 0, text.length));
// A transition between two layers of one scene: crossfade at time tx over d seconds.
const xf = (T, tx, d = 0.35) => ease(T, tx, tx + d);

// Syntax colouring for the developer scenes (python, json, xml, diff): a tokenizer, so markup never nests wrongly.
function tok(line, re, fn) {
  let out = "", last = 0, m;
  re.lastIndex = 0;
  while ((m = re.exec(line))) {
    if (m[0].length === 0) { re.lastIndex++; continue; }
    out += esc(line.slice(last, m.index));
    const cls = fn(m);
    out += cls ? `<span class="${cls}">${esc(m[0])}</span>` : esc(m[0]);
    last = m.index + m[0].length;
  }
  return out + esc(line.slice(last));
}
const RE_PY = /(#.*$)|("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|(@\w+)|\b(def|class|return|import|from|if|else|elif|for|in|not|and|or|None|True|False|self|with|as|raise|try|except|while|pass|lambda)\b|\b(\d+(?:\.\d+)?)\b/g;
const RE_JSON = /("(?:[^"\\]|\\.)*")(\s*:)?|\b(true|false|null)\b|(-?\d+(?:\.\d+)?)/g;
const RE_XML = /(<!--[\s\S]*?-->)|(<\/?[\w:-]+)|("[^"]*")|([\w-]+)(?==)|(\{\{.*?\}\}|\{%.*?%\})/g;
function highlight(lang, line) {
  if (lang === "diff") {
    if (/^\+/.test(line)) return `<span class="add">${esc(line)}</span>`;
    if (/^-/.test(line)) return `<span class="del">${esc(line)}</span>`;
    if (/^@@/.test(line)) return `<span class="c">${esc(line)}</span>`;
    return esc(line);
  }
  if (lang === "json") return tok(line, RE_JSON, m => (m[2] ? "k" : m[1] ? "s" : "n"));
  if (lang === "xml") return tok(line, RE_XML, m => (m[1] ? "c" : m[2] ? "k" : m[3] ? "s" : m[4] ? "n" : "d"));
  return tok(line, RE_PY, m => (m[1] ? "c" : m[2] ? "s" : m[3] ? "d" : m[4] ? "k" : "n"));
}
// A whole file: the same, with python's triple-quoted strings (docstrings, prompts) carried across lines.
function highlightBlock(lang, text) {
  const lines = text.split("\n");
  if (lang !== "python") return lines.map(l => highlight(lang, l));
  let inT = false;
  return lines.map(l => {
    let out = "", rest = l;
    if (inT) {
      const i = rest.indexOf('"""');
      if (i < 0) return `<span class="s">${esc(rest)}</span>`;
      out += `<span class="s">${esc(rest.slice(0, i + 3))}</span>`;
      rest = rest.slice(i + 3); inT = false;
    }
    const j = rest.indexOf('"""');
    if (j >= 0) {
      const k = rest.indexOf('"""', j + 3);
      if (k >= 0) return out + highlight("python", rest.slice(0, j)) + `<span class="s">${esc(rest.slice(j, k + 3))}</span>` + highlight("python", rest.slice(k + 3));
      inT = true;
      return out + highlight("python", rest.slice(0, j)) + `<span class="s">${esc(rest.slice(j))}</span>`;
    }
    return out + highlight("python", rest);
  });
}
