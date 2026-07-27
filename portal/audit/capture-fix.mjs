// Targeted re-capture: ready-to-issue ConfirmModal + issue-btn micro + registry mint (operators tab)
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as FX from "./fixtures.mjs";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(__dirname, "screenshots");
const APP = "http://localhost:5173";
const BATCH_UUID = "batch-0001-uuid-abcdef012345";
const CORS = { "access-control-allow-origin": "*", "access-control-allow-methods": "GET,POST,PATCH,PUT,DELETE,OPTIONS", "access-control-allow-headers": "authorization,content-type" };
const json = (b, s = 200) => ({ status: s, headers: { ...CORS, "content-type": "application/json" }, body: JSON.stringify(b) });
const manifest = [];

function readyDetail() {
  const d = FX.batchDetail("default");
  d.batch.status = "RECEIVED"; // issuable but NOT yet issued -> Issue button renders
  return d;
}

async function ctxFor(browser, theme) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await context.addInitScript((t) => {
    localStorage.setItem("tc_theme", t);
    localStorage.setItem("dmrv.portal.token", "mock");
    localStorage.setItem("dmrv.portal.role", "admin");
  }, theme);
  await context.route("**/api/v1/portal/**", async (route) => {
    const req = route.request(); const url = new URL(req.url()); const p = url.pathname;
    if (req.method() === "OPTIONS") return route.fulfill({ status: 204, headers: CORS });
    if (/\/media\/[^/]+$/.test(p) && req.method() === "GET")
      return route.fulfill({ status: 200, headers: { ...CORS, "content-type": "image/jpeg" }, body: Buffer.from(FX.JPEG_B64, "base64") });
    if (/\/batches\/[^/]+$/.test(p)) return route.fulfill(json(readyDetail()));
    if (p.endsWith("/registry/kilns") && req.method() === "GET") return route.fulfill(json(FX.kilns()));
    if (p.endsWith("/tokens")) return route.fulfill(json(FX.mintTokenResp));
    if (p.endsWith("/registry-configs")) return route.fulfill(json(FX.registryConfigs));
    return route.fulfill(json({}));
  });
  await context.route(/https?:\/\/(?!localhost)/, (r) => r.abort());
  return context;
}

const browser = await chromium.launch();
for (const theme of ["light", "dark"]) {
  const context = await ctxFor(browser, theme);
  const page = await context.newPage();

  // 1) ready-to-issue hero + ConfirmModal mid-token
  await page.goto(APP + `/batches/${BATCH_UUID}`);
  try { await page.waitForLoadState("networkidle", { timeout: 8000 }); } catch {}
  await page.waitForTimeout(600);
  const dir = path.join(OUT, "batch-detail", theme, "1440x900");
  fs.mkdirSync(dir, { recursive: true });
  await page.screenshot({ path: path.join(dir, "ready-to-issue.png"), fullPage: true });
  manifest.push({ screenshot: `screenshots/batch-detail/${theme}/1440x900/ready-to-issue.png`, route: "batch-detail", theme, viewport: "1440x900", state: "ready-to-issue", role: "admin" });

  const issueBtn = page.getByRole("button", { name: /^issue credit$/i }).first();
  // micro shots of the issue button
  const mdir = path.join(OUT, "_micro", theme);
  fs.mkdirSync(mdir, { recursive: true });
  for (const [name, action] of [["issue-btn-default", null], ["issue-btn-hover", "hover"], ["issue-btn-focus", "focus"]]) {
    try {
      if (action === "hover") await issueBtn.hover();
      if (action === "focus") await issueBtn.focus();
      await page.waitForTimeout(200);
      const box = await issueBtn.boundingBox();
      await page.screenshot({ path: path.join(mdir, `${name}.png`), clip: { x: box.x - 24, y: box.y - 24, width: box.width + 48, height: box.height + 48 } });
      manifest.push({ screenshot: `screenshots/_micro/${theme}/${name}.png`, route: "micro", theme, viewport: "1440x900", state: name, role: "admin" });
    } catch (e) { manifest.push({ route: "micro", state: name, theme, error: String(e) }); }
  }
  try {
    await issueBtn.click({ timeout: 3000 });
    await page.waitForTimeout(400);
    const input = page.locator("[role=dialog] input").first();
    await input.fill("ISSUE-ba");
    await page.waitForTimeout(250);
    await page.screenshot({ path: path.join(dir, "confirm-modal-mid-token.png"), fullPage: true });
    manifest.push({ screenshot: `screenshots/batch-detail/${theme}/1440x900/confirm-modal-mid-token.png`, route: "batch-detail", theme, viewport: "1440x900", state: "confirm-modal-mid-token", role: "admin" });
    // also matching token state
    await input.fill(`ISSUE-batch-`);
    await page.waitForTimeout(250);
    await page.screenshot({ path: path.join(dir, "confirm-modal-token-match.png"), fullPage: false });
    manifest.push({ screenshot: `screenshots/batch-detail/${theme}/1440x900/confirm-modal-token-match.png`, route: "batch-detail", theme, viewport: "1440x900", state: "confirm-modal-token-match", role: "admin" });
    await page.keyboard.press("Escape");
  } catch (e) { manifest.push({ route: "batch-detail", state: "confirm-modal-mid-token", theme, error: String(e) }); }

  // 2) registry mint (operators tab)
  await page.goto(APP + "/registry");
  try { await page.waitForLoadState("networkidle", { timeout: 8000 }); } catch {}
  await page.waitForTimeout(400);
  try {
    await page.getByRole("tab", { name: /operator training/i }).click({ timeout: 3000 });
    await page.waitForTimeout(400);
    const rdir = path.join(OUT, "registry", theme, "1440x900");
    fs.mkdirSync(rdir, { recursive: true });
    await page.screenshot({ path: path.join(rdir, "operators-tab.png"), fullPage: true });
    manifest.push({ screenshot: `screenshots/registry/${theme}/1440x900/operators-tab.png`, route: "registry", theme, viewport: "1440x900", state: "operators-tab", role: "admin" });
    await page.getByRole("button", { name: /mint enrollment token/i }).click({ timeout: 3000 });
    await page.waitForTimeout(700);
    await page.screenshot({ path: path.join(rdir, "token-minted.png"), fullPage: true });
    manifest.push({ screenshot: `screenshots/registry/${theme}/1440x900/token-minted.png`, route: "registry", theme, viewport: "1440x900", state: "token-minted", role: "admin" });
  } catch (e) { manifest.push({ route: "registry", state: "token-minted", theme, error: String(e) }); }

  await context.close();
  console.log("fix pass done:", theme);
}
await browser.close();
const mPath = path.join(__dirname, "manifest.json");
let prev = []; try { prev = JSON.parse(fs.readFileSync(mPath, "utf8")); } catch {}
// drop old error rows for the states we just recaptured
prev = prev.filter((p) => !(p.error && ["confirm-modal-mid-token", "token-minted", "issue-btn-default", "issue-btn-hover", "issue-btn-focus"].includes(p.state)));
fs.writeFileSync(mPath, JSON.stringify([...prev, ...manifest], null, 2));
console.log("manifest updated:", prev.length + manifest.length);
