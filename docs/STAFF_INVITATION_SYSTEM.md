# Staff Invitation System

## Overview

The Staff Invitation System provides a secure, email-based workflow for creating office staff accounts in the YEA PMS. This system ensures that staff members set their own passwords and verify their email addresses before gaining access to the system.

## Key Features

- **Email-based invitations** with secure token generation
- **7-day token expiry** for security
- **Password self-setup** by invited staff
- **Email verification** through invitation acceptance
- **Role hierarchy enforcement** (admins can only invite lower-tier roles)
- **Permission validation** at every step
- **Invitation management** (resend, cancel)

## Comparison: Farmers vs Office Staff Account Creation

### Farmers (Existing System)
1. Farmer submits FarmApplication online
2. Application goes through 3-tier approval (Constituency → Regional → National)
3. Upon approval, system sends invitation email via FarmInvitation
4. Farmer clicks link and creates account with farm details
5. Account activated with role='FARMER'

### Office Staff (New System)
1. Admin creates staff invitation with basic info (no password)
2. System generates secure token and sends invitation email via StaffInvitationService
3. Staff member clicks link and sets password
4. Account activated with assigned role (EXTENSION_OFFICER, CONSTITUENCY_OFFICIAL, etc.)
5. Staff can immediately log in

## API Endpoints

### 1. Create Staff Invitation

**Endpoint:** `POST /api/admin/users/create/`

**Authentication:** Required (Admin roles only)

**Permissions:**
- `SUPER_ADMIN`: Can invite all roles except SUPER_ADMIN
- `NATIONAL_ADMIN`: Can invite all roles except SUPER_ADMIN and NATIONAL_ADMIN
- `REGIONAL_COORDINATOR`: Can invite CONSTITUENCY_OFFICIAL and EXTENSION_OFFICER only

**Request Body:**
```json
{
  "email": "staff@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "CONSTITUENCY_OFFICIAL",
  "phone": "+233241234567",
  "region": "Greater Accra",
  "constituency": "Tema East"
}
```

**Required Fields:**
- `email`: Valid email address
- `first_name`: Staff member's first name
- `last_name`: Staff member's last name
- `role`: One of: EXTENSION_OFFICER, CONSTITUENCY_OFFICIAL, REGIONAL_COORDINATOR, NATIONAL_ADMIN, SUPER_ADMIN

**Optional Fields:**
- `phone`: Phone number (recommended)
- `region`: Required for REGIONAL_COORDINATOR and below
- `constituency`: Required for CONSTITUENCY_OFFICIAL and EXTENSION_OFFICER

**Response (201 Created):**
```json
{
  "id": "uuid",
  "username": "john.doe",
  "email": "staff@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "CONSTITUENCY_OFFICIAL",
  "is_active": false,
  "invitation_sent": true,
  "expires_at": "2024-12-31T23:59:59Z",
  "message": "Staff invitation created and email sent to staff@example.com"
}
```

**Error Responses:**
- `400 Bad Request`: Missing required fields or invalid data
- `403 Forbidden`: Insufficient permissions or role hierarchy violation
- `500 Internal Server Error`: Email sending failure or unexpected error

**Example cURL:**
```bash
curl -X POST http://localhost:8000/api/admin/users/create/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "staff@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "CONSTITUENCY_OFFICIAL",
    "region": "Greater Accra",
    "constituency": "Tema East"
  }'
```

---

### 2. Accept Staff Invitation

**Endpoint:** `POST /api/accounts/staff/accept-invitation/`

**Authentication:** Not required (public endpoint)

**Request Body:**
```json
{
  "uidb64": "encoded_user_id",
  "token": "invitation_token",
  "password": "SecurePassword123!"
}
```

**Required Fields:**
- `uidb64`: Base64-encoded user ID (from invitation email)
- `token`: Invitation token (from invitation email)
- `password`: New password (minimum 8 characters)

**Response (200 OK):**
```json
{
  "id": "uuid",
  "username": "john.doe",
  "email": "staff@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "CONSTITUENCY_OFFICIAL",
  "is_active": true,
  "message": "Invitation accepted successfully. You can now log in with your credentials."
}
```

**Error Responses:**
- `400 Bad Request`: Invalid token, expired invitation, weak password, or user already active
- `500 Internal Server Error`: Unexpected error during activation

**Invitation URL Format:**
```
http://your-frontend-domain.com/staff/accept-invitation?uidb64=ABC123&token=xyz789
```

