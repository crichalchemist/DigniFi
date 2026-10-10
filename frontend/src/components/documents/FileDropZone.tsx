import { useRef } from 'react';

interface FileDropZoneProps {
  label: string;
  onFiles: (files: File[]) => void;
  disabled?: boolean;
}

const ACCEPTED_TYPES = ['application/pdf', 'image/jpeg', 'image/png'];
const ACCEPTED_EXTS = '.pdf,.jpg,.jpeg,.png';

export function FileDropZone({ label, onFiles, disabled }: FileDropZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (disabled) return;
    const files = Array.from(e.dataTransfer.files).filter((f) => ACCEPTED_TYPES.includes(f.type));
    if (files.length) onFiles(files);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    // Clear the pick so choosing the same file again (a retry) fires another change.
    e.target.value = '';
    if (files.length) onFiles(files);
  };

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`${label}: drop files here or click to upload`}
      aria-disabled={disabled}
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
      onClick={() => !disabled && inputRef.current?.click()}
      onKeyDown={(e) => {
        if (disabled) return;
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
      className="file-drop-zone"
    >
      <p>Drop PDF, JPEG, or PNG files here</p>
      <p className="text-muted">or click to browse</p>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_EXTS}
        multiple
        hidden
        disabled={disabled}
        onChange={handleChange}
      />
    </div>
  );
}
