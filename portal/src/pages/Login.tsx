import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, EyeOff } from "lucide-react";
import { login, ApiError } from "../api";
import { setSession } from "../auth";
import Card from "../ui/Card/Card";
import Button from "../ui/Button/Button";
import Logo from "../ui/Logo/Logo";
import styles from "./Login.module.css";

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
      nav("/dashboard");
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
        <Card as="form" className="login" style={{ width: "100%" }} onSubmit={submit}>
          <h1>Sign in to TerraCipher</h1>
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)", width: "100%", textAlign: "left" }}>
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
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)", width: "100%", textAlign: "left" }}>
            <label className="micro" htmlFor="password">Password</label>
            <div style={{ position: "relative", display: "flex" }}>
              <input
                id="password"
                type={showPw ? "text" : "password"}
                value={password}
                style={{ ...invalidStyle, flex: 1, paddingRight: "var(--space-7)" }}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
              <button
                type="button"
                className={`linkbtn ${styles.pwToggle}`}
                aria-label={showPw ? "Hide password" : "Show password"}
                onClick={() => setShowPw((s) => !s)}
              >
                {showPw ? <EyeOff size={14} aria-hidden /> : <Eye size={14} aria-hidden />}
              </button>
            </div>
          </div>
          <Button type="submit" disabled={busy} style={{ marginTop: "var(--space-2)" }}>
            {busy ? "Signing in…" : "Sign in"}
          </Button>
          {err && <div className="err">{err}</div>}
        </Card>
        <Card
          as="aside"
          style={{
            background: "var(--basalt-950)",
            color: "var(--basalt-50)",
            border: 0,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            gap: "var(--space-3)",
            padding: "var(--space-6)",
          }}
        >
          <Logo size={48} aria-hidden />
          <div style={{ fontSize: 22, fontWeight: "var(--fw-bold)", letterSpacing: "-0.02em" }}>
            TerraCipher
          </div>
          <div style={{ fontSize: 13, lineHeight: 1.6, color: "var(--basalt-300)" }}>
            Verifier portal for biochar carbon credits, following the CSI
            Global Artisan C-Sink and Rainbow Biochar Standard methodologies
            (C0–C10).
          </div>
        </Card>
      </div>
    </div>
  );
}
