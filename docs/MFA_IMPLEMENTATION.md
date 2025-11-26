# Multi-Factor Authentication (MFA) System

## Overview

The PMS platform includes a comprehensive Multi-Factor Authentication (MFA) system that provides enhanced security for user accounts through multiple verification methods.

## Features

### Supported MFA Methods

1. **TOTP (Time-based One-Time Password)**
   - Authenticator apps: Google Authenticator, Microsoft Authenticator, Authy
   - 6-digit codes that rotate every 30 seconds
   - Most secure option (offline, app-based)

2. **SMS Verification**
   - 6-digit codes sent via SMS
   - Valid for 10 minutes
   - Maximum 5 attempts per code

3. **Backup Codes**
   - 10 single-use recovery codes
   - Format: XXXX-XXXX
   - Used when primary method unavailable

### Additional Features

- **Trusted Devices**: Remember devices for 30 days (configurable)
- **Multiple Methods**: Users can enable both TOTP and SMS
- **Enforced MFA**: Admins can require MFA for specific users
- **Sensitive Action Protection**: Require MFA for password changes, etc.

## Database Models

### MFASettings
User's MFA configuration and preferences.

**Fields:**
- `user`: OneToOne to User
- `is_enabled`: Whether MFA is active
- `is_enforced`: Admin-enforced (cannot be disabled by user)
- `enabled_at` / `disabled_at`: Timestamps
- `require_for_sensitive_actions`: Require MFA for sensitive operations
- `remember_device_enabled`: Allow trusted devices
- `remember_device_days`: Days to remember devices (default: 30)
- `backup_codes_remaining`: Count of unused backup codes
- `last_successful_verification`: Last successful MFA verification
- `failed_verification_attempts`: Count of failed attempts

### MFAMethod
MFA methods configured for a user.

**Method Types:**
- `totp`: Authenticator App (TOTP)
- `sms`: SMS Verification
- `email`: Email Verification

**Fields:**
- `user`: FK to User
- `method_type`: Choice of totp/sms/email
- `is_primary`: Default method for user
- `is_enabled`: Method is active
- `is_verified`: User has successfully verified this method
- `totp_secret`: Base32 encoded secret for TOTP
- `phone_number`: For SMS methods
- `email_address`: For email methods
- `last_used_at`: Last time method was used
- `use_count`: Number of times used

**Unique Constraint:** (user, method_type)

### MFABackupCode
Single-use backup recovery codes.

**Fields:**
- `user`: FK to User
- `code_hash`: SHA256 hash of backup code
- `is_used`: Whether code has been consumed
- `used_at`: When code was used
- `used_from_ip`: IP address where code was used

**Format:** XXXX-XXXX (8 characters)
**Count:** 10 codes generated per user

### MFAVerificationCode
Temporary codes for SMS/Email verification.

**Code Types:**
- `login`: Login verification
- `setup`: MFA setup
- `disable`: MFA disable confirmation
- `recovery`: Account recovery

**Fields:**
- `user`: FK to User
- `mfa_method`: FK to MFAMethod (optional)
- `code_type`: Choice of login/setup/disable/recovery
- `code`: 6-digit verification code
- `sent_to`: Phone number or email
- `expires_at`: Code expires after 10 minutes
- `is_used`: Whether code has been consumed
- `verification_attempts`: Number of attempts (max 5)

### TrustedDevice
Devices that don't require MFA for a period.

**Fields:**
- `user`: FK to User
- `device_name`: User-provided or auto-detected name
- `device_fingerprint`: Hash of user agent + IP
- `user_agent`: Browser/device user agent
- `ip_address`: IP address
- `is_trusted`: Device is trusted
- `trust_expires_at`: Trust expires after 30 days (default)
- `last_used_at`: Last time device was used
- `revoked`: Device trust revoked
- `revoked_at`: When revoked
- `revoke_reason`: Why revoked

## API Endpoints

### Get MFA Status

```http
GET /api/auth/mfa/status/
Authorization: Bearer <token>
```

