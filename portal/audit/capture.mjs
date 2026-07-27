// Playwright capture harness for the TerraCipher portal UI/UX audit.
// Mock-first: all /api/v1/portal/* requests are fulfilled from fixtures.mjs
// (typed against src/api.ts). No backend needed.
//
// Usage:  node audit/capture.mjs [base|states|print|micro|all]
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as FX from "./fixtures.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(__dirname, "screenshots");
const APP = "http://localhost:5173";
const manifest = [];

const VIEWPORTS = [
  { name: "1440x900", width: 1440, height: 900 },
  { name: "1280x800", width: 1280, height: 800 },
  { name: "768x1024", width: 768, height: 1024 },
  { name: "390x844", width: 390, height: 844 },
];

const BATCH_UUID = "batch-0001-uuid-abcdef012345";
const ROUTES = [
  { name: "login", path: "/login", authed: false },
  { name: "dashboard", path: "/dashboard" },
  { name: "batches", path: "/batches" },
  { name: "batch-detail", path: `/batches/${BATCH_UUID}` },
  { name: "lab-scan", path: "/lab/scan" },
  { name: "lab-entry", path: `/lab/${BATCH_UUID}` },
  { name: "registry", path: "/registry" },
  { name: "projects", path: "/projects" },
  { name: "farmers", path: "/farmers" },
  { name: "dispatch", path: "/dispatch" },
];

const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET,POST,PATCH,PUT,DELETE,OPTIONS",
  "access-control-allow-headers": "authorization,content-type",
};

function json(body, status = 200) {
  return { status, headers: { ...CORS, "content-type": "application/json" }, body: JSON.stringify(body) };
}

// scenario: default | empty | overflow | error | provisional | single
// opts.delayMs: hold every response (loading-state capture)
async function mockApi(context, scenario = "default", opts = {}) {
  await context.route("**/api/v1/portal/**", async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const p = url.pathname;
    const method = req.method();

    if (method === "OPTIONS") return route.fulfill({ status: 204, headers: CORS });
    if (opts.delayMs) await new Promise((r) => setTimeout(r, opts.delayMs));
    if (scenario === "error" && method === "GET")
      return route.fulfill(json({ detail: "internal server error" }, 500));

    // media bytes
    if (/\/media\/[^/]+$/.test(p) && method === "GET")
      return route.fulfill({
        status: 200,
        headers: { ...CORS, "content-type": "image/jpeg" },
        body: Buffer.from(FX.JPEG_B64, "base64"),
      });

    if (p.endsWith("/login")) return route.fulfill(json(FX.loginResp));
    if (p.endsWith("/logout")) return route.fulfill(json({}));
    if (p.endsWith("/summary"))
      return route.fulfill(json(scenario === "empty" ? FX.summaryEmpty : FX.summary));
    if (p.endsWith("/metrics/credit-timeseries")) {
      const bucket = url.searchParams.get("bucket") || "month";
      return route.fulfill(
        json(scenario === "empty" ? FX.creditTimeseriesEmpty(bucket) : FX.creditTimeseries(bucket)),
      );
    }
    if (p.endsWith("/metrics/quality"))
      return route.fulfill(json(scenario === "empty" ? FX.qualityMetricsEmpty : FX.qualityMetrics));

    if (/\/batches\/[^/]+\/issue$/.test(p))
      return route.fulfill(json({ status: "ISSUED", net_credit_t_co2e: 42.318 }));
    if (/\/batches\/[^/]+\/export\//.test(p))
      return route.fulfill(json({ report: "mock", batch_uuid: BATCH_UUID }));
    if (/\/batches\/[^/]+\/lab-results$/.test(p))
      return route.fulfill(json({ status: "ok", provisional: false, reasons: [] }));
    if (/\/batches\/[^/]+\/lab-certificate$/.test(p))
      return route.fulfill(json({ operation_id: "op-cert-1", sha256_hash: "b".repeat(64) }));
    if (/\/batches\/[^/]+$/.test(p))
      return route.fulfill(json(FX.batchDetail(scenario === "provisional" ? "provisional" : "default")));
    if (p.endsWith("/batches")) return route.fulfill(json(FX.batches(scenario)));

    if (/\/media\/[^/]+\/verify$/.test(p))
      return route.fulfill(json({ operation_id: "op-x", verification_status: "approved", verification_remarks: null }));

    if (p.endsWith("/registry/kilns") && method === "GET") return route.fulfill(json(FX.kilns(scenario)));
    if (p.includes("/registry/") && method === "POST") return route.fulfill(json({ ok: true }));
    if (p.endsWith("/registry-configs")) return route.fulfill(json(FX.registryConfigs));
    if (p.endsWith("/tokens") && method === "POST") return route.fulfill(json(FX.mintTokenResp));

    if (p.endsWith("/projects") && method === "GET") return route.fulfill(json(FX.projects(scenario)));
    if (p.endsWith("/projects") && method === "POST")
      return route.fulfill(json(FX.projects().projects[0]));
    if (p.endsWith("/parcels") && method === "GET") return route.fulfill(json(FX.parcels(scenario)));
    if (p.endsWith("/parcels") && method === "POST") return route.fulfill(json(FX.parcels().parcels[0]));

    if (/\/farmers\/[^/]+$/.test(p)) return route.fulfill(json(FX.farmerDetail));
    if (p.endsWith("/farmers")) return route.fulfill(json(FX.farmers(scenario)));

    if (p.endsWith("/facilities") && method === "GET") return route.fulfill(json(FX.facilities(scenario)));
    if (p.endsWith("/facilities") && method === "POST") return route.fulfill(json(FX.facilities().facilities[0]));
    if (p.endsWith("/dispatch")) return route.fulfill(json(FX.dispatch(scenario)));

    return route.fulfill(json({ detail: `unmocked: ${method} ${p}` }, 404));
  });
  // Block external map tiles etc. — deterministic screenshots.
  await context.route(/https?:\/\/(?!localhost)/, (route) => route.abort());
}

