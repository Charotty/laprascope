import { useCallback, useRef, useState } from 'react';

type Props = {
  accept: string;
  label: string;
  disabled?: boolean;
  onFileSelected: (file: File) => void;
};

export default function FileUpload({ accept, label, disabled, onFileSelected }: Props) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [isOver, setIsOver] = useState(false);

  const open = useCallback(() => {
    if (disabled) return;
    inputRef.current?.click();
  }, [disabled]);

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      if (disabled) return;
      setIsOver(false);

      const file = e.dataTransfer.files?.[0];
      if (file) onFileSelected(file);
    },
    [disabled, onFileSelected]
  );

  return (
    <div>
      <div
        className="card"
        role="button"
        tabIndex={0}
        onClick={open}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') open();
        }}
        onDragEnter={(e) => {
          e.preventDefault();
          if (!disabled) setIsOver(true);
        }}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setIsOver(true);
        }}
        onDragLeave={(e) => {
          e.preventDefault();
          setIsOver(false);
        }}
        onDrop={onDrop}
        style={{
          cursor: disabled ? 'not-allowed' : 'pointer',
          outline: isOver ? '2px solid rgba(91, 124, 255, 0.9)' : 'none'
        }}
      >
        <div style={{ fontWeight: 800, marginBottom: 6 }}>{label}</div>
        <div className="muted" style={{ lineHeight: 1.55 }}>
          Click to select file or drag & drop here.
        </div>
        <div className="muted" style={{ marginTop: 10, fontSize: 12 }}>
          accepted: {accept}
        </div>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={accept}
        disabled={disabled}
        style={{ display: 'none' }}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFileSelected(file);
          if (inputRef.current) inputRef.current.value = '';
        }}
      />
    </div>
  );
}
