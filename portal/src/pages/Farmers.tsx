import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  listFarmers,
  getFarmer,
  AuthError,
  type FarmerRow,
  type FarmerDetail,
} from "../api";
import DataTable, { type ColumnDef } from "../components/DataTable/DataTable";
import EmptyState from "../components/EmptyState/EmptyState";

const PAGE_SIZE = 25;

function fmtDate(iso: string | null) {
  return iso ? iso.slice(0, 10) : "—";
}

export default function Farmers() {
  const nav = useNavigate();
  const [rows, setRows] = useState<FarmerRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [selected, setSelected] = useState<FarmerDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const fetchPage = useCallback(
    async (p: number, q: string) => {
      setLoading(true);
      setErr(null);
      try {
        const res = await listFarmers({ page: p, size: PAGE_SIZE, search: q || undefined });
        setRows(res.items);
        setTotal(res.total);
      } catch (e) {
        if (e instanceof AuthError) nav("/login");
        else setErr("Failed to load farmers.");
      } finally {
        setLoading(false);
      }
    },
    [nav],
  );

  useEffect(() => {
    document.title = "Farmers · TerraCipher";
    fetchPage(1, "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function openDetail(uuid: string) {
    setDetailLoading(true);
    try {
      setSelected(await getFarmer(uuid));
    } catch (e) {
      if (e instanceof AuthError) nav("/login");
    } finally {
      setDetailLoading(false);
    }
  }

  function runSearch(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setSelected(null);
    fetchPage(1, search);
  }

  const lastPage = Math.max(1, Math.ceil(total / PAGE_SIZE));

  function goTo(p: number) {
    const next = Math.min(lastPage, Math.max(1, p));
    setPage(next);
    setSelected(null);
    fetchPage(next, search);
  }

  const columns: ColumnDef<FarmerRow>[] = [
    {
      key: "name",
      header: "Name",
      render: (f) => `${f.first_name}${f.last_name ? ` ${f.last_name}` : ""}`,
    },
    { key: "mobile", header: "Mobile", mono: true, render: (f) => f.mobile_number },
    { key: "village", header: "Village", render: (f) => f.village ?? "—" },
    { key: "kyc", header: "KYC", render: (f) => f.kyc_status ?? "—" },
    { key: "consent", header: "Consent", render: (f) => f.consent_status ?? "—" },
    { key: "created", header: "Registered", render: (f) => fmtDate(f.created_at) },
  ];

  return (
    <div className="wrap">
      <h1 className="page-title">Farmers</h1>

      <form className="filters" style={{ marginBottom: 14 }} onSubmit={runSearch}>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <label className="micro" htmlFor="farmer-search">
            Search name or mobile
          </label>
          <input
            id="farmer-search"
            aria-label="Search farmers by name or mobile"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <button className="primary" type="submit" style={{ alignSelf: "flex-end" }}>
          Search
        </button>
      </form>

      {err && (
        <div
          className="card"
          style={{
            borderColor: "var(--status-error-fg)",
            marginBottom: 16,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span className="err" style={{ margin: 0 }}>
            {err}
          </span>
          <button className="neutral" type="button" onClick={() => fetchPage(page, search)}>
            Retry
          </button>
        </div>
      )}

      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(f) => f.farmer_uuid}
        onRowClick={(f) => openDetail(f.farmer_uuid)}
        loading={loading}
        empty={
          <EmptyState
            title="No farmers found"
            description="Adjust the search, or wait for field devices to sync farmer registrations."
          />
        }
      />

      <nav className="pager" aria-label="Farmers pagination">
        <button
          className="neutral"
          type="button"
          onClick={() => goTo(page - 1)}
          disabled={loading || page <= 1}
        >
          ‹ Previous
        </button>
        <span className="micro pager-status" aria-live="polite">
          Page {page} of {lastPage} · {total} total
        </span>
        <button
          className="neutral"
          type="button"
          onClick={() => goTo(page + 1)}
          disabled={loading || page >= lastPage}
        >
          Next ›
        </button>
      </nav>

      {(detailLoading || selected) && (
        <section className="card" style={{ marginTop: 18 }} aria-label="Farmer detail">
          {detailLoading && <span className="micro">Loading…</span>}
          {selected && (
            <>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <span className="micro">
                  {selected.first_name}
                  {selected.last_name ? ` ${selected.last_name}` : ""} ·{" "}
                  {selected.mobile_number}
                </span>
                <button
                  className="linkbtn"
                  type="button"
                  onClick={() => setSelected(null)}
                >
                  Close
                </button>
              </div>

              <dl className="kv" style={{ marginTop: 10 }}>
                <div>
                  <dt className="micro">Village</dt>
                  <dd>{selected.village ?? "—"}</dd>
                </div>
                <div>
                  <dt className="micro">Guardian</dt>
                  <dd>{selected.guardian_name ?? "—"}</dd>
                </div>
                <div>
                  <dt className="micro">KYC</dt>
                  <dd>{selected.kyc_status ?? "—"}</dd>
                </div>
                <div>
                  <dt className="micro">Consent</dt>
                  <dd>{selected.consent_status ?? "—"}</dd>
                </div>
              </dl>

              {/* Deferred R1 — entity-scoped media presence. Text-only status,
                  not a gallery: media rows aren't fetched by this page yet
                  (would need a new farmer-media list endpoint call), so this
                  shows only what's already on the farmer/consent/document
                  records themselves — honest "captured"/"not captured", never
                  a fabricated thumbnail for media that hasn't arrived. */}
              <span className="micro" style={{ display: "block", marginTop: 12 }}>
                Signature
              </span>
              <span className={selected.signature_media_id ? "" : "text-tertiary"}>
                {selected.signature_media_id ? "Captured" : "Not captured"}
              </span>

              <span className="micro" style={{ display: "block", marginTop: 12 }}>
                Identity documents (last-4 only)
              </span>
              {selected.documents.length === 0 ? (
                <span className="text-tertiary">None</span>
              ) : (
                <ul>
                  {selected.documents.map((d) => (
                    <li key={d.id}>
                      {d.doc_type}: ••••{d.last4}
                      {d.media_id ? " · photo captured" : " · photo not captured"}
                    </li>
                  ))}
                </ul>
              )}

              <span className="micro" style={{ display: "block", marginTop: 12 }}>
                Payment methods (masked)
              </span>
              {selected.payments.length === 0 ? (
                <span className="text-tertiary">None</span>
              ) : (
                <ul>
                  {selected.payments.map((p) => (
                    <li key={p.id}>
                      {p.rail}:{" "}
                      {p.masked_account ?? p.masked_upi_id ?? p.masked_mfs_id ?? "—"}
                    </li>
                  ))}
                </ul>
              )}

              <span className="micro" style={{ display: "block", marginTop: 12 }}>
                FPIC consent
              </span>
              {selected.consents.length === 0 ? (
                <span className="text-tertiary">None recorded</span>
              ) : (
                <ul>
                  {selected.consents.map((c) => (
                    <li key={c.id}>
                      signed {fmtDate(c.signed_at)} · exclusivity{" "}
                      {c.exclusivity_ack ? "acknowledged" : "not acknowledged"} ·{" "}
                      consent PDF {c.signed_pdf_media_id ? "captured" : "not captured"} ·{" "}
                      holding photo{" "}
                      {c.holding_photo_media_id ? "captured" : "not captured"}
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </section>
      )}
    </div>
  );
}
