// Render every frame of the film:  node render.mjs [--workers 8] [--from S] [--to S] [--fps 24]
// Frames land in out/frames/f000000.jpg and so on; the frame at index i shows the film at time i / fps.
import { chromium } from "playwright";
import fs from "node:fs";
import { serve } from "./serve.mjs";

const arg = (k, d) => { const i = process.argv.indexOf("--" + k); return i > 0 ? Number(process.argv[i + 1]) : d; };
const WORKERS = arg("workers", 8), FPS = arg("fps", 24);
const data = JSON.parse(fs.readFileSync("data/timeline.json", "utf8"));
const from = Math.round(arg("from", 0) * FPS), to = Math.round(arg("to", data.total) * FPS);
fs.mkdirSync("out/frames", { recursive: true });
const { server, url } = await serve();
const browser = await chromium.launch({ channel: "chrome" });
let next = from, done = 0;
const total = to - from, t0 = Date.now();
const CHUNK = 12;
async function worker() {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1, colorScheme: "light" });
  page.on("pageerror", e => console.log("pageerror:", e.message));
  await page.goto(url);
  await page.evaluate(() => window.__ready);
  for (;;) {
    const a = next; next += CHUNK;
    if (a >= to) break;
    for (let i = a; i < Math.min(a + CHUNK, to); i++) {
      await page.evaluate(t => window.render(t), i / FPS);
      await page.screenshot({ path: `out/frames/f${String(i).padStart(6, "0")}.jpg`, type: "jpeg", quality: 92 });
      done++;
    }
    if (done % 240 < CHUNK) {
      const el = (Date.now() - t0) / 1000;
      console.log(`${done}/${total} frames, ${(done / el).toFixed(1)} fps, about ${Math.round((total - done) / (done / el))} s left`);
    }
  }
  await page.close();
}
await Promise.all(Array.from({ length: WORKERS }, worker));
await browser.close();
server.close();
console.log(`done: ${total} frames in ${Math.round((Date.now() - t0) / 1000)} s`);
