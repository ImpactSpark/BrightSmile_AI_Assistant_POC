import { useCallback, useEffect, useRef, useState } from "react";
import { listKnownDoctors } from "../api/client";

const ALLOWED_TYPES = ["image/jpeg", "image/png"];
const MAX_SIZE_BYTES = 10 * 1024 * 1024;

interface Props {
  onAnalyze: (file: File, dentistName: string, patientName: string) => void;
  loading: boolean;
  defaultDentistName?: string;
}

export function UploadPanel({ onAnalyze, loading, defaultDentistName }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [dentistName, setDentistName] = useState(defaultDentistName ?? "");
  const [patientName, setPatientName] = useState("");
  const [doctorNames, setDoctorNames] = useState<string[]>([]);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const blurTimeout = useRef<number | undefined>(undefined);

  useEffect(() => {
    listKnownDoctors()
      .then(setDoctorNames)
      .catch(() => setDoctorNames([]));
  }, []);

  const filteredNames = doctorNames.filter((name) =>
    name.toLowerCase().includes(dentistName.toLowerCase())
  );

  const validateAndSet = useCallback((candidate: File | undefined) => {
    if (!candidate) return;
    if (!ALLOWED_TYPES.includes(candidate.type)) {
      setError("Unsupported file type. Please upload a JPEG or PNG X-ray image.");
      setFile(null);
      setPreviewUrl(null);
      return;
    }
    if (candidate.size > MAX_SIZE_BYTES) {
      setError("File is too large. Maximum upload size is 10MB.");
      setFile(null);
      setPreviewUrl(null);
      return;
    }
    setError(null);
    setFile(candidate);
    setPreviewUrl(URL.createObjectURL(candidate));
  }, []);

  return (
    <div className="upload-panel">
      <div
        className={`upload-panel__dropzone${dragActive ? " upload-panel__dropzone--active" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          validateAndSet(e.dataTransfer.files[0]);
        }}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
      >
        {previewUrl ? (
          <img src={previewUrl} alt="X-ray preview" className="upload-panel__preview" />
        ) : (
          <p>Drag & drop an X-ray image here, or click to select a file</p>
        )}
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png"
          className="upload-panel__file-input"
          data-testid="file-input"
          onChange={(e) => validateAndSet(e.target.files?.[0])}
        />
      </div>

      {error && (
        <p className="upload-panel__error" role="alert">
          {error}
        </p>
      )}

      <label className="upload-panel__dentist-label">
        Dentist name
        <div className="dropdown-field">
          <input
            type="text"
            className="upload-panel__dentist-input"
            placeholder="Dr. …"
            value={dentistName}
            onChange={(e) => setDentistName(e.target.value)}
            onFocus={() => {
              window.clearTimeout(blurTimeout.current);
              setDropdownOpen(true);
            }}
            onBlur={() => {
              blurTimeout.current = window.setTimeout(() => setDropdownOpen(false), 150);
            }}
          />
          {dropdownOpen && doctorNames.length > 0 && (
            <ul className="dropdown-field__menu">
              {filteredNames.length === 0 ? (
                <li className="dropdown-field__empty">No matching dentists</li>
              ) : (
                filteredNames.map((name) => (
                  <li key={name}>
                    <button
                      type="button"
                      onMouseDown={(e) => e.preventDefault()}
                      onClick={() => {
                        setDentistName(name);
                        setDropdownOpen(false);
                      }}
                    >
                      {name}
                    </button>
                  </li>
                ))
              )}
            </ul>
          )}
        </div>
      </label>

      <label className="upload-panel__dentist-label">
        Patient name (required)
        <input
          type="text"
          className="upload-panel__dentist-input"
          placeholder="Jane Doe"
          value={patientName}
          onChange={(e) => setPatientName(e.target.value)}
          required
        />
      </label>

      <button
        type="button"
        className="upload-panel__analyze-btn"
        disabled={!file || !patientName.trim() || loading}
        onClick={() => file && onAnalyze(file, dentistName, patientName.trim())}
      >
        {loading ? (
          <>
            <span className="app__spinner" /> Analyzing…
          </>
        ) : (
          "Analyze"
        )}
      </button>
    </div>
  );
}
