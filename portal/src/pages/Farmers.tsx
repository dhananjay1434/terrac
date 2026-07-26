import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  listFarmers,
  getFarmer,
  AuthError,
  type FarmerRow,
  type FarmerDetail,
} from "../api";
import { fmtDate } from "../format";
import CardError from "../ui/CardError/CardError";
import DataTable, { type ColumnDef } from "../components/DataTable/DataTable";
import StatusDot from "../components/StatusDot/StatusDot";
import EmptyState from "../components/EmptyState/EmptyState";
import Skeleton from "../components/Skeleton/Skeleton";
import Button from "../ui/Button/Button";
import Card from "../ui/Card/Card";

const PAGE_SIZE = 25;

const KYC_VARIANT = { verified: "success", pending: "warning" } as const;
const CONSENT_VARIANT = { signed: "success", revoked: "error" } as const;


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
  const detailRef = useRef<HTMLElement>(null);

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

  useEffect(() => {
    if (selected) detailRef.current?.scrollIntoView?.({ behavior: "smooth", block: "nearest" });
  }, [selected]);

  async function openDetail(uuid: string) {
    setDetailLoading(true);
    try {
      setSelected(await getFarmer(uuid));
    } catch (e) {
      if (e instanceof AuthError) nav("/login");
      else setErr("Couldn't load farmer detail.");
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
    {
      key: "kyc",
      header: "KYC",
      render: (f) =>
        f.kyc_status ? (
          <StatusDot variant={KYC_VARIANT[f.kyc_status as keyof typeof KYC_VARIANT] ?? "inert"} label={f.kyc_status} />
        ) : (
          "—"
        ),
    },
    {
      key: "consent",
      header: "Consent",
      render: (f) =>
        f.consent_status ? (
          <StatusDot variant={CONSENT_VARIANT[f.consent_status as keyof typeof CONSENT_VARIANT] ?? "inert"} label={f.consent_status} />
        ) : (
          "—"
        ),
    },
    { key: "created", header: "Registered", render: (f) => fmtDate(f.created_at) },
  ];

  return (
    <div className="wrap">
      <h1 className="page-title">Farmers</h1>

      <form className="filters" style={{ marginBottom: "var(--space-4)" }} onSubmit={runSearch}>
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)" }}>
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
        <Button type="submit" style={{ alignSelf: "flex-end" }}>
          Search
        </Button>
      </form>

      {err && (
        <CardError message={err} onRetry={() => fetchPage(page, search)} />
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
        <Button
          variant="neutral"
          size="sm"
          type="button"
          onClick={() => goTo(page - 1)}
          disabled={loading || page <= 1}
        >
          ‹ Previous
        </Button>
        <span className="micro pager-status" aria-live="polite">
          Page {page} of {lastPage} · {total} total
        </span>
        <Button
          variant="neutral"
          size="sm"
          type="button"
          onClick={() => goTo(page + 1)}
          disabled={loading || page >= lastPage}
        >
          Next ›
        </Button>
      </nav>

      {(detailLoading || selected) && (
        <Card as="section" ref={detailRef} style={{ marginTop: "var(--space-4)" }} aria-label="Farmer detail">
          {detailLoading && <Skeleton variant="card" />}
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

              <dl className="kv" style={{ marginTop: "var(--space-3)" }}>
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

                {/* Deferred R1 — entity-scoped media presence. Text-only status,
                    not a gallery: media rows aren't fetched by this page yet
                    (would need a new farmer-media list endpoint call), so this
                    shows only what's already on the farmer/consent/document
                    records themselves — honest "captured"/"not captured", never
                    a fabricated thumbnail for media that hasn't arrived. */}
                <div className="kv-divider" aria-hidden="true" />

                <div>
                  <dt className="micro">Signature</dt>
                  <dd className={selected.signature_media_id ? "" : "text-tertiary"}>
                    {selected.signature_media_id ? "Captured" : "Not captured"}
                  </dd>
                </div>

                <div>
                  <dt className="micro">Identity documents (last-4 only)</dt>
                  <dd>
                    {selected.documents.length === 0 ? (
                      <span className="text-tertiary">None</span>
                    ) : (
                      <ul>
                        {selected.documents.map((d) => (
                          <li key={d.id}>
                            {d.doc_type}: <span className="mono">••••{d.last4}</span>
                            {d.media_id ? " · photo captured" : " · photo not captured"}
                          </li>
                        ))}
                      </ul>
                    )}
                  </dd>
                </div>

                <div>
                  <dt className="micro">Payment methods (masked)</dt>
                  <dd>
                    {selected.payments.length === 0 ? (
                      <span className="text-tertiary">None</span>
                    ) : (
                      <ul>
                        {selected.payments.map((p) => (
                          <li key={p.id}>
                            {p.rail}:{" "}
                            <span className="mono">{p.masked_account ?? p.masked_upi_id ?? p.masked_mfs_id ?? "—"}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </dd>
                </div>

                <div>
                  <dt className="micro">FPIC consent</dt>
                  <dd>
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
                  </dd>
                </div>
              </dl>
            </>
          )}
        </Card>
      )}
    </div>
  );
}
