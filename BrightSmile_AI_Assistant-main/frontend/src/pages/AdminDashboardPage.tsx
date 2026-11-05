import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, caseImageUrl, listAdminTables, listAllCasesAdmin } from "../api/client";
import type { AdminTableInfo } from "../api/client";
import type { CaseSummary } from "../types/domain";

export function AdminDashboardPage() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [tables, setTables] = useState<AdminTableInfo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([listAllCasesAdmin(), listAdminTables()])
      .then(([c, t]) => {
        setCases(c);
        setTables(t);
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load admin data."))
      .finally(() => setLoading(false));
  }, []);

  if (loading)
    return (
      <p className="chat-panel__empty">
        <span className="app__spinner" /> Loading…
      </p>
    );
  if (error)
    return (
      <p className="app__error" role="alert">
        {error}
      </p>
    );

  return (
    <div className="gallery app__fade-in">
      <h2>Database tables</h2>
      <ul className="gallery__dentist-list">
        {tables.map((t) => (
          <li key={t.name}>
            <Link className="gallery__dentist-item" to={`/admin/tables/${encodeURIComponent(t.name)}`}>
              <span>{t.name}</span>
              <span className="gallery__dentist-count">{t.description}</span>
            </Link>
          </li>
        ))}
      </ul>

      <h2>All cases ({cases.length})</h2>
      {cases.length === 0 && <p>No cases uploaded yet.</p>}
      <div className="gallery__grid">
        {cases.map((c) => (
          <Link key={c.case_id} className="gallery__item" to={`/cases/${c.case_id}`}>
            <img src={caseImageUrl(c.case_id)} alt={`X-ray for ${c.dentist_name}`} loading="lazy" />
            <span>Dentist: {c.dentist_name || "—"}</span>
            <span>{new Date(c.created_at).toLocaleString()}</span>
            {c.patient_name && (
              <span>
                Patient: {c.patient_name} ({c.patient_id})
              </span>
            )}
            <span>{c.finding_count} finding(s)</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
