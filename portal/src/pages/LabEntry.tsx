import { useState, useEffect } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { submitLabResults, uploadLabCertificate, AuthError } from "../api";
import { validateLabForm, type LabForm } from "../lab";
import { GROUP_LABEL } from "../compliance";
import InfoTip from "../components/InfoTip/InfoTip";

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

  return (
    <div className="wrap">
      <Link className="back" to="/lab/scan">
        ← Scan another
      </Link>
      <h1 className="page-title">
        Lab results · {uuid.slice(0, 8)}
      </h1>
      <div className="registry-grid">
        <form className="login" style={{ width: "100%", maxWidth: 420 }} onSubmit={submit}>
          <label className="micro" htmlFor="lab_h_corg">
            H:Corg ratio (0.1–1.5)
            <InfoTip label="Molar hydrogen-to-organic-carbon ratio; a permanence indicator for biochar (target 0.1–1.5)." />
          </label>
          <input
            id="lab_h_corg"
            className="input-lg"
            inputMode="decimal"
            value={form.lab_h_corg}
            onChange={(e) => set("lab_h_corg", e.target.value)}
          />
          <label className="micro" htmlFor="organic_carbon_pct">Organic carbon fraction (0–1]</label>
          <input
            id="organic_carbon_pct"
            className="input-lg"
            inputMode="decimal"
            value={form.organic_carbon_pct}
            onChange={(e) => set("organic_carbon_pct", e.target.value)}
          />
          <label className="micro" htmlFor="biochar_moisture_samples">Biochar moisture samples (≥3, comma sep.)</label>
          <input
            id="biochar_moisture_samples"
            className="input-lg"
            value={form.biochar_moisture_samples}
            onChange={(e) => set("biochar_moisture_samples", e.target.value)}
            placeholder="8, 9, 10"
          />
          <label className="micro" htmlFor="dry_bulk_density">Dry bulk density (kg/m³)</label>
          <input
            id="dry_bulk_density"
            className="input-lg"
            inputMode="decimal"
            value={form.dry_bulk_density}
            onChange={(e) => set("dry_bulk_density", e.target.value)}
          />
          <label className="micro" htmlFor="certificate_pdf">Certificate PDF (optional)</label>
          <input
            id="certificate_pdf"
            className="input-lg"
            type="file"
            accept="application/pdf"
            onChange={(e) => setCert(e.target.files?.[0] ?? null)}
          />
          <button className="primary" type="submit" disabled={busy}>
            {busy ? "Submitting…" : "Submit results"}
          </button>
          {errors.map((er) => (
            <div className="err" key={er}>
              ⚠ {er}
            </div>
          ))}
        </form>
        <aside className="card">
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
              <span className="chip ok">
                ✓ {cert.name} attached ({fmtBytes(cert.size)})
              </span>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
