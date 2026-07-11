import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { clearSession, isAuthed } from "./auth";
import { logout } from "./api";
import Login from "./pages/Login";
import Batches from "./pages/Batches";
import BatchDetail from "./pages/BatchDetail";
import LabScan from "./pages/LabScan";
import LabEntry from "./pages/LabEntry";
import type { JSX } from "react";

function RequireAuth({ children }: { children: JSX.Element }) {
  return isAuthed() ? children : <Navigate to="/login" replace />;
}

function TopBar() {
  const nav = useNavigate();
  async function signOut() {
    await logout();
    clearSession();
    nav("/login");
  }
  return (
    <div className="top">
      <div className="top-in">
        <div className="mark">TC</div>
        <div className="brand">
          TerraCipher <span>· Verifier Portal</span>
        </div>
        <span className="spacer" />
        <button className="linkbtn" onClick={() => nav("/lab/scan")}>
          Lab scan
        </button>
        <button className="linkbtn" onClick={signOut}>
          Sign out
        </button>
      </div>
    </div>
  );
}

function Shell({ children }: { children: JSX.Element }) {
  return (
    <>
      <TopBar />
      {children}
    </>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/batches"
        element={
          <RequireAuth>
            <Shell>
              <Batches />
            </Shell>
          </RequireAuth>
        }
      />
      <Route
        path="/batches/:uuid"
        element={
          <RequireAuth>
            <Shell>
              <BatchDetail />
            </Shell>
          </RequireAuth>
        }
      />
      <Route
        path="/lab/scan"
        element={
          <RequireAuth>
            <Shell>
              <LabScan />
            </Shell>
          </RequireAuth>
        }
      />
      <Route
        path="/lab/:uuid"
        element={
          <RequireAuth>
            <Shell>
              <LabEntry />
            </Shell>
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/batches" replace />} />
    </Routes>
  );
}