async function newPage(browser, { viewport, theme, role, authed = true }) {
  const context = await browser.newContext({ viewport, reducedMotion: "no-preference" });
  await context.addInitScript(
    ({ theme, role, authed }) => {
      localStorage.setItem("tc_theme", theme);
      if (authed) {
        localStorage.setItem("dmrv.portal.token", "mock-bearer-token");
        localStorage.setItem("dmrv.portal.role", role);
      }
    },
    { theme, role, authed },
  );
  return context;
}

async function shoot(page, { route, theme, viewport, state, role, note }) {
  const dir = path.join(OUT, route, theme, viewport);
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, `${state}${role === "verifier" ? ".verifier" : ""}.png`);
  await page.screenshot({ path: file, fullPage: true });
  manifest.push({
    screenshot: path.relative(path.join(__dirname), file).replace(/\\/g, "/"),
    route, theme, viewport, state, role, note: note || null,
  });
  return file;
}

async function settle(page, ms = 700) {
  try { await page.waitForLoadState("networkidle", { timeout: 8000 }); } catch {}
  await page.waitForTimeout(ms);
}

// ---------- base grid: routes x viewports x themes x roles ----------
async function baseGrid(browser) {
  for (const role of ["admin", "verifier"]) {
    for (const theme of ["light", "dark"]) {
      for (const vp of VIEWPORTS) {
        const context = await newPage(browser, { viewport: vp, theme, role });
        await mockApi(context, "default");
        const page = await context.newPage();
        for (const r of ROUTES) {
          if (r.authed === false) {
            // login page unauthenticated
            const c2 = await newPage(browser, { viewport: vp, theme, role, authed: false });
            await mockApi(c2, "default");
            const p2 = await c2.newPage();
            await p2.goto(APP + r.path);
            await settle(p2);
            await shoot(p2, { route: r.name, theme, viewport: vp.name, state: "default", role });
            await c2.close();
            continue;
          }
          try {
            await page.goto(APP + r.path);
            await settle(page);
            await shoot(page, { route: r.name, theme, viewport: vp.name, state: "default", role });
          } catch (e) {
            manifest.push({ route: r.name, theme, viewport: vp.name, state: "default", role, error: String(e) });
          }
        }
        await context.close();
        console.log(`base grid done: role=${role} theme=${theme} vp=${vp.name}`);
      }
    }
  }
}

