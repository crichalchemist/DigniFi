# Authentication & Authorization

## Current Implementation

### JWT-Based Authentication

**Token Types:**
- **Access Token:** Short-lived (15 minutes), used for API requests
- **Refresh Token:** Long-lived (7 days), used to obtain new access tokens

**Storage:**
- **MVP:** localStorage (acceptable for legal clinic internal network)
- **Production:** httpOnly cookies (prevents XSS token theft)

**Token Payload:**
```json
{
  "user_id": 123,
  "username": "user@example.com",
  "exp": 1234567890,
  "iat": 1234567800
}
```

**Security Features:**
- Signed with `SECRET_KEY` (HS256 algorithm)
- Short expiration prevents token replay attacks
- Refresh tokens can be revoked server-side

### Password Security

**Hashing Algorithm:** Argon2 (Django 4.x default)

**Password Requirements (Current):**
- Minimum 8 characters
- Django's built-in validators (common passwords, similarity to username)

**Planned Improvements:**
- zxcvbn strength meter in UI
- Minimum 12 characters
- Require mix of character types (optional, UX consideration)

**Password Reset:**
- Email-based reset link
- Token expires in 1 hour
- One-time use tokens
- Rate limited (5 attempts per hour per email)

### Session Management

**Django Sessions:**
- Backend stores session data (Redis or database)
- Session ID in cookie (httpOnly, Secure, SameSite=Strict)
- Session expiry: 7 days of inactivity

**JWT Refresh Flow:**
1. User logs in → receive access + refresh tokens
2. Access token expires after 15 minutes
3. Frontend automatically uses refresh token to get new access token
4. Refresh token expires after 7 days → user must log in again

## Authorization Patterns

### Permission Classes

**DRF Permission Classes:**
- `IsAuthenticated` - All PII endpoints require authentication
- `IsOwner` - Users can only access their own data

**Example:**
```python
class IntakeSessionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Users can only see their own sessions
        return IntakeSession.objects.filter(user=self.request.user)
```

### Object-Level Permissions

**Pattern:**
- Filter queries by `user=self.request.user`
- Never trust client-provided user IDs
- Always validate ownership in backend

**Preventing IDOR (Insecure Direct Object References):**
- ❌ Unsafe: Accept any session ID, return data
- ✅ Safe: Filter by session ID AND user ownership

## Rate Limiting

### DRF Throttling

**Configuration (base.py):**
```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'auth': '30/minute',  # Login/register endpoints
    }
}
```

**Endpoint-Specific Rates:**
- Authentication: 30 requests/minute (prevents brute force)
- Form generation: 10 requests/hour per session (prevents abuse)
- File downloads: 100 requests/hour (reasonable for legitimate use)

### Account Lockout (Planned)

**Trigger:** 5 failed login attempts within 1 hour

**Lockout Duration:** 30 minutes

**Notification:**
- Email to account owner (suspicious activity alert)
- Log to AuditLog model

**Unlock:**
- Automatic after 30 minutes
- Manual unlock via password reset flow

## Multi-Factor Authentication (Planned)

### Implementation Timeline

**Phase 1 (6 months):** TOTP (Time-Based One-Time Password)
- Google Authenticator, Authy compatible
- Backup codes (10 single-use codes)
- Optional for users, required for admins

**Phase 2 (12 months):** WebAuthn/FIDO2
- Hardware security keys (YubiKey, etc.)
- Biometric authentication (Touch ID, Face ID)
- Phishing-resistant

### User Experience

**Enrollment:**
- Show QR code during account setup
- Scan with authenticator app
- Verify with test code
- Download backup codes (encrypted PDF)

**Login Flow:**
1. Username + password
2. If MFA enabled → prompt for 6-digit code
3. Option to "trust this device" for 30 days

## API Security

### CORS (Cross-Origin Resource Sharing)

**Production Configuration:**
```python
CORS_ALLOWED_ORIGINS = [
    "https://dignifi.org",
    "https://app.dignifi.org",
]
```

**Development:**
```python
CORS_ALLOW_ALL_ORIGINS = True  # Only for localhost
```

### CSRF Protection

**Django Middleware:** Enabled by default

**AJAX Requests:**
- CSRF token in `X-CSRFToken` header
- Token obtained from cookie
- Required for POST/PUT/PATCH/DELETE

**Exempt Endpoints:**
- JWT authentication endpoints (stateless, no CSRF needed)
- Explicitly marked with `@csrf_exempt` decorator

### Security Headers

**Recommended Headers (add to middleware):**
```python
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
```

**Content Security Policy (CSP):**
```
default-src 'self';
script-src 'self' 'unsafe-inline';
style-src 'self' 'unsafe-inline';
img-src 'self' data:;
```

## Authentication Bypass Prevention

### Common Pitfalls

**1. Client-Side Checks Only**
- ❌ Unsafe: Hide UI elements based on client state
- ✅ Safe: Always validate on server with permission_classes

**2. Trusting Client-Provided User IDs**
- ❌ Unsafe: `/api/users/{user_id}/` returns any user's data
- ✅ Safe: Filter by `request.user`, ignore client user_id

**3. Missing Permission Checks**
- ❌ Unsafe: Forget permission_classes on viewset
- ✅ Safe: Default to `IsAuthenticated`, add to all viewsets

**4. JWT Secret Exposure**
- ❌ Unsafe: Hardcode SECRET_KEY in settings.py
- ✅ Safe: Load from environment variable

**5. Token Leakage in Logs**
- ❌ Unsafe: Log full Authorization header
- ✅ Safe: Redact tokens in logging middleware

## Session Security

### Session Fixation Prevention

**Django Built-In Protection:**
- New session ID generated on login
- Old session invalidated
- `django.contrib.sessions.middleware.SessionMiddleware`

### Session Hijacking Prevention

**Cookie Flags:**
- `HttpOnly` - JavaScript cannot read cookie
- `Secure` - Only sent over HTTPS
- `SameSite=Strict` - Prevents CSRF

**Additional Protections:**
- Bind session to IP address (optional, breaks mobile switching)
- Rotate session ID periodically
- Log out all devices (revoke all sessions)

### Concurrent Sessions

**Current:** Allow multiple sessions per user

**Planned:** Configurable limit (e.g., max 3 devices)
- Track device fingerprint (user agent, IP)
- Show "active sessions" in user settings
- Allow revocation of specific sessions

## Security Testing

### Authentication Tests

**Test Cases:**
- Unauthenticated requests return 401
- Expired tokens return 401
- Invalid tokens return 401
- Refresh token rotation works
- CSRF protection works for state-changing requests
- Rate limiting blocks excessive attempts

**Example Test:**
```python
def test_unauthenticated_access_denied(api_client):
    response = api_client.get('/api/intake/sessions/')
    assert response.status_code == 401
```

### Authorization Tests

**Test Cases:**
- Users cannot access other users' data
- Permission classes enforced on all viewsets
- Object-level permissions validated
- Admin-only endpoints reject non-admin users

---

**Last Updated:** March 2026
