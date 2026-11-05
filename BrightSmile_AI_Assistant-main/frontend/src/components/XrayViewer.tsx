import { useEffect, useRef, useState } from "react";
import type { Finding, ImageDimensions } from "../types/domain";
import { CONDITION_LABELS } from "../types/domain";
import { originalToDisplay } from "../utils/coordinates";

interface Props {
  imageUrl: string;
  imageDimensions: ImageDimensions;
  findings: Finding[];
  selectedFindingId?: string;
  onSelectFinding?: (findingId: string) => void;
}

const MIN_ZOOM = 1;
const MAX_ZOOM = 4;
const LABEL_HEIGHT = 20;

/** Greedily assigns each label a vertical "lane" so overlapping labels
 * (boxes close together on the x-axis) stack instead of colliding. */
function assignLabelLanes(
  items: { id: string; x1: number; x2: number }[]
): Map<string, number> {
  const lanes: number[] = []; // last-used x2 per lane
  const result = new Map<string, number>();
  const sorted = [...items].sort((a, b) => a.x1 - b.x1);
  for (const item of sorted) {
    let lane = lanes.findIndex((laneEnd) => laneEnd <= item.x1);
    if (lane === -1) {
      lane = lanes.length;
      lanes.push(item.x2);
    } else {
      lanes[lane] = item.x2;
    }
    result.set(item.id, lane);
  }
  return result;
}

export function XrayViewer({
  imageUrl,
  imageDimensions,
  findings,
  selectedFindingId,
  onSelectFinding,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const [displaySize, setDisplaySize] = useState({ width: 0, height: 0 });
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const dragState = useRef<{ startX: number; startY: number; panX: number; panY: number } | null>(
    null
  );

  useEffect(() => {
    const el = imgRef.current;
    if (!el) return;

    const update = () => {
      setDisplaySize({ width: el.clientWidth, height: el.clientHeight });
    };
    update();

    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, [imageUrl]);

  useEffect(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, [imageUrl]);

  function handleWheel(e: React.WheelEvent) {
    e.preventDefault();
    setZoom((z) => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, z - e.deltaY * 0.0015)));
  }

  function handleMouseDown(e: React.MouseEvent) {
    if (zoom <= 1) return;
    dragState.current = { startX: e.clientX, startY: e.clientY, panX: pan.x, panY: pan.y };
  }

  function handleMouseMove(e: React.MouseEvent) {
    if (!dragState.current) return;
    const dx = (e.clientX - dragState.current.startX) / zoom;
    const dy = (e.clientY - dragState.current.startY) / zoom;
    setPan({ x: dragState.current.panX + dx, y: dragState.current.panY + dy });
  }

  function stopDrag() {
    dragState.current = null;
  }

  const boxes =
    displaySize.width > 0
      ? findings.map((finding) => ({
          finding,
          box: originalToDisplay(
            finding.bbox,
            imageDimensions.width,
            imageDimensions.height,
            displaySize.width,
            displaySize.height
          ),
        }))
      : [];

  const lanes = assignLabelLanes(
    boxes.map(({ finding, box }) => ({ id: finding.finding_id, x1: box.x1, x2: box.x2 }))
  );

  return (
    <div className="xray-viewer" ref={containerRef}>
      <div className="xray-viewer__zoom-controls">
        <button type="button" onClick={() => setZoom((z) => Math.min(MAX_ZOOM, z + 0.5))}>
          +
        </button>
        <button type="button" onClick={() => setZoom((z) => Math.max(MIN_ZOOM, z - 0.5))}>
          −
        </button>
        <button
          type="button"
          onClick={() => {
            setZoom(1);
            setPan({ x: 0, y: 0 });
          }}
        >
          Reset
        </button>
      </div>
      <div
        className="xray-viewer__zoom-frame"
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={stopDrag}
        onMouseLeave={stopDrag}
        style={{ cursor: zoom > 1 ? "grab" : "default" }}
      >
        <div
          className="xray-viewer__zoom-content"
          style={{ transform: `scale(${zoom}) translate(${pan.x}px, ${pan.y}px)` }}
        >
          <img
            ref={imgRef}
            src={imageUrl}
            alt="Uploaded dental X-ray"
            className="xray-viewer__image"
            draggable={false}
          />
          {displaySize.width > 0 && (
            <div
              className="xray-viewer__overlay"
              style={{ width: displaySize.width, height: displaySize.height }}
            >
              {boxes.map(({ finding, box }) => {
                const isSelected = finding.finding_id === selectedFindingId;
                const severity =
                  finding.confidence >= 0.6
                    ? "high"
                    : finding.confidence >= 0.35
                      ? "medium"
                      : "low";
                const lane = lanes.get(finding.finding_id) ?? 0;
                return (
                  <button
                    key={finding.finding_id}
                    type="button"
                    className={`xray-viewer__box xray-viewer__box--${severity}${isSelected ? " xray-viewer__box--selected" : ""} xray-viewer__box--${finding.status}`}
                    style={{
                      left: box.x1,
                      top: box.y1,
                      width: box.x2 - box.x1,
                      height: box.y2 - box.y1,
                    }}
                    onClick={() => onSelectFinding?.(finding.finding_id)}
                    aria-label={`${CONDITION_LABELS[finding.condition]}, ${Math.round(finding.confidence * 100)}% confidence`}
                  >
                    <span
                      className="xray-viewer__box-label"
                      style={{ top: -LABEL_HEIGHT * (lane + 1) }}
                    >
                      {CONDITION_LABELS[finding.condition]} {Math.round(finding.confidence * 100)}%
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
