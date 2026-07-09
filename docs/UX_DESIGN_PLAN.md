# Kon-Tiki dMRV — UI/UX Design Plan

*A design system + screen spec a designer or Flutter engineer can execute from directly.
Every major decision carries its rationale. Grounded in the existing code
(`lib/ui/**`), the backend compliance model (C0–C10), and the Rainbow BiCRS
methodology, not in generic field-app assumptions.*

---

## 0. What this product actually is (grounded)

**Kon-Tiki dMRV** is an offline-first field-evidence app that turns a rural biochar
burn into a cryptographically-anchored carbon credit under the **Rainbow BiCRS /
CSI Global Artisan C-Sink** methodology. It is the *sensor and notary* at the edge of
a carbon-credit supply chain.

**The workflow it replaces:** paper logbooks + spreadsheet + trust. Today an artisan
burns biomass in a Kon-Tiki (open) or retort (closed) kiln, someone writes down a
weight and a date, and a verifier shows up months later with no tamper-proof trail.
This app replaces that with: capture-at-source, sensor-bound (BLE scale +
thermocouple), photo-with-hash, GPS-anchored, device-signed (Ed25519), and
sync-when-connected evidence — each batch accumulating toward an *issuable* credit.

**Technical constraints that shape every UX decision:**
- **Direct tropical sunlight** — the screen competes with the sun; contrast is survival.
- **Leather work gloves** — 48px touch targets fail; the code already uses ≥64px + heavy haptics.
- **Low/no connectivity** — everything is written to a local encrypted (SQLCipher) outbox
  and synced opportunistically. The user must trust that "saved" ≠ "lost" even with no bars.
- **Low digital literacy + Hindi-first** — the theme already ships `NotoSansDevanagari`.
  Language is visual and numeric first, textual second.
- **Trust is the product.** The credit only has value if the buyer/verifier believes the
  data wasn't faked. So the UI's job is not just capture — it is *making integrity visible*.

**What makes it different from adjacent tools** (generic ODK/KoboToolbox form apps): those
collect data; this one **corroborates and grades** it. The backend computes a `provisional`
state with a specific list of missing/failed methodology checks
(`provisional_reasons`). That list is not backend plumbing — **it is the spine of the
field UX** (see §3.1). An adjacent form app has no notion of "this record is 70% of the way
to being a sellable credit." This one does, and the UI must show it.

---

## 1. Users we are building for

### Persona A — Aarav, the Kiln Operator (PRIMARY, ~90% of screen-time)
- **Who:** 20–50, rural India, operates 1–3 Kon-Tiki kilns. Runs the capture flow.
- **Fluency:** Low. Comfortable with WhatsApp and a camera; not with forms, jargon, or English.
  Reads Hindi; reads numbers fluently.
- **Environment:** Outdoors, midday sun, gloved or ash-covered hands, phone held one-handed,
  intermittent 2G/no signal, cheap-to-mid Android device.
