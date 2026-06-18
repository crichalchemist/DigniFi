/**
 * API Client for DigniFi Backend
 *
 * Provides type-safe methods for interacting with Django REST Framework API.
 * Handles authentication, error handling, and request/response transformation.
 *
 * Security: access token stored in memory (not localStorage) to prevent XSS
 * exfiltration. Refresh token in localStorage for persistence across reloads.
 */

import type {
  IntakeSession,
  CreateSessionRequest,
  CreateSessionResponse,
  UpdateStepRequest,
  UpdateStepResponse,
  CalculateMeansTestResponse,
  GenerateFormRequest,
  GenerateFormResponse,
  GenerateAllFormsResponse,
  SessionSummaryResponse,
  AssetInfo,
  DebtInfo,
  GeneratedForm,
  APIError,
  LoginRequest,
  LoginResponse,
  DemoLoginResponse,
  RegisterRequest,
  RegisterResponse,
  UserProfile,
  FormType,
  UploadedDocument,
  DocumentUploadResponse,
  OCRResult,
  SOFAReport,
  FormUISpec,
  AnswerPayload,
} from '../types/api';

// ============================================================================
// Configuration
// ============================================================================

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// ============================================================================
// Token Management (memory-based for access, localStorage for refresh)
// ============================================================================

let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function getRefreshToken(): string | null {
  return localStorage.getItem('refresh_token');
}

export function setRefreshToken(token: string | null): void {
  if (token) {
    localStorage.setItem('refresh_token', token);
  } else {
    localStorage.removeItem('refresh_token');
  }
}

export function clearTokens(): void {
  accessToken = null;
  localStorage.removeItem('refresh_token');
}

// ============================================================================
// Error Handling
// ============================================================================

export class APIClientError extends Error {
  statusCode: number;
  details?: Record<string, unknown>;

  constructor(message: string, statusCode: number, details?: Record<string, unknown>) {
    super(message);
    this.name = 'APIClientError';
    this.statusCode = statusCode;
    this.details = details;
  }
}

/**
 * Parse API error response and throw typed error
 */
async function handleAPIError(response: Response): Promise<never> {
  let errorData: APIError;

  try {
    errorData = await response.json();
  } catch {
    throw new APIClientError('An unexpected error occurred. Please try again.', response.status);
  }

  throw new APIClientError(
    errorData.message || errorData.error || 'Request failed',
    response.status,
    errorData.details
  );
}

// ============================================================================
// HTTP Client
// ============================================================================

/** Flag to prevent concurrent refresh attempts */
let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

/**
 * Attempt to refresh the access token using the stored refresh token.
 * Returns true if refresh succeeded, false otherwise.
 */