// ---------- state overlays at 1440, both themes ----------
async function states(browser) {
  const vp = VIEWPORTS[0];
  for (const theme of ["light", "dark"]) {
    // per-scenario captures on data routes
    const dataRoutes = ["dashboard", "batches", "batch-detail", "registry", "projects", "farmers", "dispatch"];
    for (const scenario of ["empty", "error", "overflow"]) {
      const context = await newPage(browser, { viewport: vp, theme, role: "admin" });
      await mockApi(context, scenario);
      const page = await context.newPage();
      for (const name of dataRoutes) {
        const r = ROUTES.find((x) => x.name === name);
        try {
          await page.goto(APP + r.path);
          await settle(page);
          await shoot(page, { route: r.name, theme, viewport: vp.name, state: scenario, role: "admin" });
        } catch (e) {
          manifest.push({ route: r.name, theme, viewport: vp.name, state: scenario, role: "admin", error: String(e) });
        }
      }
      await context.close();
      console.log(`states ${scenario} done theme=${theme}`);
    }

    // loading (delayed responses; shoot before data lands)
    {
      const context = await newPage(browser, { viewport: vp, theme, role: "admin" });
      await mockApi(context, "default", { delayMs: 6000 });
      const page = await context.newPage();
      for (const name of ["dashboard", "batches", "batch-detail", "farmers", "dispatch"]) {
        const r = ROUTES.find((x) => x.name === name);
        try {
          await page.goto(APP + r.path, { waitUntil: "commit" });
          await page.waitForTimeout(1500);
          await shoot(page, { route: r.name, theme, viewport: vp.name, state: "loading", role: "admin" });
        } catch (e) {
          manifest.push({ route: r.name, theme, viewport: vp.name, state: "loading", role: "admin", error: String(e) });
        }
      }
      await context.close();
      console.log(`states loading done theme=${theme}`);
    }

    // interactive states (default data)
    {
      const context = await newPage(browser, { viewport: vp, theme, role: "admin" });
      await mockApi(context, "default");
      const page = await context.newPage();

      // provisional batch detail (checklist failures + reasons)
      {
        const c = await newPage(browser, { viewport: vp, theme, role: "admin" });
        await mockApi(c, "provisional");
        const p = await c.newPage();
        await p.goto(APP + `/batches/${BATCH_UUID}`);
        await settle(p);
        await shoot(p, { route: "batch-detail", theme, viewport: vp.name, state: "provisional", role: "admin" });
        await c.close();
      }

      // batch-detail: ConfirmModal mid-token-entry + lightbox
      await page.goto(APP + `/batches/${BATCH_UUID}`);
      await settle(page);
      try {
        const issueBtn = page.getByRole("button", { name: /issue/i }).first();
        await issueBtn.click({ timeout: 4000 });
        await page.waitForTimeout(400);
        const input = page.locator(".modal-panel input, [role=dialog] input").first();
        try { await input.fill("batch-00", { timeout: 2500 }); } catch {}
        await shoot(page, { route: "batch-detail", theme, viewport: vp.name, state: "confirm-modal-mid-token", role: "admin" });
        await page.keyboard.press("Escape");
        await page.waitForTimeout(300);
      } catch (e) {
        manifest.push({ route: "batch-detail", theme, viewport: vp.name, state: "confirm-modal-mid-token", role: "admin", error: String(e) });
      }
      try {
        const thumb = page.locator(".media-img img, [class*=media] img").first();
        await thumb.click({ timeout: 4000 });
        await page.waitForTimeout(500);
        await shoot(page, { route: "batch-detail", theme, viewport: vp.name, state: "lightbox-open", role: "admin" });
        await page.keyboard.press("Escape");
      } catch (e) {
        manifest.push({ route: "batch-detail", theme, viewport: vp.name, state: "lightbox-open", role: "admin", error: String(e) });
      }

      // batches: active filters
      try {
        await page.goto(APP + "/batches");
        await settle(page);
        const search = page.locator("input").first();
        await search.fill("FIELD-KILN", { timeout: 3000 });
        const sel = page.locator("select").first();
        try { await sel.selectOption({ index: 1 }, { timeout: 2000 }); } catch {}
        await page.waitForTimeout(600);
        await shoot(page, { route: "batches", theme, viewport: vp.name, state: "filters-active", role: "admin" });
      } catch (e) {
        manifest.push({ route: "batches", theme, viewport: vp.name, state: "filters-active", role: "admin", error: String(e) });
      }

      // sidebar collapsed (dashboard)
      try {
        await page.goto(APP + "/dashboard");
        await settle(page);
        await page.getByRole("button", { name: /collapse sidebar/i }).click({ timeout: 3000 });
        await page.waitForTimeout(400);
        await shoot(page, { route: "dashboard", theme, viewport: vp.name, state: "sidebar-collapsed", role: "admin" });
        await page.getByRole("button", { name: /expand sidebar/i }).click({ timeout: 3000 });
      } catch (e) {
        manifest.push({ route: "dashboard", theme, viewport: vp.name, state: "sidebar-collapsed", role: "admin", error: String(e) });
      }

      // account menu open
      try {
        await page.getByRole("button", { name: /account menu/i }).click({ timeout: 3000 });
        await page.waitForTimeout(350);
        await shoot(page, { route: "dashboard", theme, viewport: vp.name, state: "account-menu-open", role: "admin" });
        await page.keyboard.press("Escape");
      } catch (e) {
        manifest.push({ route: "dashboard", theme, viewport: vp.name, state: "account-menu-open", role: "admin", error: String(e) });
      }

      // login: validation error (failed login)
      try {
        const c = await newPage(browser, { viewport: vp, theme, role: "admin", authed: false });
        await c.route("**/api/v1/portal/**", (route) => {
          if (route.request().method() === "OPTIONS") return route.fulfill({ status: 204, headers: CORS });
          return route.fulfill(json({ detail: "invalid credentials" }, 403));
        });
        const p = await c.newPage();
        await p.goto(APP + "/login");
        await settle(p, 300);
        await p.locator("input").first().fill("verifier@example.org");
        await p.locator("input[type=password]").first().fill("wrong-password");
        await p.getByRole("button").first().click();
        await p.waitForTimeout(700);
        await shoot(p, { route: "login", theme, viewport: vp.name, state: "error-invalid-credentials", role: "admin" });
        await c.close();
      } catch (e) {
        manifest.push({ route: "login", theme, viewport: vp.name, state: "error-invalid-credentials", role: "admin", error: String(e) });
      }

      // registry: mint token result
      try {
        await page.goto(APP + "/registry");
        await settle(page);
        const mint = page.getByRole("button", { name: /mint|token/i }).first();
        await mint.click({ timeout: 4000 });
        await page.waitForTimeout(700);
        await shoot(page, { route: "registry", theme, viewport: vp.name, state: "token-minted", role: "admin" });
      } catch (e) {
        manifest.push({ route: "registry", theme, viewport: vp.name, state: "token-minted", role: "admin", error: String(e) });
      }

      // lab-entry: validation errors (submit empty form)
      try {
        await page.goto(APP + `/lab/${BATCH_UUID}`);
        await settle(page);
        const submit = page.getByRole("button", { name: /submit|save/i }).first();
        await submit.click({ timeout: 4000 });
        await page.waitForTimeout(600);
        await shoot(page, { route: "lab-entry", theme, viewport: vp.name, state: "validation-error", role: "admin" });
      } catch (e) {
        manifest.push({ route: "lab-entry", theme, viewport: vp.name, state: "validation-error", role: "admin", error: String(e) });
      }

      await context.close();
      console.log(`states interactive done theme=${theme}`);
    }
  }
}

