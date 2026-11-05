import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, uploadXray } from "../api/client";
import { UploadPanel } from "../components/UploadPanel";
import { useAuth } from "../context/AuthContext";

export function UploadPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const { role, id } = useAuth();

  async function handleAnalyze(file: File, dentistName: string, patientName: string) {
    setLoading(true);
    setError(null);
    try {
      const result = await uploadXray(file, dentistName, patientName);
      navigate(`/cases/${result.case_id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Upload failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app__fade-in">
      {error && (
        <p className="app__error" role="alert">
          {error}
        </p>
      )}
      <UploadPanel
        onAnalyze={handleAnalyze}
        loading={loading}
        defaultDentistName={role === "doctor" ? (id ?? undefined) : undefined}
      />
    </div>
  );
}