- **Psychological drivers:**
  - *Trust-before-action:* will not tap "SUBMIT" if he can't tell what happens to the data or
    whether it's safe. **Needs a persistent, plain-language "your data is safe / X steps left"
    signal.** (The code's `integrity_footer` + "ALL DATA SECURE" banner are the seed of this.)
  - *Fear of doing it wrong:* the biggest drop-off cause is ambiguity — "did the weight save?
    is the photo good enough? why is it still yellow?" Every state must be unambiguous and
    reversible.
  - *Reward:* seeing the batch move from "in progress" → "secured" → (later) "credit issued"
    is the dopamine loop that keeps him compliant. The **Proof Wallet** is that reward surface.
- **Design implications:** one primary action per screen; giant targets; numbers not prose;
  live sensor feedback; never block on connectivity; celebrate every confirmed capture.

### Persona B — Priya, the Project Developer / Verifier (SECONDARY, admin/desk)
- **Who:** Runs the project across the 3 sites; interfaces with the Rainbow auditor. Uses the
  admin/compliance surface (the `/compliance` endpoint, registries), not the field flow.
- **Fluency:** High. Technical, English, desk browser/tablet.
- **Psychological drivers:** *Defensibility.* She needs to prove to an auditor that every issued
  credit is backed by complete, tamper-evident evidence. She needs density, filters, and a
  per-batch **compliance checklist** that maps 1:1 to the methodology.
- **Design implications:** information-dense, English, data-table patterns, the compliance
  report as a first-class screen. This is a *different* visual register from the field flow
  (see §5.4 — the "Console" sub-theme).

> **Scope note:** the prompt's "core flow" is Aarav's field capture. Priya's console is
> specified at lower resolution here and flagged as a second track.

---

## 2. The central design problem (must be resolved first)

**There are two competing, half-migrated design systems in the codebase:**

| | Light system | Dark system |
|---|---|---|
| Theme file | `AppTheme` (`app_theme.dart`) | `FarmerTheme` (`farmer_theme.dart`) |
| Background | `tacticalTitanium #F0F4F8` | `deepSlate #1A1D20` |
| Primary CTA | `cobaltShield #1D4ED8` | `neonYellow #E0FF00` |
| Success | `yieldGold #F59E0B` | `fieldGreen #00E676` |
| Button widget | `PremiumFieldButton` | `RuggedButton` |
| Status | powers older screens | added later, "lives ALONGSIDE" |

The code is explicit that these coexist to avoid breaking compiles. **This is the #1 thing to
fix** — two palettes means inconsistent trust signals (is "confirmed" gold or green?), double
maintenance, and a fragmented feel that quietly erodes Aarav's confidence.

**Decision (with rationale): unify on a single LIGHT, high-albedo field theme; port the dark
system's high-signal semantic hues onto it; reserve true-dark for one deliberate "vault"
moment only.**

Why light wins for *this* environment, despite the dark theme's "sunlight" claim:
- Phone/tablet LCD/OLED cannot out-emit direct sun. Under sunlight, *reflected ambient light*
  dominates the panel, so a "dark" theme washes to muddy grey and its contrast collapses. A
  light background with near-black text preserves the highest effective contrast (this is why
  e-paper and ruggedized field devices are light). The `AppTheme` author's instinct
  ("high-albedo off-white for sunlight readability") is correct.
- Dark themes win *indoors/at night* and save OLED power — so we keep a real dark mode as an
  option, but the **canonical, default field theme is light.**
- The dark system's *semantic colors* (neon action, green confirmed, crimson error) are
  excellent high-signal choices; we keep those meanings and recalibrate the hues for AA
  contrast on a light surface (§5).

Net: **one token set, semantically named, light by default.** No more `AppTheme` vs
`FarmerTheme` — a single `DesignTokens` with `surface`, `onSurface`, `action`, `confirmed`,
`error`, `verifiedVault`. Both button widgets collapse into one `FieldButton` with variants.

---

## 3. Screen-by-screen breakdown (Aarav's core flow)

The flow mirrors the backend evidence channels and the batch lifecycle. Existing screens
(from `lib/ui/screens/`) are noted; the plan reorganizes them around one spine.

### 3.1 The spine: the Batch Checklist (new organizing principle)
Instead of a linear wizard the operator can't exit, the flow is anchored by a **Batch
Checklist** — a live rendering of the backend's `provisional_reasons`. Each methodology
requirement is a row with one of three states:
- ○ **Not started** (grey)
- ◐ **Captured, syncing / provisional** (amber `action`)
- ● **Confirmed & corroborated** (`confirmed` green)

Rationale: this converts the opaque backend gate into Aarav's to-do list and answers his core
anxiety ("what's left, am I done?") on every screen. It also means the flow is **non-linear and
resumable** — critical when a burn spans hours and the phone dies. The checklist *is* the
`/compliance` checklist Priya sees, rendered for a low-literacy user with icons + Hindi labels.

### Screen list (each: single primary job · entry → exit · error/offline behavior)

| # | Screen (code file) | Single primary job | Entry → Exit | Error / Offline |
|---|---|---|---|---|
| 1 | **Home / Batch List** (`dashboard_screen`) | Show my batches + their checklist state; start a new batch | App open → tap batch or "＋ New Burn" | Offline is the *default*; show outbox count + "X saved, will upload" — never an error |
| 2 | **Batch Checklist** (new; hub) | Show the 7–9 evidence steps for this batch + % to issuable | From Home → tap any step | A failed/expired check (e.g. GPS mismatch) shows as a red row with a plain-language fix |
| 3 | **Biomass Sourcing** (`lantana_sourcing_screen`) | Record feedstock + input amount + method (C1) | Checklist → save → back to Checklist | Weight from BLE or manual fallback; no signal irrelevant (local write) |
| 4 | **Moisture Capture** (`moisture_verification_screen`) | Log ≥10 photographed moisture readings, ≥1/100kg (C2) | Checklist → capture loop → Checklist | Camera required; if photo hash fails, retake — never silently accept |
| 5 | **Pyrolysis / Burn** (`pyrolysis_screen`) | Live temp curve + kiln type + flame photos (C0/C3) | Checklist → live session → Checklist | BLE thermocouple drop → banner + last-good reading held; session not lost |
| 6 | **Yield Capture** (`yield_scale_screen`) | BLE crane-scale wet-yield reading (C6 mass) | Checklist → weigh → Checklist | Scale disconnected → big reconnect card + manual-entry escape hatch |
| 7 | **Transport Event(s)** (new, folds into flow) | Distance/weight/vehicle/fuel per leg (C6) | Checklist → add leg → Checklist | Pure form; offline-safe |
| 8 | **Composite Sample** (new/small) | Set-aside sub-sample photo + kiln/batch QR (C4) | Checklist → capture → Checklist | QR scan or manual code entry |
| 9 | **End-Use / Delivery** (`end_use_application_screen`) | Delivery record + buyer identity + GPS (C5) | Checklist → save → Checklist | GPS optional-degraded; buyer name is the gate |
| 10 | **Secure Camera** (`secure_camera_screen`) | Capture a photo that is hashed + GPS/EXIF-stamped at source | Invoked by 4/5/8/9 → returns asset | If camera/permission fails, block with a clear reason + retry; never fake a capture |
| 11 | **Proof Wallet** (`proof_wallet_screen`) | The reward: batches as signed "proofs," provisional vs issued | Home tab → proof detail | Shows signature/anchor state; offline shows local proof, "will confirm on sync" |
| 12 | **Sync / Integrity status** (`integrity_footer` promoted) | Persistent: "N items secured locally, M uploaded, all signed" | Global footer, tap → detail | This screen's whole job IS the offline story |

**Removed from the happy path:** `camera_debug_view` (dev-only; gate behind a hidden build flag).

### 3.2 Entry/exit principle
Every capture screen returns to the **Checklist**, not to the next step. Rationale: a linear
wizard punishes the real-world order (burns interrupt, sensors drop, steps happen out of
sequence). The checklist lets Aarav do steps in any order and always see "what's left,"
which is exactly how the backend's converge-as-evidence-arrives model already works.

---

## 4. Information hierarchy per screen

General rule (justified by sunlight + glove + low-literacy): **one primary number or action
per screen, huge; everything else recedes.** Above the fold on every capture screen:

- **Primary (huge, center):** the live value being captured (the weight in kg, the temp in °C,
  the moisture %), or the single CTA. `SpaceMono`, 48–72px, `onSurface`.
- **Secondary (top):** which batch + which step ("Burn #A47 · Step 4 of 9"), so Aarav never
  loses context. Small `SpaceGrotesk`.
- **Tertiary (bottom, persistent):** the integrity/sync footer — "🔒 Saved on device · 3 to
  upload." Present but never competing with the primary.

Screen-specific:
- **Yield/Pyrolysis:** the live sensor reading is the hero; connection state is a colored pill
  beside it (cobalt = live BLE, grey = idle, crimson = lost). The "LOCK IN" CTA is disabled
  (visually obvious) until the reading is stable — the code already models `connection=idle →
  "----"`.
- **Checklist:** the % complete ring is primary; the step rows are the scannable secondary; the
  "SUBMIT BATCH" CTA is deliberately absent until 100% (you cannot submit an incomplete credit —
  mirrors the backend refusing to sign a provisional batch).
- **Proof Wallet:** the credit state badge (Provisional / Issued) is primary; the cryptographic
  detail (signature, hash, anchor) is a deliberately "premium/vault" secondary block.

---

> **⚠️ SUPERSEDED (2026-07-03):** §5 (color), §6.1 (type), §7 (component visuals) and
> §8 (motion register) are replaced by **`UX_FIELD_THEME_SPEC.md`** — the "field
> equipment" overhaul (warm paper/ink neutrals, safety-orange action, tractor-green
> confirmed, stamp-ink certified, Noto Sans superfamily, key-cap buttons, parchi→mohar
> state metaphor). The fintech/crypto register below (`telemetryCyan`, `verifiedVault`,
> `verifiedGold`, Space Grotesk) is **dead** — kept only as historical rationale.
> Everything structural in this doc (§0–§4, §6.2 grid, §9 order, §10) still stands.

