import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Finding } from "../types/domain";
import { ReviewPanel } from "./ReviewPanel";

const finding: Finding = {
  finding_id: "finding_001",
  condition: "Caries",
  confidence: 0.87,
  bbox: { x1: 100, y1: 200, x2: 300, y2: 400 },
  review_required: true,
  status: "pending",
  clinical_message: "Possible Caries detected in this region — dentist review required.",
};

describe("ReviewPanel", () => {
  it("calls onAccept when Accept is clicked", async () => {
    const onAccept = vi.fn();
    render(
      <ReviewPanel finding={finding} onAccept={onAccept} onReject={vi.fn()} onCorrect={vi.fn()} busy={false} />
    );
    await userEvent.click(screen.getByRole("button", { name: /accept/i }));
    expect(onAccept).toHaveBeenCalledWith("finding_001");
  });

  it("calls onReject when Reject is clicked", async () => {
    const onReject = vi.fn();
    render(
      <ReviewPanel finding={finding} onAccept={vi.fn()} onReject={onReject} onCorrect={vi.fn()} busy={false} />
    );
    await userEvent.click(screen.getByRole("button", { name: /reject/i }));
    expect(onReject).toHaveBeenCalledWith("finding_001");
  });

  it("shows editable condition + bbox fields and calls onCorrect with edited values", async () => {
    const onCorrect = vi.fn();
    render(
      <ReviewPanel finding={finding} onAccept={vi.fn()} onReject={vi.fn()} onCorrect={onCorrect} busy={false} />
    );
    await userEvent.click(screen.getByRole("button", { name: /correct/i }));

    await userEvent.selectOptions(screen.getByRole("combobox"), "Deep_Caries");

    const x1Input = screen.getByLabelText("X1");
    await userEvent.clear(x1Input);
    await userEvent.type(x1Input, "50");

    await userEvent.click(screen.getByRole("button", { name: /save correction/i }));

    expect(onCorrect).toHaveBeenCalledWith(
      "finding_001",
      "Deep_Caries",
      expect.objectContaining({ x1: 50 })
    );
  });

  it("does not expose unsupported conditions in the correction dropdown", async () => {
    render(
      <ReviewPanel finding={finding} onAccept={vi.fn()} onReject={vi.fn()} onCorrect={vi.fn()} busy={false} />
    );
    await userEvent.click(screen.getByRole("button", { name: /correct/i }));
    const options = screen.getAllByRole("option").map((o) => o.textContent);
    expect(options).toEqual(["Caries", "Deep Caries", "Periapical Lesion", "Impacted Tooth"]);
  });
});
