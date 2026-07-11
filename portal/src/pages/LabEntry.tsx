import { useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { submitLabResults, uploadLabCertificate, AuthError } from "../api";
import { validateLabForm, type LabForm } from "../lab";

const EMPTY: LabForm = {
  lab_h_corg: "",
  organic_carbon_pct: "",
  biochar_moisture_samples: "",
  dry_bulk_density: "",
};

export default function LabEntry() {
  const { uuid = "" } = useParams();
  const nav = useNavigate();
  const [form, setForm] = useState<LabForm>(EMPTY);
  const [cert, setCert] = useState<File | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

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
      <h1 style={{ fontSize: 20, margin: "12px 0" }}>
        Lab results · {uuid.slice(0, 8)}
      </h1>
      <form className="login" style={{ width: 420 }} onSubmit={submit}>
        <label className="micro">H:Corg ratio (0.1–1.5)</label>
        <input
          inputMode="decimal"
          value={form.lab_h_corg}
          onChange={(e) => set("lab_h_corg", e.target.value)}
        />
        <label className="micro">Organic carbon fraction (0–1]</label>
        <input
          inputMode="decimal"
          value={form.organic_carbon_pct}
          onChange={(e) => set("organic_carbon_pct", e.target.value)}
        />
        <label className="micro">Biochar moisture samples (≥3, comma sep.)</label>
        <input
          value={form.biochar_moisture_samples}
          onChange={(e) => set("biochar_moisture_samples", e.target.value)}
          placeholder="8, 9, 10"
        />
        <label className="micro">Dry bulk density (kg/m³)</label>
        <input
          inputMode="decimal"
          value={form.dry_bulk_density}
          onChange={(e) => set("dry_bulk_density", e.target.value)}
        />
        <label className="micro">Certificate PDF (optional)</label>
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setCert(e.target.files?.[0] ?? null)}
        />
        <button className="primary" type="submit" disabled={busy}>
          {busy ? "Submitting…" : "Submit results"}
        </button>
        {errors.map((er) => (
          <div className="err" key={er}>
            {er}
          </div>
        ))}
      </form>
    </div>
  );
}
