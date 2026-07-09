# Kon-Tiki dMRV — Field Equipment Theme (Overhaul Spec)

*Supersedes `UX_DESIGN_PLAN.md` §5 (color), §6.1 (type), §7 (components), §8 (motion).
Everything else in the design plan — the checklist spine, the calm budget, the screen
inventory, the state machine, the test gates in `UX_EXECUTION_PLAN.md` — survives
unchanged. This is a re-skin of the finish, not the bones.*

*Contrast ratios in this document are **computed** (WCAG 2.x relative luminance,
script-verified against the actual surface hexes, 2026-07-03), not asserted. Re-run
WebAIM/axe on the rendered build at each phase gate per `UX_EXECUTION_PLAN.md`.*

---

## 0. The kill list — what dies today, and why

The previous palette optimized the *surface* for "looks trustworthy to a European
auditor" and produced a crypto-wallet aesthetic. The operator in Sagar, MP is not a
crypto user. He is standing next to a 700°C kiln in 2 PM sun, wearing gloves, afraid
of ruining a batch. Every token below is removed because it serves the wrong person:

| Killed | Was | Why it dies |
|---|---|---|
| `telemetryCyan #00E5FF` | live chart trace | Server-room signal. Heat is orange. A temperature trace drawn in cyan is semantically backwards. |
| `verifiedVault #0B1026` | dark "crypto vault" surface | The tamper-proof moment must read as *official document*, not NFT mint. The vault metaphor is dead. |
| `verifiedGold #D4A017` | certification sigil | Gold-on-black = crypto. Certification now reads as a **rubber stamp** (§5). |
| `tacticalTitanium #F0F4F8` | scaffold | Cold blue-white. Replaced by warm paper (§1). |
| `cobaltShield #1D4ED8` as brand accent | trust blue | Fintech blue. "Live sensor" state no longer needs its own accent hue (§1.3). |
| **Space Grotesk** (all uses) | headings/labels/buttons | Hacker-terminal geometry. Replaced by Noto Sans (§2). |
| **Space Mono** in the operator path | hero readings | Monospace hero numbers = terminal. Quarantined to the auditor disclosure only (§2.3). |
| Crypto vocabulary (`vault`, `telemetry`, `tactical`, `armor`, `shield`) | token names | Names steer designers. New names come from the operator's world: paper, ink, machine, tractor, seal. |

**What explicitly survives:** the calm budget (≤1 primary action, ≤2 accents on
screen, ≤5 above-fold), ≥64px targets, haptics-before-callback, the checklist spine,
offline-as-default, the provisional↔certified state machine bound to the backend
signature, and the rule that the UI never renders a credit as certified that the
backend calls provisional.

---

## 1. The Rugged Palette — "paper, ink, and machinery"

The organizing metaphor: **a government field form filled out next to a machine.**
Paper surface, carbon-ink text, safety-orange machinery for actions, tractor-green
for confirmed, stamp-ink blue for certified. Nothing glows.

### 1.1 Ground (neutrals)

| Token | Hex | Use | Rationale + computed contrast |
|---|---|---|---|
| `paper` | `#ECE7DC` | All scaffold backgrounds | Sun-bleached paper / khadi. High-albedo (survives 2 PM sun — reflected light dominates the panel outdoors, so light ground = max effective contrast) but warm and ~8% dimmer than pure white → measurably less glare bounce than `#F0F4F8`, and it reads as *material*, not screen. |
| `paperRaised` | `#F6F3EB` | Cards/panels | Only 1.11:1 tonal difference vs `paper` — deliberately subtle, so **cards are defined by their border, not their fill** (§3.4). Soft shadows die in sunlight; borders don't. |
| `ink` | `#211D16` | All primary text/icons | Warm carbon black — literally the color of biochar. **13.6:1 on `paper`**, 15.1:1 on `paperRaised`. Not pure black: less glare shimmer. |
| `inkMuted` | `ink @ 72%` | Secondary text | Effective ~`#5B564B` → **5.92:1** on `paper`. Passes AA with margin (the old 60% token was a 4.56:1 squeaker — fixed by moving to 72%). Floor: 16px. |
| `inkLine` | `ink @ 15%` | Borders, dividers, ruled lines | Structure like a printed form's rules. |
| `charcoal` | `#26221C` | ONE surface only: the live pyrolysis chart panel | The single dark panel in the app. A live temperature trace reads best on dark, like a real instrument cluster — and the trace is drawn in **ember amber `#FFA94D`** (~8:1 on charcoal, re-verify at handoff), because heat is orange. This is the only place dark-panel treatment is permitted. |

