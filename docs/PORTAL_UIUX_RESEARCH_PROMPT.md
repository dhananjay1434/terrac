# DEEP RESEARCH PROMPT — Redesign direction for the TerraCipher Verifier Portal

> Feed everything below this line to a research-capable AI. It contains a
> complete, neutral inventory of the CURRENT design system (every color, type
> size, spacing value, component, and screen) plus the product context. The
> researcher must do its own deep research (design-system benchmarks, trust-UX
> literature, competitor/adjacent-product analysis, accessibility standards)
> and then decide — from first principles, with zero obligation to keep any
> current choice — exactly how this portal should look.

---

## YOUR ROLE

You are a principal product designer + design researcher. You have been handed
a working web portal and a complete factual inventory of its current visual
system. Your job is NOT to execute someone else's palette. Your job is to:

1. Research how the best comparable products in the world look and why
   (carbon registries, climate MRV platforms, fintech back-offices, audit and
   compliance tools, scientific/laboratory software).
2. Decide — independently, with evidence — what visual language this specific
   product SHOULD have. You may keep, modify, or discard any current choice.
   Justify every keep and every kill.
3. Deliver a complete, implementable design specification (tokens, type,
   color, spacing, components, per-screen layouts, states, motion,
   accessibility) precise enough that an engineer can apply it without
   guessing.

Do not flatter the current design. Do not assume it is wrong either. Reason
from the product's job, its users, and your research.

**SCOPE — WEB PORTAL ONLY.** Your redesign covers exclusively the React web
portal (the six screens + top bar inventoried in Section 3). The Flutter
field app on farmers' phones and the FastAPI backend are described below
ONLY as context for what data the portal displays — do NOT propose designs,
themes, or changes for the mobile app, the backend, or any API. If a portal
improvement would ideally need new backend data, note it as a dependency and
design the portal around the data that exists today (Section 3.5 lists
exactly what each screen receives).

---

## SECTION 1 — WHAT THE PRODUCT IS

**TerraCipher Verifier Portal** — the web back-office of a dMRV (digital
Measurement, Reporting & Verification) system for **biochar carbon credits**
produced by smallholder farmers using Kon-Tiki flame-curtain kilns, following
the **CSI Global Artisan C-Sink** and **Rainbow Biochar Standard**
methodologies (compliance criteria coded C0–C10).

The data pipeline feeding it: a Flutter field app on farmers' phones captures
evidence (photos of the batch, flame curtain, quenching, flame height, smoke
opacity at 0/50/90/100%, moisture samples, GPS, pyrolysis telemetry), signs it
with a device-held **Ed25519 key**, and syncs to a FastAPI backend. The
backend corroborates evidence server-side (SHA-256 photo hashes, EXIF GPS vs
claimed coordinates, signed telemetry vs claimed temperatures), computes the
carbon credit via an LCA engine, HMAC-seals the audit trail, and gates
issuance behind the C0–C10 checklist.

**The portal is where humans make the final, permanent, financial decision:**
a verifier reviews a batch's evidence and compliance state, and an admin
clicks "Issue credit" — issuing N tonnes of CO₂e that are recorded
permanently and exported to registries (CSI / Rainbow report formats).

### Users and their jobs

| Role | Screens | Job | Context |
|---|---|---|---|
| Verifier | Batches list, Batch detail | Review evidence, judge issuability | Desk, long sessions, desktop |
| Admin | + Issue button, exports, Registry | Issue credits (permanent), manage kilns/tokens/training records | Desk, desktop |
| Lab technician | Lab scan, Lab entry | Scan a sample card QR at the bench, type H:Corg / carbon / moisture / density results, upload PDF cert | Laboratory bench, likely tablet/phone, camera in use |

### What is at stake emotionally

This is a **trust product**. Carbon markets have a fraud reputation problem.
Every pixel either says "this evidence chain is rigorous and this credit is
real" or it doesn't. The buyer of these credits, the registry auditing them,
and the verifier issuing them all need the interface itself to feel
evidentiary, calm, and incorruptible. Simultaneously the underlying story is
warm: smallholder farmers, soil, fire, carbon returned to earth.

Tension for you to resolve through research: **institutional rigor vs living,
regenerative subject matter.** Where should this product sit on that axis?

---

## SECTION 2 — CURRENT TECH ENVELOPE (constraints on any proposal)

- React 18 + Vite + TypeScript, react-router. **One global stylesheet**
  (`src/styles.css`, ~400 lines) + scattered inline `style={{}}` props.
- **No CSS framework, no Tailwind, no component library, no icon library, no
  design tokens beyond CSS custom properties.** (Some dead Tailwind class
  names exist in one file; they do nothing.)
