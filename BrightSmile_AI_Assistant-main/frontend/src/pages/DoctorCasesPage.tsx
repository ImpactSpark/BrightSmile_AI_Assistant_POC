import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, caseImageUrl, listCasesForDoctor } from "../api/client";
import { useAuth } from "../context/AuthContext";
import type { CaseSummary } from "../types/domain";

export function DoctorCasesPage() {
  const { doctorId = "" } = useParams<{ doctorId: string }>();
  const { id: ownDoctorId } = useAuth();
  const isOwnGallery = doctorId === ownDoctorId;
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    listCasesForDoctor(doctorId)
      .then(setCases)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load cases."))
      .finally(() => setLoading(false));
  }, [doctorId]);

  if (loading)
    return (
      <p className="chat-panel__empty">
        <span className="app__spinner" /> Loading cases…
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
      <h2>{isOwnGallery ? "Your" : `${doctorId}'s`} case history ({cases.length})</h2>
      {cases.length === 0 && <p>No cases for this dentist.</p>}
      <div className="gallery__grid">
        {cases.map((c) => (
          <Link key={c.case_id} className="gallery__item" to={`/cases/${c.case_id}`}>
            <img src={caseImageUrl(c.case_id)} alt={`X-ray for ${doctorId}`} loading="lazy" />
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
