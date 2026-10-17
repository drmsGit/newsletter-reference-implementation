"use strict";
// The manager's world: S05 to S11, S17, S18. Real captures of the app as animated layers (camera moves, cursor, rings).
// Anchors are in layer pixels (the capture at 1440 px width). Shots without their final capture use a generic push-in.

// a soft fade on the right edge of a cropped layer, so a cropped table does not end in a hard cut
function fadeRight(L, x1, w = 50) {
  const m = `linear-gradient(to right, #000 ${x1 - w}px, transparent ${x1}px)`;
  L.wrap.style.webkitMaskImage = m; L.wrap.style.maskImage = m;
}
// A generic shot: a gentle push-in towards (x, y), for captures whose exact anchors are tuned later.
const gen = (id, a, b, o = {}) => Object.assign({ id, a, b, from: [720, 405, 1.0], to: [o.x || 800, o.y || 430, o.z || 1.12] }, o);

// ---------------------------------------------------------------- S05 · content
defScene("S05", "light", 0.5, (root, s) => {
  const sh = shotScene(root, s, [
    { id: "c06-content-search", a: 0, b: 3.6, fade: 0, from: [720, 405, 1.0], to: [500, 470, 1.4], rings: [{ x: 238, y: 468, w: 368, h: 132, a: 1.5, b: 3.6 }],
      cursor: [[0.2, 349, 100], [1.5, 440, 540, 1]] },
    { id: "c07-record-categories", a: 3.2, b: 8.0, from: [1020, 760, 1.0], to: [1190, 1880, 1.6], rings: [{ x: 1128, y: 1840, w: 204, h: 160, a: 5.7, b: 8.0 }] },
  ]);
  const p = pill(root, "Day hikes in the Chiemgau: plan the return journey first", 0.8, 3.4);
  return (T, t) => { sh(T, t); p(t); };
});

// ---------------------------------------------------------------- S06 · a campaign points to it
defScene("S06", "light", 0, (root, s) => {
  return shotScene(root, s, [
    { id: "c08-editor-chips", a: 0, b: 3.9, fade: 0, from: [430, 300, 1.2], to: [430, 360, 1.5],
      rings: [{ x: 250, y: 111, w: 90, h: 28, a: 0.5, b: 1.6 }, { x: 250, y: 211, w: 94, h: 28, a: 1.4, b: 2.5 }, { x: 250, y: 484, w: 70, h: 26, a: 2.3, b: 3.7 }] },
    { id: "c09-override-before", a: 3.6, b: 6.5, from: [1000, 850, 1.5], to: [1000, 850, 1.55], cursor: [[3.9, 1250, 700], [5.0, 900, 815, 1]] },
    { id: "c10-override-after", a: 6.3, b: 10, fade: 0.25, from: [1000, 850, 1.55], to: [1020, 860, 1.65],
      rings: [{ x: 664, y: 784, w: 440, h: 28, a: 6.8, b: 8.0 }, { x: 884, y: 856, w: 208, h: 38, a: 7.9, b: 10 }] },
  ]);
});