### 1.2 Action & state (the ≤2-accent budget)

| Token | Hex | Meaning | Rationale + computed contrast |
|---|---|---|---|
| `machineOrange` | `#E8590C` (fill) / `#9A3412` (text/icon on paper) | THE primary action. "Do this next." Also the pending/saved-locally chip. | High-vis safety orange — chainsaws, tow hooks, hazard vests. Universally decoded as "the part you operate," including by non-readers. **Fill labels are `ink` (black-on-orange, 4.68:1 ✅) exactly like real safety equipment — white-on-orange is 3.58:1 and is BANNED for normal text.** Text-on-paper form `#9A3412` = 5.93:1 ✅. |
| `tractorGreen` | `#2E6B1F` | Confirmed. Sensor locked, step corroborated, upload done. | Agricultural equipment green — the green of a machine that works, not a mint-green app chip. **5.26:1 on `paper`** ✅ as text; as a fill, labels are white ≥18px bold (6.48:1 ✅). The single "done" color. |
| `sealBlue` | `#2E3A8C` | CERTIFIED — and nothing else. | Stamp-pad ink. The color of the *sarkari mohar* — the round official stamp every operator has seen on a land record, a mandi receipt, a ration card. **8.11:1 on `paper`** ✅. It appears exclusively in the stamp treatment (§5.2) and the certified chip. Scarcity is the point: when blue ink appears, it is final. |
| `hotIronRed` | `#B91C1C` | Errors that block the credit. Nothing decorative, ever. | **5.25:1 on `paper`** ✅ — the warm surface fixes the old two-tier red problem; one red token, no exceptions table. Fill use: white ≥18px bold labels. |

### 1.3 What happened to "live/connected blue"

Deleted as an accent. Live-sensor state is now shown structurally, not chromatically:
a **pulsing `tractorGreen` dot + the word "जुड़ा" (connected)** in the connection
pill, grey dot for idle, `hotIronRed` dot + "टूट गया" for lost. Rationale:
connected-ness is a precondition, not an achievement — it doesn't earn one of the
two accent slots on a capture screen (those belong to the action and the state).
This *frees the calm budget*: scale screen = orange CTA + green lock-state. Two
accents, done.

### 1.4 Calm-budget mapping (unchanged rule, new hues)

Per screen, at most: **1× `machineOrange` element** (the primary action or the
pending chip — if both would appear, the chip demotes to outline style) and **1×
state color** (`tractorGreen`, `sealBlue`, or `hotIronRed` — these never co-occur
as accents because a row is in exactly one state). Everything else is `paper`/`ink`.

### 1.5 Computed contrast table (the gate)

| Pair | Ratio | AA 4.5 normal |
|---|---|---|
| `ink` on `paper` | **13.60:1** | ✅ |
| `inkMuted` (72%) on `paper` | **5.92:1** | ✅ (≥16px rule anyway) |
| `machineOrange` text `#9A3412` on `paper` | **5.93:1** | ✅ |
| `ink` on `machineOrange` fill | **4.68:1** | ✅ |
| white on `machineOrange` fill | 3.58:1 | ❌ **banned** for normal text (large-only, avoid) |
| `tractorGreen` on `paper` | **5.26:1** | ✅ |
| white on `tractorGreen` fill | **6.48:1** | ✅ |
| `sealBlue` on `paper` | **8.11:1** | ✅ |
| `hotIronRed` on `paper` | **5.25:1** | ✅ |
| `hotIronRed` on `paperRaised` | **5.83:1** | ✅ |
| `paper` vs `paperRaised` (non-text) | 1.11:1 | borders carry structure, by design |

