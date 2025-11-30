# Manual Test Flow - Consent & Privacy Service

## Prerequisites
- Service running on http://localhost:8000
- API Key: `local-dev-key`
- Database connected (PostgreSQL or SQLite)

---

## Step-by-Step Test Flow

### 1. Health Check ✅
```bash
GET http://localhost:8000/health
```
**Expected:** `{"status":"healthy"}`

---

### 2. Region Detection ✅
```bash
GET http://localhost:8000/region
```
**Expected:** `{"region":"ROW"}` (or your detected region)

---

### 3. Create a User
```bash
POST http://localhost:8000/users
Headers: X-API-Key: local-dev-key
Body:
{
  "email": "test@example.com",
  "region": "EU"
}
```
**Expected:** 201 Created with user ID

**Save the `id` from response for next steps!**

---

### 4. Grant Consent (Analytics)
```bash
POST http://localhost:8000/consent/grant
Headers: X-API-Key: local-dev-key
Body:
{
  "user_id": "<USER_ID_FROM_STEP_3>",
  "purpose": "analytics",
  "region": "EU"
}
```
**Expected:** 200 OK - Consent granted

---

### 5. Check Decision (Should be ALLOWED)
```bash
GET http://localhost:8000/decision?user_id=<USER_ID>&purpose=analytics
Headers: X-API-Key: local-dev-key
```
**Expected:** 
```json
{
  "allowed": true,
  "reason": "gdpr_granted",
  "policy_snapshot": {...}
}
```

---

### 6. Check Decision Without Consent (Should be DENIED for EU)
```bash
GET http://localhost:8000/decision?user_id=<USER_ID>&purpose=ads
Headers: X-API-Key: local-dev-key
```
**Expected:** 
```json
{
  "allowed": false,
  "reason": "gdpr_requires_grant",
  ...
}
```

---

### 7. Process Event (Analytics - Should be ALLOWED)
```bash
POST http://localhost:8000/events
Headers: X-API-Key: local-dev-key
Body:
{
  "user_id": "<USER_ID>",
  "event_name": "page_view",
  "properties": {"path": "/home"}
}
```
**Expected:** 
```json
{
  "accepted": true,
  "reason": "gdpr_granted"
}
```

---

### 8. Process Event (Ads - Should be BLOCKED)
```bash
POST http://localhost:8000/events
Headers: X-API-Key: local-dev-key
Body:
{
  "user_id": "<USER_ID>",
  "event_name": "ad_click",
  "properties": {"ad_id": "123"}
}
```
**Expected:** 
```json
{
  "accepted": false,
  "reason": "gdpr_requires_grant"
}
```

---

### 9. Get Consent History
```bash
GET http://localhost:8000/consent/history/<USER_ID>
Headers: X-API-Key: local-dev-key
```
**Expected:** Array of consent records

---

### 10. Get Preferences
```bash
GET http://localhost:8000/consent/preferences/<USER_ID>
Headers: X-API-Key: local-dev-key
```
**Expected:** Current preferences for all purposes

---

### 11. Create Export Request (Subject Rights)
```bash
POST http://localhost:8000/subject-requests
Headers: X-API-Key: local-dev-key
Body:
{
  "user_id": "<USER_ID>",
  "request_type": "export"
}
```
**Expected:** 201 Created with `request_id` and `verification_token`

**Save both for next step!**

---

### 12. Process Export Request
```bash
GET http://localhost:8000/subject-requests/<REQUEST_ID>?token=<VERIFICATION_TOKEN>
Headers: X-API-Key: local-dev-key
```
**Expected:** Full export data with history and preferences

---

### 13. Revoke Consent
```bash
POST http://localhost:8000/consent/revoke
Headers: X-API-Key: local-dev-key
Body:
{
  "user_id": "<USER_ID>",
  "purpose": "analytics",
  "region": "EU"
}
```
**Expected:** 200 OK - Consent revoked

---

### 14. Check Decision After Revoke (Should be DENIED)
```bash
GET http://localhost:8000/decision?user_id=<USER_ID>&purpose=analytics
Headers: X-API-Key: local-dev-key
```
**Expected:** `"allowed": false`

---

### 15. Test US Region (CCPA - Default Allow)
```bash
# Create US user
POST http://localhost:8000/users
Headers: X-API-Key: local-dev-key
Body:
{
  "email": "us-test@example.com",
  "region": "US"
}

# Check decision without consent (should be ALLOWED for US)
GET http://localhost:8000/decision?user_id=<US_USER_ID>&purpose=analytics
Headers: X-API-Key: local-dev-key
```
**Expected:** `"allowed": true, "reason": "ccpa_default_allow"`

---

### 16. Admin - View Users
```bash
GET http://localhost:8000/admin/users
Headers: X-API-Key: local-dev-key
```
**Expected:** List of all users

---

### 17. Admin - View Audit Logs
```bash
GET http://localhost:8000/admin/audit
Headers: X-API-Key: local-dev-key
```
**Expected:** List of audit log entries

---

### 18. Admin - View Subject Requests
```bash
GET http://localhost:8000/admin/subject-requests
Headers: X-API-Key: local-dev-key
```
**Expected:** List of subject requests

---

## Using the Interactive API Docs

**Easiest way to test:** Open http://localhost:8000/docs in your browser

1. Click on any endpoint
2. Click "Try it out"
3. Fill in the parameters
4. Click "Execute"
5. See the response

---

## Quick Test with cURL (PowerShell)

```powershell
# Health check
Invoke-WebRequest -Uri "http://localhost:8000/health" -Method GET

# Create user
$headers = @{"X-API-Key" = "local-dev-key"; "Content-Type" = "application/json"}
$body = @{email = "test@example.com"; region = "EU"} | ConvertTo-Json
Invoke-WebRequest -Uri "http://localhost:8000/users" -Method POST -Headers $headers -Body $body
```

---

## What to Verify

✅ **Consent Management:**
- Grant consent works
- Revoke consent works
- History is append-only

✅ **Decision Engine:**
- GDPR (EU): Deny by default, requires explicit grant
- CCPA (US): Allow by default, honors revoke
- Policy snapshots captured

✅ **Event Processing:**
- Events allowed when consent granted
- Events blocked when consent denied
- Audit logs created

✅ **Subject Rights:**
- Export request creates and processes
- Data includes history and preferences
- Verification token works

✅ **Admin:**
- Users list accessible
- Audit logs viewable
- Subject requests viewable

---

## Troubleshooting

**500 Error:** Check database connection (DATABASE_URL in config)
**401 Error:** Check API key (should be `local-dev-key`)
**404 Error:** Check user_id/request_id is valid UUID