// ---------------------------------------------------------------- S07 · one slot, three readers, three picks
const READERS = [
  { id: "c12-preview-reader-a", who: "lea.huber.32", head: ["49 euros and room for a layer", "On 15 May, we draw", "A small seat mat, less pause theatre"] },
  { id: "c12-preview-reader-b", who: "michael.zimmermann.127", head: ["A track is not yet a species", "Eightfold, but not restless", "Talking through tracks and pictures"] },
  { id: "c12-preview-reader-c", who: "peter.mueller.330", head: ["Rain trousers: take one deep squat", "What did you notice today?", "With children: choose the rest stops first"] },
];
defScene("S07", "light", 0, (root, s) => {
  const main = shotScene(root, s, [
    { id: "c11-slot-settings", a: 0, b: 1.9, fade: 0, crop: [0, 60, 640, 740], shadow: false, from: [320, 400, 1.15], to: [320, 420, 1.2], rings: [{ x: 240, y: 470, w: 362, h: 72, a: 0.3, b: 1.9 }] },
    { id: "c11-slot-settings", a: 1.8, b: 3.0, crop: [640, 80, 1410, 124], shadow: false, from: [1025, 102, 1.3], to: [1025, 102, 1.35], rings: [{ x: 650, y: 86, w: 752, h: 36, a: 2.0, b: 3.0 }] },
    { id: "c11-slot-settings", a: 2.9, b: 3.8, crop: [640, 212, 1410, 470], shadow: false, from: [1025, 341, 1.2], to: [1025, 341, 1.25], rings: [{ x: 650, y: 233, w: 752, h: 36, a: 3.0, b: 3.8 }] },
    { id: "c12-preview-reader-a", a: 3.6, b: 5.5, from: [720, 405, 1.0], to: [900, 2300, 1.1], rings: [{ x: 118, y: 131, w: 226, h: 26, a: 3.9, b: 4.6 }] },
    { id: "c12-preview-reader-b", a: 5.3, b: 7.1, from: [720, 405, 1.0], to: [900, 2300, 1.1], rings: [{ x: 118, y: 131, w: 300, h: 26, a: 5.6, b: 6.3 }] },
    { id: "c12-preview-reader-c", a: 6.9, b: 8.4, from: [720, 405, 1.0], to: [900, 2300, 1.1], rings: [{ x: 118, y: 131, w: 260, h: 26, a: 7.2, b: 7.9 }] },
    { id: "c03-slot-detail", a: 11.6, b: 20, fade: 0.5, from: [1020, 420, 1.0], to: [1020, 760, 1.5], rings: [{ x: 652, y: 610, w: 764, h: 102, a: 12.6, b: 15.0 }] },
  ]);
  // the triptych: the tail of the three previews side by side, one shared top, three different tails
  const tri = mk("div", "abs", root, { left: 0, top: 0, width: "1920px", height: "1080px", background: LINEN, opacity: 0, display: "none" });
  const cols = READERS.map((r, i) => {
    const cx = 400 + i * 560;
    const L = layer(tri, r.id, { shadow: false });
    crop(L, 558, 1735, 1300, 3000);
    cam(L, 929, 2367, 0.39, cx, 495, false);
    const hd = text(tri, r.who, { left: (cx - 270) + "px", width: "540px", top: "118px", textAlign: "center", font: "500 28px var(--mono)", color: MUTED });
    const cap = text(tri, "", { left: (cx - 270) + "px", width: "540px", top: "838px", textAlign: "center", font: "400 24px/32px var(--font)", color: INK });
    cap.innerHTML = r.head.filter(Boolean).map(h => `<div>${esc(h)}</div>`).join("");
    return { L, hd, cap };
  });
  const tp = pill(tri, "Same email. Three readers. Three picks.", 8.4, 11.8, { top: "26px" });
  EVENTS.push(s.start + 8.2);
  const p = pill(root, "Every pick has a reason.", 12.2, 19.6);
  return (T, t) => {
    const on = t >= 8.2 && t < 11.9;
    tri.style.display = on ? "block" : "none";
    tri.style.opacity = ease(t, 8.2, 8.6) * (1 - ease(t, 11.6, 11.9));
    cols.forEach((c, i) => {
      const k = ease(t, 8.3 + i * 0.25, 8.9 + i * 0.25);
      c.L.wrap.style.opacity = k; c.hd.style.opacity = k; c.cap.style.opacity = k;
    });
    tp(t);
    main(T, t);
    p(t);
  };
});

