# PM Roadmap — TerraCipher dMRV vs Varaha "Kalki" (unbiased, multi-agent synthesis)

Synthesized from four parallel domain deep-dives (farmer lifecycle, field
capture/production, logistics/facility ops, platform), each code-verified
against both products. No cheerleading — where we're behind, it says so; where
we lead, it says why it's defensible.

## The honest one-paragraph verdict

Varaha is a **shipping, full-supply-chain operations platform** (KYC + payments +
consent, logistics, dispatch, facility admin, multi-country/role/tenant) at
v1.6.2. We are a **pre-production, integrity-first MRV pipeline** with a genuine
technical moat Varaha does not have: **encrypted-at-rest data, Ed25519-signed
evidence, hardware-sensor-grounded burn data (BLE thermocouple + secure-element
attestation), a transparent server-side credit engine, and a verifier portal.**
On *operational breadth* Varaha wins decisively (~15–20% coverage on logistics,
a `// TODO` on farmer KYC). On *evidence defensibility* we win decisively. The
roadmap: fix one credibility-destroying bug immediately, then buy breadth without
trading away the moat.

## Domain scorecard

| Domain | Winner | Margin | Note |
|---|---|---|---|
| Evidence integrity / security | **TerraCipher** | Large | SQLCipher + Ed25519 signing + sensor attestation vs plaintext DB + unsigned metadata |
| Burn / production evidence | **TerraCipher** | Medium | Live BLE temperature + stabilized scale vs photos of smoke |
| Credit engine + verifier product | **TerraCipher** | Large | Transparent CSI/Rainbow engine + auditor portal vs none in-app |
| i18n | **TerraCipher** | Small | en+hi+Devanagari vs English-only |
| Farmer lifecycle (KYC/pay/consent) | **Varaha** | Large | Full offline module vs non-functional stub |
| Logistics & facility ops | **Varaha** | Large | ~30 screens/6 tables/2 state machines vs ~1.5 partial |
| Boundary / land mapping | **Varaha** | Large | Real map+WKT+overlap vs a **fake stub** (see 🔴 below) |
| Media pipeline | **Varaha** | Medium | compress/transcode/presigned-S3/progress vs full-res two-phase |
| Remote ops (flags/kill-switch/updates) | **Varaha** | Large | Firebase Remote Config + in-app updates vs none |
| Observability breadth | **Varaha** | Medium | Crashlytics+Perf+APM vs Sentry-only |
| Cross-platform / iOS shipping | **Varaha** | Medium | KMP iOS shipping vs Flutter Android-only |
| ML on-device vision | **Varaha** | Medium | doc-scanner/barcode vs none |
| Production maturity | **Varaha** | Large | v1.6.2 shipped, 3 countries vs pre-production |

## 🔴 Urgent, do-before-anything-else (integrity credibility)

**Fix the boundary-mapping false attestation.** Our sourcing screen tells the
operator a GPS polygon was captured ("captured / 4 vertices") while persisting
only a **boolean** (`lib/providers/lantana_sourcing_notifier.dart:209-214`,
`lantana_sourcing_screen.dart:304-370`). This is worse than a missing feature —
it is a *fabricated evidence claim* an auditor can trivially expose, and it
directly contradicts the "signed, sensor-grounded, tamper-evident" story that is
our entire differentiator. Two acceptable fixes: (a) build real capture (see
P0-2), or (b) immediately remove the fake affordance until real capture ships.
**Do not demo the current stub as if it works.** Effort to de-fake: S.

## The unified roadmap (reconciled across all four domains)

Priorities reconciled by a single PM lens: **credibility risk first, then
compete-ability, then differentiators.** Effort: S ≤1 sprint · M 1–2 · L 3+.