## 5. Color palette (unified — resolves §2) — SUPERSEDED, see banner above

One semantic token set. Hex values recalibrated for **WCAG AA (≥4.5:1) on the light surface**.
Field-theme names in parentheses map to existing code tokens so migration is mechanical.

### 5.1 Core / neutral
| Token | Hex | Use | Rationale |
|---|---|---|---|
| `surface` (was `tacticalTitanium`) | `#F0F4F8` | All scaffold backgrounds | High-albedo off-white: max effective contrast under direct sun; not pure white (reduces glare fatigue). |
| `surfaceRaised` (`pureAlbedo`) | `#FFFFFF` | Cards/panels only | Pure white lifts cards off the off-white scaffold without shadows that vanish in sunlight. |
| `onSurface` (`armorSlate`) | `#0F172A` | All primary text/icons | Near-black slate, not `#000`: 15:1 contrast, softer than pure black under glare. |
| `onSurfaceMuted` (`armorSlate60`) | `#0F172A @ 60%` | Secondary text, hints | Single source of de-emphasis; the code's pre-computed opacity ladder is kept. |
| `hairline` | `#0F172A @ 12%` | Dividers, card borders | Structure without heavy lines that read as "error" under low vision. |

### 5.2 Semantic (the trust signals — ported from the dark system, recalibrated)
| Token | Hex | Meaning | Rationale |
|---|---|---|---|
| `action` (was `neonYellow`→amber) | `#B45309` (text/icon) / `#F59E0B` (fill) | Primary CTA, "action required", pending/provisional | Neon `#E0FF00` fails AA on white and reads as "warning." Amber keeps the "do this next" urgency while passing contrast; it also matches the *provisional* backend state ("not done yet"). |
| `confirmed` (`fieldGreen`) | `#047857` (on light) / `#00E676` (dark mode) | Sensor locked, step corroborated, "secured" | Green = the universal "safe/done." Darkened to `#047857` for AA on white; the vivid `#00E676` is retained for dark mode and for solid-fill success chips. This is the single "done" color — kills the gold-vs-green ambiguity. |
| `error` (`crimsonRed`) | `#DC2626` fill/icon/large · `#B91C1C` normal-size text | Hardware failure, hash mismatch, GPS teleport, expired calibration | Red reserved *exclusively* for "this blocks your credit," never decoration. **Contrast caveat (verified, §5.5):** `#DC2626` is ~4.8:1 on pure white but only **~4.36:1 on the `#F0F4F8` scaffold — a normal-size AA fail.** So `#DC2626` is fine for fills, icons, and ≥18px error headings (large-text AA needs only 3:1), but normal-size error *body text* on the scaffold must use the darker `#B91C1C` (~5.9:1). On white cards either is fine. |
| `live` (`cobaltShield`) | `#1D4ED8` | Active BLE link, GPS lock, "system is listening" | Blue = calm technical credibility + "connected." Distinct from action(amber) and confirmed(green) so "connected" ≠ "done." |

