import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ApiError,
  listKnownDoctors,
  loginAdmin,
  loginDoctor,
  loginPatient,
  resetAdminPassword,
  resetDoctorPassword,
  resetPatientPassword,
} from "../api/client";
import { useAuth } from "../context/AuthContext";

type UserType = "doctor" | "patient" | "admin";

export function LoginPage() {
  const [userType, setUserType] = useState<UserType>("doctor");
  const [id, setId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [doctorNames, setDoctorNames] = useState<string[]>([]);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const { refresh } = useAuth();
  const navigate = useNavigate();
  const blurTimeout = useRef<number | undefined>(undefined);

  useEffect(() => {
    if (userType !== "doctor") return;
    listKnownDoctors()
      .then(setDoctorNames)
      .catch(() => setDoctorNames([]));
  }, [userType]);

  const filteredNames = doctorNames.filter((name) =>
    name.toLowerCase().includes(id.toLowerCase())
  );

  function handleTypeChange(next: UserType) {
    setUserType(next);
    setId("");
    setPassword("");
    setError(null);
    setInfo(null);
  }

  async function handleLogin() {
    setBusy(true);
    setError(null);
    setInfo(null);
    try {
      if (userType === "doctor") {
        await loginDoctor(id, password);
        await refresh();
        navigate(`/gallery/${encodeURIComponent(id)}`);
      } else if (userType === "patient") {
        await loginPatient(id, password);
        await refresh();
        navigate("/patient/cases");
      } else {
        await loginAdmin(password);
        await refresh();
        navigate("/admin");
      }
    } catch (e) {
      if (e instanceof ApiError && e.status === 404 && userType === "doctor") {
        setError(`"${id}" is not a registered dentist name. Pick one from the list below.`);
      } else {
        setError(e instanceof ApiError ? e.message : "Login failed.");
      }
    } finally {
      setBusy(false);
    }
  }

  async function handleReset() {
    if (userType !== "admin" && !id) {
      setError(`Enter your ${userType === "doctor" ? "dentist name" : "patient ID"} first, then reset.`);
      return;
    }
    setBusy(true);
    setError(null);
    setInfo(null);
    try {
      if (userType === "doctor") {
        await resetDoctorPassword(id);
      } else if (userType === "patient") {
        await resetPatientPassword(id);
      } else {
        await resetAdminPassword();
      }
      setInfo("Password reset to 123456.");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Reset failed.");
    } finally {
      setBusy(false);
    }
  }

  const needsId = userType !== "admin";

  return (
    <div className="upload-panel app__fade-in">
      <h2>Log in</h2>

      <label className="upload-panel__dentist-label">
        I am a
        <select
          className="upload-panel__dentist-input"
          value={userType}
          onChange={(e) => handleTypeChange(e.target.value as UserType)}
        >
          <option value="doctor">Dentist</option>
          <option value="patient">Patient</option>
          <option value="admin">SysAdmin</option>
        </select>
      </label>

      {needsId && (
        <label className="upload-panel__dentist-label">
          {userType === "doctor" ? "Dentist name" : "Patient ID"}
          <div className="dropdown-field">
            <input
              type="text"
              className="upload-panel__dentist-input"
              placeholder={userType === "doctor" ? "Dr. …" : "PT-…"}
              value={id}
              onChange={(e) => setId(e.target.value)}
              onFocus={() => {
                window.clearTimeout(blurTimeout.current);
                setDropdownOpen(true);
              }}
              onBlur={() => {
                blurTimeout.current = window.setTimeout(() => setDropdownOpen(false), 150);
              }}
            />
            {userType === "doctor" && dropdownOpen && doctorNames.length > 0 && (
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
                          setId(name);
                          setError(null);
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
      )}

      <label className="upload-panel__dentist-label">
        Password
        <input
          type="password"
          className="upload-panel__dentist-input"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </label>

      {error && (
        <p className="app__error" role="alert">
          {error}
        </p>
      )}
      {info && <p className="app__disclaimer">{info}</p>}

      <button
        type="button"
        className="upload-panel__analyze-btn"
        disabled={busy || (needsId && !id) || !password}
        onClick={handleLogin}
      >
        {busy ? "Logging in…" : "Log in"}
      </button>
      <button type="button" className="app__secondary-btn" disabled={busy} onClick={handleReset}>
        Forgot password? Reset to default (123456)
      </button>
    </div>
  );
}
