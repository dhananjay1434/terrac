import { useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import * as Tabs from "@radix-ui/react-tabs";
import * as Dialog from "@radix-ui/react-dialog";
import {
  registryPost,
  listKilns,
  mintToken,
  AuthError,
  type KilnRow,
} from "../api";
import { kilnQrPayload } from "../qr";
import { useNavigate } from "react-router-dom";

// A tiny generic form: field defs -> values -> POST. Keeps this admin page
// compact without a form library.
type Field = { key: string; label: string; type?: string };

function Form({
  title,
  fields,
  onSubmit,
}: {
  title: string;
  fields: Field[];
  onSubmit: (values: Record<string, string>) => Promise<void>;
}) {
  const [v, setV] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!msg) return;
    const t = setTimeout(() => setMsg(null), 4000);
    return () => clearTimeout(t);
  }, [msg]);
  return (
    <form
      className="card"
      style={{ marginBottom: 14 }}
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        setMsg(null);
        try {
          await onSubmit(v);
          setMsg({ text: "✓ Saved", ok: true });
          setV({});
        } catch {
          setMsg({ text: "Save failed — check values", ok: false });
        } finally {
          setBusy(false);
        }
      }}
    >
      <span className="micro">{title}</span>
      <div className="filters" style={{ marginTop: 10 }}>
        {fields.map((f) => (
          <input
            key={f.key}
            placeholder={f.label}
            aria-label={f.label}
            type={f.type ?? "text"}
            value={v[f.key] ?? ""}
            onChange={(e) => setV((s) => ({ ...s, [f.key]: e.target.value }))}
          />
        ))}
        <button className="primary" type="submit" disabled={busy}>
          Save
        </button>
      </div>
      {msg && (
        <div style={{ marginTop: 12 }}>
          <div className={`chip ${msg.ok ? "ok" : "err"}`}>{msg.text}</div>
        </div>
      )}
    </form>
  );
}

function num(s: string | undefined): number | undefined {
  if (!s || !s.trim()) return undefined;
  const n = Number(s);
  return Number.isFinite(n) ? n : undefined;
}

const KILN_STEPS = ["Identity", "Build", "Review"] as const;

/**
 * Register-kiln stepper (Radix Dialog). Steps cover exactly the fields the
 * existing kilns endpoint accepts — the final submit sends the same payload
 * shape the old inline form sent, via the same registryPost("kilns", …).
 */