### 5.3 The one dark accent — the "vault"
| Token | Hex | Use | Rationale |
|---|---|---|---|
| `verifiedVault` (`midnightCyber`) | `#0B1026` | Background of the cryptographic proof footer / Proof Wallet signature block ONLY | A single, deliberate dark "vault" moment signals *this part is the tamper-proof cryptography.* Scarcity makes it meaningful — the visual embodiment of "your data is signed and safe," the product's core trust promise. |
| `verifiedGold` (was `yieldGold`) | `#D4A017` | Signature / anchor **confirmation** sigil — ON the `verifiedVault` dark surface ONLY | **Deliberately a DIFFERENT hex from `action` (`#F59E0B`).** Rationale + the fix for the original collision: gold's *intent* here is "final, certified, cryptographically confirmed" — the semantic OPPOSITE of `action`'s "pending / do this next." If both used `#F59E0B`, the everyday pending-chip and the once-per-batch confirmation sigil would be visually identical, reintroducing exactly the "is confirmed gold or green?" ambiguity §2 exists to kill. `verifiedGold` is a deeper, metallic "gold-leaf/seal" tone that reads as *precious and final* on near-black; `action` amber is a brighter alert-orange on light. They also never share a surface (gold on `#0B1026` dark; amber on `#F0F4F8` light), so context + shade + surface all separate them. Verified ~7.9:1 on `verifiedVault` (§5.5). |
| `telemetryCyan` | `#00E5FF` | Live temp-curve line on the vault-dark pyrolysis chart | High-emission cyan on dark is the one place a dark panel is justified — a live data trace reads best on dark, like an instrument. |

