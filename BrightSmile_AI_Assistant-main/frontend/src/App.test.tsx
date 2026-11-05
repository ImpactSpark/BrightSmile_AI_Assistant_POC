import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { AuthProvider } from "./context/AuthContext";
import * as apiClient from "./api/client";

vi.mock("./api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof apiClient>();
  return {
    ...actual,
    uploadXray: vi.fn(),
    submitReview: vi.fn(),
    getCase: vi.fn(),
    getMe: vi.fn(),
    logout: vi.fn(),
  };
});

const mockedUpload = vi.mocked(apiClient.uploadXray);
const mockedReview = vi.mocked(apiClient.submitReview);
const mockedGetCase = vi.mocked(apiClient.getCase);
const mockedGetMe = vi.mocked(apiClient.getMe);

function renderApp() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MemoryRouter>
  );
}

function makeFile() {
  return new File([new Uint8Array(10)], "xray.jpg", { type: "image/jpeg" });
}

beforeEach(() => {
  vi.resetAllMocks();
  globalThis.URL.createObjectURL = vi.fn(() => "blob:mock-url");
  mockedGetMe.mockResolvedValue({ role: "doctor", id: "Dr. Smith" });
});

describe("App end-to-end upload -> results -> review flow", () => {
  it("uploads an image, renders findings, and lets a dentist accept a finding", async () => {
    mockedUpload.mockResolvedValue({
      case_id: "case123",
      model_version: "test",
      image_dimensions: { width: 640, height: 480 },
      findings: [
        {
          finding_id: "finding_001",
          condition: "Caries",
          confidence: 0.87,
          bbox: { x1: 100, y1: 200, x2: 300, y2: 400 },
          review_required: true,
          status: "pending",
          clinical_message: "Possible Caries detected in this region — dentist review required.",
        },
      ],
      disclaimer: "AI-assisted, unverified findings. Dentist review required.",
    });
    mockedReview.mockResolvedValue({
      finding_id: "finding_001",
      original_finding: {
        finding_id: "finding_001",
        condition: "Caries",
        confidence: 0.87,
        bbox: { x1: 100, y1: 200, x2: 300, y2: 400 },
        review_required: true,
        status: "pending",
        clinical_message: "Possible Caries detected in this region — dentist review required.",
      },
      action: "accepted",
      corrected_condition: null,
      corrected_bbox: null,
      reviewed_at: "2024-01-01T00:00:00Z",
    });
    mockedGetCase.mockResolvedValue({
      case_id: "case123",
      model_version: "test",
      image_dimensions: { width: 640, height: 480 },
      findings: [
        {
          finding_id: "finding_001",
          condition: "Caries",
          confidence: 0.87,
          bbox: { x1: 100, y1: 200, x2: 300, y2: 400 },
          review_required: true,
          status: "pending",
          clinical_message: "Possible Caries detected in this region — dentist review required.",
        },
      ],
      dentist_name: "Dr. Smith",
      patient_name: "Test Patient",
      reviews: [],
      disclaimer: "AI-assisted, unverified findings. Dentist review required.",
    });

    renderApp();

    const input = await screen.findByTestId("file-input");
    await userEvent.upload(input, makeFile());
    await userEvent.type(screen.getByPlaceholderText(/jane doe/i), "Jane Doe");
    await userEvent.click(screen.getByRole("button", { name: /^analyze$/i }));

    await waitFor(() => expect(screen.getByText("Caries")).toBeInTheDocument());
    expect(screen.getByText(/87% confidence/i)).toBeInTheDocument();
    expect(screen.getAllByText(/dentist review required/i).length).toBeGreaterThan(0);

    await userEvent.click(screen.getByRole("button", { name: /accept/i }));

    await waitFor(() => expect(mockedReview).toHaveBeenCalledWith("case123", "finding_001", "accepted", undefined));
    await waitFor(() => expect(screen.getByTestId("review-status")).toHaveTextContent("accepted"));
  });

  it("shows an error message when upload fails", async () => {
    mockedUpload.mockRejectedValue(new apiClient.ApiError(422, "unsupported file extension"));
    renderApp();
    const input = await screen.findByTestId("file-input");
    await userEvent.upload(input, makeFile());
    await userEvent.type(screen.getByPlaceholderText(/jane doe/i), "Jane Doe");
    await userEvent.click(screen.getByRole("button", { name: /^analyze$/i }));
    await waitFor(() => expect(mockedUpload).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/unsupported file extension/i));
  });
});