### P0 — must, before calling it a product
| # | Item | Domain | Effort | Type | Why |
|---|---|---|---|---|---|
| 1 | De-fake OR build **real boundary mapping** (map + GPS-walk/draw → WKT + server overlap check) | Capture | S (de-fake) / L (full) | Table-stakes | Fixes the false attestation; land parcel is registry table-stakes |
| 2 | **Farmer registry + hash-anchored FPIC consent** (persisted, syncable; template→sign→upload + holding photo, SHA-256 anchored) | Farmer | M | Table-stakes + differentiator | Legal/credit-eligibility blocker; we can do it *better* than Varaha (they don't hash consent) |
| 3 | **Facility entity + Dispatch state machine** (Draft→In-Transit→Received; source-weigh → facility-reweigh) | Logistics | L | Table-stakes | The defining primitive of a supply chain; today we can't represent material moving between custodians |
| 4 | **Remote control plane** (signed boot-time config: feature flags + kill-switch + min-version gate) | Platform | M | Table-stakes | Private-APK + CI-off = zero ability to respond to a live incident on the fleet |

### P1 — needed to actually compete
| # | Item | Domain | Effort | Type |
|---|---|---|---|---|
| 5 | **Media compression/transcode + upload progress %** | Platform | M | Table-stakes (rural bandwidth / farmer trust) |
| 6 | **Field roles + multi-facility scoping** (Site/Facility Manager, Enumerator) | Logistics | L | Table-stakes for multi-crew |
| 7 | **Dual weighing + tare + method + truck-fill %**, delta→corroboration flag | Logistics | M | Table-stakes → integrity differentiator (hash-anchor both tickets) |
| 8 | **Multi-site aggregation** (N source sites → one truck load) | Logistics | M | Table-stakes (field reality) |
| 9 | **Bulk-density capture** (reuse BLE scale + kiln volume → density) | Capture | M | Table-stakes; cheapest high-value add |
| 10 | **Farmer list/search/profile + ID doc + payment (UPI/bank)** | Farmer | M | Table-stakes |
| 11 | **In-app / forced update** (self-hosted APK min-version) | Platform | M | Table-stakes (no store) |
| 12 | **Observability breadth** (extend Sentry: perf + release-health) | Platform | M | Table-stakes |
| 13 | **QR/barcode scanner** (bind kiln + composite bag by scan; we already generate the QR) | Capture | S | Differentiator (closes our own chain) |
| 14 | **In-app video capture** (quenching/flame-curtain, hash+EXIF) | Capture | M | Table-stakes |

### P2 — differentiators / scale / later
| # | Item | Domain | Effort |
|---|---|---|---|
| 15 | Multi-tenant / multi-org backend (`organization_id` + tenant header) | Logistics/Platform | L |
| 16 | Pull-sync + conflict/tombstone states | Platform | L |
| 17 | Encrypted PII lead is already ours — market it; keep it as consent/payment land | Farmer | — |
| 18 | Biochar→farmer distribution flow + history | Logistics | M |
| 19 | ML Kit document scanner; address/IFSC auto-fill | Farmer/Capture | M |
| 20 | On-device PDF (verifier packets, weight slips) | Capture | M |
| 21 | True iOS build-out (cheaper for us via Flutter) | Platform | L |
| 22 | Day-start facility audit; dispatch worklist; facility intake entity | Logistics | S each |

## The moat to protect (do not trade away)

Every new feature above MUST preserve: **encryption-at-rest (SQLCipher),
Ed25519-signed + replay-protected evidence, and sensor-grounded measurement
(BLE temperature/weight + hardware attestation).** These are architectural, not
features Varaha can bolt on in a sprint — they are the reason our credits are
more defensible. When we add presigned-S3 media, iOS, dispatch, etc., each must
keep the signed-canonical + encrypted guarantee. This is also the hero of the
comparison video: *"the most trustworthy carbon data"* vs *"the most complete
operations."*

## Do NOT copy from Varaha (their shipped mistakes)
Plaintext PII at rest, cleartext traffic + no cert pinning, a network inspector
(Inspektify) shipped in production, and APM pointed at a test endpoint in prod.
These are in their live v1.6.2 build — useful contrast points, not patterns.

## Suggested sequencing for the demo/meetings
1. **Now:** de-fake boundary (🔴) so nothing on stage is a false claim.
2. **Sprint 1–2:** P0-2 (farmer registry + FPIC) and P0-4 (control plane) — both
   medium, both close a glaring gap and a safety gap.
3. **Sprint 3+:** P0-3 (facility + dispatch) — the large structural investment
   that makes us a supply-chain product, built on our signed/encrypted spine.
4. **Throughout:** lead every pitch with the integrity moat; show the security
   scorecard (we win 8/9) against a real, named, shipping competitor.
