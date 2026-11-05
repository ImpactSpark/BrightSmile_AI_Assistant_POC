import type {
  CaseDetailResponse,
  CaseSummary,
  ChatMessage,
  ChatResponse,
  Condition,
  DoctorSummary,
  PredictionResponse,
  ReviewAction,
  ReviewedFinding,
  BoundingBox,
} from "../types/domain";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(`${API_BASE}${path}`, { ...init, credentials: "include" });
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? body.error ?? detail;
    } catch {
      // response had no JSON body
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export async function uploadXray(
  file: File,
  dentistName = "",
  patientName = ""
): Promise<PredictionResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("dentist_name", dentistName);
  form.append("patient_name", patientName);
  const res = await apiFetch(`/predictions`, {
    method: "POST",
    body: form,
  });
  return handle<PredictionResponse>(res);
}

export async function getCase(caseId: string): Promise<CaseDetailResponse> {
  const res = await apiFetch(`/cases/${caseId}`);
  return handle<CaseDetailResponse>(res);
}

export function caseImageUrl(caseId: string): string {
  return `${API_BASE}/cases/${caseId}/image`;
}

export async function listCases(): Promise<CaseSummary[]> {
  const res = await apiFetch(`/cases`);
  return handle<CaseSummary[]>(res);
}

export async function listDoctors(): Promise<DoctorSummary[]> {
  const res = await apiFetch(`/doctors`);
  return handle<DoctorSummary[]>(res);
}

export async function listCasesForDoctor(doctorId: string): Promise<CaseSummary[]> {
  const res = await apiFetch(`/doctors/${encodeURIComponent(doctorId)}/cases`);
  return handle<CaseSummary[]>(res);
}

export async function listCasesForPatient(patientId: string): Promise<CaseSummary[]> {
  const res = await apiFetch(`/patients/${encodeURIComponent(patientId)}/cases`);
  return handle<CaseSummary[]>(res);
}

export async function getChatHistory(caseId: string): Promise<ChatMessage[]> {
  const res = await apiFetch(`/cases/${caseId}/chat`);
  return handle<ChatMessage[]>(res);
}

export async function sendChatMessage(caseId: string, message: string): Promise<ChatResponse> {
  const res = await apiFetch(`/cases/${caseId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  return handle<ChatResponse>(res);
}

export async function clearChatHistory(caseId: string): Promise<void> {
  const res = await apiFetch(`/cases/${caseId}/chat`, { method: "DELETE" });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? body.error ?? detail;
    } catch {
      // response had no JSON body
    }
    throw new ApiError(res.status, detail);
  }
}

export async function submitReview(
  caseId: string,
  findingId: string,
  action: ReviewAction,
  correction?: { condition: Condition; bbox: BoundingBox }
): Promise<ReviewedFinding> {
  const res = await apiFetch(`/cases/${caseId}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      finding_id: findingId,
      action,
      condition: correction?.condition,
      bbox: correction?.bbox,
    }),
  });
  return handle<ReviewedFinding>(res);
}

export interface MeResponse {
  role: "doctor" | "patient" | "admin";
  id: string;
}

export interface AdminTableInfo {
  name: string;
  description: string;
}

export async function listKnownDoctors(): Promise<string[]> {
  const res = await apiFetch(`/auth/doctors`);
  return handle<string[]>(res);
}

export async function getMe(): Promise<MeResponse> {
  const res = await apiFetch(`/auth/me`);
  return handle<MeResponse>(res);
}

export async function loginDoctor(id: string, password: string): Promise<MeResponse> {
  const res = await apiFetch(`/auth/doctor/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id, password }),
  });
  return handle<MeResponse>(res);
}

export async function loginPatient(id: string, password: string): Promise<MeResponse> {
  const res = await apiFetch(`/auth/patient/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id, password }),
  });
  return handle<MeResponse>(res);
}

export async function logout(): Promise<void> {
  await apiFetch(`/auth/logout`, { method: "POST" });
}

export async function resetDoctorPassword(id: string): Promise<void> {
  const res = await apiFetch(`/auth/doctor/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id }),
  });
  await handle<{ status: string }>(res);
}

export async function resetPatientPassword(id: string): Promise<void> {
  const res = await apiFetch(`/auth/patient/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id }),
  });
  await handle<{ status: string }>(res);
}

export async function loginAdmin(password: string): Promise<MeResponse> {
  const res = await apiFetch(`/auth/admin/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  return handle<MeResponse>(res);
}

export async function resetAdminPassword(): Promise<void> {
  const res = await apiFetch(`/auth/admin/reset-password`, { method: "POST" });
  await handle<{ status: string }>(res);
}

export async function listAllCasesAdmin(): Promise<CaseSummary[]> {
  const res = await apiFetch(`/admin/cases`);
  return handle<CaseSummary[]>(res);
}

export async function listAdminTables(): Promise<AdminTableInfo[]> {
  const res = await apiFetch(`/admin/tables`);
  return handle<AdminTableInfo[]>(res);
}

export async function getAdminTableRows(tableName: string): Promise<Record<string, unknown>[]> {
  const res = await apiFetch(`/admin/tables/${encodeURIComponent(tableName)}/rows`);
  return handle<Record<string, unknown>[]>(res);
}
