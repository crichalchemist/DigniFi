# Auth + Landing Page Design

**Date:** 2026-02-24
**Status:** Approved
**Scope:** Backend registration endpoint, frontend auth flow, landing page, protected routes

---

## Architecture

### Routes

```
/              → LandingPage    (public)
/login         → LoginPage      (public)
/register      → RegisterPage   (public)
/intake        → IntakeWizard   (protected)
```

React Router v7 with `<BrowserRouter>`. `ProtectedRoute` wrapper redirects unauthenticated users to `/login`.

### Auth Flow

1. User visits `/` → sees hero + value props + CTAs
2. "Get Started" → `/register`
3. Register form: email, username, password, confirm password, UPL disclaimer checkbox
4. Backend creates user + sets `agreed_to_upl_disclaimer=True` + `upl_disclaimer_agreed_at`
5. Auto-login after registration → JWT tokens → redirect to `/intake`
6. Returning users: `/login` → JWT → `/intake`

### Token Management

- **Access token:** React state (AuthContext) — cleared on tab close
- **Refresh token:** localStorage — survives page reload
- **On mount:** If refresh token exists, silently call `/api/token/refresh/` to restore session
- **On 401:** API client intercepts, attempts token refresh, retries original request once
- **Auth header:** `Authorization: Bearer <access_token>` (JWT standard, not `Token`)

---

## Backend: User Registration Endpoint

### New Files

- `backend/apps/users/serializers.py` — `RegisterSerializer` with password validation
- `backend/apps/users/views.py` — `RegisterView` (single endpoint)
- `backend/apps/users/urls.py` — Wire up register URL

### POST /api/users/register/

**Request:**
```json
{
  "email": "jane@example.com",
  "username": "janedoe",
  "password": "securepass123",
  "agreed_to_upl_disclaimer": true,
  "agreed_to_terms": true
}
```

**Response (201):**
```json
{
  "id": 1,
  "email": "jane@example.com",
  "username": "janedoe",
  "message": "Account created. Please sign in."
}
```

**Validation:**
- Email uniqueness
- Username uniqueness
- Password strength (Django's built-in validators)
- `agreed_to_upl_disclaimer` must be `true` (DB constraint requires it)
- `agreed_to_terms` must be `true`

---

## Frontend: New Files

### `src/context/AuthContext.tsx`

```typescript
interface AuthState {
  user: { id: number; email: string; username: string } | null;
  isAuthenticated: boolean;
  isLoading: boolean;  // true during silent token refresh on mount
}

interface AuthActions {
  login(email: string, password: string): Promise<void>;
  register(data: RegisterRequest): Promise<void>;
  logout(): void;
}
```

- Wraps entire app
- On mount: checks localStorage for refresh token → silent refresh → decode user from JWT
- Exposes `login`, `register`, `logout` actions

### `src/components/auth/ProtectedRoute.tsx`

- If `isLoading` → spinner
- If `!isAuthenticated` → `<Navigate to="/login" />`
- Else → render children

### `src/pages/LandingPage.tsx`

- Hero: "Take the first step toward financial relief"
- 3 value props: Free, Private & Secure, Legal Information (not advice)
- Two CTAs: "Get Started" → `/register`, "Sign In" → `/login`
- Footer: UPL disclaimer

### `src/pages/LoginPage.tsx`

- Email + password using existing `FormField` component
- Trauma-informed errors: "We couldn't find that account" (not "Invalid credentials")
- Loading state on submit
- Link to register

### `src/pages/RegisterPage.tsx`

- Email, username, password, confirm password
- UPL disclaimer checkbox (required) with full disclaimer text
- Terms of service checkbox (required)
- Auto-login after success → redirect to `/intake`
- Link to login

### Modified Files

- `src/api/client.ts` — JWT Bearer auth, 401 refresh interceptor, auth endpoints
- `src/App.tsx` — Add `<BrowserRouter>`, `<AuthProvider>`, route definitions
- `src/styles/global.css` — Landing page + auth page styles

---

## Styling

Desktop-first, consistent with existing wizard aesthetic:
- Same gradient header color scheme (#667eea → #764ba2)
- Centered card layout for login/register forms
- High contrast, WCAG 2.1 AA compliant
- Trauma-informed language throughout

---

## Dependency

Add `react-router-dom` v7 to frontend package.json.

---

## Test Plan

- Backend: Registration endpoint tests (success, duplicate email, missing UPL agreement, weak password)
- Frontend: Component tests deferred to Phase 5 (testing phase)