async function attemptTokenRefresh(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) return false;

  try {
    const response = await fetch(`${API_BASE_URL}/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    });

    if (!response.ok) {
      clearTokens();
      return false;
    }

    const data = await response.json();
    setAccessToken(data.access);
    return true;
  } catch {
    clearTokens();
    return false;
  }
}

import { withRetry } from '../utils/retry';

/**
 * Single-attempt fetch with authentication and error handling.
 * Includes 401 interceptor: on 401, tries token refresh and retries once.
 */
async function apiFetchOnce<T>(
  endpoint: string,
  options: RequestInit = {},
  skipAuth = false
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (!skipAuth && accessToken) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${accessToken}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  // 401 interceptor: try refresh, retry once
  if (response.status === 401 && !skipAuth && getRefreshToken()) {
    if (!isRefreshing) {
      isRefreshing = true;
      refreshPromise = attemptTokenRefresh().finally(() => {
        isRefreshing = false;
        refreshPromise = null;
      });
    }

    const refreshed = await (refreshPromise ?? attemptTokenRefresh());
    if (refreshed) {
      // Retry with new token
      const retryHeaders: HeadersInit = {
        'Content-Type': 'application/json',
        ...options.headers,
      };
      if (accessToken) {
        (retryHeaders as Record<string, string>)['Authorization'] = `Bearer ${accessToken}`;
      }

      const retryResponse = await fetch(url, { ...options, headers: retryHeaders });
      if (!retryResponse.ok) {
        await handleAPIError(retryResponse);
      }
      if (retryResponse.status === 204) return {} as T;
      return retryResponse.json();
    }
  }

  if (!response.ok) {
    await handleAPIError(response);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

/**
 * Retry-wrapped fetch: retries up to 3 times on 5xx errors with exponential backoff.
 * 4xx errors (client errors) are never retried.
 */
async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {},
  skipAuth = false
): Promise<T> {
  return withRetry(() => apiFetchOnce<T>(endpoint, options, skipAuth));
}

// ============================================================================
// Auth API
// ============================================================================

export const authAPI = {
  /**
   * Obtain JWT token pair
   * POST /api/token/obtain/
   */
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const response = await apiFetch<LoginResponse>(
      '/token/obtain/',
      { method: 'POST', body: JSON.stringify(data) },
      true
    );
    setAccessToken(response.access);
    setRefreshToken(response.refresh);
    return response;
  },

  /**
   * Issue JWT tokens for the pre-seeded demo account (no credentials needed).
   * POST /api/users/demo/
   */
  demoLogin: async (): Promise<DemoLoginResponse> => {
    const response = await apiFetch<DemoLoginResponse>('/users/demo/', { method: 'POST' }, true);
    setAccessToken(response.access);
    setRefreshToken(response.refresh);
    return response;
  },

  /**
   * Refresh access token
   * POST /api/token/refresh/
   */
  refresh: async (): Promise<boolean> => {
    return attemptTokenRefresh();
  },

  /**
   * Register a new user
   * POST /api/users/register/
   */
  register: async (data: RegisterRequest): Promise<RegisterResponse> => {
    return apiFetch<RegisterResponse>(
      '/users/register/',
      { method: 'POST', body: JSON.stringify(data) },
      true
    );
  },

  /**
   * Get current user profile
   * GET /api/users/me/
   */
  me: async (): Promise<UserProfile> => {
    return apiFetch<UserProfile>('/users/me/');
  },

  /**
   * Clear tokens and reset auth state
   */
  logout: (): void => {
    clearTokens();
  },
};

// ============================================================================
// Intake Session API
// ============================================================================

export const intakeAPI = {
  /**
   * Create a new intake session
   * POST /api/intake/sessions/
   */
  createSession: async (data: CreateSessionRequest): Promise<CreateSessionResponse> => {
    return apiFetch<CreateSessionResponse>('/intake/sessions/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Get intake session by ID
   * GET /api/intake/sessions/{id}/
   */
  getSession: async (sessionId: number): Promise<IntakeSession> => {
    return apiFetch<IntakeSession>(`/intake/sessions/${sessionId}/`);
  },

  /**
   * Update wizard step
   * POST /api/intake/sessions/{id}/update_step/
   */
  updateStep: async (sessionId: number, data: UpdateStepRequest): Promise<UpdateStepResponse> => {
    return apiFetch<UpdateStepResponse>(`/intake/sessions/${sessionId}/update_step/`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Complete intake session
   * POST /api/intake/sessions/{id}/complete/
   */
  completeSession: async (sessionId: number): Promise<{ message: string }> => {
    return apiFetch<{ message: string }>(`/intake/sessions/${sessionId}/complete/`, {
      method: 'POST',
    });
  },

  /**
   * Calculate means test
   * POST /api/intake/sessions/{id}/calculate_means_test/
   */
  calculateMeansTest: async (sessionId: number): Promise<CalculateMeansTestResponse> => {
    return apiFetch<CalculateMeansTestResponse>(
      `/intake/sessions/${sessionId}/calculate_means_test/`,
      {
        method: 'POST',
      }
    );
  },

  /**
   * Preview Form 101
   * GET /api/intake/sessions/{id}/preview_form_101/
   */
  previewForm101: async (sessionId: number): Promise<unknown> => {
    return apiFetch<unknown>(`/intake/sessions/${sessionId}/preview_form_101/`);
  },

  /**
   * Get session summary
   * GET /api/intake/sessions/{id}/summary/
   */
  getSessionSummary: async (sessionId: number): Promise<SessionSummaryResponse> => {
    return apiFetch<SessionSummaryResponse>(`/intake/sessions/${sessionId}/summary/`);
  },

  /**
   * Update partial session data
   * PATCH /api/intake/sessions/{id}/
   */
  updateSession: async (
    sessionId: number,
    data: Partial<IntakeSession>
  ): Promise<IntakeSession> => {
    return apiFetch<IntakeSession>(`/intake/sessions/${sessionId}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  // Contracts (Schedule G)
  contracts: async (sessionId: number): Promise<unknown[]> => {
    return apiFetch<unknown[]>(`/intake/sessions/${sessionId}/contracts/`);
  },
  createContract: async (sessionId: number, data: unknown): Promise<unknown> => {
    return apiFetch<unknown>(`/intake/sessions/${sessionId}/contracts/`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  deleteContract: async (sessionId: number, contractId: number): Promise<void> => {
    await apiFetch<void>(`/intake/sessions/${sessionId}/contracts/${contractId}/`, {
      method: 'DELETE',
    });
  },

  // Codebtors (Schedule H)
  codebtors: async (sessionId: number): Promise<unknown[]> => {
    return apiFetch<unknown[]>(`/intake/sessions/${sessionId}/codebtors/`);
  },
  createCodebtor: async (sessionId: number, data: unknown): Promise<unknown> => {
    return apiFetch<unknown>(`/intake/sessions/${sessionId}/codebtors/`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  deleteCodebtor: async (sessionId: number, codebtorId: number): Promise<void> => {
    await apiFetch<void>(`/intake/sessions/${sessionId}/codebtors/${codebtorId}/`, {
      method: 'DELETE',
    });
  },
};

// ============================================================================
// Assets API
// ============================================================================

export const assetsAPI = {
  create: async (sessionId: number, data: Partial<AssetInfo>): Promise<AssetInfo> => {
    return apiFetch<AssetInfo>('/intake/assets/', {
      method: 'POST',
      body: JSON.stringify({ ...data, session: sessionId }),
    });
  },

  update: async (assetId: number, data: Partial<AssetInfo>): Promise<AssetInfo> => {
    return apiFetch<AssetInfo>(`/intake/assets/${assetId}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  delete: async (assetId: number): Promise<void> => {
    return apiFetch<void>(`/intake/assets/${assetId}/`, {
      method: 'DELETE',
    });
  },
};

// ============================================================================
// Debts API
// ============================================================================

export const debtsAPI = {
  create: async (sessionId: number, data: Partial<DebtInfo>): Promise<DebtInfo> => {
    return apiFetch<DebtInfo>('/intake/debts/', {
      method: 'POST',
      body: JSON.stringify({ ...data, session: sessionId }),
    });
  },

  update: async (debtId: number, data: Partial<DebtInfo>): Promise<DebtInfo> => {
    return apiFetch<DebtInfo>(`/intake/debts/${debtId}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  delete: async (debtId: number): Promise<void> => {
    return apiFetch<void>(`/intake/debts/${debtId}/`, {
      method: 'DELETE',
    });
  },
};

// ============================================================================
// Fee Waiver API
// ============================================================================

export interface FeeWaiverPayload {
  session: number;
  household_size: number;
  monthly_income: string;
  monthly_expenses: string;
  receives_public_benefits: boolean;
  benefit_types: string[];
  cannot_pay_full: boolean;
  cannot_pay_installments: boolean;
}

export interface FeeWaiverApplication {
  id: number;
  session: number;
  household_size: number;
  monthly_income: string;
  monthly_expenses: string;
  receives_public_benefits: boolean;
  benefit_types: string[];
  cannot_pay_full: boolean;
  cannot_pay_installments: boolean;
  status: 'pending' | 'approved' | 'denied';
  created_at: string;
  updated_at: string;
}

export const feeWaiverAPI = {
  create: async (data: FeeWaiverPayload): Promise<FeeWaiverApplication> => {
    return apiFetch<FeeWaiverApplication>('/intake/fee-waiver/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};

// ============================================================================
// Forms API
// ============================================================================

export const formsAPI = {
  /**
   * Generate a single form by type
   * POST /api/forms/generate/
   */
  generate: async (sessionId: number, formType: FormType): Promise<GenerateFormResponse> => {
    return apiFetch<GenerateFormResponse>('/forms/generate/', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, form_type: formType }),
    });
  },

  /**
   * Generate all 13 forms atomically
   * POST /api/forms/generate_all/
   */
  generateAll: async (sessionId: number): Promise<GenerateAllFormsResponse> => {
    return apiFetch<GenerateAllFormsResponse>('/forms/generate_all/', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId }),
    });
  },

  /**
   * Preview form data without generating
   * GET /api/forms/{id}/preview/
   */
  preview: async (formId: number): Promise<GeneratedForm> => {
    return apiFetch<GeneratedForm>(`/forms/${formId}/preview/`);
  },

  /**
   * List all generated forms for a session
   * GET /api/forms/?session={sessionId}
   */
  listBySession: async (sessionId: number): Promise<GeneratedForm[]> => {
    const response = await apiFetch<GeneratedForm[] | { results: GeneratedForm[] }>(
      `/forms/?session=${sessionId}`
    );
    // Handle both paginated ({results: [...]}) and unpaginated ([...]) responses
    return Array.isArray(response) ? response : (response.results ?? []);
  },

  /** @deprecated Use generate() with form_type */
  generateForm101: async (data: GenerateFormRequest): Promise<GenerateFormResponse> => {
    return apiFetch<GenerateFormResponse>('/forms/generate_form_101/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  markDownloaded: async (formId: number): Promise<{ message: string }> => {
    return apiFetch<{ message: string }>(`/forms/${formId}/mark_downloaded/`, {
      method: 'POST',
    });
  },

  markFiled: async (formId: number): Promise<{ message: string }> => {
    return apiFetch<{ message: string }>(`/forms/${formId}/mark_filed/`, {
      method: 'POST',
    });
  },

  /**
   * Download a generated form as a filled PDF.
   * GET /api/forms/{id}/download/
   * Triggers a browser file save dialog.
   */
  downloadForm: async (formId: number, filename: string): Promise<void> => {
    const doFetch = () => {
      const token = getAccessToken();
      return fetch(`${API_BASE_URL}/forms/${formId}/download/`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
    };
    let response = await doFetch();
    if (response.status === 401 && getRefreshToken()) {
      const refreshed = await attemptTokenRefresh();
      if (refreshed) response = await doFetch();
    }
    if (!response.ok) {
      throw new APIClientError(`Download failed (${response.status})`, response.status);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },
};

// ============================================================================
// Document Scanning API
// ============================================================================

export async function uploadDocument(
  sessionId: number,
  file: File,
  documentType: string
): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('document_type', documentType);
  formData.append('session_id', String(sessionId));

  const token = getAccessToken();
  const res = await fetch(`${API_BASE_URL}/documents/upload/`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json();
}

export async function pollDocument(id: number): Promise<UploadedDocument> {
  return apiFetch<UploadedDocument>(`/documents/${id}/`);
}

export async function listDocuments(sessionId: number): Promise<UploadedDocument[]> {
  return apiFetch<UploadedDocument[]>(`/documents/?session_id=${sessionId}`);
}

export async function validateDocument(
  id: number,
  fields: Record<string, unknown>
): Promise<OCRResult> {
  return apiFetch<OCRResult>(`/documents/${id}/validate/`, {
    method: 'POST',
    body: JSON.stringify({ fields }),
  });
}

// ============================================================================
// Export unified API client
// ============================================================================

// ============================================================================
// SOFA Report API
// ============================================================================

export const sofaReportAPI = {
  /**
   * Get SOFA report for a session (GET /api/intake/sofa-report/{sessionId}/)
   * Creates an empty report if none exists.
   */
  get: async (sessionId: number): Promise<SOFAReport> => {
    return apiFetch<SOFAReport>(`/intake/sofa-report/${sessionId}/`);
  },

  /**
   * Update SOFA report booleans and/or nested rows (PATCH /api/intake/sofa-report/{sessionId}/)
   */
  patch: async (sessionId: number, data: Partial<SOFAReport>): Promise<SOFAReport> => {
    return apiFetch<SOFAReport>(`/intake/sofa-report/${sessionId}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },
};

// ============================================================================
// SP4: Ask-Modules API
// ============================================================================

export const askModulesAPI = {
  getUISpec: async (formType: string): Promise<FormUISpec> => {
    return apiFetch<FormUISpec>(`/forms/schema/${formType}/ui-spec/`);
  },

  bulkUpsertAnswers: async (
    sessionId: number,
    answers: AnswerPayload[]
  ): Promise<{ status: string; created: number; updated: number }> => {
    return apiFetch(`/intake/sessions/${sessionId}/answers/bulk/`, {
      method: 'POST',
      body: JSON.stringify({ answers }),
    });
  },
};

export const api = {
  auth: authAPI,
  intake: intakeAPI,
  assets: assetsAPI,
  debts: debtsAPI,
  forms: formsAPI,
  feeWaiver: feeWaiverAPI,
  sofaReport: sofaReportAPI,
  askModules: askModulesAPI,
};

export default api;