**Response:**
```json
{
    "mfa_enabled": true,
    "mfa_enforced": false,
    "methods": [
        {
            "id": "uuid",
            "method_type": "totp",
            "method_display": "Authenticator App (TOTP)",
            "is_primary": true,
            "is_enabled": true,
            "is_verified": true,
            "last_used_at": "2025-11-26T10:30:00Z",
            "use_count": 45,
            "created_at": "2025-11-01T08:00:00Z"
        }
    ],
    "backup_codes_remaining": 8,
    "trusted_devices": [
        {
            "id": "uuid",
            "device_name": "My Laptop",
            "last_used": "2025-11-26T09:00:00Z",
            "expires_at": "2025-12-26T09:00:00Z",
            "is_valid": true
        }
    ],
    "remember_device_enabled": true
}
```

### Enable TOTP MFA

**Step 1: Initiate TOTP Setup**

```http
POST /api/auth/mfa/totp/enable/
Authorization: Bearer <token>
```

**Response:**
```json
{
    "secret": "JBSWY3DPEHPK3PXP",
    "provisioning_uri": "otpauth://totp/PMS:user@email.com?secret=JBSWY3DPEHPK3PXP&issuer=PMS",
    "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
    "method_id": "uuid",
    "message": "Scan the QR code with your authenticator app and verify with a code to complete setup"
}
```

**Step 2: Verify TOTP Code**

```http
POST /api/auth/mfa/totp/verify/
Authorization: Bearer <token>
Content-Type: application/json

{
    "code": "123456",
    "method_id": "uuid"
}
```

**Response:**
```json
{
    "success": true,
    "message": "TOTP MFA enabled successfully",
    "backup_codes": [
        "A1B2-C3D4",
        "E5F6-G7H8",
        "I9J0-K1L2",
        ...
    ],
    "warning": "Save these backup codes in a safe place. You will need them if you lose access to your authenticator app."
}
```

### Enable SMS MFA

**Step 1: Initiate SMS Setup**

```http
POST /api/auth/mfa/sms/enable/
Authorization: Bearer <token>
Content-Type: application/json

{
    "phone_number": "+233XXXXXXXXX"
}
```

**Response:**
```json
{
    "method_id": "uuid",
    "phone_number": "+233XXXXXXXXX",
    "message": "Verification code sent to +233XXXXXXXXX. Code expires in 10 minutes."
}
```

**Step 2: Verify SMS Code**

```http
POST /api/auth/mfa/sms/verify/
Authorization: Bearer <token>
Content-Type: application/json

{
    "code": "123456",
    "method_id": "uuid"
}
```

**Response:**
```json
{
    "success": true,
    "message": "SMS MFA enabled successfully",
    "backup_codes": [
        "A1B2-C3D4",
        ...
    ],
    "warning": "Save these backup codes in a safe place."
}
```

### Verify MFA (Login or Sensitive Action)

```http
POST /api/auth/mfa/verify/
Authorization: Bearer <token>
Content-Type: application/json

{
    "code": "123456",
    "method_type": "totp",  // optional
    "remember_device": true,  // optional
    "device_name": "My Laptop"  // optional
}
```

**Response:**
```json
{
    "success": true,
    "message": "MFA verification successful",
    "method": "totp",
    "device_trusted": true
}
```

**Using Backup Code:**
```json
{
    "code": "A1B2-C3D4"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Backup code verified",
    "remaining_codes": 9,
    "warning": "You have 9 backup codes remaining"
}
```

### Send Login Code (SMS/Email)

```http
POST /api/auth/mfa/send-code/
Authorization: Bearer <token>
```

**Response:**
```json
{
    "method": "sms",
    "message": "Verification code sent to +233XXXXXXXXX"
}
```

### Disable MFA

```http
POST /api/auth/mfa/disable/
Authorization: Bearer <token>
Content-Type: application/json

{
    "password": "current_password"
}
```

**Response:**
```json
{
    "success": true,
    "message": "MFA disabled successfully"
}
```

### Regenerate Backup Codes

```http
POST /api/auth/mfa/backup-codes/regenerate/
Authorization: Bearer <token>
Content-Type: application/json

{
    "password": "current_password"
}
```

**Response:**
```json
{
    "success": true,
    "backup_codes": [
        "X1Y2-Z3A4",
        ...
    ],
    "message": "New backup codes generated. Save them in a safe place.",
    "warning": "Old backup codes have been invalidated."
}
```

### Revoke Trusted Device

```http
POST /api/auth/mfa/devices/revoke/
Authorization: Bearer <token>
Content-Type: application/json

{
    "device_id": "uuid",
    "reason": "Lost device"  // optional
}
```

