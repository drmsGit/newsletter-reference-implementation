"use strict";
// The three lines (S19) and the end card (S20).

defScene("S19", "light", 0, (root, s) => {
  const P = D.parts.S19;
  const lines = ["See what it does.", "Change it with a file.", "Keep the core."].map((str, i) =>
    text(root, str, { left: "230px", top: (250 + i * 205) + "px", font: "650 138px var(--font)", color: i === 2 ? PET : INK, letterSpacing: "-.02em", whiteSpace: "nowrap", opacity: 0 }));
  return T => {
    lines.forEach((e, i) => {
      const a = P[i].start - 0.05, k = ease(T, a, a + 0.4);
      e.style.opacity = k; e.style.transform = `translateY(${(1 - k) * 26}px)`;
    });
  };
});

defScene("S20", "light", 0, (root, s) => {
  const A = mk("div", "abs", root, { left: 0, top: 0, width: "1920px", height: "1080px", transformOrigin: "50% 0" });
  const name = text(A, D.name, { left: 0, right: 0, top: "330px", textAlign: "center", font: "650 78px var(--font)", color: INK, letterSpacing: "-.015em", opacity: 0 });
  const rule = mk("div", "abs", A, { left: "760px", top: "485px", width: "400px", height: "3px", background: PET, transform: "scaleX(0)", transformOrigin: "50% 50%" });
  const tag = text(A, "Building a communication system you control.", { left: 0, right: 0, top: "520px", textAlign: "center", font: "400 40px var(--font)", color: MUTED, opacity: 0 });
  const by = text(A, "By Diede Slembrouck", { left: 0, right: 0, top: "600px", textAlign: "center", font: "500 30px var(--font)", color: MUTED, letterSpacing: ".04em", opacity: 0 });
  const adapt = text(A, "Always adapting to your business.", { left: 0, right: 0, top: "672px", textAlign: "center", font: "500 38px var(--font)", color: PET, opacity: 0 });
  const three = ["The playbook.", "The working code.", "A conversation."].map((str, i) =>
    text(root, str, { left: 0, right: 0, top: (470 + i * 96) + "px", textAlign: "center", font: "650 66px var(--font)", color: INK, letterSpacing: "-.01em", opacity: 0 }));
  const addr = text(root, "linkedin.com/in/diede-slembrouck", { left: 0, right: 0, top: "776px", textAlign: "center", font: "500 40px var(--mono)", color: PET, opacity: 0 });
  const small = text(root, "A local proof of concept. Email and push built. Demo data is fictional.", { left: 0, right: 0, top: "1004px", textAlign: "center", font: "400 25px var(--font)", color: MUTED, opacity: 0 });
  return T => {
    name.style.opacity = ease(T, 268.4, 269.1); name.style.transform = `translateY(${(1 - ease(T, 268.4, 269.1)) * 14}px)`;
    const g = ease(T, 268.8, 269.5); rule.style.transform = `scaleX(${g})`;
    tag.style.opacity = ease(T, 268.9, 269.6);
    by.style.opacity = ease(T, 270.0, 270.7);
    adapt.style.opacity = ease(T, 271.64, 272.3);
    const up = ease(T, 274.4, 275.6);
    A.style.transform = `translateY(${-160 * up}px) scale(${1 - 0.18 * up})`;
    three.forEach((e, i) => { const a = 275.6 + i * 1.3, k = ease(T, a, a + 0.45); e.style.opacity = k; e.style.transform = `translateY(${(1 - k) * 18}px)`; });
    addr.style.opacity = ease(T, 279.2, 279.8);
    small.style.opacity = ease(T, 279.2, 279.8);
  };
});
