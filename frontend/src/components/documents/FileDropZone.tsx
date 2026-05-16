import { useRef } from 'react';

interface FileDropZoneProps {
  onFiles: (files: File[]) => void;
  disabled?: boolean;
}

const ACCEPTED_TYPES = ['application/pdf', 'image/jpeg', 'image/png'];
const ACCEPTED_EXTS = '.pdf,.jpg,.jpeg,.png';

export function FileDropZone({ onFiles, disabled }: FileDropZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files).filter((f) => ACCEPTED_TYPES.includes(f.type));
    if (files.length) onFiles(files);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (files.length) onFiles(files);
  };

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Drop files here or click to upload"
      aria-disabled={disabled}
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
      onClick={() => !disabled && inputRef.current?.click()}
      onKeyDown={(e) => e.key === 'Enter' && !disabled && inputRef.current?.click()}
      style={{
        border: '2px dashed #6b7280',
        borderRadius: 8,
        padding: '2rem',
        textAlign: 'center',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
      }}
    >
      <p>Drop PDF, JPEG, or PNG files here</p>
      <p style={{ fontSize: '0.875rem', color: '#6b7280' }}>or click to browse</p>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_EXTS}
        multiple
        hidden
        onChange={handleChange}
      />
    </div>
  );
}