**Response:**
```json
{
    "success": true,
    "message": "Device \"My Laptop\" has been revoked"
}
```

## Usage Examples

### Example 1: Enable TOTP MFA

```python
# Step 1: Initiate setup
response = requests.post(
    'http://localhost:8000/api/auth/mfa/totp/enable/',
    headers={'Authorization': f'Bearer {access_token}'}
)

data = response.json()
qr_code = data['qr_code']  # Display to user
secret = data['secret']  # Show as text alternative
method_id = data['method_id']

# User scans QR code with authenticator app

# Step 2: User enters code from app
verification_response = requests.post(
    'http://localhost:8000/api/auth/mfa/totp/verify/',
    headers={'Authorization': f'Bearer {access_token}'},
    json={
        'code': '123456',  # From authenticator app
        'method_id': method_id
    }
)

result = verification_response.json()
backup_codes = result['backup_codes']  # Save these securely!
```

### Example 2: Login with MFA

```python
# Step 1: Normal login
login_response = requests.post(
    'http://localhost:8000/api/auth/login/',
    json={
        'email': 'user@example.com',
        'password': 'password123'
    }
)

access_token = login_response.json()['access']

# Step 2: Check if MFA is enabled
status_response = requests.get(
    'http://localhost:8000/api/auth/mfa/status/',
    headers={'Authorization': f'Bearer {access_token}'}
)

mfa_enabled = status_response.json()['mfa_enabled']

if mfa_enabled:
    # Step 3: Verify MFA
    # If TOTP: User enters code from authenticator app
    # If SMS: Request code first, then verify
    
    mfa_response = requests.post(
        'http://localhost:8000/api/auth/mfa/verify/',
        headers={'Authorization': f'Bearer {access_token}'},
        json={
            'code': '123456',
            'remember_device': True,
            'device_name': 'My Browser'
        }
    )
    
    if mfa_response.json()['success']:
        # MFA verified, proceed with session
        pass
```

### Example 3: Use Backup Code

```python
# If user loses access to authenticator app
response = requests.post(
    'http://localhost:8000/api/auth/mfa/verify/',
    headers={'Authorization': f'Bearer {access_token}'},
    json={
        'code': 'A1B2-C3D4'  # Backup code format
    }
)

result = response.json()
if result['success']:
    remaining = result['remaining_codes']
    print(f"Backup code verified. {remaining} codes remaining.")
    
    # If running low on backup codes, generate new ones
    if remaining < 3:
        regenerate_response = requests.post(
            'http://localhost:8000/api/auth/mfa/backup-codes/regenerate/',
            headers={'Authorization': f'Bearer {access_token}'},
            json={'password': 'current_password'}
        )
        new_codes = regenerate_response.json()['backup_codes']
```

## Service Methods

### MFAService

Located: `accounts/services/mfa_service.py`

#### enable_totp(user)
```python
MFAService.enable_totp(user)
# Returns: dict with secret, provisioning_uri, qr_code, method_id
```

#### verify_totp_setup(user, code, method_id)
```python
MFAService.verify_totp_setup(user, '123456', method_id)
# Returns: dict with success, message, backup_codes, warning
```

#### enable_sms(user, phone_number)
```python
MFAService.enable_sms(user, '+233XXXXXXXXX')
# Returns: dict with method_id, phone_number, message
```

#### verify_sms_setup(user, code, method_id)
```python
MFAService.verify_sms_setup(user, '123456', method_id)
# Returns: dict with success, message, backup_codes, warning
```

#### disable_mfa(user, password)
```python
MFAService.disable_mfa(user, 'password123')
# Returns: dict with success, message
```

#### verify_mfa(user, code, method_type=None)
```python
MFAService.verify_mfa(user, '123456', method_type='totp')
# Returns: dict with success, message, method
```

#### generate_backup_codes(user)
```python
codes = MFAService.generate_backup_codes(user)
# Returns: list of 10 backup codes
```

#### verify_backup_code(user, code)
```python
MFAService.verify_backup_code(user, 'A1B2-C3D4')
# Returns: dict with success, message, remaining_codes, warning
```

#### add_trusted_device(user, device_name, user_agent, ip_address)
```python
device = MFAService.add_trusted_device(
    user,
    'My Laptop',
    request.META.get('HTTP_USER_AGENT'),
    request.META.get('REMOTE_ADDR')
)
```

