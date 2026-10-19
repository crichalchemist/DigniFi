# Deployment Security

> **Status (2026-10-15):** Production runs on Heroku: `heroku.yml` builds the image from `Dockerfile.heroku`, gunicorn serves Django and whitenoise serves the static files, and the release phase runs `python manage.py migrate`. Heroku runs the `prod` branch; a deploy fast-forwards `prod` to `main`, then runs `git push heroku prod:main`, and only the owner deploys. The Nginx, certbot, UFW, AWS security group, PostgreSQL hardening and cron backup sections describe a self-hosted server, not production.

## Production Readiness Checklist

Before deploying to production, complete this checklist:

### Application Configuration

- [ ] `DEBUG=False` in Django settings
- [ ] Unique `SECRET_KEY` (not the default or dev key)
- [ ] `ALLOWED_HOSTS` configured (not "\*")
- [ ] HTTPS enforced (redirect HTTP → HTTPS)
- [ ] Database credentials rotated from defaults
- [ ] File upload limits enforced (10MB max)
- [ ] CORS configured (not allow-all origins)
- [ ] Security headers enabled (HSTS, CSP, X-Content-Type-Options)
- [ ] Error pages don't expose stack traces
- [ ] Admin interface disabled or behind strong auth
- [ ] Logging configured (errors, security events)
- [ ] Monitoring and alerting enabled

### Infrastructure

- [ ] Firewall rules: Only 80/443 exposed
- [ ] SSH keys only (no password auth)
- [ ] OS security updates enabled
- [ ] Database backups configured (encrypted)
- [ ] Backup restore tested
- [ ] SSL certificate valid and auto-renewing
- [ ] CDN configured (if serving static assets)
- [ ] Rate limiting at application and infrastructure level

### Security

- [ ] Field-level encryption enabled
- [ ] Encryption keys in secret manager (not .env file)
- [ ] Audit logging enabled
- [ ] SIEM integration (if available)
- [ ] Intrusion detection configured
- [ ] DDoS protection enabled
- [ ] WAF configured (if available)

### Forms step 3: before deploying

- [ ] Run `python manage.py loaddata ilnd_2025_data` right after the release: the districts migration 0003 ends production's existing median row on 2026-03-31.
- [ ] Reseed the personas with `python manage.py seed_demo_data --reset`.
- [ ] Count the completed sessions that still hold a draft debt: their forms now leave it off.
- [ ] Run `python manage.py time_packet --session <id> --budget-generate 15 --budget-download 15` on the Eco dyno for one persona's session. It times Generate All and each download and writes nothing; a missed budget fails the command and names it.

## Django Settings for Production

### Security Settings

```python
# backend/config/settings/production.py

# Never enable debug in production
DEBUG = False

# Strong secret key from environment
SECRET_KEY = env("DJANGO_SECRET_KEY", default="")  # base.py; raises only when empty and DEBUG is off

# Restrict allowed hosts
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# HTTPS enforcement
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookie security
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# Content security
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# File upload limits: none enforced yet (DOCUMENT_UPLOAD_MAX_SIZE in base.py is unused)
```

### Database Configuration

```python
DATABASES = {"default": env.db("DATABASE_URL", default="postgres://dignifi:dignifi@localhost:5432/dignifi_dev")}  # base.py; production.py sets CONN_MAX_AGE from DATABASE_CONN_MAX_AGE (default 600)
```

### Logging Configuration

Production uses base.py's `LOGGING`: JSON lines to the console (Heroku logs), and the `dignifi.audit` and `dignifi.upl` loggers also write `logs/audit.log`.

## Web Server Configuration

### Nginx (Recommended)

```nginx
# /etc/nginx/sites-available/dignifi.org

server {
    listen 80;
    server_name dignifi.org www.dignifi.org;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name dignifi.org www.dignifi.org;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/dignifi.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dignifi.org/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.3 TLSv1.2;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Content Security Policy
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'none';" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=30r/m;
    limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/h;

    # Static files
    location /static/ {
        alias /var/www/dignifi/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Media files (uploaded documents) — never served directly; generated forms stream from Django
    location /media/ {
        alias /var/www/dignifi/media/;
        internal;  # Only accessible via X-Accel-Redirect from Django
    }

    # API endpoints
    location /api/ {
        limit_req zone=api burst=5 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Login and token refresh (stricter rate limit; /api/users/register/ and /api/users/demo/ need the same)
    location /api/token/ {
        limit_req zone=auth burst=2 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Frontend (React SPA)
    location / {
        root /var/www/dignifi/frontend/dist;
        try_files $uri $uri/ /index.html;
    }
}
```

### SSL/TLS Configuration

**Let's Encrypt (Free Certificates):**

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Generate certificate
sudo certbot --nginx -d dignifi.org -d www.dignifi.org

# Auto-renewal (runs twice daily)
sudo systemctl enable certbot.timer
```

**SSL Test:**

- Test with https://www.ssllabs.com/ssltest/
- Target: A+ rating

## Firewall Configuration

### UFW (Ubuntu)

```bash
# Default deny
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (change port if using non-standard)
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable
```

### AWS Security Groups

```yaml
# Inbound rules
- Port 22 (SSH): Your IP only
- Port 80 (HTTP): 0.0.0.0/0
- Port 443 (HTTPS): 0.0.0.0/0
- Port 5432 (PostgreSQL): Private subnet only

