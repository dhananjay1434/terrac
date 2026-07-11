import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login, ApiError } from "../api";
import { setSession } from "../auth";

export default function Login() {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

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
        <h1>Verifier Portal</h1>
        <span className="micro">Lab &amp; verifier sign-in</span>
        <input
          type="email"
          placeholder="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="username"
        />
        <input
          type="password"
          placeholder="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
        />
        <button className="primary" type="submit" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
        {err && <div className="err">{err}</div>}
      </form>
    </div>
  );
}