// ---------------------------------------------------------------- S08 · AI proposes, a person decides (the AI results are drawings)
defScene("S08", "light", 0, (root, s) => {
  return shotScene(root, s, [
    { id: "c13-new-record-dialog", a: 0, b: 2.1, fade: 0, from: [720, 405, 1.2], to: [720, 405, 1.7], rings: [{ x: 888, y: 488, w: 76, h: 34, a: 1.3, b: 2.1 }],
      cursor: [[0.3, 880, 440], [1.5, 925, 506, 1]] },
    { id: "c14-record-draft-source", a: 2.0, b: 4.1, from: [1020, 260, 1.15], to: [1020, 300, 1.3],
      rings: [{ x: 650, y: 104, w: 752, h: 128, a: 2.1, b: 2.9 }, { x: 650, y: 322, w: 752, h: 40, a: 2.8, b: 3.6 }],
      cursor: [[2.3, 900, 150], [3.0, 880, 342], [3.7, 690, 398, 1]] },
    { id: "c15-draft-proposal", a: 4.0, b: 6.7, from: [1020, 330, 1.2], to: [1020, 560, 1.25], rings: [{ x: 650, y: 452, w: 752, h: 226, a: 4.5, b: 5.9 }],
      cursor: [[4.3, 1100, 300], [4.9, 700, 474, 1], [5.2, 700, 515, 1], [5.5, 700, 555, 1], [6.1, 716, 699, 1]] },
    { id: "c16-record-saved", a: 6.6, b: 7.7, from: [900, 1560, 1.3], to: [900, 1580, 1.3], rings: [{ x: 650, y: 1598, w: 128, h: 28, a: 6.8, b: 7.7 }] },
    { id: "c16-record-saved", a: 7.6, b: 8.6, from: [900, 420, 1.25], to: [900, 420, 1.3], rings: [{ x: 648, y: 328, w: 384, h: 38, a: 7.8, b: 8.6 }] },
    { id: "c17-new-blank-variant", a: 8.5, b: 10.1, from: [1020, 500, 1.15], to: [1020, 540, 1.4], rings: [{ x: 1245, y: 612, w: 160, h: 38, a: 9.0, b: 10.1 }],
      cursor: [[8.6, 900, 500], [9.5, 1320, 630, 1]] },
    { id: "c18-prepare-from-topic", a: 10.0, b: 11.8, from: [1020, 560, 1.15], to: [1020, 600, 1.35], rings: [{ x: 650, y: 590, w: 752, h: 70, a: 10.1, b: 11.0 }],
      cursor: [[10.4, 1100, 500], [11.4, 716, 702, 1]] },
    { id: "c19-topic-review", a: 11.7, b: 13.9, from: [1020, 780, 1.2], to: [1020, 900, 1.15], rings: [{ x: 640, y: 741, w: 780, h: 314, a: 11.9, b: 13.0 }],
      cursor: [[12.0, 1100, 780], [13.4, 716, 1075, 1]] },
    { id: "c20-built-stack", a: 13.8, b: 16.3, from: [420, 330, 1.5], to: [430, 400, 1.5], rings: [{ x: 250, y: 584, w: 164, h: 26, a: 14.8, b: 16.2 }] },
    { id: "c21-approvals-request", a: 16.2, b: 19.7, from: [720, 405, 1.0], to: [780, 470, 1.15], sy: 540, sy2: 440,
      rings: [{ x: 246, y: 196, w: 364, h: 84, a: 16.5, b: 17.6 }, { x: 648, y: 240, w: 765, h: 32, a: 17.2, b: 18.3 }, { x: 648, y: 731, w: 148, h: 48, a: 18.4, b: 19.7 }],
      cursor: [[17.9, 1000, 560], [19.1, 722, 755, 1]] },
    { id: "c22-approvals-approved", a: 19.6, b: 22, from: [780, 470, 1.15], to: [780, 470, 1.19], sy: 440, rings: [{ x: 796, y: 204, w: 94, h: 28, a: 19.9, b: 21.6 }] },
  ]);
});

// ---------------------------------------------------------------- S09 · the send is planned first
defScene("S09", "light", 0, (root, s) => {
  // each step is cropped to its own card, so the lines of step 2 never show
  return shotScene(root, s, [
    { id: "c23-send-step1", a: 0, b: 3.5, fade: 0, crop: [620, 20, 1440, 640], shadow: false, from: [1030, 330, 1.16], to: [1030, 330, 1.22], rings: [{ x: 650, y: 92, w: 230, h: 26, a: 0.9, b: 2.4 }] },
    { id: "c24-send-plan", a: 3.3, b: 6.9, crop: [620, 290, 1440, 790], shadow: false, from: [1030, 540, 1.275], to: [1030, 540, 1.32],
      rings: [{ x: 641, y: 502, w: 352, h: 30, a: 3.9, b: 5.6 }], cursor: [[4.4, 1100, 420], [6.3, 708, 759, 1]] },
    { id: "c25-send-ready", a: 6.7, b: 10, crop: [620, 1052, 1440, 1175], shadow: false, from: [1030, 1113, 1.5], to: [1030, 1113, 1.56],
      rings: [{ x: 650, y: 1072, w: 400, h: 26, a: 7.1, b: 8.8 }], cursor: [[7.6, 1200, 1070], [8.9, 703, 1128, 1]] },
  ]);
});

