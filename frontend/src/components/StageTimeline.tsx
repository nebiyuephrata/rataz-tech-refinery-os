import { CheckCircle2, LoaderCircle, XCircle } from "lucide-react";

import type { StageState } from "../hooks/useExtraction";

type Props = {
  stages: StageState[];
};

export default function StageTimeline({ stages }: Props) {
  return (
    <div className="neon-border rounded-2xl bg-[var(--panel)] p-5 backdrop-blur">
      <h2 className="font-display text-xl">Realtime Pipeline Status</h2>
      <div className="mt-4 space-y-3">
        {stages.map((stage) => (
          <div key={stage.id} className="flex items-center gap-3 rounded-lg border border-white/10 px-4 py-3">
            {stage.state === "done" && <CheckCircle2 className="h-4 w-4 text-emerald-400" />}
            {stage.state === "running" && <LoaderCircle className="h-4 w-4 animate-spin text-cyan-300" />}
            {stage.state === "error" && <XCircle className="h-4 w-4 text-rose-400" />}
            {stage.state === "idle" && <div className="h-4 w-4 rounded-full border border-white/20" />}
            <p className="text-sm">{stage.label}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