#### is_trusted_device(user, user_agent, ip_address)
```python
is_trusted = MFAService.is_trusted_device(
    user,
    request.META.get('HTTP_USER_AGENT'),
    request.META.get('REMOTE_ADDR')
)
```

#### get_user_mfa_status(user)
```python
status = MFAService.get_user_mfa_status(user)
# Returns: dict with mfa_enabled, methods, backup_codes_remaining, trusted_devices
```

## Security Features

### Rate Limiting
- SMS codes: Maximum 5 verification attempts per code
- Failed MFA attempts tracked per user
- Automatic lockout after repeated failures (configurable)

### Code Expiration
- SMS/Email codes: 10 minutes
- TOTP codes: 30-second window with 1-interval tolerance for clock skew

### Backup Code Security
- Stored as SHA256 hashes (never plaintext)
- Single-use only
- Automatic invalidation when regenerating

### Trusted Device Security
- Device fingerprinting based on User-Agent + IP
- Configurable trust duration (default: 30 days)
- Can be revoked at any time
- All devices revoked when MFA disabled

### TOTP Security
- Base32 encoded secrets
- Industry-standard HOTP algorithm (RFC 4226)
- Compatible with all major authenticator apps

## Admin Configuration

### Enforce MFA for User

```python
from accounts.mfa_models import MFASettings

# Get or create settings
settings, created = MFASettings.objects.get_or_create(user=user)

# Enforce MFA
settings.is_enforced = True
settings.save()

# User cannot disable MFA now
```

### View User's MFA Status

Admin interface provides:
- List of all MFA methods per user
- Backup codes status
- Trusted devices list
- Recent verification history
- Failed attempt tracking

### Bulk Operations

```python
# Enforce MFA for all admin users
from accounts.models import User
from accounts.mfa_models import MFASettings

admins = User.objects.filter(is_staff=True)
for admin in admins:
    settings, _ = MFASettings.objects.get_or_create(user=admin)
    settings.is_enforced = True
    settings.save()
```

## Best Practices

### For Users

1. **Enable TOTP First**: Most secure method
2. **Save Backup Codes**: Store in password manager or offline
3. **Use Multiple Methods**: Enable both TOTP and SMS as backup
4. **Trust Only Personal Devices**: Don't trust public/shared computers
5. **Regenerate Backup Codes**: When running low or compromised

### For Developers

1. **Always Require MFA for Sensitive Actions**: Password changes, email updates, etc.
2. **Check Trusted Devices**: Skip MFA prompt if device trusted
3. **Handle MFA Failures Gracefully**: Provide clear error messages
4. **Log MFA Events**: Track setup, verification, failures for security audits
5. **Test QR Code Generation**: Ensure QR codes work with all authenticator apps

### For Admins

1. **Enforce MFA for Privileged Users**: All staff, admins, officers
2. **Monitor Failed Attempts**: Investigate repeated MFA failures
3. **Review Trusted Devices**: Periodically audit trusted devices
4. **Set Appropriate Trust Duration**: Balance security and convenience
5. **Educate Users**: Provide MFA setup guides and support

## Troubleshooting

### User Lost Authenticator App

```python
# User can use backup codes
# Or admin can disable MFA to allow re-setup
settings = user.mfa_settings
settings.disable_mfa()

# Disable all methods
user.mfa_methods.update(is_enabled=False)

# User can now set up MFA again
```

### QR Code Not Working

- Verify provisioning URI format is correct
- Check that secret is valid Base32
- Try manual entry of secret key
- Ensure authenticator app is up to date

### SMS Codes Not Arriving

- Verify phone number format (+233XXXXXXXXX)
- Check SMS service configuration
- Verify user has not hit rate limits
- Check SMS provider logs

### Backup Codes Not Working

- Verify code format (XXXX-XXXX)
- Check if code already used
- Ensure backup codes were generated
- Verify user is entering correct code

## Next Steps

- ✅ Models created and migrated
- ✅ Service layer implemented
- ✅ API endpoints created
- ✅ Admin interface configured
- ⏳ Frontend UI for MFA setup
- ⏳ Integration with login flow
- ⏳ Email MFA method implementation
- ⏳ MFA enforcement policies
- ⏳ Security audit logging
- ⏳ User documentation and guides