**Example cURL:**
```bash
curl -X POST http://localhost:8000/api/accounts/staff/accept-invitation/ \
  -H "Content-Type: application/json" \
  -d '{
    "uidb64": "ABC123",
    "token": "xyz789",
    "password": "SecurePassword123!"
  }'
```

---

### 3. Resend Staff Invitation

**Endpoint:** `POST /api/admin/staff/{user_id}/resend-invitation/`

**Authentication:** Required (Admin roles only)

**Permissions:** Same as create invitation

**URL Parameters:**
- `user_id`: UUID of the inactive user

**Request Body:** None

**Response (200 OK):**
```json
{
  "id": "uuid",
  "username": "john.doe",
  "email": "staff@example.com",
  "invitation_sent": true,
  "expires_at": "2024-12-31T23:59:59Z",
  "message": "Invitation resent to staff@example.com"
}
```

**Error Responses:**
- `400 Bad Request`: User already active or not found
- `403 Forbidden`: Insufficient permissions
- `500 Internal Server Error`: Email sending failure

**Example cURL:**
```bash
curl -X POST http://localhost:8000/api/admin/staff/uuid-here/resend-invitation/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

### 4. Cancel Staff Invitation

**Endpoint:** `DELETE /api/admin/staff/{user_id}/cancel-invitation/`

**Authentication:** Required (Admin roles only)

**Permissions:** Same as create invitation

**URL Parameters:**
- `user_id`: UUID of the inactive user

**Request Body:** None

**Response (200 OK):**
```json
{
  "message": "Invitation cancelled successfully"
}
```

**Error Responses:**
- `400 Bad Request`: User already active or not found
- `403 Forbidden`: Insufficient permissions
- `500 Internal Server Error`: Unexpected error

**Example cURL:**
```bash
curl -X DELETE http://localhost:8000/api/admin/staff/uuid-here/cancel-invitation/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Service Layer

### StaffInvitationService

Located at: `accounts/services/staff_invitation_service.py`

**Methods:**

#### create_staff_invitation()
```python
@staticmethod
def create_staff_invitation(
    admin_user,
    email,
    first_name,
    last_name,
    role,
    phone=None,
    region=None,
    constituency=None
):
    """
    Creates inactive user and sends invitation email.
    
    Returns:
        {
            'user': User instance,
            'invitation_url': str,
            'expires_at': datetime,
            'message': str
        }
    
    Raises:
        PermissionError: If admin lacks permission
        ValueError: If required fields missing or invalid
    """
```

#### accept_invitation()
```python
@staticmethod
def accept_invitation(uidb64, token, password):
    """
    Validates token and activates user account.
    
    Returns:
        User instance (activated)
    
    Raises:
        ValueError: If token invalid, expired, or password weak
    """
```

#### resend_invitation()
```python
@staticmethod
def resend_invitation(admin_user, user_id):
    """
    Generates new token and resends invitation email.
    
    Returns:
        {
            'user': User instance,
            'invitation_url': str,
            'expires_at': datetime,
            'message': str
        }
    
    Raises:
        PermissionError: If admin lacks permission
        ValueError: If user active or not found
    """
```

#### cancel_invitation()
```python
@staticmethod
def cancel_invitation(admin_user, user_id):
    """
    Deletes inactive user (cancels invitation).
    
    Raises:
        PermissionError: If admin lacks permission
        ValueError: If user active or not found
    """
```

---

## Email Templates

### Invitation Email

**Subject:** "Your YEA PMS Staff Account Invitation"

**Body:**
```
Dear {first_name} {last_name},

You have been invited to join the YEA Poultry Management System as a {role}.

Account Details:
- Email: {email}
- Role: {role}
- Region: {region}
- Constituency: {constituency}

Please click the link below to set your password and activate your account:
{invitation_url}

This invitation link will expire in 7 days.

If you did not expect this invitation, please ignore this email.

Best regards,
YEA PMS Administration Team
```

### Welcome Email (after activation)

**Subject:** "Welcome to YEA PMS"

**Body:**
```
Dear {first_name} {last_name},

Your YEA PMS account has been successfully activated!

Login Details:
- Username: {username}
- Login URL: http://your-frontend-domain.com/login

Your Role: {role}
Jurisdiction:
- Region: {region}
- Constituency: {constituency}

You can now log in using your username and the password you set during activation.

If you have any questions or need assistance, please contact your administrator.

Best regards,
YEA PMS Administration Team
```

