"use client";

const STAGES = [
  "Validating",
  "Capturing",
  "Analyzing",
  "Scoring",
  "Ready",
] as const;

export type PipelineStage = (typeof STAGES)[number] | "failed";

type ProgressTrackerProps = {
  status: string;
  error: string | null;
  failedAtStepIndex?: number;
};

function normalizeStatus(raw: string): { stage: PipelineStage; failed: boolean } {
  const s = raw.toLowerCase().replace(/_/g, " ").trim();
  if (s === "failed" || s === "error") return { stage: "failed", failed: true };
  if (
    s === "ready" ||
    s === "completed" ||
    s === "complete" ||
    s === "done"
  ) {
    return { stage: "Ready", failed: false };
  }
  if (s === "scoring" || s === "score") return { stage: "Scoring", failed: false };
  if (s === "analyzing" || s === "analysis")
    return { stage: "Analyzing", failed: false };
  if (s === "capturing" || s === "capture" || s === "screenshot")
    return { stage: "Capturing", failed: false };
  if (
    s === "validating" ||
    s === "validation" ||
    s === "pending" ||
    s === "queued" ||
    s === "created" ||
    s === "starting" ||
    s === ""
  ) {
    return { stage: "Validating", failed: false };
  }
  return { stage: "Validating", failed: false };
}

function stageIndex(stage: PipelineStage): number {
  if (stage === "failed") return -1;
  const i = STAGES.indexOf(stage);
  return i >= 0 ? i : 0;
}

export function pipelineStepFromStatus(raw: string): number {
  const { stage, failed } = normalizeStatus(raw);
  if (failed) return -1;
  return stageIndex(stage);
}

export function ProgressTracker({ status, error }: ProgressTrackerProps) {
  const { stage, failed } = normalizeStatus(status);
  const currentIdx = failed ? -1 : stageIndex(stage);
  const failMessage = failed ? error || "Analysis failed" : null;
  const displayFailAt =
    failed && currentIdx < 0 ? 0 : failed ? Math.max(0, currentIdx) : -1;

  return (
    <div className="w-full max-w-md">
      <h2 className="mb-8 text-center text-sm font-medium uppercase tracking-[0.2em] text-slate-500">
        Pipeline
      </h2>
      <ol className="relative space-y-0">
        {STAGES.map((label, idx) => {
          const isLast = idx === STAGES.length - 1;
          const isComplete = !failed && currentIdx > idx;
          const isCurrent = !failed && currentIdx === idx;
          const isFailedHere = failed && idx === displayFailAt;

          return (
            <li key={label} className="relative flex gap-4 pb-10 last:pb-0">
              {!isLast ? (
                <span
                  className={`absolute left-[1.125rem] top-10 h-[calc(100%-0.5rem)] w-px ${
                    isComplete
                      ? "bg-gradient-to-b from-emerald-500 to-cyan-500/50"
                      : "bg-slate-700/80"
                  }`}
                  aria-hidden
                />
              ) : null}
              <div className="relative z-10 flex shrink-0 flex-col items-center">
                <span
                  className={`flex h-9 w-9 items-center justify-center rounded-full border-2 text-xs font-bold transition-all duration-500 ${
                    isFailedHere
                      ? "border-red-500/80 bg-red-950/60 text-red-300 shadow-[0_0_24px_-4px_rgb(239_68_68_0.5)]"
                      : isComplete
                        ? "border-emerald-400/60 bg-emerald-950/40 text-emerald-300 shadow-[0_0_20px_-6px_rgb(52_211_153_0.45)]"
                        : isCurrent
                          ? "animate-neuro-glow border-cyan-400/70 bg-cyan-950/30 text-cyan-200"
                          : "border-slate-600 bg-[#111827] text-slate-500"
                  }`}
                >
                  {isFailedHere ? (
                    <svg
                      className="h-4 w-4"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                    >
                      <path d="M18 6 6 18M6 6l12 12" />
                    </svg>
                  ) : isComplete ? (
                    <svg
                      className="h-4 w-4"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M20 6 9 17l-5-5" />
                    </svg>
                  ) : isCurrent ? (
                    <span
                      className="h-3.5 w-3.5 rounded-full border-2 border-cyan-300/40 border-t-cyan-300 animate-neuro-spin"
                      aria-hidden
                    />
                  ) : (
                    <span className="text-[10px] opacity-60">{idx + 1}</span>
                  )}
                </span>
              </div>
              <div className="min-w-0 flex-1 pt-0.5">
                <p
                  className={`text-base font-semibold transition-colors duration-300 ${
                    isFailedHere
                      ? "text-red-200"
                      : isComplete
                        ? "text-emerald-200"
                        : isCurrent
                          ? "text-cyan-100"
                          : "text-slate-500"
                  }`}
                >
                  {label}
                </p>
                {isCurrent && !failed ? (
                  <p className="mt-1 text-sm text-cyan-400/70">In progress…</p>
                ) : null}
                {isFailedHere && failMessage ? (
                  <p className="mt-2 text-sm leading-relaxed text-red-300/90">
                    {failMessage}
                  </p>
                ) : null}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
