// Exact class names from the frozen YOLO11m model (model_artifacts/frozen_model_config.json).
// Do not rename, reorder, or add to this list without updating the frozen model.
export type Condition =
  | "Caries"
  | "Deep_Caries"
  | "Periapical_Lesion"
  | "Impacted_Tooth";

export const SUPPORTED_CONDITIONS: Condition[] = [
  "Caries",
  "Deep_Caries",
  "Periapical_Lesion",
  "Impacted_Tooth",
];

export const CONDITION_LABELS: Record<Condition, string> = {
  Caries: "Caries",
  Deep_Caries: "Deep Caries",
  Periapical_Lesion: "Periapical Lesion",
  Impacted_Tooth: "Impacted Tooth",
};

export interface BoundingBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export type FindingStatus = "pending" | "accepted" | "rejected" | "corrected";

export interface Finding {
  finding_id: string;
  condition: Condition;
  confidence: number;
  bbox: BoundingBox;
  review_required: boolean;
  status: FindingStatus;
  clinical_message: string;
}

export interface ImageDimensions {
  width: number;
  height: number;
}

export interface PredictionResponse {
  case_id: string;
  model_version: string;
  image_dimensions: ImageDimensions;
  findings: Finding[];
  disclaimer: string;
}

export type ReviewAction = "accepted" | "rejected" | "corrected";

export interface ReviewedFinding {
  finding_id: string;
  original_finding: Finding;
  action: ReviewAction;
  corrected_condition: Condition | null;
  corrected_bbox: BoundingBox | null;
  reviewed_at: string;
}

export interface CaseDetailResponse {
  case_id: string;
  model_version: string;
  image_dimensions: ImageDimensions;
  findings: Finding[];
  reviews: ReviewedFinding[];
  disclaimer: string;
  dentist_name: string;
  patient_name: string;
}

export interface CaseSummary {
  case_id: string;
  dentist_name: string;
  patient_id: string;
  patient_name: string;
  model_version: string;
  created_at: string;
  finding_count: number;
}

export interface DoctorSummary {
  doctor_id: string;
  name: string;
  case_count: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  created_at?: string;
  citations?: Citation[];
  annotated_image?: string | null;
}

export interface Citation {
  chunk_id: string;
  source: string;
  url: string;
}

export interface ChatResponse {
  reply: string;
  citations: Citation[];
  annotated_image?: string | null;
}
