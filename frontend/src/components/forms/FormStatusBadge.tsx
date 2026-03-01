/**
 * FormStatusBadge - Visual indicator for form generation/download/filing status
 */

import type { FormStatus } from '../../types/api';

interface FormStatusBadgeProps {
  status: FormStatus | 'pending';
}

const STATUS_CONFIG: Record<FormStatus | 'pending', { label: string; className: string }> = {
  pending:    { label: 'Not Generated', className: 'form-status-badge--pending' },
  generated:  { label: 'Generated',     className: 'form-status-badge--generated' },
  downloaded: { label: 'Downloaded',    className: 'form-status-badge--downloaded' },
  filed:      { label: 'Filed',         className: 'form-status-badge--filed' },
};

export function FormStatusBadge({ status }: FormStatusBadgeProps) {
  const config = STATUS_CONFIG[status];

  return (
    <span className={`form-status-badge ${config.className}`} role="status">
      {config.label}
    </span>
  );
}
