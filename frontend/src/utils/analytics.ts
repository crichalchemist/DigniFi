/**
 * Analytics event tracking via the existing AuditLog API.
 *
 * Fire-and-forget — analytics should never block the UI or throw.
 * Events are posted to /api/audit/logs/ and stored alongside
 * existing audit records for unified reporting.
 */

import { getAccessToken } from '../api/client';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

/**
 * Track a user event via the audit log API.
 * Silent on failure — analytics must never degrade the user experience.
 */
export function trackEvent(
  action: string,
  details: Record<string, unknown> = {},
  resourceType = 'analytics',
  resourceId?: number,
): void {
  const payload = {
    action,
    resource_type: resourceType,
    resource_id: resourceId ?? null,
    details: { ...details, timestamp: new Date().toISOString() },
  };

  if (import.meta.env.DEV) {
    console.debug('[analytics]', action, details);
  }

  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  const token = getAccessToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Fire and forget — POST to audit log, swallow errors
  fetch(`${API_BASE}/audit/logs/`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  }).catch(() => {
    // Silent — analytics should never break the app
  });
}
