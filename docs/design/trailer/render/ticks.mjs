// Where the mix puts its ticks: one per press and per cut that the scenes announce.  node ticks.mjs  ->  data/ticks.json
// Then:  TICKS_JSON=data/ticks.json python3 ../animatic/tools/mix_eleven.py <narration wav44> <music> <sfx> out/mix-ticks
import { chromium } from "playwright";
import fs from "node:fs";
import { serve } from "./serve.mjs";

const HITS = [3.0, 5.8, 8.6, 23.5, 64.0, 179.0, 191.0, 203.0, 215.0, 221.0, 266.0];
const { server, url } = await serve();
const browser = await chromium.launch({ channel: "chrome" });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
await page.goto(url + "?caps=0");
await page.evaluate(() => window.__ready);
const raw = await page.evaluate(() => EVENTS.slice());
await browser.close(); server.close();
const sorted = [...new Set(raw.map(t => Math.round(t * 100) / 100))].sort((a, b) => a - b);
const ticks = [];
for (const t of sorted) {
  if (t < 14 || t > 285) continue;                                     // the hook has drone and hits only
  if (ticks.length && t - ticks[ticks.length - 1] < 0.4) continue;     // one tick for a press and its cut
  if (HITS.some(h => Math.abs(h - t) < 0.3)) continue;                  // a low hit already marks this moment
  ticks.push(t);
}
fs.writeFileSync("data/ticks.json", JSON.stringify({ ticks }, null, 1));
console.log(ticks.length, "ticks");
