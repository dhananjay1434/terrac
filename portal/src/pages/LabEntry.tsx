import { useState, useEffect } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { submitLabResults, uploadLabCertificate, AuthError } from "../api";
import { validateLabForm, type LabForm } from "../lab";
import { GROUP_LABEL } from "../compliance";
import InfoTip from "../components/InfoTip/InfoTip";
import Button from "../ui/Button/Button";
import Card from "../ui/Card/Card";
import StatusPill from "../ui/StatusPill/StatusPill";
import Field from "../ui/Field/Field";

const EMPTY: LabForm = {
  lab_h_corg: "",
  organic_carbon_pct: "",
  biochar_moisture_samples: "",
  dry_bulk_density: "",
};

function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

// validateLabForm returns a flat list; route each message to the field it
// belongs to so it renders under that input. Unmatched messages (e.g. "enter
// at least one result", a submit failure) stay form-level.
type FieldErrors = {
  lab_h_corg?: string;
  organic_carbon_pct?: string;
  biochar_moisture_samples?: string;
  dry_bulk_density?: string;
  form?: string;
};
function fieldErrors(errs: string[]): FieldErrors {
  const fe: FieldErrors = {};
  for (const e of errs) {
    if (e.includes("H:Corg")) fe.lab_h_corg = e;
    else if (e.includes("Organic carbon")) fe.organic_carbon_pct = e;
    else if (e.toLowerCase().includes("moisture")) fe.biochar_moisture_samples = e;
    else if (e.includes("Dry bulk density")) fe.dry_bulk_density = e;
    else fe.form = e;
  }
  return fe;
}

export default function LabEntry() {
  const { uuid = "" } = useParams();
  const nav = useNavigate();
  const [form, setForm] = useState<LabForm>(EMPTY);
  const [cert, setCert] = useState<File | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    document.title = "Lab results · TerraCipher";
  }, []);

  function set(k: keyof LabForm, v: string) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const { errors: errs, body } = validateLabForm(form);
    setErrors(errs);
    if (errs.length) return;
    setBusy(true);
    try {
      await submitLabResults(uuid, body as Record<string, unknown>);
      if (cert) await uploadLabCertificate(uuid, cert);
      nav(`/batches/${uuid}`);
    } catch (e) {
      if (e instanceof AuthError) nav("/login");
      else setErrors(["Submit failed — check the values and try again."]);
    } finally {
      setBusy(false);
    }
  }

  const fe = fieldErrors(errors);

  return (
    <div className="wrap">
      <Link className="back" to="/lab/scan">
        ← Scan another
      </Link>
      <h1 className="page-title">
        Lab results · <span className="mono">{uuid.slice(0, 8)}</span>
      </h1>
      <div className="registry-grid">
        <form className="login" style={{ width: "100%", maxWidth: 420 }} onSubmit={submit}>
          <Field
            label={
              <>
                H:Corg ratio (0.1–1.5)
                <InfoTip label="Molar hydrogen-to-organic-carbon ratio; a permanence indicator for biochar (target 0.1–1.5)." />
              </>
            }
            htmlFor="lab_h_corg"
            error={fe.lab_h_corg}
          >
            <input
              id="lab_h_corg"
              className="input-lg"
              inputMode="decimal"
              value={form.lab_h_corg}
              onChange={(e) => set("lab_h_corg", e.target.value)}
            />
          </Field>
          <Field
            label="Organic carbon fraction (0–1]"
            htmlFor="organic_carbon_pct"
            error={fe.organic_carbon_pct}
          >
            <input
              id="organic_carbon_pct"
              className="input-lg"
              inputMode="decimal"
              value={form.organic_carbon_pct}
              onChange={(e) => set("organic_carbon_pct", e.target.value)}
            />
          </Field>
          <Field
            label="Biochar moisture samples (≥3, comma sep.)"
            htmlFor="biochar_moisture_samples"
            hint="e.g. 8, 9, 10 — three or more percentages"
            error={fe.biochar_moisture_samples}
          >
            <input
              id="biochar_moisture_samples"
              className="input-lg"
              value={form.biochar_moisture_samples}
              onChange={(e) => set("biochar_moisture_samples", e.target.value)}
            />
          </Field>
          <Field
            label="Dry bulk density (kg/m³)"
            htmlFor="dry_bulk_density"
            error={fe.dry_bulk_density}
          >
            <input
              id="dry_bulk_density"
              className="input-lg"
              inputMode="decimal"
              value={form.dry_bulk_density}
              onChange={(e) => set("dry_bulk_density", e.target.value)}
            />
          </Field>
          <Field label="Certificate PDF (optional)" htmlFor="certificate_pdf">
            <input
              id="certificate_pdf"
              className="input-lg"
              type="file"
              accept="application/pdf"
              onChange={(e) => setCert(e.target.files?.[0] ?? null)}
            />
          </Field>
          <Button type="submit" disabled={busy}>
            {busy ? "Submitting…" : "Submit results"}
          </Button>
          {fe.form && <div className="err">⚠ {fe.form}</div>}
        </form>
        <Card as="aside">
          <span className="micro">{GROUP_LABEL.lab}</span>
          <div style={{ marginTop: 10, fontSize: 13, fontWeight: 600 }}>
            Rules checked on submit
          </div>
          <ul
            style={{
              margin: "8px 0 0 18px",
              fontSize: 13,
              color: "var(--text-secondary)",
              lineHeight: 1.7,
            }}
          >
            <li>H:Corg ratio within 0.1–1.5</li>
            <li>Organic carbon fraction within (0–1]</li>
            <li>At least 3 comma-separated moisture samples</li>
            <li>Dry bulk density in kg/m³</li>
          </ul>
          {cert && (
            <div style={{ marginTop: 14 }} data-testid="cert-attached">
              <StatusPill status="success">
                ✓ {cert.name} attached ({fmtBytes(cert.size)})
              </StatusPill>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
