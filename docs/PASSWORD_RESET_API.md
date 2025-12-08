# Password Reset API Documentation

This guide details the API endpoints required to implement the password reset flow in the frontend application.

## Overview

The password reset process consists of two steps:
1.  **Request Reset**: User provides their email. If the account exists, a reset link is sent to their email.
2.  **Confirm Reset**: User clicks the link (which contains a token), enters a new password, and the system updates it.

---

## 1. Request Password Reset

Initiates the password reset process.

-   **Endpoint**: `/api/auth/password-reset/request/`
-   **Method**: `POST`
-   **Authentication**: None required (Public)

### Request Body

```json
{
  "email": "user@example.com"
}
```

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `email` | string | Yes | The email address associated with the user account. |

### Response

**Success (200 OK)**

The API will always return a 200 OK response to prevent email enumeration, even if the email does not exist in the system.

```json
{
  "message": "If an account exists with this email, a password reset link has been sent."
}
```

**Error (400 Bad Request)**

Occurs if the request body is invalid (e.g., missing email field).

```json
{
  "email": [
    "This field is required."
  ]
}
```

---

## 2. Confirm Password Reset

Completes the password reset process using the token received in the email.

-   **Endpoint**: `/api/auth/password-reset/confirm/`
-   **Method**: `POST`
-   **Authentication**: None required (Public)

### Frontend Flow

1.  User clicks the link in their email: `https://[frontend-url]/reset-password/[token]`
2.  Frontend extracts the `token` from the URL.
3.  Frontend presents a form for the user to enter their new password.
4.  Frontend sends the `token` and `new_password` to this endpoint.

### Request Body

```json
{
  "token": "url-safe-token-string-from-email-link",
  "new_password": "NewSecurePassword123!",
  "new_password_confirm": "NewSecurePassword123!"
}
```

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `token` | string | Yes | The token extracted from the reset link URL. |
| `new_password` | string | Yes | The new password. Must meet complexity requirements. |
| `new_password_confirm` | string | Yes | Must match `new_password`. |

### Response

**Success (200 OK)**

```json
{
  "message": "Password reset successfully"
}
```

**Error (400 Bad Request)**

Occurs if the token is invalid/expired or passwords do not match/meet requirements.

```json
{
  "error": "Invalid password reset token"
}
```

OR

```json
{
  "new_password": [
    "New password fields didn't match."
  ]
}
```

OR

```json
{
  "error": "Password reset token has expired"
}
```

---

## Email Configuration

The password reset functionality requires email to be properly configured to send reset links to users.

### Current Configuration

The system is configured to use **Gmail SMTP** for sending emails:

-   **Backend**: `django.core.mail.backends.smtp.EmailBackend`
-   **Host**: `smtp.gmail.com`
-   **Port**: `587`
-   **TLS**: Enabled
-   **From Email**: `alphalogiquetechnologies@gmail.com`

### Email Settings Location

Email configuration is managed through environment variables in `.env.development`:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=alphalogiquetechnologies@gmail.com
EMAIL_HOST_PASSWORD=ejyicakvhwpvkipd
DEFAULT_FROM_EMAIL=alphalogiquetechnologies@gmail.com
EMAIL_TIMEOUT=60
```

> [!NOTE]
> The email configuration has been tested and is working correctly. Password reset emails will be sent successfully.

### Testing Email Functionality

To verify email sending works, run:

```bash
python test-scripts/test_email.py
```

This will attempt to send a test email and display the configuration being used.

---

## Frontend URL Configuration

The password reset link sent in emails uses a configurable frontend URL. This ensures the reset link points to your actual frontend application.

### Configuration

The frontend URL is configured via the `FRONTEND_URL` environment variable in `.env.development`:

```env
FRONTEND_URL=http://localhost:5173
```

### How It Works

When a password reset email is sent, the system generates a reset URL like:

```
http://localhost:5173/reset-password/{token}
```

The frontend should:
1. Extract the `{token}` from the URL path
2. Present a form for the user to enter their new password
3. Send a POST request to `/api/auth/password-reset/confirm/` with the token and new password

### Changing the Frontend URL

To change the frontend URL (e.g., for production or different dev ports):

1. Update `.env.development`:
   ```env
   FRONTEND_URL=http://localhost:YOUR_PORT
   ```

2. Restart the Django development server to pick up the changes

### Default Values

- **Development**: `http://localhost:5173` (Vite default port)
- **Can be overridden** via `FRONTEND_URL` environment variable
- **Production**: Set to your actual frontend domain (e.g., `https://pms.yea.gov.gh`)