// ---------------------------------------------------------------- S10 · exactly what each person got
// a drawn state the demo cannot produce: a send that looks stranded, in the app's own look (a drawing, noted in CAPTURE-LOG's spirit)
function drawStranded(wrap) {
  const pane = mk("div", "abs", wrap, { left: "613px", top: 0, width: "827px", height: "810px", background: "#fcf8f2" });
  const hi = mk("div", "abs", wrap, { left: "240px", top: "137px", width: "363px", height: "76px", background: "rgb(220,234,239)", borderRadius: "14px", mixBlendMode: "multiply" });
  const box = mk("div", "abs", pane, { left: "23px", top: 0, width: "760px", height: "800px", font: "14px/1.5 var(--font)", color: INK });
  box.innerHTML = `<div style="position:absolute;left:0;top:24px;font:650 27px var(--font)">Hüttensaison-Finale</div>
    <div style="position:absolute;left:0;top:78px;font:600 19px var(--font)">This send looks stranded</div>
    <div style="position:absolute;left:-17px;top:106px;width:762px;border:2px solid #b8860b;border-radius:10px;background:#fff">
      <div style="padding:16px 20px;font-size:14.5px;line-height:1.5">It is still marked sending, but nothing has happened since 17 Oct 2026, 23:31. The process sending it may have stopped. Releasing it marks it failed so it can be retried: a retry skips everyone already sent to, marks the person in flight as uncertain (never sent again), and sends the rest.</div>
      <div style="border-top:1px solid #e4daca;padding:12px 20px"><span id="release" style="display:inline-block;border:1px solid #d9cfbf;border-radius:6px;padding:6px 14px;font-size:14px;background:#fff">Release this send</span></div></div>
    <div style="position:absolute;left:-17px;top:262px;width:762px;border:1px solid #e4daca;border-radius:10px;background:#fff">${[["Status", "sending"], ["Audience", "Interesse: Familie & Kinder"], ["Provider", "mock"], ["Recipients", "177"], ["Sent", "171"], ["Failed", "0"], ["Excluded", "0"]]
      .map(([k, v], i) => `<div style="display:flex;padding:8px 20px;${i ? "border-top:1px solid #efe7da;" : ""}"><span style="width:200px;color:#62594e">${k}</span><span>${v}</span></div>`).join("")}</div>`;
}
defScene("S10", "light", 0, (root, s) => {
  const sh = shotScene(root, s, [
    { id: "c04-as-sent-127", a: 0, b: 3.2, fade: 0, crop: [630, 311, 1420, 378], shadow: false, from: [1025, 345, 1.5], to: [1025, 345, 1.6], rings: [{ x: 640, y: 313, w: 772, h: 62, a: 0.8, b: 3.0 }] },
    { id: "c04-as-sent-127", a: 3.0, b: 6.4, crop: [630, 458, 1420, 1150], shadow: false, from: [1025, 804, 0.92], to: [1025, 804, 0.98], sy: 520 },
    { id: "c05-slot-reasons", a: 6.2, b: 9.2, from: [1000, 405, 1.0], to: [1020, 420, 1.3], rings: [{ x: 650, y: 383, w: 745, h: 52, a: 6.8, b: 9.0 }] },
    { id: "c01-deliveries-list", a: 9.0, b: 12, draw: drawStranded, from: [800, 330, 1.15], to: [820, 330, 1.25], rings: [{ x: 649, y: 177, w: 130, h: 36, a: 10.0, b: 12 }],
      cursor: [[9.4, 1200, 480], [10.7, 712, 199, 1]] },
  ]);
  const p = pill(root, "The content this reader received.", 3.6, 6.4);
  return (T, t) => { sh(T, t); p(t); };
});