---

## Security Features

### Token Generation
- Uses Django's `default_token_generator`
- Cryptographically secure
- One-time use
- 7-day expiry

### Password Requirements
- Minimum 8 characters
- Validated by Django's password validators
- User sets own password (never transmitted via email)

### Permission Validation
- Role hierarchy enforced at service layer
- Admins cannot invite roles at or above their level
- Permission checks on every operation

### Email Verification
- Email verified through invitation acceptance
- `email_verified=True` set upon activation
- No separate verification step needed

---

## Frontend Integration Guide

### 1. Admin Dashboard - Invite Staff

**Component Location:** `src/pages/admin/UsersManagement.jsx`

**UI Elements:**
- "Invite Staff" button
- Modal form with fields:
  - Email (required)
  - First Name (required)
  - Last Name (required)
  - Role (dropdown, required)
  - Phone (optional)
  - Region (conditional, required for regional roles)
  - Constituency (conditional, required for constituency roles)

**Form Submission:**
```javascript
const inviteStaff = async (formData) => {
  try {
    const response = await axios.post('/api/admin/users/create/', formData, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      }
    });
    
    // Show success message
    toast.success(`Invitation sent to ${response.data.email}`);
    
    // Refresh user list
    fetchUsers();
  } catch (error) {
    if (error.response?.data?.error) {
      toast.error(error.response.data.error);
    } else {
      toast.error('Failed to send invitation');
    }
  }
};
```

### 2. User List - Pending Invitations

**Display inactive users with "Pending" status:**
```javascript
const UserRow = ({ user }) => {
  return (
    <tr>
      <td>{user.username}</td>
      <td>{user.email}</td>
      <td>{user.role}</td>
      <td>
        {user.is_active ? (
          <span className="badge badge-success">Active</span>
        ) : (
          <span className="badge badge-warning">Pending Invitation</span>
        )}
      </td>
      <td>
        {!user.is_active && (
          <>
            <button onClick={() => resendInvitation(user.id)}>
              Resend
            </button>
            <button onClick={() => cancelInvitation(user.id)}>
              Cancel
            </button>
          </>
        )}
      </td>
    </tr>
  );
};
```

### 3. Staff Invitation Acceptance Page

**Route:** `/staff/accept-invitation`

**Component Location:** `src/pages/auth/AcceptStaffInvitation.jsx`

**URL Parameters:**
- `uidb64`: User ID (base64 encoded)
- `token`: Invitation token

**Form:**
```javascript
import { useSearchParams } from 'react-router-dom';

const AcceptStaffInvitation = () => {
  const [searchParams] = useSearchParams();
  const uidb64 = searchParams.get('uidb64');
  const token = searchParams.get('token');
  
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (password !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }
    
    try {
      const response = await axios.post('/api/accounts/staff/accept-invitation/', {
        uidb64,
        token,
        password
      });
      
      toast.success('Account activated! Redirecting to login...');
      
      // Redirect to login after 2 seconds
      setTimeout(() => {
        navigate('/login');
      }, 2000);
    } catch (error) {
      if (error.response?.data?.error) {
        toast.error(error.response.data.error);
      } else {
        toast.error('Failed to activate account');
      }
    }
  };
  
  return (
    <div className="invitation-page">
      <h2>Set Your Password</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="password"
          placeholder="Password (min 8 characters)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Confirm Password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          required
        />
        <button type="submit">Activate Account</button>
      </form>
    </div>
  );
};
```

---

## Testing

### Test Scenario 1: Successful Invitation

1. Login as admin (adminuser)
2. Navigate to Users Management
3. Click "Invite Staff"
4. Fill form:
   - Email: newstaff@example.com
   - First Name: Test
   - Last Name: Staff
   - Role: CONSTITUENCY_OFFICIAL
   - Region: Greater Accra
   - Constituency: Tema East
5. Submit form
6. Verify success message and invitation sent
7. Check user list for "Pending Invitation" status

### Test Scenario 2: Accept Invitation

1. Check email for invitation link
2. Click link (opens acceptance page)
3. Set password (min 8 characters)
4. Submit
5. Verify success message
6. Login with new credentials
7. Verify access to appropriate dashboard

### Test Scenario 3: Resend Invitation