# Outbound rules
- All traffic: 0.0.0.0/0 (for updates, API calls)
```

## Database Security

### PostgreSQL Hardening

```sql
-- Create application user with limited privileges
CREATE USER dignifi_app WITH PASSWORD 'strong-random-password';

-- Grant only necessary privileges
GRANT CONNECT ON DATABASE dignifi TO dignifi_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO dignifi_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO dignifi_app;

-- Revoke dangerous privileges
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON pg_database FROM PUBLIC;
```

**PostgreSQL Configuration (postgresql.conf):**

```ini
# Network
listen_addresses = 'localhost'  # Or private IP
port = 5432

# SSL
ssl = on
ssl_cert_file = '/etc/postgresql/ssl/server.crt'
ssl_key_file = '/etc/postgresql/ssl/server.key'

# Logging
log_connections = on
log_disconnections = on
log_duration = on
log_statement = 'all'
```

**Authentication (pg_hba.conf):**

```
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             postgres                                peer
host    dignifi         dignifi_app     127.0.0.1/32            scram-sha-256
host    dignifi         dignifi_app     10.0.0.0/8              scram-sha-256
```

## Monitoring & Alerting

### Application Monitoring

**Sentry (Error Tracking):**

```python
# backend/config/settings/production.py
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:  # optional; without a DSN, Sentry stays off
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0),
        send_default_pii=False,  # Don't send PII to Sentry
        include_local_variables=False,
        max_request_body_size="never",
    )
```

**Health Check Endpoint:**

```python
# backend/config/views.py  (/health/ and /health/detailed/)
from django.http import JsonResponse
from django.db import connection

def health_check(request):
    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse({'status': 'error', 'database': 'error'})  # HTTP 200 even when the database is down

    return JsonResponse({'status': 'ok', 'database': 'ok'})
```

### Security Monitoring

**Log Monitoring:**

- Failed authentication attempts
- Unusual API access patterns
- High error rates
- Slow queries (potential DoS)

**Alerting Rules:**

- > 10 failed logins from same IP in 1 hour
- > 100 4xx errors in 5 minutes
- > 10 5xx errors in 1 minute
- Database CPU > 80% for 5 minutes
- Disk space < 10% free

### Uptime Monitoring

**Services:**

- UptimeRobot (free tier available)
- Pingdom
- StatusCake

**Monitor:**

- HTTPS endpoint (every 1 minute)
- Health check endpoint
- API response time
- SSL certificate expiration

## Backup & Disaster Recovery

### Database Backups

**Automated Backups (cron):**

```bash
#!/bin/bash
# /usr/local/bin/backup-db.sh

BACKUP_DIR="/var/backups/dignifi"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="dignifi_${TIMESTAMP}.sql.gz"

# Dump database
pg_dump -U postgres dignifi | gzip > "${BACKUP_DIR}/${BACKUP_FILE}"

# Encrypt backup
gpg --encrypt --recipient admin@dignifi.org "${BACKUP_DIR}/${BACKUP_FILE}"

# Upload to S3 (or other secure storage)
aws s3 cp "${BACKUP_DIR}/${BACKUP_FILE}.gpg" s3://dignifi-backups/

# Delete local backup (keep encrypted version in S3)
rm "${BACKUP_DIR}/${BACKUP_FILE}"

# Delete backups older than 30 days
find "${BACKUP_DIR}" -name "*.gpg" -mtime +30 -delete
```

**Crontab:**

```cron
# Daily backup at 2 AM
0 2 * * * /usr/local/bin/backup-db.sh
```

### Backup Testing

**Quarterly Restore Drill:**

1. Download latest backup from S3
2. Decrypt backup
3. Restore to test database
4. Verify data integrity
5. Document restore time and any issues

## Incident Response

### Incident Severity Levels

**P0 (Critical) - Respond Immediately:**

- Data breach (PII exposed)
- Total service outage
- Authentication bypass
- Active attack in progress

**P1 (High) - Respond Within 1 Hour:**

- Partial service outage
- Security vulnerability confirmed
- Data corruption detected

**P2 (Medium) - Respond Within 4 Hours:**

- Performance degradation
- Non-critical errors
- Suspicious activity detected

**P3 (Low) - Respond Within 1 Business Day:**

- Minor bugs
- Optimization opportunities
- General inquiries

### Incident Response Playbook

**1. Detection & Triage (0-15 minutes):**

- Confirm incident is real (not false alarm)
- Classify severity
- Notify incident commander
- Create incident ticket

**2. Containment (15-60 minutes):**

- Isolate affected systems
- Stop the bleeding (prevent further damage)
- Preserve evidence (logs, snapshots)
- Block malicious actors (IP bans, etc.)

**3. Investigation (1-4 hours):**

- Determine root cause
- Identify scope of impact
- Check for data exfiltration
- Review audit logs

**4. Remediation (4-24 hours):**

- Fix vulnerability
- Restore service
- Patch systems
- Verify fix works

**5. Communication (24-72 hours):**

- Notify affected users
- Public disclosure (if applicable)
- Report to authorities (if required)
- Document incident

**6. Post-Mortem (1 week):**

- Write incident report
- Update runbooks
- Implement preventive measures
- Share lessons learned with team

---

**Last Updated:** March 2026