// ---------------------------------------------------------------- S11 · the signal comes back
defScene("S11", "light", 0, (root, s) => {
  const tbl = mkShot(root, { id: "c26-results", a: 0, b: 4.6, fade: 0, crop: [636, 200, 1307, 438], shadow: false, from: [972, 319, 1.0], to: [972, 319, 1.06], sx: 500, sy: 470 });
  fadeRight(tbl.L, 1307);
  // the decaying weight of one click: weight x 0.5 ^ (age / half-life), half-life 45 days
  const card = mk("div", "abs", root, { left: "1010px", top: "240px", width: "810px", height: "500px", background: "#fff", border: `2px solid ${LINE}`, borderRadius: "22px", opacity: 0 });
  const X0 = 70, Y0 = 410, XW = 690, YH = 285;
  const pts = []; for (let d = 0; d <= 135; d += 3) pts.push([X0 + d / 135 * XW, Y0 - 5 * Math.pow(0.5, d / 45) / 5 * YH]);
  const path = pts.map((q, i) => (i ? "L" : "M") + q[0].toFixed(1) + " " + q[1].toFixed(1)).join(" ");
  const hl = [X0 + 45 / 135 * XW, Y0 - 0.5 * YH];
  card.innerHTML = `<svg width="810" height="500" viewBox="0 0 810 500" style="position:absolute;left:0;top:0">
    <line x1="${X0}" y1="${Y0}" x2="${X0 + XW}" y2="${Y0}" stroke="${LINE}" stroke-width="3"/><line x1="${X0}" y1="${Y0}" x2="${X0}" y2="${Y0 - YH - 10}" stroke="${LINE}" stroke-width="3"/>
    <path id="curve" d="${path}" fill="none" stroke="${PET}" stroke-width="6" stroke-linecap="round" stroke-dasharray="1400" stroke-dashoffset="1400"/>
    <circle id="hl" cx="${hl[0]}" cy="${hl[1]}" r="9" fill="${PET}" opacity="0"/>
    <text x="${X0}" y="48" font-size="30" font-weight="650" fill="${INK}" font-family="-apple-system, system-ui, sans-serif">One click, as time passes</text>
    <text x="${X0 + XW}" y="${Y0 + 44}" font-size="24" fill="${MUTED}" text-anchor="end" font-family="-apple-system, system-ui, sans-serif">age</text>
    <text x="${X0 + 10}" y="${Y0 - YH - 20}" font-size="22" fill="${MUTED}" font-family="-apple-system, system-ui, sans-serif">weight</text>
    <text id="hlt" x="${hl[0] + 18}" y="${hl[1] - 12}" font-size="24" fill="${INK}" opacity="0" font-family="-apple-system, system-ui, sans-serif">half-life</text></svg>`;
  const curve = card.querySelector("#curve"), hlc = card.querySelector("#hl"), hlt = card.querySelector("#hlt");
  const slot = shotScene(root, s, [
    { id: "c03-slot-detail", a: 4.5, b: 8, fade: 0.4, from: [1020, 1000, 1.25], to: [1020, 1000, 1.3], rings: [{ x: 652, y: 862, w: 748, h: 36, a: 4.9, b: 6.2 }, { x: 652, y: 897, w: 748, h: 36, a: 6.0, b: 8 }] },
  ]);
  const p = pill(root, "Clicks count. They fade.", 0.8, 7.4);
  return (T, t) => {
    const on = t < 4.7;
    tbl.box.style.display = on ? "block" : "none";
    card.style.display = on ? "block" : "none";
    if (on) {
      updShot(tbl, t);
      card.style.opacity = ease(t, 1.3, 1.8) * (1 - ease(t, 4.3, 4.7));
      curve.style.strokeDashoffset = 1400 * (1 - ease(t, 1.8, 3.8));
      hlc.setAttribute("opacity", ease(t, 3.8, 4.0)); hlt.setAttribute("opacity", ease(t, 3.8, 4.0));
    }
    slot(T, t);
    p(t);
  };
});

