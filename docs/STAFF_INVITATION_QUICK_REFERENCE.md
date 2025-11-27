# Staff Invitation Quick Reference

## API Endpoints Summary

### Admin Endpoints (Require Authentication)

| Method | Endpoint | Purpose | Permissions |
|--------|----------|---------|------------|
| POST | `/api/admin/users/create/` | Create staff invitation | SUPER_ADMIN, NATIONAL_ADMIN, REGIONAL_COORDINATOR |
| POST | `/api/admin/staff/{user_id}/resend-invitation/` | Resend invitation | Same as create |
| DELETE | `/api/admin/staff/{user_id}/cancel-invitation/` | Cancel pending invitation | Same as create |

### Public Endpoints (No Authentication)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/accounts/staff/accept-invitation/` | Accept invitation & set password |

## Quick Examples

### 1. Create Invitation (Admin)

```bash
curl -X POST http://localhost:8000/api/admin/users/create/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
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

**Response:**
```json
{
  "id": "uuid",
  "username": "john.doe",
  "email": "staff@example.com",
  "is_active": false,
  "invitation_sent": true,
  "expires_at": "2024-12-31T23:59:59Z"
}
```

### 2. Accept Invitation (Staff)

```bash
curl -X POST http://localhost:8000/api/accounts/staff/accept-invitation/ \
  -H "Content-Type: application/json" \
  -d '{
    "uidb64": "ABC123",
    "token": "xyz789",
    "password": "SecurePass123!"
  }'
```

**Response:**
```json
{
  "id": "uuid",
  "username": "john.doe",
  "is_active": true,
  "message": "Invitation accepted successfully"
}
```

### 3. Resend Invitation (Admin)

```bash
curl -X POST http://localhost:8000/api/admin/staff/{user_id}/resend-invitation/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Cancel Invitation (Admin)

