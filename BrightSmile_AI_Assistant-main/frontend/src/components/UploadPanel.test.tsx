import { render, screen, fireEvent, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { UploadPanel } from "./UploadPanel";

function makeFile(name: string, type: string, sizeBytes = 100) {
  const content = new Uint8Array(sizeBytes);
  return new File([content], name, { type });
}

describe("UploadPanel", () => {
  it("disables Analyze until a file is chosen", () => {
    render(<UploadPanel onAnalyze={vi.fn()} loading={false} />);
    expect(screen.getByRole("button", { name: /analyze/i })).toBeDisabled();
  });

  it("accepts a valid file via the file input and enables Analyze", async () => {
    render(<UploadPanel onAnalyze={vi.fn()} loading={false} />);
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    const file = makeFile("xray.jpg", "image/jpeg");
    await userEvent.upload(input, file);
    await userEvent.type(screen.getByPlaceholderText(/jane doe/i), "Jane Doe");
    expect(screen.getByRole("button", { name: /analyze/i })).toBeEnabled();
    expect(screen.getByAltText(/x-ray preview/i)).toBeInTheDocument();
  });

  it("shows a validation error for unsupported file types", async () => {
    render(<UploadPanel onAnalyze={vi.fn()} loading={false} />);
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    const file = makeFile("notes.txt", "text/plain");
    // userEvent.upload respects the input's `accept` filter, so a non-matching
    // file must be injected directly to exercise the app's own validation.
    Object.defineProperty(input, "files", { value: [file] });
    fireEvent.change(input);
    expect(screen.getByRole("alert")).toHaveTextContent(/unsupported file type/i);
    expect(screen.getByRole("button", { name: /analyze/i })).toBeDisabled();
  });

  it("shows a validation error for oversized files", async () => {
    render(<UploadPanel onAnalyze={vi.fn()} loading={false} />);
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    const file = makeFile("xray.jpg", "image/jpeg", 11 * 1024 * 1024);
    await userEvent.upload(input, file);
    expect(screen.getByRole("alert")).toHaveTextContent(/too large/i);
  });

  it("shows loading state and calls onAnalyze with the chosen file", async () => {
    const onAnalyze = vi.fn();
    const { rerender } = render(<UploadPanel onAnalyze={onAnalyze} loading={false} />);
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    const file = makeFile("xray.jpg", "image/jpeg");
    await userEvent.upload(input, file);
    await userEvent.type(screen.getByPlaceholderText(/jane doe/i), "Jane Doe");

    fireEvent.click(screen.getByRole("button", { name: /analyze/i }));
    expect(onAnalyze).toHaveBeenCalledWith(file, "", "Jane Doe");

    rerender(<UploadPanel onAnalyze={onAnalyze} loading={true} />);
    expect(within(document.body).getByRole("button", { name: /analyzing/i })).toBeDisabled();
  });
});
