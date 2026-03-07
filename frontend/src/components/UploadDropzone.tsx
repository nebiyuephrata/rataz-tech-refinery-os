import { UploadCloud } from "lucide-react";
import { useCallback, useRef } from "react";

type Props = {
  disabled?: boolean;
  onFileSelected: (file: File) => void;
};

export default function UploadDropzone({ disabled, onFileSelected }: Props) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  const onPick = useCallback(() => inputRef.current?.click(), []);

  const onChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (file) onFileSelected(file);
      event.target.value = "";
    },
    [onFileSelected]
  );

  const onDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      if (disabled) return;
      const file = event.dataTransfer.files?.[0];
      if (file) onFileSelected(file);
    },
    [disabled, onFileSelected]
  );

  return (
    <div
      onDragOver={(e) => e.preventDefault()}
      onDrop={onDrop}
      className="neon-border rounded-2xl bg-[var(--panel)] p-6 backdrop-blur"
    >
      <input ref={inputRef} className="hidden" type="file" accept=".pdf,.txt" onChange={onChange} />
      <button
        type="button"
        onClick={onPick}
        disabled={disabled}
        className="group flex w-full items-center justify-between rounded-xl border border-white/20 bg-black/20 px-5 py-4 text-left transition hover:border-cyan-300 disabled:opacity-50"
      >
        <div>
          <p className="font-display text-lg">Upload document</p>
          <p className="text-sm text-[var(--text-soft)]">Drop PDF/TXT or click to browse</p>
        </div>
        <UploadCloud className="h-6 w-6 text-cyan-300 transition group-hover:scale-110" />
      </button>
    </div>
  );
}
