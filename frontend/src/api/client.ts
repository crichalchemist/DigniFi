/**
 * API Client for DigniFi Backend
 *
 * Provides type-safe methods for interacting with Django REST Framework API.
 * Handles authentication, error handling, and request/response transformation.
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
} from '../types/api';

// ============================================================================
// Configuration
// ============================================================================

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// ============================================================================
// Error Handling
// ============================================================================

export class APIClientError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public details?: Record<string, any>
  ) {
    super(message);
    this.name = 'APIClientError';
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

/**
 * Base fetch wrapper with authentication and error handling
 */
async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  // Get auth token from localStorage (set during login)
  const token = localStorage.getItem('auth_token');

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Token ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

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
  /**
   * Create or update debtor info for session
   */
  createOrUpdate: async (
    sessionId: number,
    data: Partial<DebtorInfo>
  ): Promise<DebtorInfo> => {
    // Check if debtor_info exists for this session
    try {
      const session = await intakeAPI.getSession(sessionId);
      if (session.debtor_info) {
        // Update existing
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

    // Create new
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
  /**
   * Create or update income info for session
   */
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
  /**
   * Create or update expense info for session
   */
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
  /**
   * Create asset
   */
  create: async (
    sessionId: number,
    data: Partial<AssetInfo>
  ): Promise<AssetInfo> => {
    return apiFetch<AssetInfo>('/intake/assets/', {
      method: 'POST',
      body: JSON.stringify({ ...data, session: sessionId }),
    });
  },

  /**
   * Update asset
   */
  update: async (
    assetId: number,
    data: Partial<AssetInfo>
  ): Promise<AssetInfo> => {
    return apiFetch<AssetInfo>(`/intake/assets/${assetId}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  /**
   * Delete asset
   */
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
  /**
   * Create debt
   */
  create: async (
    sessionId: number,
    data: Partial<DebtInfo>
  ): Promise<DebtInfo> => {
    return apiFetch<DebtInfo>('/intake/debts/', {
      method: 'POST',
      body: JSON.stringify({ ...data, session: sessionId }),
    });
  },

  /**
   * Update debt
   */
  update: async (
    debtId: number,
    data: Partial<DebtInfo>
  ): Promise<DebtInfo> => {
    return apiFetch<DebtInfo>(`/intake/debts/${debtId}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  /**
   * Delete debt
   */
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
  /**
   * Generate Form 101 (Voluntary Petition)
   * POST /api/forms/generate_form_101/
   */
  generateForm101: async (
    data: GenerateForm101Request
  ): Promise<GenerateForm101Response> => {
    return apiFetch<GenerateForm101Response>('/forms/generate_form_101/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Mark form as downloaded
   * POST /api/forms/{id}/mark_downloaded/
   */
  markDownloaded: async (formId: number): Promise<{ message: string }> => {
    return apiFetch<{ message: string }>(
      `/forms/${formId}/mark_downloaded/`,
      {
        method: 'POST',
      }
    );
  },

  /**
   * Mark form as filed
   * POST /api/forms/{id}/mark_filed/
   */
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
  intake: intakeAPI,
  debtor: debtorAPI,
  income: incomeAPI,
  expense: expenseAPI,
  assets: assetsAPI,
  debts: debtsAPI,
  forms: formsAPI,
};

export default api;
