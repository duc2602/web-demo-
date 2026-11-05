import { useRef, useState } from "react";

interface Props {
  beforeUrl: string;
  afterUrl: string;
  beforeLabel?: string;
  afterLabel?: string;
}

export default function BeforeAfter({ beforeUrl, afterUrl, beforeLabel = "BEFORE", afterLabel = "AFTER" }: Props) {
  const [pct, setPct] = useState(50);
  const containerRef = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);

  function updateFromClientX(clientX: number) {
    const el = containerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const ratio = ((clientX - rect.left) / rect.width) * 100;
    setPct(Math.min(100, Math.max(0, ratio)));
  }

  return (
    <div
      ref={containerRef}
      role="slider"
      aria-label="Before and after image comparison"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(pct)}
      tabIndex={0}
      className="relative w-full aspect-video touch-none rounded-lg overflow-hidden border border-border select-none cursor-ew-resize bg-black/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      onPointerDown={(e) => {
        dragging.current = true;
        e.currentTarget.setPointerCapture(e.pointerId);
        updateFromClientX(e.clientX);
      }}
      onPointerMove={(e) => {
        if (dragging.current) updateFromClientX(e.clientX);
      }}
      onPointerUp={() => (dragging.current = false)}
      onPointerCancel={() => (dragging.current = false)}
      onKeyDown={(e) => {
        if (e.key === "ArrowLeft") setPct((value) => Math.max(0, value - 5));
        if (e.key === "ArrowRight") setPct((value) => Math.min(100, value + 5));
        if (e.key === "Home") setPct(0);
        if (e.key === "End") setPct(100);
      }}
    >
      <img src={afterUrl} alt="After" className="absolute inset-0 w-full h-full object-contain" />
      <div
        className="absolute inset-0 overflow-hidden"
        style={{ clipPath: `inset(0 ${100 - pct}% 0 0)` }}
      >
        <img src={beforeUrl} alt="Before" className="absolute inset-0 w-full h-full object-contain" />
      </div>

      <div
        className="absolute top-0 bottom-0 w-0.5 bg-white/80"
        style={{ left: `${pct}%` }}
      >
        <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-7 h-7 rounded-full bg-white shadow-lg flex items-center justify-center">
          <div className="w-1 h-3 bg-bg rounded-full mx-0.5" />
          <div className="w-1 h-3 bg-bg rounded-full mx-0.5" />
        </div>
      </div>

      <span className="absolute top-2 left-2 text-[10px] px-2 py-0.5 rounded bg-black/60 text-white">
        {beforeLabel}
      </span>
      <span className="absolute top-2 right-2 text-[10px] px-2 py-0.5 rounded bg-black/60 text-white">
        {afterLabel}
      </span>
    </div>
  );
}
