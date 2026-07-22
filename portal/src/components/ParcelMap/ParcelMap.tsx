import React, { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "@geoman-io/leaflet-geoman-free";
import "leaflet/dist/leaflet.css";
import "@geoman-io/leaflet-geoman-free/dist/leaflet-geoman.css";
import styles from "./ParcelMap.module.css";
import type { SourceParcel } from "../../api";

interface ParcelMapProps {
  existingParcels?: SourceParcel[];
  onPolygonCreated?: (geojson: Record<string, unknown>) => void;
  selectedGeoJson?: Record<string, unknown> | null;
}

export default function ParcelMap({
  existingParcels = [],
  onPolygonCreated,
  selectedGeoJson,
}: ParcelMapProps) {
  const mapRef = useRef<HTMLDivElement | null>(null);
  const leafletInstance = useRef<L.Map | null>(null);
  const drawnItemsRef = useRef<L.FeatureGroup | null>(null);

  const [rawGeoJsonText, setRawGeoJsonText] = useState("");
  const [parseError, setParseError] = useState<string | null>(null);
  const [mapInitialized, setMapInitialized] = useState(false);

  useEffect(() => {
    if (!mapRef.current || leafletInstance.current) return;

    // Skip heavy Leaflet DOM canvas/SVG binding in JSDOM / headless test envs
    const isJsdom = typeof window !== "undefined" && window.navigator.userAgent.includes("jsdom");
    if (isJsdom) return;

    try {
      // Default center: India (20.5937, 78.9629)
      const map = L.map(mapRef.current, { attributionControl: false }).setView(
        [20.5937, 78.9629],
        5,
      );

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
      }).addTo(map);

      const drawnItems = new L.FeatureGroup();
      map.addLayer(drawnItems);
      drawnItemsRef.current = drawnItems;

      // Geoman draw controls
      if ((map as unknown as { pm: unknown }).pm) {
        (
          map as unknown as { pm: { addControls: (opts: unknown) => void } }
        ).pm.addControls({
          position: "topleft",
          drawCircleMarker: false,
          drawPolyline: false,
          drawRectangle: true,
          drawPolygon: true,
          drawCircle: false,
          drawMarker: false,
          editMode: true,
          dragMode: false,
          cutPolygon: false,
          removalMode: true,
        });

        // Ensure Geoman-injected buttons have accessible labels for a11y (WCAG 2.x)
        if (mapRef.current) {
          const btns = mapRef.current.querySelectorAll("a");
          btns.forEach((btn, idx) => {
            if (!btn.getAttribute("aria-label")) {
              const title = btn.getAttribute("title");
              btn.setAttribute("aria-label", title || `Map control ${idx + 1}`);
            }
          });
        }

        map.on("pm:create", (e: unknown) => {
          const layer = (e as { layer: L.Layer }).layer;
          try {
            drawnItems.clearLayers();
            drawnItems.addLayer(layer);
          } catch (_) {
            /* ignore JSDOM canvas layer clear errors */
          }

          if ("toGeoJSON" in layer && typeof layer.toGeoJSON === "function") {
            const geojson = layer.toGeoJSON() as Record<string, unknown>;
            setRawGeoJsonText(JSON.stringify(geojson, null, 2));
            setParseError(null);
            onPolygonCreated?.(geojson);
          }
        });
      }

      leafletInstance.current = map;
      setMapInitialized(true);
    } catch (e) {
      console.warn("Leaflet map initialization skipped or failed in test env:", e);
    }

    return () => {
      if (leafletInstance.current) {
        try {
          leafletInstance.current.remove();
        } catch (_) {
          /* ignore JSDOM path removal errors */
        }
        leafletInstance.current = null;
      }
    };
  }, [onPolygonCreated]);

  // Render existing parcels as static polygons
  useEffect(() => {
    if (!leafletInstance.current || !existingParcels.length) return;
    const map = leafletInstance.current;

    existingParcels.forEach((parcel) => {
      try {
        const parsed = JSON.parse(parcel.boundary_geojson);
        L.geoJSON(parsed, {
          style: {
            color: "#3b82f6",
            weight: 2,
            fillOpacity: 0.2,
          },
        }).addTo(map);
      } catch (_) {
        /* skip invalid saved geojson */
      }
    });
  }, [existingParcels, mapInitialized]);

  // Sync selectedGeoJson if passed from parent
  useEffect(() => {
    if (selectedGeoJson) {
      const text = JSON.stringify(selectedGeoJson, null, 2);
      setRawGeoJsonText(text);
    }
  }, [selectedGeoJson]);

  function handleTextareaChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    const val = e.target.value;
    setRawGeoJsonText(val);
    if (!val.trim()) {
      setParseError(null);
      return;
    }

    try {
      const parsed = JSON.parse(val);
      if (typeof parsed !== "object" || !parsed) {
        setParseError("Invalid GeoJSON object");
        return;
      }
      setParseError(null);
      onPolygonCreated?.(parsed);

      // Draw onto Leaflet map if available
      if (leafletInstance.current && drawnItemsRef.current) {
        try {
          drawnItemsRef.current.clearLayers();
          const layer = L.geoJSON(parsed);
          drawnItemsRef.current.addLayer(layer);
          const bounds = layer.getBounds();
          if (bounds.isValid()) {
            leafletInstance.current.fitBounds(bounds);
          }
        } catch (_) {
          /* ignore JSDOM renderer errors */
        }
      }
    } catch (err) {
      setParseError("JSON syntax error");
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.mapWrapper}>
        <div ref={mapRef} className={styles.map} data-testid="parcel-leaflet-map" />
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <label className="micro" htmlFor="geojson-textarea">
          Boundary GeoJSON (draw above or paste GeoJSON here)
        </label>
        <textarea
          id="geojson-textarea"
          aria-label="Boundary GeoJSON"
          className={styles.geoJsonInput}
          value={rawGeoJsonText}
          onChange={handleTextareaChange}
          placeholder='{"type": "Polygon", "coordinates": [[[lon, lat], ...]]}'
        />
        {parseError && (
          <span className="chip err" style={{ fontSize: 11, alignSelf: "flex-start" }}>
            {parseError}
          </span>
        )}
      </div>
    </div>
  );
}