- Fonts: system stack only. No webfonts loaded today. Self-hosted fonts are
  acceptable in a proposal; CDN dependencies are not desired.
- Only third-party UI deps: `qrcode.react` (QR rendering), `jsqr` (QR camera
  scan fallback).
- Media thumbnails are fetched as authenticated blobs → object URLs; on a
  failed fetch the cell shows the text "unavailable" (storage is ephemeral in
  the current demo deployment — thumbnails can legitimately be dead; the
  design must degrade gracefully).
- Your proposal may introduce a token architecture, fonts, and new CSS, and
  may restructure layouts. It should NOT assume a component library will be
  adopted; everything must be achievable with hand-written CSS/TSX.

---

## SECTION 3 — COMPLETE CURRENT VISUAL INVENTORY (factual, exhaustive)

### 3.1 Declared CSS custom properties (the entire token system)

```css
--bg:         #eef1f6;                      /* page background, cool gray    */
--card:       #ffffff;                      /* all surfaces                  */
--ink:        #0b1220;                      /* primary text AND primary btn  */
--muted:      #64707f;                      /* secondary text                */
--faint:      #96a0ad;                      /* tertiary text, labels, inert  */
--line:       #e6e9ef;                      /* all borders, ring track       */
--emerald:    #0f9d63;                      /* "ok" checklist dots           */
--emerald-d:  #0a7a4c;                      /* issuable badge text           */
--emerald-bg: rgba(15,157,99,.10);          /* issuable badge background     */
--amber:      #b4620a;                      /* provisional/missing text      */
--amber-bg:   rgba(217,119,6,.12);          /* provisional badge bg — NOTE:
                                               the rgb inside is #d97706, a
                                               DIFFERENT amber than --amber  */
--red:        #c62828;                      /* error text only               */
--indigo:     #4f46e5;                      /* "credit issued" seal text     */
--shadow:     0 1px 2px rgba(11,18,32,.04), 0 8px 24px rgba(11,18,32,.06);
--shadow-lg:  0 2px 4px rgba(11,18,32,.05), 0 24px 60px rgba(11,18,32,.10);
```

### 3.2 Colors hardcoded OUTSIDE the token system

| Location | Value | Used for |
|---|---|---|
| Logo mark + compliance ring gradient | `linear-gradient(135deg, #12b981, #0ea5e9)` | brand mark "TC" chip and the ring stroke. `#12b981` ≠ `--emerald`; `#0ea5e9` (sky blue) appears nowhere else in the UI |
| Hero credit number | `linear-gradient(135deg, #0b1220, #0a7a4c)` text-clip | the 60px tCO₂e figure |
| Table row hover | `#f7f9fc` | |
| "Credit issued" seal background | `rgba(46,58,140,.10)` | note: that rgb is navy `#2e3a8c`, while the seal TEXT is `--indigo #4f46e5` — background and text tints come from two different hues |
| Media gallery group boxes (inline styles) | `border: 1px solid #ddd`, heading `color: #888` | evidence photo group wells |
| Camera video well | `background: #000` | |
| Page background decoration | two fixed radial gradients: `rgba(15,157,99,.10)` glow top-left, `rgba(79,70,229,.10)` glow top-right | the only "atmosphere" in the app |