```bash
curl -X DELETE http://localhost:8000/api/admin/staff/{user_id}/cancel-invitation/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Frontend Integration Snippets

### Create Invitation Form

```javascript
const InviteStaffForm = () => {
  const [formData, setFormData] = useState({
    email: '',
    first_name: '',
    last_name: '',
    role: '',
    region: '',
    constituency: ''
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const response = await axios.post('/api/admin/users/create/', formData, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      toast.success(`Invitation sent to ${response.data.email}`);
      onSuccess();
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to send invitation');
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input name="email" required />
      <input name="first_name" required />
      <input name="last_name" required />
      <select name="role" required>
        <option value="EXTENSION_OFFICER">Extension Officer</option>
        <option value="CONSTITUENCY_OFFICIAL">Constituency Official</option>
        <option value="REGIONAL_COORDINATOR">Regional Coordinator</option>
        <option value="NATIONAL_ADMIN">National Admin</option>
      </select>
      <input name="region" />
      <input name="constituency" />
      <button type="submit">Send Invitation</button>
    </form>
  );
};
```

### Accept Invitation Page

```javascript
const AcceptInvitation = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (password !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }

    try {
      await axios.post('/api/accounts/staff/accept-invitation/', {
        uidb64: searchParams.get('uidb64'),
        token: searchParams.get('token'),
        password
      });
      
      toast.success('Account activated! Redirecting to login...');
      setTimeout(() => navigate('/login'), 2000);
    } catch (error) {
      toast.error(error.response?.data?.error || 'Activation failed');
    }
  };

  return (
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
  );
};
```

### User List with Invitation Management

```javascript
const UserList = () => {
  const [users, setUsers] = useState([]);

  const resendInvitation = async (userId) => {
    try {
      await axios.post(`/api/admin/staff/${userId}/resend-invitation/`, {}, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      toast.success('Invitation resent');
    } catch (error) {
      toast.error('Failed to resend invitation');
    }
  };

  const cancelInvitation = async (userId) => {
    if (!confirm('Cancel this invitation?')) return;
    
    try {
      await axios.delete(`/api/admin/staff/${userId}/cancel-invitation/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      toast.success('Invitation cancelled');
      fetchUsers(); // Refresh list
    } catch (error) {
      toast.error('Failed to cancel invitation');
    }
  };

  return (
    <table>
      <thead>
        <tr>
          <th>Name</th>
          <th>Email</th>
          <th>Role</th>
          <th>Status</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {users.map(user => (
          <tr key={user.id}>
            <td>{user.first_name} {user.last_name}</td>
            <td>{user.email}</td>
            <td>{user.role}</td>
            <td>
              {user.is_active ? (
                <span className="badge-success">Active</span>
              ) : (
                <span className="badge-warning">Pending</span>
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
        ))}
      </tbody>
    </table>
  );
};
```

## Role Hierarchy Quick Reference

| Admin Role | Can Invite |
|-----------|-----------|
| SUPER_ADMIN | All except SUPER_ADMIN |
| NATIONAL_ADMIN | Regional, Constituency, Extension |
| REGIONAL_COORDINATOR | Constituency, Extension only |
| CONSTITUENCY_OFFICIAL | ❌ None |
| EXTENSION_OFFICER | ❌ None |

## Error Codes

| Code | Error | Cause |
|------|-------|-------|
| 400 | Missing required fields | email, first_name, last_name, or role missing |
| 400 | Invalid token | Token expired, invalid, or already used |
| 400 | User already active | Cannot resend/cancel for active users |
| 403 | Permission denied | Role hierarchy violation |
| 500 | Email sending failed | Email service configuration issue |

## Invitation Email Flow

```
1. Admin creates invitation
   ↓
2. System creates inactive user (is_active=False)
   ↓
3. System generates token (7-day expiry)
   ↓
4. System sends email with link:
   http://frontend.com/staff/accept-invitation?uidb64=ABC&token=xyz
   ↓
5. Staff clicks link
   ↓
6. Staff sets password
   ↓
7. System validates token
   ↓
8. System activates account (is_active=True, email_verified=True)
   ↓
9. System sends welcome email
   ↓
10. Staff can login
```

## Key Security Points

- ✅ Passwords NEVER sent via email
- ✅ Tokens expire after 7 days
- ✅ Tokens are one-time use
- ✅ Email verified through invitation acceptance
- ✅ Role hierarchy enforced
- ✅ Inactive users cannot login

## Troubleshooting

### Email not received
1. Check email settings in Django settings.py
2. Check spam/junk folder
3. Use resend invitation feature
4. Check email service logs

### Token expired
- Use resend invitation to generate new token
- New token has fresh 7-day expiry

### Cannot invite role
- Check role hierarchy matrix
- Lower roles can only invite even lower roles

### User already active error
- User has accepted invitation
- Cannot resend/cancel for active users
- Check user.is_active status

## Testing Checklist

- [ ] Create invitation as SUPER_ADMIN
- [ ] Create invitation as NATIONAL_ADMIN
- [ ] Try to invite higher role (should fail)
- [ ] Accept invitation with valid token
- [ ] Accept invitation with expired token (should fail)
- [ ] Resend invitation
- [ ] Cancel invitation
- [ ] Login after activation

## Files to Review

1. **Service Layer**: `accounts/services/staff_invitation_service.py`
2. **API Views**: `accounts/admin_views.py` (lines 323-427, 620-755)
3. **URLs**: `accounts/admin_urls.py`, `accounts/urls.py`
4. **Full Documentation**: `docs/STAFF_INVITATION_SYSTEM.md`
5. **Implementation Summary**: `STAFF_ACCOUNT_CREATION_IMPLEMENTATION.md`

## Common Use Cases

### Use Case 1: Invite Extension Officer
```json
{
  "email": "officer@example.com",
  "first_name": "Jane",
  "last_name": "Smith",
  "role": "EXTENSION_OFFICER",
  "region": "Greater Accra",
  "constituency": "Tema East",
  "phone": "+233241234567"
}
```

### Use Case 2: Invite Regional Coordinator
```json
{
  "email": "coordinator@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "REGIONAL_COORDINATOR",
  "region": "Greater Accra"
}
```

### Use Case 3: Invite National Admin
```json
{
  "email": "admin@example.com",
  "first_name": "Alice",
  "last_name": "Johnson",
  "role": "NATIONAL_ADMIN"
}
```

## Environment Configuration

### Development
```python
# settings.py
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # Prints to console
FRONTEND_URL = 'http://localhost:5173'
```

### Production
```python
# settings.py
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ['EMAIL_USER']
EMAIL_HOST_PASSWORD = os.environ['EMAIL_PASSWORD']
FRONTEND_URL = 'https://your-domain.com'
```

## Next Steps

1. ✅ Backend implementation complete
2. ⏳ Update frontend to integrate new endpoints
3. ⏳ Write unit tests
4. ⏳ Write integration tests
5. ⏳ Configure production email service
6. ⏳ Deploy and test end-to-end
