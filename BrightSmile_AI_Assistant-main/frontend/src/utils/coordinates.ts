import type { BoundingBox } from "../types/domain";

/**
 * Maps a bounding box in original-image pixel space to displayed-element
 * pixel space, given the displayed element's rendered size. Assumes the
 * image is displayed at `displayWidth x displayHeight` with no cropping
 * (object-fit: contain is NOT assumed here -- caller must pass the actual
 * rendered box size, e.g. from getBoundingClientRect on an <img> sized by
 * CSS width/height with the image's natural aspect ratio preserved).
 */
export function originalToDisplay(
  bbox: BoundingBox,
  originalWidth: number,
  originalHeight: number,
  displayWidth: number,
  displayHeight: number
): BoundingBox {
  const scaleX = displayWidth / originalWidth;
  const scaleY = displayHeight / originalHeight;
  return {
    x1: bbox.x1 * scaleX,
    y1: bbox.y1 * scaleY,
    x2: bbox.x2 * scaleX,
    y2: bbox.y2 * scaleY,
  };
}

export function displayToOriginal(
  bbox: BoundingBox,
  originalWidth: number,
  originalHeight: number,
  displayWidth: number,
  displayHeight: number
): BoundingBox {
  const scaleX = originalWidth / displayWidth;
  const scaleY = originalHeight / displayHeight;
  return {
    x1: bbox.x1 * scaleX,
    y1: bbox.y1 * scaleY,
    x2: bbox.x2 * scaleX,
    y2: bbox.y2 * scaleY,
  };
}

export function clampBox(box: BoundingBox, maxWidth: number, maxHeight: number): BoundingBox {
  return {
    x1: Math.max(0, Math.min(box.x1, maxWidth)),
    y1: Math.max(0, Math.min(box.y1, maxHeight)),
    x2: Math.max(0, Math.min(box.x2, maxWidth)),
    y2: Math.max(0, Math.min(box.y2, maxHeight)),
  };
}
