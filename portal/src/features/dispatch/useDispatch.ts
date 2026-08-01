import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  listDispatch,
  getDispatchJourney,
  listFacilities,
  createFacility,
  AuthError,
  ApiError,
  type DispatchRow,
  type FacilityRow,
} from "../../api";
import type { JourneyData } from "../../components/JourneyPanel/JourneyPanel";

const PAGE_SIZE = 25;

export const DISPATCH_VIEWS = {
  all: { label: "All", status: "" },
  draft: { label: "Draft", status: "draft" },
  in_transit: { label: "In-Transit", status: "in_transit" },
  received: { label: "Received", status: "received" },
} as const;
export type DispatchViewKey = keyof typeof DISPATCH_VIEWS;

/**
 * Owns all Dispatch page data: the dispatch list + cursor pagination, the
 * admin facility-registration form, and the click-through journey detail.
 * The page composes this state into JSX; it fetches and transforms nothing
 * itself.
 */
export function useDispatch() {
  const nav = useNavigate();
  const [view, setView] = useState<DispatchViewKey>("all");
  const [rows, setRows] = useState<DispatchRow[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [currentBefore, setCurrentBefore] = useState<string | null>(null);
  const [prevStack, setPrevStack] = useState<(string | null)[]>([]);
  const [pageIndex, setPageIndex] = useState(1);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [facilities, setFacilities] = useState<FacilityRow[]>([]);
  const [facilityUuid, setFacilityUuid] = useState("");
  const [facilityName, setFacilityName] = useState("");
  const [facilityType, setFacilityType] = useState<"artisanal" | "industrial">(
    "artisanal",
  );
  const [facilityMsg, setFacilityMsg] = useState<{ text: string; ok: boolean } | null>(
    null,
  );
  const [facilitySubmitting, setFacilitySubmitting] = useState(false);
  const [showFacilityForm, setShowFacilityForm] = useState(false);

  const [selected, setSelected] = useState<DispatchRow | null>(null);
  const [journeyData, setJourneyData] = useState<JourneyData | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const detailRef = useRef<HTMLDivElement>(null);

  const fetchPage = useCallback(
    async (before: string | null) => {
      setLoading(true);
      setErr(null);
      try {
        const params: Record<string, string> = { limit: String(PAGE_SIZE) };
        const statusFilter = DISPATCH_VIEWS[view].status;
        if (statusFilter) params.status = statusFilter;
        if (before) params.before = before;
        const r = await listDispatch(params);
        setRows(r.dispatches);
        setNextCursor(r.next_cursor);
      } catch (e) {
        if (e instanceof AuthError) nav("/login");
        else setErr("Failed to load dispatches.");
      } finally {
        setLoading(false);
      }
    },
    [nav, view],
  );

  const fetchFacilities = useCallback(async () => {
    try {
      const r = await listFacilities({ limit: String(PAGE_SIZE) });
      setFacilities(r.facilities);
    } catch (_) {
      /* facility panel is supplementary; ignore background failure */
    }
  }, []);

  useEffect(() => {
    document.title = "Dispatch · TerraCipher";
    fetchFacilities();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    setPrevStack([]);
    setCurrentBefore(null);
    setPageIndex(1);
    fetchPage(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view]);

  useEffect(() => {
    if (!facilityMsg) return;
    const t = setTimeout(() => setFacilityMsg(null), 4000);
    return () => clearTimeout(t);
  }, [facilityMsg]);

  function goNext() {
    if (!nextCursor) return;
    setPrevStack((s) => [...s, currentBefore]);
    setCurrentBefore(nextCursor);
    setPageIndex((n) => n + 1);
    fetchPage(nextCursor);
  }
  function goPrev() {
    setPrevStack((s) => {
      const copy = [...s];
      const target = copy.pop() ?? null;
      setCurrentBefore(target);
      setPageIndex((n) => Math.max(1, n - 1));
      fetchPage(target);
      return copy;
    });
  }

  async function submitFacility(e: React.FormEvent) {
    e.preventDefault();
    if (!facilityUuid.trim() || !facilityName.trim()) {
      setFacilityMsg({ text: "Facility UUID and name are required", ok: false });
      return;
    }
    setFacilitySubmitting(true);
    setFacilityMsg(null);
    try {
      await createFacility({
        facility_uuid: facilityUuid.trim(),
        name: facilityName.trim(),
        facility_type: facilityType,
      });
      setFacilityMsg({ text: "✓ Facility registered", ok: true });
      setFacilityUuid("");
      setFacilityName("");
      await fetchFacilities();
    } catch (e) {
      if (e instanceof AuthError) {
        nav("/login");
      } else if (e instanceof ApiError && e.status === 409) {
        setFacilityMsg({ text: "A facility with that UUID already exists", ok: false });
      } else {
        setFacilityMsg({ text: "Registration failed — check values", ok: false });
      }
    } finally {
      setFacilitySubmitting(false);
    }
  }

  async function openDetail(uuid: string) {
    const row = rows.find((r) => r.dispatch_uuid === uuid) ?? null;
    setSelected(row);
    if (!row) {
      setJourneyData(null);
      return;
    }
    setDetailLoading(true);
    try {
      const jd = await getDispatchJourney(uuid);
      // Construct JourneyData adding the recipient
      const sites = row.sites ?? [];
      const primaryContactName = sites.find((s) => s.contact_name)?.contact_name ?? null;
      const primaryContactPhone = sites.find((s) => s.contact_phone)?.contact_phone ?? null;
      // Mask phone
      let maskedPhone = null;
      if (primaryContactPhone) {
        maskedPhone = primaryContactPhone.length > 4
          ? `••••${primaryContactPhone.slice(-4)}`
          : "••••" + primaryContactPhone;
      }

      const fullJd: JourneyData = {
        ...jd.journey,
        manifest: jd.manifest,
        recipient: {
          contact_name: primaryContactName,
          contact_phone_masked: maskedPhone,
        },
      };
      setJourneyData(fullJd);

      setTimeout(() => {
        detailRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 50);
    } catch (err) {
      console.error(err);
      setJourneyData(null);
    } finally {
      setDetailLoading(false);
    }
  }

  return {
    view,
    setView,
    rows,
    loading,
    err,
    fetchPage,
    currentBefore,
    pageIndex,
    nextCursor,
    prevStack,
    goNext,
    goPrev,

    facilities,
    facilityUuid,
    setFacilityUuid,
    facilityName,
    setFacilityName,
    facilityType,
    setFacilityType,
    facilityMsg,
    facilitySubmitting,
    showFacilityForm,
    setShowFacilityForm,
    submitFacility,

    selected,
    setSelected,
    journeyData,
    detailLoading,
    detailRef,
    openDetail,
  };
}