No token in the operator path is below 4.5:1. The two fragile tokens of the old
palette (`#DC2626` small text, 60% muted) are gone, not special-cased.

---

## 2. Typography — the tractor manual, not the terminal

### 2.1 One superfamily, two scripts

**Latin/digits: `Noto Sans`. Devanagari: `Noto Sans Devanagari` (already shipped).**

This is the entire recommendation, and it is deliberately boring. Noto Sans and Noto
Sans Devanagari are the *same designed superfamily* — harmonized x-heights, stroke
weights, and vertical metrics. A mixed Hindi/Latin line ("बैच A47 · 142 kg") sets as
**one voice**, with no visual seam where the script switches. That seam is exactly
where a low-literacy reader stumbles. No display face. No personality font. The
personality of this app is the paper, the orange machinery, and the stamp — the type's
job is to disappear into legibility, like a tractor manual.

Weights: 400 (body), 500 (labels), 700 (headings, buttons, hero numbers). Nothing else.

**Engineering note:** add `NotoSans-Regular/Medium/Bold.ttf` (OFL, free) to
`assets/fonts/` + `pubspec.yaml`. `SpaceGrotesk-*.ttf` is deleted from the bundle at
migration end (Phase 3 gate). `SpaceMono-Regular.ttf` stays for §2.3 only.

### 2.2 Type scale (Hindi-first floors)

| Role | Font / Weight | Size | Notes |
|---|---|---|---|
| Hero reading (kg / °C / %) | Noto Sans 700 + **tabular figures** | 64 | `FontFeature.tabularFigures()` gives digit alignment WITHOUT monospace — kills the terminal look, keeps the instrument alignment. |
| Screen title | Noto Sans / Devanagari 700 | 24 | |
| Step / row label (Hindi) | Noto Sans Devanagari 700 | 20 | Devanagari conjuncts need x-height; 700 weight survives glare. |
| Body / instruction (Hindi) | Noto Sans Devanagari 400 | 18 | Floor for prose. |
| Button label | Noto Sans / Devanagari 700 | 18 | +0.25 tracking, sentence case (ALL-CAPS Devanagari doesn't exist; don't case-shift Latin either — one rule for both scripts). |
| Meta / units / dates | Noto Sans 500 | 16 | `inkMuted` floor per §1.1. |
| Auditor detail (hash/GPS) | **Space Mono 400** | 14 | §2.3 quarantine only. |

Digits: Latin numerals (0-9) by default — the persona reads numbers fluently and the
scale/thermocouple hardware displays them; a Devanagari-numeral locale switch is a
later, cheap addition.

### 2.3 The Space Mono quarantine

Monospace appears in exactly one place: the **"तकनीकी विवरण / Technical details"**
disclosure — a collapsed-by-default row at the bottom of a batch/proof detail screen
containing the evidence hash, the raw GPS pair, the device ID, and the signature
state. It exists so Priya or an auditor can stand next to the operator and verify;
the operator never needs to open it. Space Mono anywhere else in the widget tree is
a **build-time lint failure** (Phase 0 adds the check). Hashes are never rendered
outside this disclosure — an operator-facing error says "फ़ोटो दोबारा लें" (retake
the photo), never `hash mismatch 0x…`.

---

## 3. Components — chunky, punchable, obviously physical

Design law for every component: **no soft shadows, no gradients, no glow.** All die
in sunlight. Depth is communicated the way physical equipment communicates it — a
hard bottom edge, like a keyboard key or a machine button.

### 3.1 `FieldButton` (replaces RuggedButton + PremiumFieldButton)