1. Login as admin
2. Find pending invitation in user list
3. Click "Resend" button
4. Verify new invitation email sent
5. Confirm new token works for acceptance

### Test Scenario 4: Cancel Invitation

1. Login as admin
2. Find pending invitation in user list
3. Click "Cancel" button
4. Confirm deletion
5. Verify user removed from list

### Test Scenario 5: Permission Validation

1. Login as REGIONAL_COORDINATOR
2. Try to invite NATIONAL_ADMIN
3. Verify 403 Forbidden error
4. Try to invite CONSTITUENCY_OFFICIAL
5. Verify success

---

## Common Issues & Solutions

### Issue 1: Invitation email not received

**Causes:**
- Email service not configured
- Invalid email address
- Email in spam folder

**Solutions:**
- Check Django email settings (EMAIL_HOST, EMAIL_PORT, etc.)
- Verify email address format
- Check spam/junk folder
- Use resend invitation feature

### Issue 2: Token expired

**Cause:** More than 7 days passed since invitation sent

**Solution:** Use resend invitation to generate new token

### Issue 3: Cannot invite certain roles

**Cause:** Role hierarchy violation

**Solution:** Ensure admin role allows inviting target role (check permissions table in RBAC guide)

### Issue 4: User already active error

**Cause:** Trying to resend/cancel invitation for active user

**Solution:** User has already accepted invitation, cannot resend

---

## Database Schema

### User Model Fields (relevant to invitations)

```python
class User:
    id = UUIDField(primary_key=True)
    username = CharField(unique=True)
    email = EmailField(unique=True)
    first_name = CharField()
    last_name = CharField()
    role = CharField(choices=ROLE_CHOICES)
    is_active = BooleanField(default=False)  # False until invitation accepted
    email_verified = BooleanField(default=False)  # True after acceptance
    phone = CharField(blank=True, null=True)
    region = CharField(blank=True, null=True)
    constituency = CharField(blank=True, null=True)
    created_at = DateTimeField(auto_now_add=True)
```

**Inactive User States:**
- `is_active=False`: User created but hasn't accepted invitation
- `email_verified=False`: Email not verified yet
- No password set: Cannot login

**Active User States (after invitation acceptance):**
- `is_active=True`: User can login
- `email_verified=True`: Email verified through invitation
- Password set: User can authenticate

---

## Role Hierarchy & Permissions

### Can Invite Matrix

| Admin Role | Can Invite |
|-----------|-----------|
| SUPER_ADMIN | NATIONAL_ADMIN, REGIONAL_COORDINATOR, CONSTITUENCY_OFFICIAL, EXTENSION_OFFICER |
| NATIONAL_ADMIN | REGIONAL_COORDINATOR, CONSTITUENCY_OFFICIAL, EXTENSION_OFFICER |
| REGIONAL_COORDINATOR | CONSTITUENCY_OFFICIAL, EXTENSION_OFFICER |
| CONSTITUENCY_OFFICIAL | None |
| EXTENSION_OFFICER | None |

---

## Workflow Diagram

```
Admin Action                     System Response                  Staff Action
     |                                  |                              |
     v                                  v                              v
[Invite Staff] --------> [Create Inactive User] 
     |                         |
     |                         v
     |                  [Generate Token]
     |                         |
     |                         v
     |                  [Send Email with Link]
     |                         |
     |                         |-------------------------------> [Click Link]
     |                         |                                      |
     |                         |                                      v
     |                         |                              [Set Password]
     |                         |                                      |
     |                         |                                      v
     |                         | <--------------------------[Submit Password]
     |                         |
     |                         v
     |                  [Validate Token]
     |                         |
     |                         v
     |                  [Activate User]
     |                         |
     |                         v
     |                  [Set email_verified=True]
     |                         |
     |                         v
     |                  [Send Welcome Email] ---------> [Login]
     v                                                       v
[See Active User]                                   [Access Dashboard]
```

---

## Conclusion

The Staff Invitation System provides a secure, user-friendly workflow for onboarding office staff into the YEA PMS. By separating the farmer application process from staff account creation, the system maintains appropriate security boundaries while ensuring all users have verified email addresses and secure passwords.

Key benefits:
- ✅ Enhanced security (users set own passwords)
- ✅ Email verification built-in
- ✅ Role hierarchy enforcement
- ✅ Token expiry prevents stale invitations
- ✅ Admin can manage pending invitations
- ✅ Clear separation between farmer and staff onboarding
