import { Navigate, Route, Routes } from "react-router-dom";
import { isAuthed } from "./auth";
import Login from "./pages/Login";
import Batches from "./pages/Batches";
import BatchDetail from "./pages/BatchDetail";
import LabScan from "./pages/LabScan";
import LabEntry from "./pages/LabEntry";
import Registry from "./pages/Registry";
import Projects from "./pages/Projects";
import Farmers from "./pages/Farmers";
import Dispatch from "./pages/Dispatch";
import AppShell from "./components/AppShell/AppShell";
import type { JSX } from "react";

function RequireAuth({ children }: { children: JSX.Element }) {
  return isAuthed() ? children : <Navigate to="/login" replace />;
}

function Shell({ children }: { children: JSX.Element }) {
  return <AppShell>{children}</AppShell>;
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
      <Route path="*" element={<Navigate to="/batches" replace />} />
    </Routes>
  );
}
