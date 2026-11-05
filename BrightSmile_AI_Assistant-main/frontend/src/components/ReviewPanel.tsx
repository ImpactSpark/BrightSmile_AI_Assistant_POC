import { useState } from "react";
import type { BoundingBox, Condition, Finding } from "../types/domain";
import { CONDITION_LABELS, SUPPORTED_CONDITIONS } from "../types/domain";

interface Props {
  finding: Finding;
  onAccept: (findingId: string) => void;
  onReject: (findingId: string) => void;
  onCorrect: (findingId: string, condition: Condition, bbox: BoundingBox) => void;
  busy: boolean;
  readOnly?: boolean;
}

export function ReviewPanel({ finding, onAccept, onReject, onCorrect, busy, readOnly }: Props) {
  const [correcting, setCorrecting] = useState(false);
  const [condition, setCondition] = useState<Condition>(finding.condition);
  const [bbox, setBbox] = useState<BoundingBox>(finding.bbox);

  const reviewed = finding.status !== "pending";
  const severity =
    finding.confidence >= 0.6 ? "high" : finding.confidence >= 0.35 ? "medium" : "low";

  return (
    <div className={`review-panel review-panel--${severity}`}>
      <header className="review-panel__header">
        <h3>{CONDITION_LABELS[finding.condition]}</h3>
        <span className={`review-panel__confidence review-panel__confidence--${severity}`}>
          {Math.round(finding.confidence * 100)}% confidence
        </span>
      </header>
      <p className="review-panel__hint">{finding.clinical_message}</p>

      {reviewed && (
        <p className="review-panel__status" data-testid="review-status">
          Status: {finding.status}
        </p>
      )}

      {!correcting && !readOnly && (
        <div className="review-panel__actions">
          <button type="button" disabled={busy} onClick={() => onAccept(finding.finding_id)}>
            Accept
          </button>
          <button type="button" disabled={busy} onClick={() => onReject(finding.finding_id)}>
            Reject
          </button>
          <button type="button" disabled={busy} onClick={() => setCorrecting(true)}>
            Correct
          </button>
        </div>
      )}

      {correcting && !readOnly && (
        <div className="review-panel__correction">
          <label>
            Condition
            <select
              value={condition}
              onChange={(e) => setCondition(e.target.value as Condition)}
            >
              {SUPPORTED_CONDITIONS.map((c) => (
                <option key={c} value={c}>
                  {CONDITION_LABELS[c]}
                </option>
              ))}
            </select>
          </label>

          <div className="review-panel__bbox-inputs">
            {(["x1", "y1", "x2", "y2"] as const).map((key) => (
              <label key={key}>
                {key.toUpperCase()}
                <input
                  type="number"
                  value={bbox[key]}
                  onChange={(e) =>
                    setBbox((prev) => ({ ...prev, [key]: Number(e.target.value) }))
                  }
                />
              </label>
            ))}
          </div>

          <div className="review-panel__actions">
            <button
              type="button"
              disabled={busy}
              onClick={() => onCorrect(finding.finding_id, condition, bbox)}
            >
              Save Correction
            </button>
            <button type="button" disabled={busy} onClick={() => setCorrecting(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
