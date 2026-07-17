import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { login, ApiError } from "../api";
import { setSession } from "../auth";

export default function Login() {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
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

  return (
    <div className="login-wrap">
      <form className="login card" onSubmit={submit}>
        <div className="mark">TC</div>
        <h1>Sign in to TerraCipher</h1>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, width: '100%', textAlign: 'left' }}>
          <label className="micro" htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
          />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, width: '100%', textAlign: 'left' }}>
          <label className="micro" htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </div>
        <button className="primary" type="submit" disabled={busy} style={{ marginTop: 8 }}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
        {err && <div className="err">{err}</div>}
      </form>
    </div>
  );
}
