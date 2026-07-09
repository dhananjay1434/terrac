"""Demo helper: pick the best batch to show in the Verifier View.

Run from the repo root:  python demo_tools/pick_batch.py

Prints each batch with how many evidence pieces it has (most-complete first),
and a ready-to-open Verifier URL for the top one — copy/paste it into the
browser and the compliance record loads with everything pre-filled.
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "..", "backend", "dmrv.db")
API = "http://localhost:8000"             # the browser runs on the laptop, so localhost
PAGE = "http://localhost:8080"            # where you serve the verifier page
# NOTE: the admin secret is NEVER baked into the URL. The verifier page prompts
# for it once and keeps it in sessionStorage. This keeps secrets out of browser
# history, shell history, and shoulder-surfing range.

db = sqlite3.connect(DB)
c = db.cursor()

# Count evidence rows per batch across the side tables so we can rank "fullness".
tables = [
    "pyrolysis_telemetry", "yield_metrics", "moisture_readings",
    "composite_pile_samples", "transport_events", "end_use_application",
    "media_files", "system_metadata",
]
rows = []
for (buid, prov, credit) in c.execute(
    "SELECT batch_uuid, provisional, net_credit_t_co2e FROM batches ORDER BY id DESC"
).fetchall():
    total = 0
    for t in tables:
        try:
            total += c.execute(
                f"SELECT count(*) FROM {t} WHERE batch_uuid = ?", (str(buid),)
            ).fetchone()[0]
        except Exception:
            pass
    rows.append((total, str(buid), prov, credit))

# Most evidence first; break ties by the larger credit (nicer hero number).
rows.sort(key=lambda r: (r[0], r[3] or 0), reverse=True)
print("\nBatches (most complete first):")
print(f"{'evidence':>8}  {'provisional':>11}  {'credit(tCO2e)':>13}  batch_uuid")
for total, buid, prov, credit in rows:
    print(f"{total:>8}  {str(bool(prov)):>11}  {(credit or 0):>13.4f}  {buid}")

if rows:
    _, best, _, best_credit = rows[0]
    url = f"{PAGE}/?api={API}&uuid={best}&credit={best_credit or 0}"
    print("\n>>> Open this URL in your browser for the finale (top/most-complete batch):\n")
    print(url + "\n")
db.close()
