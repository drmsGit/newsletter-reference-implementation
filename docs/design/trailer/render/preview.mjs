// Draw single frames to look at them:  node preview.mjs <seconds> [<seconds> ...]   ->  out/preview/t<seconds>.jpg
// Add --nocaps to leave the captions off.
import { chromium } from "playwright";
import fs from "node:fs";
import { serve } from "./serve.mjs";

const args = process.argv.slice(2);
const caps = !args.includes("--nocaps");
const times = args.filter(a => !a.startsWith("--")).map(Number);
fs.mkdirSync("out/preview", { recursive: true });
const { server, url } = await serve();
const browser = await chromium.launch({ channel: "chrome" });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1, colorScheme: "light" });
page.on("console", m => { if (m.type() === "error") console.log("console:", m.text()); });
page.on("pageerror", e => console.log("pageerror:", e.message));
await page.goto(url + (caps ? "" : "?caps=0"));
await page.evaluate(() => window.__ready);
for (const T of times) {
  await page.evaluate(t => window.render(t), T);
  await page.screenshot({ path: `out/preview/t${String(T).padStart(7, "0")}.jpg`, type: "jpeg", quality: 90 });
  console.log("t", T);
}
await browser.close();
server.close();
