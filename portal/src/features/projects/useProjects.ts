import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  createProject,
  listProjects,
  createParcel,
  listParcels,
  listRegistryConfigs,
  AuthError,
  ApiError,
  type ProjectRow,
  type SourceParcel,
} from "../../api";

const PAGE_SIZE = 25;

/**
 * Owns all Projects page data: the project list + cursor pagination, the
 * admin project-registration form (incl. the feedstock dropdown sourced from
 * registry configs), and the source-parcel list + registration form. The
 * page composes this state into JSX; it fetches and transforms nothing
 * itself.
 */
export function useProjects() {
  const nav = useNavigate();
  const [rows, setRows] = useState<ProjectRow[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [currentBefore, setCurrentBefore] = useState<string | null>(null);
  const [prevStack, setPrevStack] = useState<(string | null)[]>([]);
  const [pageIndex, setPageIndex] = useState(1);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // Project form state
  const [projectId, setProjectId] = useState("");
  const [name, setName] = useState("");
  const [formMsg, setFormMsg] = useState<{ text: string; ok: boolean } | null>(
    null,
  );
  const [submitting, setSubmitting] = useState(false);

  // FM-3: feedstock dropdown options (union of every registry config's
  // corg_table keys, minus "Default") + selection + client-count input.
  const [feedstockOptions, setFeedstockOptions] = useState<string[]>([]);
  const [selectedFeedstock, setSelectedFeedstock] = useState("");
  const [clientTarget, setClientTarget] = useState("");

  // Parcel form & list state (Part 1.5)
  const [parcels, setParcels] = useState<SourceParcel[]>([]);
  const [parcelsLoading, setParcelsLoading] = useState(false);
  const [parcelProjectId, setParcelProjectId] = useState("");
  const [parcelName, setParcelName] = useState("");
  const [declaredAcres, setDeclaredAcres] = useState("");
  const [drawnGeoJson, setDrawnGeoJson] = useState<Record<string, unknown> | null>(null);
  const [parcelMsg, setParcelMsg] = useState<{ text: string; ok: boolean } | null>(null);
  const [parcelSubmitting, setParcelSubmitting] = useState(false);

  const fetchPage = useCallback(
    async (before: string | null) => {
      setLoading(true);
      setErr(null);
      try {
        const params: Record<string, string> = { limit: String(PAGE_SIZE) };
        if (before) params.before = before;
        const r = await listProjects(params);
        setRows(r.projects);
        setNextCursor(r.next_cursor);
        if (r.projects.length > 0 && !parcelProjectId) {
          setParcelProjectId(r.projects[0].project_id);
        }
      } catch (e) {
        if (e instanceof AuthError) nav("/login");
        else setErr("Failed to load projects.");
      } finally {
        setLoading(false);
      }
    },
    [nav, parcelProjectId],
  );

  const fetchParcels = useCallback(async () => {
    setParcelsLoading(true);
    try {
      const res = await listParcels(parcelProjectId || undefined);
      setParcels(res.parcels);
    } catch (_) {
      /* ignore parcel load failure in background */
    } finally {
      setParcelsLoading(false);
    }
  }, [parcelProjectId]);

  useEffect(() => {
    document.title = "Projects · TerraCipher";
    fetchPage(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    // FM-3: build the feedstock dropdown's options from real registry-config
    // data — never a hardcoded species list. The backend (create_project)
    // remains the validation authority; this union is just the picker's
    // candidate set.
    listRegistryConfigs()
      .then((r) => {
        const union = new Set<string>();
        for (const cfg of r.registry_configs) {
          for (const species of Object.keys(cfg.params?.corg_table ?? {})) {
            if (species.toLowerCase() !== "default") union.add(species);
          }
        }
        setFeedstockOptions(Array.from(union).sort());
      })
      .catch(() => {
        /* leave feedstockOptions empty — the picker disables itself below */
      });
  }, []);

  useEffect(() => {
    fetchParcels();
  }, [fetchParcels, parcelProjectId]);

  useEffect(() => {
    if (!formMsg) return;
    const t = setTimeout(() => setFormMsg(null), 4000);
    return () => clearTimeout(t);
  }, [formMsg]);

  useEffect(() => {
    if (!parcelMsg) return;
    const t = setTimeout(() => setParcelMsg(null), 5000);
    return () => clearTimeout(t);
  }, [parcelMsg]);

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

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!projectId.trim() || !name.trim()) {
      setFormMsg({ text: "Project ID and name are required", ok: false });
      return;
    }
    setSubmitting(true);
    setFormMsg(null);
    try {
      const target = clientTarget.trim() ? parseInt(clientTarget.trim(), 10) : undefined;
      await createProject({
        project_id: projectId.trim(),
        name: name.trim(),
        allowed_feedstocks: selectedFeedstock ? [selectedFeedstock] : [],
        client_target: target,
      });
      setFormMsg({ text: "✓ Project created", ok: true });
      setProjectId("");
      setName("");
      setSelectedFeedstock("");
      setClientTarget("");
      setPrevStack([]);
      setCurrentBefore(null);
      setPageIndex(1);
      await fetchPage(null);
    } catch (e) {
      if (e instanceof AuthError) {
        nav("/login");
      } else if (e instanceof ApiError && e.status === 409) {
        setFormMsg({ text: "A project with that ID already exists", ok: false });
      } else if (e instanceof ApiError && e.status === 422) {
        let msg = "That feedstock is not on the registry's positive list.";
        try {
          const detail = JSON.parse(e.message);
          if (detail?.error === "feedstock_not_in_positive_list") {
            msg = `Not on the positive list: ${detail.unknown?.join(", ")}. Allowed: ${detail.allowed?.join(", ")}.`;
          }
        } catch (_) {}
        setFormMsg({ text: msg, ok: false });
      } else {
        setFormMsg({ text: "Create failed — check values", ok: false });
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function submitParcel(e: React.FormEvent) {
    e.preventDefault();
    if (!parcelProjectId.trim() || !parcelName.trim() || !drawnGeoJson) {
      setParcelMsg({ text: "Project ID, Parcel Name, and Boundary GeoJSON are required", ok: false });
      return;
    }
    setParcelSubmitting(true);
    setParcelMsg(null);
    try {
      const acres = declaredAcres.trim() ? parseFloat(declaredAcres.trim()) : undefined;
      await createParcel({
        project_id: parcelProjectId.trim(),
        name: parcelName.trim(),
        boundary_geojson: drawnGeoJson,
        declared_area_acres: acres,
      });
      setParcelMsg({ text: "✓ Source parcel boundary registered & approved", ok: true });
      setParcelName("");
      setDeclaredAcres("");
      setDrawnGeoJson(null);
      await fetchParcels();
    } catch (e) {
      if (e instanceof AuthError) {
        nav("/login");
      } else if (e instanceof ApiError) {
        let msg = e.message;
        try {
          const detailObj = JSON.parse(e.message);
          if (detailObj.message) msg = detailObj.message;
        } catch (_) {}
        setParcelMsg({ text: `Parcel registration failed: ${msg}`, ok: false });
      } else {
        setParcelMsg({ text: "Parcel registration failed", ok: false });
      }
    } finally {
      setParcelSubmitting(false);
    }
  }

  return {
    rows,
    nextCursor,
    currentBefore,
    prevStack,
    pageIndex,
    loading,
    err,
    fetchPage,
    goNext,
    goPrev,

    projectId,
    setProjectId,
    name,
    setName,
    formMsg,
    submitting,
    feedstockOptions,
    selectedFeedstock,
    setSelectedFeedstock,
    clientTarget,
    setClientTarget,
    submit,

    parcels,
    parcelsLoading,
    parcelProjectId,
    setParcelProjectId,
    parcelName,
    setParcelName,
    declaredAcres,
    setDeclaredAcres,
    drawnGeoJson,
    setDrawnGeoJson,
    parcelMsg,
    parcelSubmitting,
    submitParcel,
  };
}
