import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import jsQR from "jsqr";
import { parseBatchQr } from "../lab";

// Scan the composite-sample card QR (dmrv-batch:v1:<uuid>) with the native
// BarcodeDetector when present, else a jsQR fallback over camera frames — both
// fully local, no CDN. A manual UUID entry is offered when the camera is denied.
export default function LabScan() {
  const nav = useNavigate();
  const videoRef = useRef<HTMLVideoElement>(null);
  const [err, setErr] = useState<string | null>(null);
  const [manual, setManual] = useState("");

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

  return (
    <div className="wrap">
      <h1 style={{ fontSize: 20, marginBottom: 12 }}>Scan batch card</h1>
      <span className="micro">Point at the QR on the composite-sample card</span>
      <div className="card" style={{ marginTop: 12, overflow: "hidden" }}>
        <video
          ref={videoRef}
          style={{ width: "100%", borderRadius: 10, background: "#000" }}
          muted
          playsInline
        />
      </div>
      {err && <div className="err">{err}</div>}
      <div className="filters" style={{ marginTop: 16 }}>
        <input
          placeholder="or paste batch UUID"
          value={manual}
          onChange={(e) => setManual(e.target.value)}
        />
        <button
          className="primary"
          onClick={() => manual.trim() && nav(`/lab/${manual.trim()}`)}
        >
          Open
        </button>
      </div>
    </div>
  );
}