Summary of hue population: **4 greens** (#0f9d63, #0a7a4c, #12b981, #d97706-based tint), **2 ambers**, **1 red**, **2 blue-purples** (#4f46e5, #2e3a8c), **1 sky blue** (#0ea5e9), plus a neutral ramp (#0b1220 → #64707f → #96a0ad → #e6e9ef → #eef1f6 → #fff).

### 3.3 Typography (system stack: -apple-system, Segoe UI, Roboto…)

| Size | Weight | Where |
|---|---|---|
| 60px / 800 / -0.04em, gradient-filled | hero credit number |
| 30px / 800 | ring center % |
| 22px / 750 | evidence tile values |
| 20px / (default) | page h1s (inline-styled per page) |
| 18px / 700 | credit unit "tCO₂e" |
| 15.5px / 750 / -0.02em | brand wordmark |
| 13.5px | table cells, checklist labels, credit-label |
| 13px | buttons, inputs, links, verdict pill, seal |
| 11px / 700 / 0.14em tracking / UPPERCASE / --faint | ".micro" label — used for ALL section headers, table headers, form labels, statuses |
| 10.5px | thumb captions, ring sublabel |

- `letter-spacing: -0.01em` globally on body; antialiased.
- `tabular-nums` utility class applied to all numerals (ids, dates, counts,
  credits, hashes).
- Hashes/UUIDs render in the proportional UI font (one `<code>` element on
  the token screen is the only monospace in the app).
- No line-height system declared anywhere.

### 3.4 Shape, space, elevation

- Radii in use: 6 (gallery wells), 9 (buttons/inputs/mark), 10 (thumbs,
  video), 14 (cards, table), 20 (hero), 999 (pills).
- Spacing values in use: 2,4,6,8,10,12,13,14,16,18,24,28,30 px — no scale.
- Layout: single centered column `max-width: 1040px`, padding 24px sides.
- Elevation: two shadow levels (above); cards get --shadow, hero gets
  --shadow-lg; nothing else elevates. No transitions/animations exist except
  none at all — zero `transition` properties in the stylesheet.
- Sticky top bar: `rgba(255,255,255,.72)` + `backdrop-filter: saturate(1.4)
  blur(14px)`, 1px bottom line.

### 3.5 Screen-by-screen inventory (what data each screen shows)

**Login** — centered 360px card: gradient "TC" mark, h1 "Verifier Portal",
micro label "LAB & VERIFIER SIGN-IN", two inputs (placeholder-only labels
"email" / "password"), full-width ink button, red error line.

**Batches (list)** — two `<select>` filters (lifecycle status:
RECEIVED/ISSUED; eligibility: provisional/issuable). Table with 6 columns:
Batch (8-char id) · Device · Received (date) · Credit tCO₂e (3 decimals) ·
Status (pill: amber PROVISIONAL / green ISSUABLE) · Flags (bare integer count
of provisional reasons). Row click navigates. "Load more" ink button
(cursor pagination). Loading state: none (table just appears). Empty state:
single muted line "No batches."

**Batch detail** — the decision screen, in DOM order:
1. "← All batches" text link.
2. **Hero card** (2-col grid): left — verdict pill (ISSUABLE green /
   PROVISIONAL amber), 60px gradient credit number + "tCO₂e", context line
   "Batch 8f3a2c1d · device dev-123", then EITHER an indigo "✓ CREDIT ISSUED"
   seal pill OR (admin only) an ink "Issue credit" button (disabled when not
   issuable, label changes to "Not yet issuable"), plus two export buttons
   ("Export CSI", "Export Rainbow") using a `.neutral` class that is **not
   defined in the stylesheet** (they render as browser-default buttons);
   right — 150px SVG compliance ring, green→sky gradient stroke on a --line
   track, center shows "NN%" + "CRITERIA MET".
   Issuance is confirmed via a native `window.confirm()` dialog.
3. **Evidence tiles**: fixed 3-column grid of cards, one per evidence count
   (micro label like "MOISTURE READINGS", 22px number).
4. **Compliance checklist**: one card per group (Field evidence / Lab results
   / Project registry / Annual verification / Device security). Header: micro
   group label + "okCount/total" tally + amber "· N missing" when blocking.
   Rows: 9px status dot (green ok / amber blocking / gray inert) + 13.5px
   label + right-aligned micro status text (OK / MISSING / N/A).
5. **Evidence media** card: photos grouped by capture step. Group wells are
   inline-styled boxes (`#ddd` border, 6px radius, 12px padding) with a
   capitalized raw key as heading ("flame curtain", "0", "Other /
   Uncategorized" — the smoke stages display as bare "0"/"50"/"90"/"100").
   Inside: responsive grid `minmax(120px,1fr)` of thumbs — 90px-tall cover
   image (or "loading…"/"unavailable" text), caption = first 12 hex chars of
   the SHA-256 + "…". **Available in the API but currently NOT displayed:**
   per-photo `capture_type_verified` (whether the Ed25519-signed telemetry
   corroborated the label), `exif_lat`/`exif_lon` GPS, upload timestamp,
   filename.
6. Loading state: the word "Loading…". Error state: "Batch not found."

**Lab scan** — h1 "Scan batch card", micro hint, camera `<video>` in a card
(black background), on camera denial an error line + manual UUID input +
"Open" button.

**Lab entry** — "← Scan another", h1 "Lab results · 8f3a2c1d", 420px form:
four micro-labeled inputs (H:Corg ratio 0.1–1.5, organic carbon fraction
(0–1], moisture samples "≥3, comma sep." with placeholder "8, 9, 10", dry
bulk density kg/m³), a PDF file input, submit button, red error lines.

**Registry (admin)** — h1 "Registry", then six stacked cards:
1. "REGISTER KILN (C8)" form — 5 placeholder-labeled inputs in a flex row
   (kiln id, type open/closed, material, weight kg, capacity litres) + Save.
2. "KILN CARDS (PRINT & MOUNT)" — grid of white cells: 110px QR code +
   caption "kiln-1 · open" (these are physically printed and mounted on
   kilns).
3. "ENROLLMENT TOKEN" — "Mint enrollment token" button; result shows a 130px
   QR + the raw token in 11px `<code>` (this is secret material, shown once).
4–6. Three more placeholder-labeled forms: operator training, supervisor
   visit, scale calibration, annual verification (methane g/kg, project id,
   year). Feedback on save: a micro line "Saved." / "Save failed."

**Top bar** (all authed screens) — gradient mark "TC", wordmark
"TerraCipher · Verifier Portal" (suffix muted), right-aligned text buttons:
"Lab scan", "Registry", "Sign out".

**HTML shell** — title "TerraCipher · Verifier Portal"; **no favicon, no
theme-color, no meta description**; no per-page titles.

### 3.6 Interaction/state inventory (current, complete)

- Zero CSS transitions or animations. Hover states: table row bg tint only.
- No `:focus-visible` styling anywhere (browser defaults on custom UI).
- Disabled buttons: `opacity: .5`.
- No skeletons/spinners — loading is literal text.
- No toasts — feedback is inline text lines.
- No dark mode, no `prefers-reduced-motion`, no print styles (kiln cards are
  explicitly meant to be printed).
- Responsive behavior: none designed. Fixed 3-col tiles, 2-col hero, 6-col
  table on all viewports. `max-width: 1040px` centered.
- Accessibility present: `role="img"` + `aria-label` on the ring,
  `autoComplete` on login. Everything else default.

---

## SECTION 4 — YOUR RESEARCH MANDATE

Do genuine deep research before proposing anything. At minimum:

1. **Benchmark the trust-adjacent field.** Study the visual systems of: carbon
   registries and MRV platforms (Verra, Gold Standard, Puro.earth, Isometric,
   Watershed, Pachama, Sylvera, BeZero), fintech/audit back-offices (Stripe
   Dashboard, Mercury, Ramp, Carta), and scientific/lab software. Extract:
   what palette families, type systems, density levels, and evidence-display
   patterns do the credible ones share? What makes some feel like toys?
2. **Color psychology & semantics for this domain.** Green is both "brand
   = climate" and "status = pass" — research how serious products resolve
   that collision. Decide: should brand green and semantic green be the same
   hue, different hues, or should the brand not be green at all?
3. **Evidence-display UX.** Research how products that present forensic /
   chain-of-custody material (audit logs, e-signature trails, blockchain
   explorers, photo-evidence systems in insurance claims) display hashes,
   signatures, GPS, timestamps, and verification states so that
   non-cryptographers trust them.
4. **High-stakes action UX.** Research confirmation patterns for irreversible
   financial actions (wire transfers, credit issuance, production deploys) —
   what does the literature and best practice say vs a native confirm()?
5. **Accessibility ground truth.** WCAG 2.2 AA at minimum: verify every
   fg/bg pair you propose (including the current ones you keep) with actual
   contrast ratios; address focus, target sizes, and the uppercase-microcopy
   legibility question at 10.5–11px.
6. **Typography for numeric authority.** Research font choices for
   tabular/financial data (what do terminals, registries, and fintech use);
   decide whether this product warrants a webfont, which, and where mono is
   mandatory (hashes? ids? all numerals?).

## SECTION 5 — WHAT YOU MUST DELIVER

A single design specification document containing:

1. **Design thesis** (one page): what this portal should feel like and why —
   grounded in your research, citing the benchmarks you drew from. Resolve
   the institutional-vs-regenerative tension explicitly.
2. **Complete token architecture**: full palette (every hex, with contrast
   ratios against its intended backgrounds), neutral ramp, semantic status
   system, elevation, radii, spacing scale, motion durations/easings — named
   tokens ready to paste as CSS custom properties. State explicitly which
   current tokens you kept/changed/killed and why.
3. **Typography system**: families (with self-hosting plan if webfonts),
   full scale with line-heights and weights, numeric/mono policy.
4. **Per-screen redesign specs** for all six screens + top bar: layout,
   hierarchy, every component's states (default/hover/focus/disabled/
   loading/empty/error), and specifically — a complete spec for the evidence
   media gallery (grouping, verification chips, GPS/timestamp/hash
   presentation, dead-thumbnail degradation) and for the credit-issuance
   confirmation flow.
5. **Component inventory**: buttons (primary/ghost/destructive), badges,
   chips, tables, forms/labels, cards, skeletons, toasts/inline feedback,
   focus ring — each fully specified.
6. **Responsive + dark-mode strategy** (whether dark mode is warranted is
   YOUR call — justify it), print styles for the kiln QR cards.
7. **Prioritized rollout plan**: rank changes by trust-impact per effort;
   identify the 20% that produces 80% of the perceived quality jump.

Rules: cite sources for research claims; show contrast math for every
status color; no component libraries or CSS frameworks in the proposal;
keep the constraint that an engineer implements this in plain CSS + React.
You are free to conclude that parts of the current system are already
correct — but only after research, and you must say why.
