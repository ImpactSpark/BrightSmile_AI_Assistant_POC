import type { ReactNode } from "react";
import { Navigate, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { AdminDashboardPage } from "./pages/AdminDashboardPage";
import { AdminTableRowsPage } from "./pages/AdminTableRowsPage";
import { CaseDetailPage } from "./pages/CaseDetailPage";
import { DoctorCasesPage } from "./pages/DoctorCasesPage";
import { LoginPage } from "./pages/LoginPage";
import { PatientCasesPage } from "./pages/PatientCasesPage";
import { UploadPage } from "./pages/UploadPage";
import { useAuth } from "./context/AuthContext";
import "./App.css";

function RequireAuth({ children }: { children: ReactNode }) {
  const { role, loading } = useAuth();
  if (loading) {
    return (
      <p className="chat-panel__empty">
        <span className="app__spinner" /> Loading…
      </p>
    );
  }
  if (!role) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function App() {
  const { role, id, loading, clear } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await clear();
    navigate("/login");
  }

  return (
    <div className="app">
      <header className="app__header">
        <div className="app__brand">
          <img src="/favicon.svg" alt="" className="app__brand-icon" />
          <h1>BrightSmile AI Assistant</h1>
        </div>
        <p className="app__disclaimer-banner">
          Clinical decision-support research tool. Not an autonomous diagnostic system.
        </p>
        <nav className="app__nav">
          {role === "doctor" && (
            <>
              <NavLink
                to="/"
                end
                className={({ isActive }) => `app__nav-btn${isActive ? " app__nav-btn--active" : ""}`}
              >
                Upload
              </NavLink>
              <NavLink
                to={`/gallery/${encodeURIComponent(id ?? "")}`}
                className={({ isActive }) => `app__nav-btn${isActive ? " app__nav-btn--active" : ""}`}
              >
                My gallery
              </NavLink>
            </>
          )}
          {role === "patient" && (
            <NavLink
              to="/patient/cases"
              className={({ isActive }) => `app__nav-btn${isActive ? " app__nav-btn--active" : ""}`}
            >
              My cases
            </NavLink>
          )}
          {role === "admin" && (
            <NavLink
              to="/admin"
              className={({ isActive }) => `app__nav-btn${isActive ? " app__nav-btn--active" : ""}`}
            >
              Admin
            </NavLink>
          )}
          {!loading && role && (
            <button type="button" className="app__nav-btn" onClick={handleLogout}>
              Log out ({id})
            </button>
          )}
        </nav>
      </header>

      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <UploadPage />
            </RequireAuth>
          }
        />
        <Route
          path="/gallery/:doctorId"
          element={
            <RequireAuth>
              <DoctorCasesPage />
            </RequireAuth>
          }
        />
        <Route
          path="/patient/cases"
          element={
            <RequireAuth>
              <PatientCasesPage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin"
          element={
            <RequireAuth>
              <AdminDashboardPage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/tables/:tableName"
          element={
            <RequireAuth>
              <AdminTableRowsPage />
            </RequireAuth>
          }
        />
        <Route
          path="/cases/:caseId"
          element={
            <RequireAuth>
              <CaseDetailPage />
            </RequireAuth>
          }
        />
      </Routes>
    </div>
  );
}

export default App;
