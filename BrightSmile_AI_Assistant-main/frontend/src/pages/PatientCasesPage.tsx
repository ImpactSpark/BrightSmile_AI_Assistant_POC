import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, caseImageUrl, listCasesForPatient } from "../api/client";
import { useAuth } from "../context/AuthContext";
import type { CaseSummary } from "../types/domain";

export function PatientCasesPage() {
  const { id } = useAuth();
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    listCasesForPatient(id)
      .then(setCases)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load cases."))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading)
    return (
      <p className="chat-panel__empty">
        <span className="app__spinner" /> Loading your cases…
      </p>
    );
  if (error)
    return (
      <p className="app__error" role="alert">
        {error}
      </p>
    );

  return (
    <div className="gallery">
      <h2>Your case history ({cases.length})</h2>
      {cases.length === 0 && <p>No cases found for your account.</p>}
      <div className="gallery__grid">
        {cases.map((c) => (
          <Link key={c.case_id} className="gallery__item" to={`/cases/${c.case_id}`}>
            <img src={caseImageUrl(c.case_id)} alt="Your X-ray" loading="lazy" />
            <span>Doctor Name: {c.dentist_name || "—"}</span>
            <span>{new Date(c.created_at).toLocaleString()}</span>
            <span>{c.finding_count} finding(s)</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