// ---------------------------------------------------------------- S17 · email and push, split screen
defScene("S17", "light", 0, (root, s) => {
  const left = mk("div", "abs", root, { left: 0, top: 0, width: "950px", height: "1080px", overflow: "hidden", background: LINEN });
  const mkSide = (id, a, b, o) => { const L = layer(left, id, { shadow: false }); if (o.crop) crop(L, ...o.crop); return Object.assign({ id, a, b, L }, o); };
  const sides = [
    mkSide("c35-campaign-two-variants", 0, 4.4, { from: [1020, 440, 0.92], to: [1020, 750, 0.92] }),
    mkSide("c36-push-editor", 4.2, 8.2, { from: [1020, 330, 0.92], to: [1020, 400, 0.98] }),
    mkSide("c37-push-preview", 8.0, 12, { crop: [530, 400, 1330, 500], from: [930, 450, 0.9], to: [930, 450, 0.95] }),
  ];
  const right = mk("div", "abs", root, { left: "970px", top: 0, width: "950px", height: "1080px", background: "#14110f" });
  mk("div", "abs", root, { left: "950px", top: 0, width: "20px", height: "1080px", background: "#cfc5b5" });
  const code = codePane(right, "python", D.code["backend/app/delivery/providers/example_push.py"].text, { x: 20, y: 130, r: 10, b: 140, fs: 19, from: 17 });
  const lab = text(right, "example_push.py", { left: "40px", top: "56px", font: "500 30px var(--mono)", color: DACC });
  const pl = pill(root, "mock (nothing is sent)", 8.6, 11.8, { left: 0, right: "970px", top: "940px" });
  EVENTS.push(s.start + 4.2, s.start + 8.0);
  return (T, t) => {
    sides.forEach(sd => {
      const vis = t >= sd.a && t < sd.b + 0.4;
      sd.L.wrap.style.display = vis ? "block" : "none";
      if (!vis) return;
      sd.L.wrap.style.opacity = sd.a === 0 ? 1 : ease(t, sd.a, sd.a + 0.35);
      const k = ease(t, sd.a, sd.b), f = sd.from, e = sd.to;
      cam(sd.L, lerp(f[0], e[0], k), lerp(f[1], e[1], k), lerp(f[2], e[2], k), 475, 540, false);
    });
    code.reveal(clamp((t - 0.4) / 2.2, 0, 1) * code.n);
    code.mark(20, 20, t > 4.4 && t < 6.0);
    pl(t);
  };
});

// ---------------------------------------------------------------- S18 · everything else, in one breath
defScene("S18", "light", 0, (root, s) => {
  // the shots follow the words: Audiences, Brands, Roles, Consent, a record of who did what, all in one place
  const shots = [
    ["c40-audiences-rules", 0.0, 1.0, 720, 137], ["c42-brand-profile", 1.0, 1.55, 900, 405], ["c44-roles-list", 1.55, 2.05, 420, 330], ["c41-recipients-list", 2.05, 2.7, 1000, 405],
    ["c38-approvals-history", 2.7, 4.5, 900, 405], ["c39-monitoring", 4.5, 5.5, 900, 405], ["c01-deliveries-list", 5.5, 6.5, 420, 300],
    ["c43-personalisation", 6.5, 7.5, 900, 405], ["c45-integration-matrix", 7.5, 8.5, 1000, 420], ["c46-ai-prompts", 8.5, 10, 420, 330],
  ];
  return shotScene(root, s, shots.map(([id, a, b, x, y]) => id === "c40-audiences-rules"
    ? { id, a, b, fade: 0, hold: 0, from: [720, 137, 0.85], to: [720, 137, 0.9], sy: 480, clamp: false, lin: true }
    : id === "c38-approvals-history"
    // the history's outcome line counts 123 delivered; the film shows 122 delivered elsewhere, so the line is covered (it is the app's own text)
    ? { id, a, b, fade: 0, hold: 0, from: [720, 405, 1.0], to: [x, y, 1.1], lin: true, draw: w => mk("div", "abs", w, { left: "578px", top: "188px", width: "205px", height: "40px", background: "#fff" }) }
    : { id, a, b, fade: 0, hold: 0, from: [720, 405, 1.0], to: [x, y, 1.1], lin: true }));
});
