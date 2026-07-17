import { useState, useEffect } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { submitLabResults, uploadLabCertificate, AuthError } from "../api";
import { validateLabForm, type LabForm } from "../lab";
import { GROUP_LABEL } from "../compliance";

const EMPTY: LabForm = {
  lab_h_corg: "",
  organic_carbon_pct: "",
  biochar_moisture_samples: "",
  dry_bulk_density: "",
};

// UI feedback only — the actual upload still goes through uploadLabCertificate.
function readBytes(f: File): Promise<ArrayBuffer> {
  if (typeof f.arrayBuffer === "function") return f.arrayBuffer();
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(r.result as ArrayBuffer);
    r.onerror = () => reject(r.error);
    r.readAsArrayBuffer(f);
  });
}

async function hashFile(f: File): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", await readBytes(f));
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export default function LabEntry() {
  const { uuid = "" } = useParams();
  const nav = useNavigate();
  const [form, setForm] = useState<LabForm>(EMPTY);
  const [cert, setCert] = useState<File | null>(null);
  const [certHash, setCertHash] = useState<string | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    document.title = "Lab results · TerraCipher";
  }, []);

  function set(k: keyof LabForm, v: string) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function onCertChange(file: File | null) {
    setCert(file);
    setCertHash(null);
    if (file) {
      try {
        setCertHash(await hashFile(file));
      } catch {
        setCertHash(null);
      }
    }
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
      <div className="registry-grid">
        <form className="login" style={{ width: "100%", maxWidth: 420 }} onSubmit={submit}>
          <label className="micro" htmlFor="lab_h_corg">H:Corg ratio (0.1–1.5)</label>
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
            onChange={(e) => onCertChange(e.target.files?.[0] ?? null)}
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
            Rules that will be checked when you submit
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
            <div style={{ marginTop: 14 }}>
              <span className="micro">Certificate SHA-256 (computed locally)</span>
              <div
                className="mono"
                data-testid="cert-hash"
                style={{ wordBreak: "break-all", marginTop: 4 }}
              >
                {certHash ?? "computing…"}
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
