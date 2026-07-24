import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import jsQR from "jsqr";
import { parseBatchQr } from "../lab";
import Button from "../ui/Button/Button";
import Card from "../ui/Card/Card";

const RECENT_KEY = "tc_recent_scans";
const BARE_UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// Manual entry must accept exactly what the camera path accepts (the
// dmrv-batch:v1:<uuid> QR payload) plus a bare pasted UUID — never a raw
// unvalidated string. Returns null when the input isn't a real batch code,
// so the caller can reject it instead of navigating to a broken page.
function resolveManual(raw: string): string | null {
  const s = raw.trim();
  if (!s) return null;
  const fromQr = parseBatchQr(s);
  if (fromQr) return fromQr;
  return BARE_UUID_RE.test(s) ? s.toLowerCase() : null;
}

function readRecent(): string[] {
  try {
    const v = JSON.parse(localStorage.getItem(RECENT_KEY) ?? "[]");
    return Array.isArray(v) ? v.filter((x) => typeof x === "string") : [];
  } catch {
    return [];
  }
}

function pushRecent(uuid: string) {
  try {
    const next = [uuid, ...readRecent().filter((u) => u !== uuid)].slice(0, 5);
    localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  } catch {
    /* storage unavailable — non-fatal */
  }
}

// Scan the composite-sample card QR (dmrv-batch:v1:<uuid>) with the native
// BarcodeDetector when present, else a jsQR fallback over camera frames — both
// fully local, no CDN. A manual UUID entry is offered when the camera is denied.
export default function LabScan() {
  const nav = useNavigate();
  const videoRef = useRef<HTMLVideoElement>(null);
  const [err, setErr] = useState<string | null>(null);
  const [manual, setManual] = useState("");
  const [manualErr, setManualErr] = useState<string | null>(null);
  const [recent] = useState<string[]>(() => readRecent());
  // Presentational only — the camera/QR pipeline below never reads this; it
  // just lets the frame show "starting…" instead of a blank black box while
  // getUserMedia resolves.
  const [cameraReady, setCameraReady] = useState(false);

  useEffect(() => {
    let stream: MediaStream | null = null;
    let raf = 0;
    let stopped = false;
    const canvas = document.createElement("canvas");

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const BD = (window as any).BarcodeDetector;
    const detector = BD ? new BD({ formats: ["qr_code"] }) : null;

    function handle(text: string) {
      const uuid = parseBatchQr(text);
      if (uuid) {
        stopped = true;
        pushRecent(uuid);
        nav(`/lab/${uuid}`);
      }
    }

    async function tick() {
      if (stopped) return;
      const video = videoRef.current;
      if (video && video.readyState === video.HAVE_ENOUGH_DATA) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext("2d");
        if (ctx) {
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
          if (detector) {
            try {
              const codes = await detector.detect(canvas);
              if (codes[0]?.rawValue) handle(codes[0].rawValue);
            } catch {
              /* ignore a transient detect error */
            }
          } else {
            const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
            const code = jsQR(img.data, img.width, img.height);
            if (code?.data) handle(code.data);
          }
        }
      }
      raf = requestAnimationFrame(tick);
    }

    navigator.mediaDevices
      ?.getUserMedia({ video: { facingMode: "environment" } })
      .then((s) => {
        stream = s;
        if (videoRef.current) {
          videoRef.current.srcObject = s;
          void videoRef.current.play();
          raf = requestAnimationFrame(tick);
        }
      })
      .catch(() => setErr("Camera unavailable — enter the batch ID below."));

    return () => {
      stopped = true;
      cancelAnimationFrame(raf);
      stream?.getTracks().forEach((t) => t.stop());
    };
  }, [nav]);

  useEffect(() => {
    document.title = "Lab scan · TerraCipher";
  }, []);

  return (
    <div className="wrap">
      <h1 className="page-title">Scan batch card</h1>
      <span className="micro">Point at the QR on the composite-sample card</span>
      <Card
        style={{
          marginTop: 12,
          overflow: "hidden",
          position: "relative",
          maxWidth: 480,
          marginLeft: "auto",
          marginRight: "auto",
        }}
      >
        <video
          ref={videoRef}
          onPlaying={() => setCameraReady(true)}
          style={{
            width: "100%",
            aspectRatio: "1 / 1",
            objectFit: "cover",
            borderRadius: "var(--r-lg)",
            background: "var(--basalt-950)",
            display: "block",
          }}
          muted
          playsInline
        />
        {!cameraReady && !err && (
          <div
            aria-hidden
            className="micro"
            style={{
              position: "absolute",
              inset: 0,
              display: "grid",
              placeItems: "center",
              color: "var(--basalt-400)",
            }}
          >
            Starting camera…
          </div>
        )}
        {/* Corner-bracket scan frame — same viewfinder, drawn as four L-shaped
            corners instead of one solid square, so it reads as a scanner
            reticle rather than a slab outline sitting on top of the feed. */}
        <div
          aria-hidden
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            width: "56%",
            aspectRatio: "1 / 1",
            pointerEvents: "none",
          }}
        >
          {(["top-left", "top-right", "bottom-left", "bottom-right"] as const).map(
            (corner) => {
              const vertical = corner.startsWith("top") ? "top" : "bottom";
              const horizontal = corner.endsWith("left") ? "left" : "right";
              return (
                <div
                  key={corner}
                  style={{
                    position: "absolute",
                    [vertical]: 0,
                    [horizontal]: 0,
                    width: 28,
                    height: 28,
                    borderTop: vertical === "top" ? "3px solid rgba(255,255,255,0.9)" : undefined,
                    borderBottom: vertical === "bottom" ? "3px solid rgba(255,255,255,0.9)" : undefined,
                    borderLeft: horizontal === "left" ? "3px solid rgba(255,255,255,0.9)" : undefined,
                    borderRight: horizontal === "right" ? "3px solid rgba(255,255,255,0.9)" : undefined,
                    borderRadius: "var(--r-sm)",
                  }}
                />
              );
            },
          )}
        </div>
      </Card>
      {err && <div className="err">{err}</div>}
      <div className="filters" style={{ marginTop: 16 }}>
        <input
          placeholder="or paste batch UUID"
          aria-label="Batch UUID"
          value={manual}
          onChange={(e) => {
            setManual(e.target.value);
            setManualErr(null);
          }}
        />
        <Button
          onClick={() => {
            const id = resolveManual(manual);
            if (!id) {
              setManualErr("Not a valid batch code.");
              return;
            }
            pushRecent(id);
            nav(`/lab/${id}`);
          }}
        >
          Open
        </Button>
      </div>
      {manualErr && <div className="err">{manualErr}</div>}
      {recent.length > 0 && (
        <Card as="section" style={{ marginTop: 16 }}>
          <span className="micro">Recently scanned</span>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 10 }}>
            {recent.map((u) => (
              <Button
                key={u}
                variant="neutral"
                size="sm"
                className="mono"
                aria-label={`Open batch ${u}`}
                onClick={() => nav(`/lab/${u}`)}
              >
                {u.slice(0, 8)}…
              </Button>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