// ---------- print ----------
async function printPacks(browser) {
  for (const theme of ["light", "dark"]) {
    const context = await newPage(browser, { viewport: VIEWPORTS[0], theme, role: "admin" });
    await mockApi(context, "default");
    const page = await context.newPage();
    const dir = path.join(OUT, "_print");
    fs.mkdirSync(dir, { recursive: true });

    await page.goto(APP + `/batches/${BATCH_UUID}`);
    await settle(page);
    await page.emulateMedia({ media: "print" });
    await shoot(page, { route: "batch-detail", theme, viewport: "print", state: "print-emulated", role: "admin" });
    try {
      await page.pdf({ path: path.join(dir, `batch-detail.${theme}.pdf`), format: "A4", printBackground: true });
      manifest.push({ screenshot: `screenshots/_print/batch-detail.${theme}.pdf`, route: "batch-detail", theme, viewport: "A4", state: "print-pdf", role: "admin" });
    } catch (e) {
      manifest.push({ route: "batch-detail", theme, viewport: "A4", state: "print-pdf", role: "admin", error: String(e) });
    }
    await page.emulateMedia({ media: "screen" });

    await page.goto(APP + "/registry");
    await settle(page);
    await page.emulateMedia({ media: "print" });
    await shoot(page, { route: "registry", theme, viewport: "print", state: "print-emulated", role: "admin" });
    try {
      await page.pdf({ path: path.join(dir, `registry.${theme}.pdf`), format: "A4", printBackground: true });
      manifest.push({ screenshot: `screenshots/_print/registry.${theme}.pdf`, route: "registry", theme, viewport: "A4", state: "print-pdf", role: "admin" });
    } catch (e) {
      manifest.push({ route: "registry", theme, viewport: "A4", state: "print-pdf", role: "admin", error: String(e) });
    }
    await context.close();
    console.log(`print done theme=${theme}`);
  }
}