### 5.4 Priya's Console sub-theme (desk/admin)
Same tokens, denser application: `surface` stays light, tables use `hairline` grids, the
compliance checklist reuses `confirmed`/`action`/`error` exactly so a green row means the same
thing to Priya and Aarav. No new colors — consistency across personas *is* the trust argument.

### 5.5 Verified contrast (computed, not asserted)
Ratios below are computed (WCAG 2.x relative-luminance) against the **actual `#F0F4F8`
scaffold**, not pure white — because that distinction is where the one real failure hides.
**Re-run in WebAIM/axe at handoff** (opacity-composited tokens especially), but these are the
numbers, not a promise to check:

| Pair | Ratio | AA normal (4.5) | Note |
|---|---|---|---|
| `onSurface #0F172A` on `#F0F4F8` | **~16.1:1** | ✅ | Body/primary — huge margin. |
| `confirmed #047857` on `#F0F4F8` | **~4.96:1** | ✅ (just) | OK for normal text; the vivid `#00E676` is fill/dark-mode only, never small text on light. |
| `error #DC2626` on `#F0F4F8` | **~4.36:1** | ❌ | **Fails normal-size** → use `#B91C1C` (~5.9:1) for error body text; keep `#DC2626` for fills/icons/≥18px. |
| `error #DC2626` on `#FFFFFF` card | ~4.8:1 | ✅ (just) | Passes on white cards only. |
| `onSurfaceMuted` (`#0F172A @60%`→ eff. `#6F6F7C`) on `#F0F4F8` | **~4.56:1** | ⚠️ (barely) | Passes but thin — for anything <16px, bump to **65–70% opacity** or restrict `onSurfaceMuted` to ≥16px meta text. This is the token most likely to fail in practice; do not use it for dense small labels. |
| `live #1D4ED8` on `#F0F4F8` | ~7.0:1 | ✅ | |
| `verifiedGold #D4A017` on `verifiedVault #0B1026` | **~7.9:1** | ✅ | Decorative sigil, mostly large — comfortable margin. |

Takeaway: two tokens carry real risk — **`error` red as small text on the scaffold (fails)** and
**`onSurfaceMuted` at small sizes (marginal)**. Both have a stated remedy above; everything else
clears with margin.

---

## 6. Typography & spacing

### 6.1 Type system (fonts already shipped — keep, systematize)
Three families, each with a *job* (rationale: role-based fonts let a low-literacy user parse
"is this a label, a number, or Hindi text?" pre-consciously):

