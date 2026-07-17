import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, EyeOff } from "lucide-react";
import { login, ApiError } from "../api";
import { setSession } from "../auth";

export default function Login() {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    document.title = "Sign in · TerraCipher";
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const r = await login(email, password);
      setSession(r.token, r.role);
      nav("/batches");
    } catch (e) {
      setErr(
        e instanceof ApiError && e.status === 401
          ? "Invalid email or password."
          : "Could not reach the server.",
      );
    } finally {
      setBusy(false);
    }
  }

  // Inline field-invalid affordance: red left border once a submit failed.
  const invalidStyle = err
    ? { borderLeft: "3px solid var(--status-error-fg)" }
    : undefined;

  return (
    <div className="login-wrap">
      <div
        className="registry-grid"
        style={{ maxWidth: 800, width: "100%", alignItems: "stretch" }}
      >
        <form className="login card" style={{ width: "100%" }} onSubmit={submit}>
          <div className="mark">TC</div>
          <h1>Sign in to TerraCipher</h1>
          <div style={{ display: "flex", flexDirection: "column", gap: 4, width: "100%", textAlign: "left" }}>
            <label className="micro" htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              style={invalidStyle}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="username"
            />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4, width: "100%", textAlign: "left" }}>
            <label className="micro" htmlFor="password">Password</label>
            <div style={{ position: "relative", display: "flex" }}>
              <input
                id="password"
                type={showPw ? "text" : "password"}
                value={password}
                style={{ ...invalidStyle, flex: 1, paddingRight: 40 }}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
              <button
                type="button"
                className="linkbtn"
                aria-label={showPw ? "Hide password" : "Show password"}
                onClick={() => setShowPw((s) => !s)}
                style={{
                  position: "absolute",
                  right: 4,
                  top: "50%",
                  transform: "translateY(-50%)",
                }}
              >
                {showPw ? <EyeOff size={14} aria-hidden /> : <Eye size={14} aria-hidden />}
              </button>
            </div>
          </div>
          <button className="primary" type="submit" disabled={busy} style={{ marginTop: 8 }}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
          {err && <div className="err">{err}</div>}
        </form>
        <aside
          className="card"
          style={{
            background: "var(--basalt-950)",
            color: "var(--basalt-50)",
            border: 0,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            gap: 12,
            padding: 32,
          }}
        >
          <div className="mark">TC</div>
          <div style={{ fontSize: 22, fontWeight: 650, letterSpacing: "-0.02em" }}>
            TerraCipher
          </div>
          <div style={{ fontSize: 13, lineHeight: 1.6, color: "var(--basalt-300)" }}>
            Verifier portal for biochar carbon credits, following the CSI
            Global Artisan C-Sink and Rainbow Biochar Standard methodologies
            (C0–C10).
          </div>
        </aside>
      </div>
    </div>
  );
}
