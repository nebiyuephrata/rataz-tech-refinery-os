import { MoonStar, Search, SunMedium } from "lucide-react";
import { useCallback } from "react";

import ResultPanels from "./components/ResultPanels";
import StageTimeline from "./components/StageTimeline";
import UploadDropzone from "./components/UploadDropzone";
import { useExtraction } from "./hooks/useExtraction";
import { useTheme } from "./hooks/useTheme";

export default function App() {
  const { isDark, toggleTheme } = useTheme();
  const {
    stages,
    result,
    queryResult,
    queryText,
    setQueryText,
    onUpload,
    onQuery,
    uploading,
    querying,
    uploadError,
    queryError,
    lastRoutes
  } = useExtraction();

  const onQuerySubmit = useCallback(
    (event: React.FormEvent) => {
      event.preventDefault();
      onQuery();
    },
    [onQuery]
  );

  return (
    <main className="min-h-screen bg-grid bg-[length:20px_20px] px-4 py-6 text-[var(--text)] sm:px-8">
      <div className="mx-auto w-full max-w-6xl space-y-5">
        <header className="neon-border rounded-2xl bg-[var(--panel)] p-5 backdrop-blur">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h1 className="font-display text-2xl sm:text-3xl">Rataz Tech Refinery OS</h1>
              <p className="mt-1 text-sm text-[var(--text-soft)]">Neon document intelligence console with provenance-first extraction.</p>
            </div>
            <button
              onClick={toggleTheme}
              className="rounded-lg border border-white/20 p-2 transition hover:border-cyan-300"
              aria-label="Toggle theme"
            >
              {isDark ? <SunMedium className="h-5 w-5" /> : <MoonStar className="h-5 w-5" />}
            </button>
          </div>
        </header>

        <div className="grid gap-4 lg:grid-cols-3">
          <div className="space-y-4 lg:col-span-2">
            <UploadDropzone onFileSelected={onUpload} disabled={uploading} />
            {uploadError && <p className="rounded-lg border border-rose-400/40 bg-rose-950/30 p-3 text-sm text-rose-300">{uploadError}</p>}
            <form onSubmit={onQuerySubmit} className="neon-border rounded-2xl bg-[var(--panel)] p-5">
              <label className="font-display text-lg">Ask the indexed document</label>
              <div className="mt-3 flex gap-2">
                <input
                  value={queryText}
                  onChange={(event) => setQueryText(event.target.value)}
                  placeholder="e.g. revenue in q3"
                  className="w-full rounded-lg border border-white/20 bg-black/30 px-3 py-2 text-sm outline-none focus:border-cyan-300"
                />
                <button
                  type="submit"
                  disabled={!result || querying}
                  className="inline-flex items-center gap-1 rounded-lg border border-cyan-300/40 bg-cyan-500/20 px-4 py-2 text-sm transition hover:bg-cyan-400/30 disabled:opacity-50"
                >
                  <Search className="h-4 w-4" /> Query
                </button>
              </div>
              {queryError && <p className="mt-3 text-sm text-rose-300">{queryError}</p>}
            </form>
          </div>

          <StageTimeline stages={stages} />
        </div>

        <ResultPanels result={result} queryResult={queryResult} routes={lastRoutes} />
      </div>
    </main>
  );
}
