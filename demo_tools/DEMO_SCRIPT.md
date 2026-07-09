# dMRV Demo — the spoken script (read once, ~5 min)

You have two things in front of you: **the phone** (the field app) and **the laptop** (the auditor's browser page). Speak in plain sentences, slow down on the trust lines. Stage directions are in `[brackets]` — don't read those aloud.

Everything in the SAY-THIS lines below is **true and code-verified**. The "only if asked" and "never say" sections keep you out of trouble.

---

## THE SCRIPT

### 0. Open — the problem (~20 sec) `[hold the phone, don't tap yet]`
> "Right now, turning a rural biochar burn into a carbon credit runs on a paper logbook and trust. Someone writes down a weight and a date, and months later a verifier shows up with no way to prove any of it actually happened. We built the sensor and the notary that sit at the source of that supply chain. Let me show you."

### 1. The field app — capture a burn (~2 min) `[walk the flow, tapping as you talk]`

`[Dashboard]`
> "This is what the operator uses in the field. One clear action at a time, and a banner that always tells them their data is safe — because out there, there's often no signal."

`[Sourcing → Moisture]`
> "They record the feedstock and the harvest, then the moisture — and they photograph the meter. Here's the important part: **the moment that photo is taken, it's hashed and stamped with GPS and time, right on the device.** You can't swap it, back-date it, or move it later."

`[Pyrolysis]`
> "During the burn we pull live temperature from a Bluetooth thermocouple, plus photos at each smoke stage. `[honest aside, only if hardware comes up:]` For the demo the sensor's simulated, but it's the exact same pipeline as the real hardware."

`[Yield → End-Use]`
> "The biochar weight comes off a Bluetooth crane scale, and finally where it was applied — GPS, a photo, the buyer. Then it's committed."

`[open Proof Wallet]`
> "Every batch becomes a signed cryptographic receipt for the operator."

**The line to land — say it slowly:**
> "Every piece of evidence is signed with a cryptographic key that **never leaves the device.** Not even our own server can forge it. That's real non-repudiation — the thing a carbon buyer actually needs."

### 2. The auditor's view — the finale (~90 sec) `[switch to the laptop browser tab]`
> "Everything the operator captured has synced to the backend. This is what a manager or a Rainbow auditor sees for that batch."

`[point at the verdict badge]`
> "It's marked **provisional** — not issuable. And this is the whole point: **the system will not call a credit 'issued' until every methodology requirement is satisfied.** It doesn't round up, it doesn't assume."

`[point at the checklist]`
> "It grades the batch against the full methodology — feedstock, moisture, the pyrolysis burn, delivery, the lab carbon analysis, the annual checks. Green is corroborated. The open items are exactly what's still needed — and notice some of these say 'lab' or 'awaiting': **the system knows which evidence has to come from an independent lab or verifier, not from the operator's phone.** It won't let the operator self-certify the things that must be independent."

**The closing line — say it slowly:**
> "So the credit isn't a number somebody typed into a spreadsheet. It's the output of grading tamper-evident, signed, field-captured evidence against the standard — and refusing to issue until it holds up. That's what makes it defensible."

### 3. The business close (~20 sec) `[optional — only if the room is a buyer/partner, not a pure auditor]`
> "And it's one codebase. What you're seeing is our India field skin; we've built it so the entire look can switch to a European register or a partner's brand from a single setting — same trusted engine underneath. So this sells three ways: our own app, a partner's white-label, or as a platform."

---

## HIDDEN GEMS — the true differentiators (rank order; each has your one-liner)

Use these if the conversation goes deeper. All verified in the code.

1. **Non-repudiation (Ed25519).** The device signs every upload with a private key generated on the phone that never leaves it. *"The server can't forge a client's data — only the device can produce its signature."* **← your strongest single fact. Lead with it.**
2. **Evidence tamper-evidence.** Photos are SHA-256 hashed + EXIF GPS/time stamped at capture; the local database is **encrypted at rest** (SQLCipher, key in the phone's hardware-backed secure storage). *"The evidence is sealed the instant it's captured, and encrypted on the device."*
3. **Anti-fraud is built in.** The backend cross-checks reported transport against the GPS distance and **flags under-reporting**; it detects mock-GPS and records integrity signals on every batch. *"We assume people will try to game it — so the system watches for it."*
4. **The honesty / provisional engine.** 19 methodology criteria, graded per batch; a credit is never auto-issued. *"It fakes nothing — provisional until proven."* **← the emotional core of the pitch.**
5. **Never-lose-data, offline-first.** Every capture is written to an encrypted local outbox *before* any network attempt, with idempotency keys so nothing double-counts. *"It works with no signal and can't lose a burn."*
6. **One codebase, any market.** Token-driven design → India/Europe skins + white-label by configuration. *"Re-brand or re-region without touching the screens."*

---

## ONLY IF ASKED (don't volunteer these)

- **"Is the hardware secure / can the sensor be spoofed?"** → *"We've architected hardware attestation — the sensor can sign its own readings, and the server has the verification interface wired. We switch it on with Google/Apple device-integrity credentials — it's the next security milestone."* `[TRUE: the path exists; verification is a stub. Do NOT say "we verify hardware attestation today."]`
- **"When does a credit actually get issued?"** → *"When every applicable gate is green and the independent lab and annual data are in. Issuance is a deliberate step, not automatic — by design."*
- **"Does it scale / what's the backend?"** → *"It's a standard cloud API; today it's running on my laptop for the demo."* `[Don't claim production Postgres/scale — it's a pilot backend.]`
- **"How many criteria / which methodology?"** → *"Rainbow / CSI Global Artisan C-Sink — we grade against C0 through C10."*
- **"Can we see it work end to end offline?"** → yes, airplane-mode the phone, capture, show "saved," reconnect, watch it sync.

---

## NEVER SAY (these will get you caught)

- ❌ "The credit is issued / verified / final." — it's **provisional**; that's the feature.
- ❌ "We verify the device hardware / attestation." — architected, not on. Say "designed for."
- ❌ "It captures everything the methodology needs." — it doesn't yet (moisture is one reading, several criteria have no screen). If pushed: *"the methodology is broader than v1's capture — the system honestly shows what's still missing, and that's the roadmap."*
- ❌ "It's production-ready / running in the cloud at scale." — pilot stage.
- ❌ Anything about the credit math internals (H:Corg, decay curves) unless they're technical and ask — you'll get pulled into the weeds.
- ❌ Don't over-explain offline-first — **one line**, framed as a field necessity, then move on. It's table-stakes done well, not the headline.

---

## THE TWO LINES THAT WIN THE ROOM (memorize these)
1. *"Every piece of evidence is signed by a key that never leaves the device — even our own server can't forge it."*
2. *"It will not issue a credit until every methodology gate holds up. It fakes nothing. That's what makes it defensible to an auditor."*