function KilnStepper({
  onSubmitKiln,
}: {
  onSubmitKiln(values: Record<string, string>): Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);
  const [v, setV] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  function set(k: string, val: string) {
    setV((s) => ({ ...s, [k]: val }));
  }
  function reset() {
    setStep(0);
    setV({});
    setErr(null);
  }
  async function finish() {
    setBusy(true);
    setErr(null);
    try {
      await onSubmitKiln(v);
      setOpen(false);
      reset();
    } catch {
      setErr("Save failed — check values");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(o) => {
        if (busy) return;
        setOpen(o);
        if (!o) reset();
      }}
    >
      <Dialog.Trigger asChild>
        <button className="primary" type="button">
          Register new kiln
        </button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="modal-overlay" />
        <Dialog.Content className="modal-panel" aria-describedby={undefined}>
          <Dialog.Title>Register kiln (C8) — {KILN_STEPS[step]}</Dialog.Title>
          <div className="micro" style={{ margin: "6px 0 12px" }}>
            Step {step + 1} of {KILN_STEPS.length}
          </div>
          {step === 0 && (
            <div className="login" style={{ width: "100%" }}>
              <label className="micro" htmlFor="kiln_id">Kiln id</label>
              <input
                id="kiln_id"
                value={v.kiln_id ?? ""}
                onChange={(e) => set("kiln_id", e.target.value)}
              />
              <label className="micro" htmlFor="kiln_type">Type (open/closed)</label>
              <input
                id="kiln_type"
                value={v.kiln_type ?? ""}
                onChange={(e) => set("kiln_type", e.target.value)}
              />
            </div>
          )}
          {step === 1 && (
            <div className="login" style={{ width: "100%" }}>
              <label className="micro" htmlFor="material">Material</label>
              <input
                id="material"
                value={v.material ?? ""}
                onChange={(e) => set("material", e.target.value)}
              />
              <label className="micro" htmlFor="weight_kg">Weight (kg)</label>
              <input
                id="weight_kg"
                inputMode="decimal"
                value={v.weight_kg ?? ""}
                onChange={(e) => set("weight_kg", e.target.value)}
              />
              <label className="micro" htmlFor="capacity_l">Capacity (litres)</label>
              <input
                id="capacity_l"
                inputMode="decimal"
                value={v.capacity_l ?? ""}
                onChange={(e) => set("capacity_l", e.target.value)}
              />
            </div>
          )}
          {step === 2 && (
            <dl style={{ margin: 0, display: "flex", flexDirection: "column", gap: 8 }}>
              {[
                ["Kiln id", v.kiln_id],
                ["Type", v.kiln_type],
                ["Material", v.material],
                ["Weight (kg)", v.weight_kg],
                ["Capacity (l)", v.capacity_l],
              ].map(([k, val]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                  <dt className="micro">{k}</dt>
                  <dd style={{ margin: 0, fontSize: 13 }}>{val || "—"}</dd>
                </div>
              ))}
            </dl>
          )}
          {err && <div className="err">{err}</div>}
          <div className="modal-actions" style={{ marginTop: 16 }}>
            {step > 0 && (
              <button className="neutral" type="button" disabled={busy} onClick={() => setStep((s) => s - 1)}>
                Back
              </button>
            )}
            <Dialog.Close asChild>
              <button className="neutral" type="button" disabled={busy}>
                Cancel
              </button>
            </Dialog.Close>
            {step < KILN_STEPS.length - 1 ? (
              <button
                className="primary"
                type="button"
                disabled={!(v.kiln_id ?? "").trim()}
                onClick={() => setStep((s) => s + 1)}
              >
                Next
              </button>
            ) : (
              <button
                className="primary"
                type="button"
                disabled={busy || !(v.kiln_id ?? "").trim()}
                onClick={finish}
              >
                {busy ? "Saving…" : "Register kiln"}
              </button>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export default function Registry() {
  const nav = useNavigate();
  const [tab, setTab] = useState("kilns");
  const [kilns, setKilns] = useState<KilnRow[]>([]);
  const [caps, setCaps] = useState<Record<string, string>>({});
  const [token, setToken] = useState<{ token: string; qr_payload: string } | null>(
    null,
  );

  async function refreshKilns() {
    try {
      setKilns((await listKilns()).kilns);
    } catch (e) {
      if (e instanceof AuthError) nav("/login");
    }
  }
  useEffect(() => {
    refreshKilns();
    document.title = "Registry · TerraCipher";
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function submitKiln(val: Record<string, string>) {
    if (val.capacity_l)
      setCaps((c) => ({ ...c, [val.kiln_id]: val.capacity_l }));
    await registryPost("kilns", {
      kiln_id: val.kiln_id,
      kiln_type: val.kiln_type || null,
      material: val.material || null,
      weight_kg: num(val.weight_kg),
    });
    await refreshKilns();
  }

  return (
    <div className="wrap">
      <h1 style={{ fontSize: 20, marginBottom: 14 }}>Registry</h1>
      <Tabs.Root value={tab} onValueChange={setTab}>
        <Tabs.List aria-label="Registry sections" style={{ display: "flex", gap: 4, marginBottom: 14 }}>
          <Tabs.Trigger value="kilns" className={`linkbtn ${tab === "kilns" ? "active" : ""}`}>
            Kilns
          </Tabs.Trigger>
          <Tabs.Trigger value="operators" className={`linkbtn ${tab === "operators" ? "active" : ""}`}>
            Operator training
          </Tabs.Trigger>
          <Tabs.Trigger value="standards" className={`linkbtn ${tab === "standards" ? "active" : ""}`}>
            Standards
          </Tabs.Trigger>
        </Tabs.List>

        <Tabs.Content value="kilns">
          <div style={{ marginBottom: 14 }}>
            <KilnStepper onSubmitKiln={submitKiln} />
          </div>

          {kilns.length > 0 && (
            <section className="card" style={{ marginBottom: 14 }}>
              <span className="micro">Kiln cards (print &amp; mount)</span>
              <div className="media-grid" style={{ marginTop: 12 }}>
                {kilns.map((k) => (
                  <div className="media-cell" key={k.kiln_id} style={{ padding: 10 }}>
                    <QRCodeSVG
                      value={kilnQrPayload({
                        kiln_id: k.kiln_id,
                        kiln_type: k.kiln_type ?? "",
                        capacity_l: num(caps[k.kiln_id]) ?? null,
                      })}
                      size={110}
                    />
                    <div className="cap">
                      {k.kiln_id} · {k.kiln_type}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          <div className="registry-grid">
            <Form
              title="Supervisor visit (idempotent on kiln+date)"
              fields={[
                { key: "kiln_id", label: "kiln id" },
                { key: "visited_at", label: "visit date" },
                { key: "notes", label: "notes" },
              ]}
              onSubmit={(val) =>
                registryPost("supervisor-visit", {
                  visit_uuid: crypto.randomUUID(),
                  kiln_id: val.kiln_id || null,
                  visited_at: val.visited_at || null,
                  notes: val.notes || null,
                }).then(() => undefined)
              }
            />
            <Form
              title="Scale calibration (C8)"
              fields={[
                { key: "scale_id", label: "scale id" },
                { key: "calibrated_at", label: "calibrated at (ISO)" },
                { key: "valid_until", label: "valid until (ISO)" },
              ]}
              onSubmit={(val) =>
                registryPost("scale-calibration", {
                  calibration_uuid: crypto.randomUUID(),
                  scale_id: val.scale_id || null,
                  calibrated_at: val.calibrated_at || null,
                  valid_until: val.valid_until || null,
                }).then(() => undefined)
              }
            />
          </div>
        </Tabs.Content>

        <Tabs.Content value="operators">
          <div className="registry-grid">
            <Form
              title="Operator training (idempotent on operator+date)"
              fields={[
                { key: "operator_id", label: "operator id" },
                { key: "completed_at", label: "completed date" },
                { key: "training_type", label: "training type" },
              ]}
              onSubmit={(val) =>
                registryPost("operator-training", {
                  record_uuid: crypto.randomUUID(),
                  operator_id: val.operator_id || null,
                  completed_at: val.completed_at || null,
                  training_type: val.training_type || null,
                }).then(() => undefined)
              }
            />
            <section className="card" style={{ marginBottom: 14 }}>
              <span className="micro">Enrollment token</span>
              <div className="filters" style={{ marginTop: 10 }}>
                <button
                  className="primary"
                  onClick={async () => {
                    try {
                      setToken(await mintToken({ expires_in_days: 7 }));
                    } catch (e) {
                      if (e instanceof AuthError) nav("/login");
                    }
                  }}
                >
                  Mint enrollment token
                </button>
              </div>
              {token && (
                <div style={{ marginTop: 12 }}>
                  <div className="token-well">
                    <code style={{ fontSize: 12, wordBreak: "break-all" }}>{token.token}</code>
                    <button
                      className="linkbtn"
                      onClick={() => navigator.clipboard.writeText(token.token)}
                    >
                      Copy
                    </button>
                  </div>
                  <div className="micro text-secondary" style={{ marginTop: 8 }}>
                    Shown once — store it now.
                  </div>
                  <div style={{ marginTop: 16 }}>
                    <QRCodeSVG value={token.qr_payload} size={130} />
                  </div>
                </div>
              )}
            </section>
          </div>
        </Tabs.Content>

        <Tabs.Content value="standards">
          <Form
            title="Annual verification (C9, keyed by project+year)"
            fields={[
              { key: "project_id", label: "project id" },
              { key: "year", label: "year" },
              { key: "methane_rate_g_per_kg", label: "methane g/kg" },
            ]}
            onSubmit={(val) =>
              registryPost("annual-verification", {
                project_id: val.project_id,
                year: num(val.year) ?? 2026,
                methane_rate_g_per_kg: num(val.methane_rate_g_per_kg),
              }).then(() => undefined)
            }
          />
        </Tabs.Content>
      </Tabs.Root>
    </div>
  );
}
