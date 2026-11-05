import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { ApiError, caseImageUrl, getCase, submitReview } from "../api/client";
import { ChatPanel } from "../components/ChatPanel";
import { ReviewPanel } from "../components/ReviewPanel";
import { XrayViewer } from "../components/XrayViewer";
import { useAuth } from "../context/AuthContext";
import type { BoundingBox, CaseDetailResponse, Condition, Finding } from "../types/domain";

export function CaseDetailPage() {
  const { caseId = "" } = useParams<{ caseId: string }>();
  const { role } = useAuth();
  const readOnly = role !== "doctor";
  const [detail, setDetail] = useState<CaseDetailResponse | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [selectedFindingId, setSelectedFindingId] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getCase(caseId)
      .then((d) => {
        setDetail(d);
        setFindings(d.findings);
        setSelectedFindingId(d.findings[0]?.finding_id);
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load case."))
      .finally(() => setLoading(false));
  }, [caseId]);

  async function handleReview(
    findingId: string,
    action: "accepted" | "rejected" | "corrected",
    correction?: { condition: Condition; bbox: BoundingBox }
  ) {
    setBusy(true);
    setError(null);
    try {
      await submitReview(caseId, findingId, action, correction);
      setFindings((prev) =>
        prev.map((f) =>
          f.finding_id === findingId
            ? {
                ...f,
                status: action,
                ...(action === "corrected" && correction
                  ? { condition: correction.condition, bbox: correction.bbox }
                  : {}),
              }
            : f
        )
      );
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Review submission failed.");
    } finally {
      setBusy(false);
    }
  }

  if (loading)
    return (
      <p className="chat-panel__empty">
        <span className="app__spinner" /> Loading case…
      </p>
    );
  if (error)
    return (
      <p className="app__error" role="alert">
        {error}
      </p>
    );
  if (!detail) return null;

  return (
    <div className="app__results app__fade-in">
      <div className="app__viewer-column">
        <XrayViewer
          imageUrl={caseImageUrl(caseId)}
          imageDimensions={detail.image_dimensions}
          findings={findings}
          selectedFindingId={selectedFindingId}
          onSelectFinding={setSelectedFindingId}
        />
        {role === "patient" ? (
          <p className="app__case-tag">Doctor Name: {detail.dentist_name || "—"}</p>
        ) : (
          <p className="app__case-tag">
            Patient: {detail.patient_name || "—"}
            {role !== "doctor" && detail.dentist_name && ` · Dentist: ${detail.dentist_name}`}
          </p>
        )}
        <p className="app__disclaimer">{detail.disclaimer}</p>
      </div>

      <div className="app__findings-column">
        <h2>Findings ({findings.length})</h2>
        {findings.length === 0 && <p>No findings above the confidence threshold.</p>}
        <ul className="app__findings-list">
          {findings.map((finding) => (
            <li
              key={finding.finding_id}
              className={finding.finding_id === selectedFindingId ? "app__findings-list-item--selected" : ""}
              onClick={() => setSelectedFindingId(finding.finding_id)}
            >
              <ReviewPanel
                finding={finding}
                busy={busy}
                readOnly={readOnly}
                onAccept={(id) => handleReview(id, "accepted")}
                onReject={(id) => handleReview(id, "rejected")}
                onCorrect={(id, condition, bbox) => handleReview(id, "corrected", { condition, bbox })}
              />
            </li>
          ))}
        </ul>
      </div>

      <div className="app__chat-column">
        <ChatPanel
          caseId={caseId}
          readOnly={readOnly}
          findings={findings}
          onHighlightFinding={setSelectedFindingId}
        />
      </div>
    </div>
  );
}
