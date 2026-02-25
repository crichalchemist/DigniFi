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
  GenerateForm101Request,
  GenerateForm101Response,
  SessionSummaryResponse,
  DebtorInfo,
  IncomeInfo,
  ExpenseInfo,
  AssetInfo,
  DebtInfo,
  APIError,
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  UserProfile,
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
  details?: Record<string, any>;

  constructor(
    message: string,
    statusCode: number,
    details?: Record<string, any>
  ) {
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
    throw new APIClientError(
      'An unexpected error occurred. Please try again.',
      response.status
    );
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

/**
 * Base fetch wrapper with authentication and error handling.
 * Includes 401 interceptor: on 401, tries token refresh and retries once.
 */
async function apiFetch<T>(
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
  createSession: async (
    data: CreateSessionRequest
  ): Promise<CreateSessionResponse> => {
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
  updateStep: async (
    sessionId: number,
    data: UpdateStepRequest
  ): Promise<UpdateStepResponse> => {
    return apiFetch<UpdateStepResponse>(
      `/intake/sessions/${sessionId}/update_step/`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    );
  },

  /**
   * Complete intake session
   * POST /api/intake/sessions/{id}/complete/
   */
  completeSession: async (sessionId: number): Promise<{ message: string }> => {
    return apiFetch<{ message: string }>(
      `/intake/sessions/${sessionId}/complete/`,
      {
        method: 'POST',
      }
    );
  },

  /**
   * Calculate means test
   * POST /api/intake/sessions/{id}/calculate_means_test/
   */
  calculateMeansTest: async (
    sessionId: number
  ): Promise<CalculateMeansTestResponse> => {
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
  previewForm101: async (sessionId: number): Promise<any> => {
    return apiFetch<any>(`/intake/sessions/${sessionId}/preview_form_101/`);
  },

  /**
   * Get session summary
   * GET /api/intake/sessions/{id}/summary/
   */
  getSessionSummary: async (
    sessionId: number
  ): Promise<SessionSummaryResponse> => {
    return apiFetch<SessionSummaryResponse>(
      `/intake/sessions/${sessionId}/summary/`
    );
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
};

// ============================================================================
// Debtor Info API
// ============================================================================

export const debtorAPI = {
  createOrUpdate: async (
    sessionId: number,
    data: Partial<DebtorInfo>
  ): Promise<DebtorInfo> => {
    try {
      const session = await intakeAPI.getSession(sessionId);
      if (session.debtor_info) {
        return apiFetch<DebtorInfo>(
          `/intake/debtor-info/${session.debtor_info.id}/`,
          {
            method: 'PATCH',
            body: JSON.stringify(data),
          }
        );
      }
    } catch (error) {
      // Fall through to create
    }

    return apiFetch<DebtorInfo>('/intake/debtor-info/', {
      method: 'POST',
      body: JSON.stringify({ ...data, session: sessionId }),
    });
  },
};

// ============================================================================
// Income Info API
// ============================================================================

export const incomeAPI = {
  createOrUpdate: async (
    sessionId: number,
    data: Partial<IncomeInfo>
  ): Promise<IncomeInfo> => {
    try {
      const session = await intakeAPI.getSession(sessionId);
      if (session.income_info) {
        return apiFetch<IncomeInfo>(
          `/intake/income-info/${session.income_info.id}/`,
          {
            method: 'PATCH',
            body: JSON.stringify(data),
          }
        );
      }
    } catch (error) {
      // Fall through to create
    }

    return apiFetch<IncomeInfo>('/intake/income-info/', {
      method: 'POST',
      body: JSON.stringify({ ...data, session: sessionId }),
    });
  },
};

// ============================================================================
// Expense Info API
// ============================================================================

export const expenseAPI = {
  createOrUpdate: async (
    sessionId: number,
    data: Partial<ExpenseInfo>
  ): Promise<ExpenseInfo> => {
    try {
      const session = await intakeAPI.getSession(sessionId);
      if (session.expense_info) {
        return apiFetch<ExpenseInfo>(
          `/intake/expense-info/${session.expense_info.id}/`,
          {
            method: 'PATCH',
            body: JSON.stringify(data),
          }
        );
      }
    } catch (error) {
      // Fall through to create
    }

    return apiFetch<ExpenseInfo>('/intake/expense-info/', {
      method: 'POST',
      body: JSON.stringify({ ...data, session: sessionId }),
    });
  },
};

// ============================================================================
// Assets API
// ============================================================================

export const assetsAPI = {
  create: async (
    sessionId: number,
    data: Partial<AssetInfo>
  ): Promise<AssetInfo> => {
    return apiFetch<AssetInfo>('/intake/assets/', {
      method: 'POST',
      body: JSON.stringify({ ...data, session: sessionId }),
    });
  },

  update: async (
    assetId: number,
    data: Partial<AssetInfo>
  ): Promise<AssetInfo> => {
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
  create: async (
    sessionId: number,
    data: Partial<DebtInfo>
  ): Promise<DebtInfo> => {
    return apiFetch<DebtInfo>('/intake/debts/', {
      method: 'POST',
      body: JSON.stringify({ ...data, session: sessionId }),
    });
  },

  update: async (
    debtId: number,
    data: Partial<DebtInfo>
  ): Promise<DebtInfo> => {
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
// Forms API
// ============================================================================

export const formsAPI = {
  generateForm101: async (
    data: GenerateForm101Request
  ): Promise<GenerateForm101Response> => {
    return apiFetch<GenerateForm101Response>('/forms/generate_form_101/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  markDownloaded: async (formId: number): Promise<{ message: string }> => {
    return apiFetch<{ message: string }>(
      `/forms/${formId}/mark_downloaded/`,
      {
        method: 'POST',
      }
    );
  },

  markFiled: async (formId: number): Promise<{ message: string }> => {
    return apiFetch<{ message: string }>(`/forms/${formId}/mark_filed/`, {
      method: 'POST',
    });
  },
};

// ============================================================================
// Export unified API client
// ============================================================================

export const api = {
  auth: authAPI,
  intake: intakeAPI,
  debtor: debtorAPI,
  income: incomeAPI,
  expense: expenseAPI,
  assets: assetsAPI,
  debts: debtsAPI,
  forms: formsAPI,
};

export default api;