Chassis: full-width, **min-height 72px** (up from 64 — this is THE button; primary
actions get the biggest target in the app), radius 10, label Noto Sans 700 18px,
optional 28px leading icon. `Semantics` label required. Constructed as a **key cap**:
a face plate sitting on a 4px solid hard edge in a ~25% darker shade of the face
color. No elevation shadows.

| Variant | Face | Edge | Label |
|---|---|---|---|
| `primary` | `machineOrange #E8590C` | `#B4530A` | `ink` (black-on-orange, like real safety gear) |
| `confirm` | `tractorGreen #2E6B1F` | `#1F4A15` | white, 18px 700 (6.48:1 ✅) |
| `danger` | `hotIronRed #B91C1C` | `#7F1414` | white, 18px 700 |
| `neutral` | `paperRaised` + 2px `ink` border | `ink @ 30%` | `ink` |

**States (the tactility spec):**
- **Default:** face + 4px edge visible. It *looks* raised because it has an underside,
  not because of a blur.
- **Pressed (pointer-down):** face translates down 3px, edge compresses to 1px,
  `HapticFeedback.heavyImpact()` fires **on press-down** (kept from RuggedButton —
  the only feedback a gloved hand feels, and it lands even if the async save is slow).
  `onPressed` fires on release inside bounds.
- **Disabled:** edge removed (flat = dead), face `ink @ 8%`, label `ink @ 38%`.
  A disabled FieldButton must always sit above one line of Hindi explaining what
  unlocks it ("पहले वज़न लॉक करें" — lock the weight first). Never a mystery.
- **Busy:** face keeps color, label swaps to "सेव हो रहा है…" + inline 3-dot pulse.
  Never a bare spinner replacing the button.

### 3.2 `ChecklistRow` (the spine, restyled)

88px min-height row on `paperRaised`, pressed state = whole row depresses 2px (rows
are buttons; they must feel like it). Layout: **56px pictogram tile** (real object
icons — a log, a water drop, a flame, a weighing scale, a truck, a field — not
abstract UI glyphs) · Hindi label 20/700 · state marker right.

State markers (one visual language, everywhere):
- **Not started:** dashed `inkLine` circle, tile at 45% opacity.
- **Saved on device (provisional):** half-filled `machineOrange` circle + micro-label
  "फ़ोन में" — the *parchi* (receipt slip) state.
- **Confirmed:** solid `tractorGreen` circle with white ✓.
- **Blocked:** `hotIronRed` circle with white ✕ + one plain-language fix line under
  the label. The fix is an action, not a diagnosis.

### 3.3 `ReadingCard` (scale / thermocouple hero)

`paperRaised` card. Hero value: Noto Sans 700 **64px tabular**, unit in 20px
`inkMuted` beside it. Connection pill above (§1.3 dot + word). While the value is
moving, digits render `inkMuted`; when stable ≥1.5s they snap to `ink` — the number
itself tells you when it's trustworthy. `confirm` FieldButton ("वज़न लॉक करें")
below, disabled until stable. Idle/no device: `--·-` placeholder, never a fake zero.

### 3.4 Cards & structure

