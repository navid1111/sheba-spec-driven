# Testing Auth Endpoints

## Correct Request Format

### 1. Request OTP

**Endpoint:** `POST /auth/request-otp`

**Request Body:**
```json
{
  "phone": "+8801712345678"
}
```

**cURL Command:**
```powershell
curl -X POST http://localhost:8000/auth/request-otp `
  -H "Content-Type: application/json" `
  -d '{\"phone\": \"+8801712345678\"}'
```

**Expected Response (200 OK):**
```json
{
  "message": "OTP sent successfully"
}
```

**Check Server Console** for the OTP code:
```
============================================================
📱 OTP for +8801712345678: 123456
============================================================
```

---

### 2. Verify OTP

**Endpoint:** `POST /auth/verify-otp`

**Request Body:**
```json
{
  "phone": "+8801712345678",
  "code": "123456"
}
```

**cURL Command:**
```powershell
curl -X POST http://localhost:8000/auth/verify-otp `
  -H "Content-Type: application/json" `
  -d '{\"phone\": \"+8801712345678\", \"code\": \"123456\"}'
```

**Expected Response (200 OK):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user_id": "uuid-here",
  "user_type": "CUSTOMER",
  "phone": "+8801712345678"
}
```

---

## Common Errors

### Error 1: Validation Error (422)
```json
{
  "detail": [
    {
      "loc": ["string", 0],
      "msg": "string",
      "type": "string"
    }
  ]
}
```

**Causes:**
- Missing required fields (`phone` or `code`)
- Wrong field names (e.g., `phone_number` instead of `phone`)
- Invalid data types
- `code` not exactly 6 characters

**Solution:** Make sure your JSON matches the exact format above.

---

### Error 2: Invalid Phone Format (400)
```json
{
  "detail": "Invalid phone number format"
}
```

**Cause:** Phone number doesn't match E.164 format (+[country code][number])

**Solution:** Use format `+8801712345678` (Bangladesh) or `+1234567890` for testing.

---

### Error 3: Invalid OTP (401)
```json
{
  "detail": "Invalid or expired OTP code"
}
```

**Causes:**
- Wrong OTP code
- OTP expired (5-minute validity)
- OTP not requested yet

**Solution:** 
1. Request OTP first
2. Copy code from server console
3. Verify within 5 minutes

---

## Using Postman/Insomnia

### Request OTP
```
POST http://localhost:8000/auth/request-otp
Content-Type: application/json

{
  "phone": "+8801712345678"
}
```

### Verify OTP
```
POST http://localhost:8000/auth/verify-otp
Content-Type: application/json

{
  "phone": "+8801712345678",
  "code": "123456"
}
```

---

## Using Python httpx

```python
import httpx

# Request OTP
response = httpx.post(
    "http://localhost:8000/auth/request-otp",
    json={"phone": "+8801712345678"}
)
print(response.json())

# Get OTP from server console, then verify
response = httpx.post(
    "http://localhost:8000/auth/verify-otp",
    json={"phone": "+8801712345678", "code": "123456"}
)
print(response.json())
```

---

## Interactive API Docs

Visit http://localhost:8000/docs for Swagger UI where you can test the endpoints interactively!