- **`SpaceGrotesk`** — headings, labels, buttons. Geometric, technical, confident → "credible
  instrument." Weights 600/700.
- **`SpaceMono`** — all numeric readings and hashes/IDs. Monospace → digits align, weights feel
  "measured/instrument-grade," and hashes are unambiguous (0 vs O). This is the *data* voice.
- **`NotoSansDevanagari`** — all body/instructional copy, Hindi-first. Full Devanagari coverage.

**Type scale** (1.25 modular, sunlight-legible floor of 14px):
| Role | Font | Size / Weight |
|---|---|---|
| Hero reading (kg/°C/%) | SpaceMono | 56 / 700 |
| Screen title | SpaceGrotesk | 24 / 700 |
| Section / step label | SpaceGrotesk | 20 / 600 |
| Body / instruction (Hindi) | NotoSansDevanagari | 18 / 500 |
| Data / meta / hash | SpaceMono | 14 / 400 |
| Button | SpaceGrotesk | 16 / 700, +0.5 tracking |

Rationale for the 18px Hindi body / 14px floor: Devanagari conjuncts need more x-height to
stay legible in sun; 14px is the smallest that survives glare on a cheap panel.

### 6.2 Spacing & grid
- **8px base grid**; steps 4/8/16/24/32. Rationale: predictable rhythm + maps to Flutter's
  density.