// ---------- interaction micro-states (element-level) ----------
async function micro(browser) {
  const vp = VIEWPORTS[0];
  for (const theme of ["light", "dark"]) {
    const context = await newPage(browser, { viewport: vp, theme, role: "admin" });
    await mockApi(context, "default");
    const page = await context.newPage();
    const dir = path.join(OUT, "_micro", theme);
    fs.mkdirSync(dir, { recursive: true });

    async function elShot(locator, name, action) {
      try {
        const el = locator.first();
        await el.waitFor({ timeout: 4000 });
        if (action === "hover") await el.hover();
        if (action === "focus") { await el.focus(); await page.keyboard.press("Tab"); await el.focus(); }
        await page.waitForTimeout(250);
        const box = await el.boundingBox();
        if (!box) throw new Error("no box");
        const pad = 24;
        await page.screenshot({
          path: path.join(dir, `${name}.png`),
          clip: {
            x: Math.max(0, box.x - pad), y: Math.max(0, box.y - pad),
            width: Math.min(vp.width, box.width + pad * 2), height: box.height + pad * 2,
          },
        });
        manifest.push({ screenshot: `screenshots/_micro/${theme}/${name}.png`, route: "micro", theme, viewport: vp.name, state: name, role: "admin" });
      } catch (e) {
        manifest.push({ route: "micro", theme, viewport: vp.name, state: name, role: "admin", error: String(e) });
      }
    }

    await page.goto(APP + `/batches/${BATCH_UUID}`);
    await settle(page);
    const issue = page.getByRole("button", { name: /issue/i });
    await elShot(issue, "issue-btn-default");
    await elShot(issue, "issue-btn-hover", "hover");
    await elShot(issue, "issue-btn-focus", "focus");

    await page.goto(APP + "/batches");
    await settle(page);
    await elShot(page.locator("tbody tr"), "table-row-default");
    await elShot(page.locator("tbody tr"), "table-row-hover", "hover");
    await elShot(page.locator("input").first(), "filter-input-default");
    await elShot(page.locator("input").first(), "filter-input-focus", "focus");

    await page.goto(APP + "/dashboard");
    await settle(page);
    await elShot(page.locator("aside a").first(), "nav-item-default");
    await elShot(page.locator("aside a").first(), "nav-item-hover", "hover");
    await elShot(page.getByRole("button", { name: /theme/i }), "theme-toggle-focus", "focus");

    await context.close();
    console.log(`micro done theme=${theme}`);
  }
}

const mode = process.argv[2] || "all";
const browser = await chromium.launch();
try {
  if (mode === "base" || mode === "all") await baseGrid(browser);
  if (mode === "states" || mode === "all") await states(browser);
  if (mode === "print" || mode === "all") await printPacks(browser);
  if (mode === "micro" || mode === "all") await micro(browser);
} finally {
  await browser.close();
  // merge with existing manifest if present
  const mPath = path.join(__dirname, "manifest.json");
  let prev = [];
  try { prev = JSON.parse(fs.readFileSync(mPath, "utf8")); } catch {}
  const merged = [...prev.filter((p) => !manifest.some((m) => m.screenshot && m.screenshot === p.screenshot)), ...manifest];
  fs.writeFileSync(mPath, JSON.stringify(merged, null, 2));
  console.log(`manifest entries: ${merged.length} (new: ${manifest.length})`);
}
