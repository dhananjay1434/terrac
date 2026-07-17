import { useEffect, useId, useState, type ReactNode } from "react";
import { QRCodeSVG } from "qrcode.react";
import * as Tabs from "@radix-ui/react-tabs";
import {
  registryPost,
  listKilns,
  mintToken,
  AuthError,
  type KilnRow,
} from "../api";
import { kilnQrPayload } from "../qr";
import { useNavigate } from "react-router-dom";
import InfoTip from "../components/InfoTip/InfoTip";

// A tiny generic form: field defs -> values -> POST. Keeps this admin page
// compact without a form library.
type Field = { key: string; label: string; type?: string; required?: boolean };

function Form({
  title,
  fields,
  onSubmit,
}: {
  title: ReactNode;
  fields: Field[];
  onSubmit: (values: Record<string, string>) => Promise<void>;
}) {
  const [v, setV] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);
  const [busy, setBusy] = useState(false);
  const scope = useId();

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
        const missing = fields.some(
          (f) => f.required && !(v[f.key] ?? "").trim(),
        );
        if (missing) {
          setMsg({ text: "Fill required fields", ok: false });
          return;
        }
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
        {fields.map((f) => {
          const id = `${scope}-${f.key}`;
          return (
            <div key={f.key} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <label className="micro" htmlFor={id}>
                {f.label}
              </label>
              <input
                id={id}
                aria-label={f.label}
                type={f.type ?? "text"}
                value={v[f.key] ?? ""}
                onChange={(e) =>
                  setV((s) => ({ ...s, [f.key]: e.target.value }))
                }
              />
            </div>
          );
        })}
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
          <Form
            title={
              <>
                Register kiln (C8)
                <InfoTip label="C8 = kiln & equipment registration criterion." />
              </>
            }
            fields={[
              { key: "kiln_id", label: "kiln id", required: true },
              { key: "kiln_type", label: "type (open/closed)" },
              { key: "material", label: "material" },
              { key: "weight_kg", label: "weight kg", type: "number" },
              { key: "capacity_l", label: "capacity litres", type: "number" },
            ]}
            onSubmit={submitKiln}
          />

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
              title="Supervisor visit"
              fields={[
                { key: "kiln_id", label: "kiln id" },
                { key: "visited_at", label: "visit date", type: "date" },
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
                { key: "calibrated_at", label: "calibrated at", type: "date" },
                { key: "valid_until", label: "valid until", type: "date" },
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
              title="Operator training"
              fields={[
                { key: "operator_id", label: "operator id" },
                { key: "completed_at", label: "completed date", type: "date" },
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
            title={
              <>
                Annual verification (C9)
                <InfoTip label="C9 = annual project verification criterion." />
              </>
            }
            fields={[
              { key: "project_id", label: "project id" },
              { key: "year", label: "year", type: "number" },
              { key: "methane_rate_g_per_kg", label: "methane g/kg", type: "number" },
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