- **Screen / layout padding = 24px (on-grid).** Rationale + reconciliation of an apparent
  conflict: `RuggedButton` uses 20px *internal* padding, and 20px is off-grid (not in the
  4/8/16/24/32 step list). Rather than make screen padding a 20px exception, we separate two
  concerns: **layout padding** (space *between* and *around* components) is on-grid at 24px;
  **component-internal padding** (inside a button/chip, e.g. RuggedButton's 20px) is a
  component-local detail and may differ — it is not part of the layout grid and does not need to
  change. So the grid stays pure and the shipped button is untouched. (If you'd rather have a
  single number end-to-end, bump RuggedButton's internal padding to 24px — a one-line change —
  but it is not required.)
- **Min touch target 64px** (not 48px) — already the code standard; gloves. Spacing *between*
  interactive targets ≥12px to prevent fat-finger mis-taps.
- **Card radius 16px** (matches `AppTheme.cardTheme`), button radius 12px (matches
  `RuggedButton`). Keep — consistency with shipped code.
- **One-thumb reachability:** primary CTA always in the bottom 25% of the screen, full-width.

---

## 7. Component patterns (collapse the two families into one)

| Component | Spec | Rationale |
|---|---|---|
| **`FieldButton`** (merge `RuggedButton` + `PremiumFieldButton`) | Full-width, ≥64px, radius 12, `SpaceGrotesk` 16/700. Variants: `primary`(action amber), `confirm`(confirmed green), `danger`(error red), `disabled`(muted). `HapticFeedback.heavyImpact` fired **before** `onPressed`. `Semantics` label required. | The code already proves the chassis; we just delete the duplicate. Heavy-impact-before-callback is a keeper — it's the only feedback felt through gloves and it confirms *even if the async save is slow*. |
| **`ReadingCard`** | White `surfaceRaised` card; hero `SpaceMono` number; a connection pill (`live`/grey/`error`); a "LOCK IN" `confirm` button disabled until value stable. | The yield/pyrolysis hero pattern; disabling until stable prevents capturing a mid-swing sensor value. |
| **`ChecklistRow`** | Icon + Hindi label + state chip (○/◐/●). Tap → the step screen. | The spine (§3.1). State chip uses the exact semantic colors → one visual language for progress. |
| **`IntegrityFooter`** (promote existing widget) | Persistent bottom strip: 🔒 "N secured · M uploaded," tap → sync detail. On `verifiedVault` dark. | Makes "your data is safe offline" *always visible* — directly answers Aarav's trust-before-action need. |
| **Form field** | 64px row, big label (Grotesk), big value (Mono), inline validation in `error` red with a *plain-language* fix, never a code. | Low literacy: an error must say "फ़ोटो दोबारा लें" (retake photo), not "hash mismatch 0x…". |
| **State: loading** | Skeleton + "Saving to device…" (never a bare spinner). | Reassure that *local* save is happening; connectivity is separate. |
| **State: empty** | Illustration + one CTA ("＋ New Burn"). No dead ends. | |
| **State: error** | Red card, plain cause, one recovery action, and — critically — "your other data is still safe." | The #1 drop-off is fear that an error lost everything; explicitly deny that. |
| **State: offline** | *Not* an error state. A neutral cloud-off pill + "will upload automatically." | Offline is the default condition, not a failure. |

---

## 8. Interaction & motion (minimal, purposeful)

Principle: **motion confirms state changes and physical capture; it never decorates.** Cheap
devices + sunlight = restraint.

- **Capture confirmation (the key moment):** on "LOCK IN," a 250ms scale-punch of the value +
  a color sweep grey→`confirmed` green + `heavyImpact` haptic. Rationale: this is the
  dopamine/trust beat — Aarav must *feel and see* that the reading is now secured. Motion +
  haptic together survive both gloves and sun (if he can't see it, he feels it).
- **Checklist row → confirmed:** the ◐ chip morphs to ● with a 200ms fill, and the % ring ticks
  up. Progress must be visible to sustain the compliance loop.
- **Sensor connect/disconnect:** the connection pill cross-fades (150ms) between `live` and
  `error`; on disconnect, a non-blocking top banner slides in. Never a modal — the burn
  continues.
- **Sync:** the footer's upload count decrements with a subtle count-roll; a brief `confirmed`
  flash when the batch is fully synced. No blocking progress bars.
- **Proof "minted":** when a batch flips Provisional → Issued, a one-time, deliberately richer
  celebration on the `verifiedVault` surface (gold sigil draw-on, ~600ms). Rationale: this is
  the payoff of the entire product — the *only* place lavish motion is warranted.
- **Transitions:** 150–200ms ease-out for screen pushes; respect `prefers-reduced-motion` and
  drop to instant on low-end devices (detect via frame budget).

---

## 9. Execution order (so an engineer can start Monday)

1. **Create `DesignTokens`** (§5) as the single source; alias old `AppTheme`/`FarmerTheme`
   names to it so nothing breaks mid-migration.
2. **Merge `RuggedButton` + `PremiumFieldButton` → `FieldButton`**; codemod call sites.
3. **Build the `Checklist` hub** wired to the backend `provisional_reasons` / `/compliance`
   response — this reframes the whole flow and is the highest-leverage change.
4. **Promote `IntegrityFooter`** to a global persistent element.
5. **Recolor screens** to tokens, screen by screen, deleting `FarmerTheme` last.
   **Done-criterion (blocks step completion):** run WebAIM/axe on the rendered build against
   the real `#F0F4F8` scaffold and confirm every text/background pair clears AA — with explicit
   sign-off on the two known-fragile tokens from §5.5: `error` as normal-size text (must be
   `#B91C1C`, not `#DC2626`, on the scaffold) and `onSurfaceMuted` (65–70% opacity, or ≥16px
   only). Computed ratios in §5.5 are hand-derived; this run is the authoritative gate.
6. **Proof Wallet vault treatment** (the reward surface).
7. Priya's Console as a separate, later track.

---

## 10. Rationale summary — the three ideas everything hangs on

1. **Make integrity visible.** The product's value is trust; the UI's primary job is to prove,
   continuously and in plain terms, that data is captured, signed, and safe offline. (Footer,
   vault, confirmed-green.)
2. **The compliance gate is the UX spine.** The backend already grades each batch with a list
   of what's missing; render *that* as the operator's checklist. Backend and field UX and the
   auditor's report become one shared model.
3. **One language, sunlight-first, glove-first.** Collapse two themes into one light,
   high-contrast, semantic token set; ≥64px + haptics; role-based fonts; numbers over prose,
   Hindi over English. Every pixel earns its contrast budget against the sun.