Cards: `paperRaised`, radius 12, **1.5px `inkLine` border** — the border does the
lifting (the 1.11:1 tonal step won't, by design). Section structure inside a screen
uses ruled `inkLine` dividers, like a printed form. Dividers are never darker than
15% — heavy lines read as errors to low-vision users.

### 3.5 `IntegrityFooter` (restyled, same job)

Persistent bottom strip on `paper` with a 1.5px `inkLine` top rule (no more dark
vault footer). Content: lock icon + "सब कुछ फ़ोन में सुरक्षित · 3 भेजना बाकी"
(everything safe on the phone · 3 left to send). Counts in tabular figures. When the
last item uploads, the count line swaps to `tractorGreen` "सब भेज दिया ✓" for 3s.
Tap → sync detail screen. Offline shows a neutral cloud-off glyph + "अपने आप भेजेगा"
(will send automatically) — offline is a status, never an alarm.

---

## 4. Micro-interactions — haptic + voice, eyes-free confirmation

The operator's eyes are on the kiln, his gloves are on, the sun is on the screen.
Confirmation must land through **three redundant channels — felt, heard, seen — any
one of which is sufficient alone.** Toasts are none of these; there are no toasts in
the operator path.

### 4.1 The haptic grammar (three words, total)

| Pattern | Meaning | Fired when |
|---|---|---|
| 1× `heavyImpact` | "the button felt you" | Pointer-down on any FieldButton / ChecklistRow |
| 2× `heavyImpact`, 90ms apart | "SAVED — it's in the phone" | The local DB transaction **commits** (not on tap — on commit; the double-thump is a physical receipt) |
| 1× 400ms vibrate | "problem — look at the screen" | Any blocking error |

Nothing else vibrates. Navigation is silent. The vocabulary stays learnable
precisely because it has three words. (Sequencing note: a tap that saves produces
thump … double-thump — press acknowledged, then commit confirmed. On a fast device
that's ~150ms apart; do not debounce them into one.)

### 4.2 Voice confirmations (Hindi, recorded, offline)

Pre-recorded human Hindi clips (a real voice, warm and unhurried — TTS sounds like
the machine talking *at* you; a human voice sounds like a colleague confirming),
bundled in assets, played offline, ≤2 seconds each:

| Event | Clip (script) |
|---|---|
| Reading locked | "वज़न सेव हो गया।" (the weight is saved) |
| Photo captured & hashed | "फ़ोटो सुरक्षित है।" (the photo is secure) |
| Step confirmed | "यह काम पूरा हुआ।" (this task is complete) |
| Batch 100% captured | "सब कुछ पूरा — अब फ़ोन भेज देगा।" (all done — the phone will send it) |
| **Certified stamp lands** | "बैच प्रमाणित हो गया।" (the batch is certified) |
| Blocking error | "रुकिए — स्क्रीन देखिए।" (stop — look at the screen) |

Rules: voice fires **only on state changes** (never navigation, never focus), respects
the ringer switch and a settings mute, never queues more than one clip (latest wins),
and every voice-confirmed state also exists visually — voice is reinforcement, not
the only record. Every instruction screen carries a small speaker icon to replay the
instruction aloud (non-readers), and clips are a swappable asset pack (Bundelkhandi
dialect later without an app release).

### 4.3 The save sequence (the trust beat, end to end)

Tap "लॉक करें" → thump + button depresses → local write commits → **double-thump +
digits sweep `inkMuted`→`tractorGreen`→`ink` (250ms) + "वज़न सेव हो गया।"** → row on
the checklist morphs ◐ orange. Total ≤400ms of motion. This beat is *warm* — it is
the daily reward. The once-per-batch stamp (§5.2) is the only bigger moment.

---

## 5. The operator's flow — a day's work, not a wizard

### 5.1 One screen = one physical tool

The "1 primary action per screen" rule is kept by making each screen *be the tool
for one physical act*, named by the act in Hindi, ordered on the checklist the way
the burn day actually runs — but tappable in any order, because real days don't run
in order:

| Checklist row (pictogram + Hindi) | Physical act | Screen |
|---|---|---|
| 🪵 लकड़ी तौलो | weigh the feedstock | Biomass sourcing |
| 💧 नमी जाँचो | check the moisture | Moisture capture loop |
| 🔥 भट्टी जलाओ | run the burn | Pyrolysis (charcoal panel + ember trace) |
| ⚖️ कोयला तौलो | weigh the char | Yield capture |
| 🧪 नमूना रखो | set the sample aside | Composite sample |
| 🚜 गाड़ी का हिसाब | log the transport | Transport legs |
| 🌱 खेत में डालो | spread it in the field | End-use / delivery |

Each screen: the tool (hero reading or camera), one orange button, back to the
checklist. The checklist header holds the batch's progress ring and its current
paper-state (§5.2). The operator never meets the words "wizard," "step 3 of 9,"
"provisional," or "hash."

### 5.2 Provisional → Certified: the *parchi and the mohar*

The farmer already has a perfect mental model for asynchronous certification — **the
receipt and the stamp.** At the mandi or the land-records office, you get a paper
slip immediately (proof you were there), and the *official round stamp* arrives when
the office processes it. Nobody has ever needed cryptography explained to trust a
stamped document. So:

- **Saved locally** → the batch card shows a receipt-slip motif with an orange tag
  **"फ़ोन में सेव"** (saved in the phone). Immediate, guaranteed, offline.
- **Sent** → tag turns grey-green **"भेज दिया"** (sent). Quietly, from the footer.
- **CERTIFIED** (backend: signed, non-provisional, issued) → the **mohar lands**: a
  round `sealBlue` rubber-stamp — rough ink edge, rotated ~-6°, reading
  **"प्रमाणित ✓"** with the date — stamps onto the batch card with a single 500ms
  scale-and-settle thunk, one `heavyImpact`, and the voice line. Once per batch.
  This replaces the gold NFT sigil with the most trusted graphic in rural Indian
  administrative life.

**The honesty contract, restated in stamp language:** no stamp is ever rendered
unless the backend has actually issued. An unstamped receipt is still shown proudly
("आपका काम फ़ोन में सुरक्षित है") — but the blue ink only ever comes from the server's
signature. The Proof Wallet becomes a **stack of receipts, some stamped** — which is
exactly what it cryptographically is.

### 5.3 Errors, in this language

A blocking error is a red row + one plain fix, and — always — the line
**"बाकी सब सुरक्षित है"** (everything else is safe). The #1 abandonment cause is
believing an error destroyed the day's work; every error screen explicitly denies it.

---

## 6. Migration map (for the Flutter team, Phase 0/1)

| Old token / widget | New | Mechanical? |
|---|---|---|
| `tacticalTitanium` | `paper #ECE7DC` | yes — alias then recolor |
| `pureAlbedo` | `paperRaised #F6F3EB` | yes |
| `armorSlate` (+opacity ladder) | `ink #211D16` (+72/38/15/8 ladder) | yes |
| `cobaltShield` | pill dot per §1.3 (`tractorGreen`/grey/`hotIronRed`) | per-callsite |
| `yieldGold` / `verifiedGold` | `sealBlue #2E3A8C` stamp treatment | per-callsite |
| `neonYellow` | `machineOrange` fill/text pair | yes |
| `fieldGreen` | `tractorGreen #2E6B1F` | yes |
| `crimsonRed` / `#B91C1C` split | single `hotIronRed #B91C1C` | yes |
| `midnightCyber`, `telemetryCyan`, `deepSlate`, `panelSlate` | deleted (`charcoal #26221C` + ember `#FFA94D` for the one chart) | delete |
| SpaceGrotesk styles | Noto Sans 400/500/700 | yes |
| SpaceMono hero numbers | Noto Sans 700 + `tabularFigures` | yes |
| SpaceMono elsewhere | lint-banned outside the auditor disclosure | Phase 0 lint |
| `RuggedButton`+`PremiumFieldButton` | `FieldButton` §3.1 | codemod |

Phase gates, calm budget, and the §C per-screen DoD in `UX_EXECUTION_PLAN.md` apply
unchanged — with one added gate item: **no soft shadow / gradient / glow anywhere in
the operator path** (golden tests catch regressions).

---

## 7. Why this is trustworthy to BOTH audiences (the resolution)

The auditor's trust never came from cyan. It comes from the state machine, the
signatures, and the compliance gate — which are untouched. The auditor gets her
register in the two places she actually looks: the technical-details disclosure
(§2.3) and Priya's console. The operator gets an app that looks like the two things
he already trusts with his livelihood: **his equipment and his stamped papers.**
One product, two honest registers, zero crypto cosplay.
