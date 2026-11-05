import { describe, expect, it } from "vitest";
import { displayToOriginal, originalToDisplay } from "./coordinates";

describe("coordinate transforms", () => {
  it("scales original bbox down to display size", () => {
    const box = originalToDisplay({ x1: 100, y1: 200, x2: 300, y2: 400 }, 1000, 2000, 500, 1000);
    expect(box).toEqual({ x1: 50, y1: 100, x2: 150, y2: 200 });
  });

  it("round-trips display -> original -> display", () => {
    const original = { x1: 100, y1: 200, x2: 300, y2: 400 };
    const display = originalToDisplay(original, 1000, 2000, 500, 1000);
    const back = displayToOriginal(display, 1000, 2000, 500, 1000);
    expect(back.x1).toBeCloseTo(original.x1);
    expect(back.y1).toBeCloseTo(original.y1);
    expect(back.x2).toBeCloseTo(original.x2);
    expect(back.y2).toBeCloseTo(original.y2);
  });

  it("handles non-uniform scaling on each axis independently", () => {
    const box = originalToDisplay({ x1: 0, y1: 0, x2: 1000, y2: 500 }, 1000, 500, 200, 400);
    expect(box).toEqual({ x1: 0, y1: 0, x2: 200, y2: 400 });
  });
});
