import { lazy, Suspense, type JSX } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { isAuthed } from "./auth";
import AppShell from "./components/AppShell/AppShell";
import ErrorBoundary from "./ui/ErrorBoundary/ErrorBoundary";

const Login = lazy(() => import("./pages/Login"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Batches = lazy(() => import("./pages/Batches"));
const BatchDetail = lazy(() => import("./pages/BatchDetail"));
const LabScan = lazy(() => import("./pages/LabScan"));
const LabEntry = lazy(() => import("./pages/LabEntry"));
const Registry = lazy(() => import("./pages/Registry"));
const Projects = lazy(() => import("./pages/Projects"));
const Farmers = lazy(() => import("./pages/Farmers"));
const Dispatch = lazy(() => import("./pages/Dispatch"));
const Ledger = lazy(() => import("./pages/Ledger"));
const UnboundSessions = lazy(() => import("./pages/UnboundSessions"));

function RequireAuth({ children }: { children: JSX.Element }) {
  return isAuthed() ? children : <Navigate to="/login" replace />;
}

function Shell({ children }: { children: JSX.Element }) {
  return <AppShell>{children}</AppShell>;
}

export default function App() {
  return (
    <ErrorBoundary>
      <Suspense fallback={<div className="wrap">Loading…</div>}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/dashboard"
            element={
              <RequireAuth>
                <Shell>
                  <Dashboard />
                </Shell>
              </RequireAuth>
            }
          />
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
          <Route
            path="/registry"
            element={
              <RequireAuth>
                <Shell>
                  <Registry />
                </Shell>
              </RequireAuth>
            }
          />
          <Route
            path="/projects"
            element={
              <RequireAuth>
                <Shell>
                  <Projects />
                </Shell>
              </RequireAuth>
            }
          />
          <Route
            path="/farmers"
            element={
              <RequireAuth>
                <Shell>
                  <Farmers />
                </Shell>
              </RequireAuth>
            }
          />
          <Route
            path="/dispatch"
            element={
              <RequireAuth>
                <Shell>
                  <Dispatch />
                </Shell>
              </RequireAuth>
            }
          />
          <Route
            path="/ledgers"
            element={
              <RequireAuth>
                <Shell>
                  <Ledger />
                </Shell>
              </RequireAuth>
            }
          />
          <Route path="/telemetry/unbound" element={<RequireAuth><Shell><UnboundSessions /></Shell></RequireAuth>} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Suspense>
    </ErrorBoundary>
  );
}
