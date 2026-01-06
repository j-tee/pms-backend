# Contact Management System Documentation

## Overview
Complete contact form and message management system for AdSense compliance. Provides public contact form submission with spam protection, rate limiting, and comprehensive admin management interface.

## Features
- ✅ Public contact form API with validation
- ✅ Honeypot spam detection
- ✅ Rate limiting (5/hour per IP, 20/day per email)
- ✅ Disposable email blocking
- ✅ Automated email responses (Celery tasks)
- ✅ Admin dashboard for message management
- ✅ Role-based access control
- ✅ Ticket ID system (CNT-XXXXXXXX)
- ✅ Message status workflow (new → assigned → in_progress → resolved → closed)
- ✅ Staff assignment and reply system
- ✅ Analytics and reporting

---

## API Endpoints

### Public Endpoints

#### Submit Contact Form
```http
POST /api/contact/submit
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com",
  "subject": "support",
  "message": "I need help with my farm registration process."
}
```

**Subject Options:**
- `general` - General inquiries
- `support` - Technical support
- `feedback` - Feedback and suggestions
- `complaint` - Complaints
- `partnership` - Partnership opportunities
- `other` - Other topics

**Response (201 Created):**
```json
{
  "success": true,
  "message": "Thank you for contacting us. We'll get back to you soon.",
  "ticket_id": "CNT-20250101"
}
```

**Response (400 Bad Request - Spam Detected):**
```json
{
  "success": false,
  "error": "Submission rejected - spam detected"
}
```

**Response (429 Too Many Requests):**
```json
{
  "error": "Rate limit exceeded. Please try again later."
}
```

**Rate Limits:**
- 5 submissions per hour per IP address
- 20 submissions per day per email address

---

### Admin Endpoints

#### List Contact Messages
```http
GET /api/admin/contact-messages/
Authorization: Bearer {token}
```

**Query Parameters:**
- `status` - Filter by status (new, assigned, in_progress, resolved, closed)
- `subject` - Filter by subject
- `assigned_to` - Filter by assigned staff (UUID)
- `search` - Search in name, email, message
- `page` - Page number
- `page_size` - Items per page (default: 20)

**Response (200 OK):**
```json
{
  "count": 50,
  "next": "http://api.example.com/api/admin/contact-messages/?page=2",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "ticket_id": "CNT-20250101",
      "name": "John Doe",
      "email": "john@example.com",
      "subject": "support",
      "subject_display": "Technical Support",
      "message": "I need help...",
      "status": "new",
      "status_display": "New",
      "assigned_to": null,
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

#### Get Contact Message Details
```http
GET /api/admin/contact-messages/{id}/
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "ticket_id": "CNT-20250101",
  "name": "John Doe",
  "email": "john@example.com",
  "phone_number": "+233200000000",
  "subject": "support",
  "subject_display": "Technical Support",
  "message": "I need help with...",
  "status": "in_progress",
  "status_display": "In Progress",
  "assigned_to": {
    "id": "uuid",
    "email": "admin@example.com",
    "full_name": "Admin User"
  },
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T11:00:00Z",
  "replies": [
    {
      "id": "uuid",
      "staff": {
        "email": "admin@example.com",
        "full_name": "Admin User"
      },
      "message": "Thank you for reaching out...",
      "created_at": "2025-01-15T11:00:00Z"
    }
  ]
}
```

#### Update Contact Message
```http
PATCH /api/admin/contact-messages/{id}/update/
Authorization: Bearer {token}
Content-Type: application/json

{
  "status": "in_progress",
  "assigned_to": "staff-uuid"
}
```

**Allowed Status Transitions:**
- new → assigned → in_progress → resolved → closed
- Can re-open resolved messages back to in_progress

**Response (200 OK):**
```json
{
  "id": "uuid",
  "status": "in_progress",
  "assigned_to": "staff-uuid",
  "message": "Message updated successfully"
}
```

#### Reply to Contact Message
```http
POST /api/admin/contact-messages/{id}/reply/
Authorization: Bearer {token}
Content-Type: application/json

{
  "message": "Thank you for your inquiry. We have processed your request.",
  "send_email": true
}
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "message": "Thank you for your inquiry...",
  "staff": {
    "email": "admin@example.com",
    "full_name": "Admin User"
  },
  "created_at": "2025-01-15T12:00:00Z",
  "email_sent": true
}
```

#### Get Contact Statistics
```http
GET /api/admin/contact-stats/
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "total_messages": 150,
  "new_messages": 25,
  "in_progress": 30,
  "resolved": 80,
  "closed": 15,
  "by_subject": {
    "support": 60,
    "general": 40,
    "feedback": 30,
    "complaint": 15,
    "partnership": 5
  },
  "response_time_avg_hours": 4.5,
  "assigned_messages": 45
}
```

---

## Database Models

### ContactMessage
Stores contact form submissions.

**Fields:**
- `id` (UUID) - Primary key
- `ticket_id` (CharField) - Human-readable ticket ID (CNT-XXXXXXXX)
- `name` (CharField) - Sender's name
- `email` (EmailField) - Sender's email
- `phone_number` (PhoneNumberField) - Optional phone number
- `subject` (CharField) - Subject category (choices)
- `message` (TextField) - Message content
- `status` (CharField) - Current status (choices)
- `assigned_to` (ForeignKey) - Assigned staff member
- `ip_address` (GenericIPAddressField) - Sender's IP
- `user_agent` (TextField) - Browser user agent
- `is_deleted` (BooleanField) - Soft delete flag
- `created_at` (DateTimeField) - Submission timestamp
- `updated_at` (DateTimeField) - Last update timestamp

**Indexes:**
- `(status, created_at)` - For filtering by status
- `(assigned_to, status)` - For staff workload queries
- `(email)` - For duplicate detection

### ContactMessageReply
Stores staff replies to contact messages.

**Fields:**
- `id` (UUID) - Primary key
- `message` (ForeignKey) - Related ContactMessage
- `staff` (ForeignKey) - Staff who replied
- `message` (TextField) - Reply content
- `created_at` (DateTimeField) - Reply timestamp

**Index:**
- `(message, created_at)` - For reply threads

### ContactFormRateLimit
Tracks rate limiting for spam prevention.

**Fields:**
- `id` (UUID) - Primary key
- `identifier` (CharField) - IP or email address
- `identifier_type` (CharField) - 'ip' or 'email'
- `submission_count` (IntegerField) - Number of submissions
- `window_start` (DateTimeField) - Rate limit window start
- `created_at` (DateTimeField) - First submission

**Index:**
- `(identifier, identifier_type, window_start)` - For rate limit checks

---

## Email Notifications

### Auto-Reply Email
Sent immediately when contact form is submitted.

**Trigger:** Contact form submission  
**Recipient:** Form submitter  
**Template:** `templates/contact/emails/auto_reply.txt`

**Variables:**
- `name` - Recipient's name
- `ticket_id` - Generated ticket ID
- `message_preview` - First 100 chars of message

### Staff Notification Email
Sent to support team when new message arrives.

**Trigger:** Contact form submission  
**Recipient:** CONTACT_NOTIFICATION_EMAIL (settings)  
**Template:** `templates/contact/emails/staff_notification.txt`

**Variables:**
- `ticket_id` - Message ticket ID
- `name` - Sender's name
- `email` - Sender's email
- `subject` - Subject category
- `message` - Full message text

### Reply Email
Sent when staff replies to a contact message.

**Trigger:** Staff creates reply with `send_email=true`  
**Recipient:** Original message sender  
**Template:** `templates/contact/emails/reply.txt`

**Variables:**
- `name` - Recipient's name
- `ticket_id` - Original ticket ID
- `reply_message` - Staff reply text
- `staff_name` - Staff member's name

---

## Permissions

### Contact Form (Public)
- No authentication required
- Rate-limited by IP and email
- Honeypot spam protection

### Admin Endpoints
All admin endpoints require:
1. Authentication (JWT token)
2. Role: SUPER_ADMIN, NATIONAL_ADMIN, or REGIONAL_COORDINATOR

**Permission Logic** (`CanManageContactMessages`):
```python
SUPER_ADMIN - Full access to all messages
NATIONAL_ADMIN - Full access to all messages
REGIONAL_COORDINATOR - Limited to messages from their region (future)
```

---

## Rate Limiting

### Implementation
Custom decorator: `@rate_limit_contact_form`

**Limits:**
- **Per IP:** 5 submissions per hour
- **Per Email:** 20 submissions per day

**Enforcement:**
1. Check IP address submissions in last hour
2. Check email address submissions in last 24 hours
3. Return 429 if either limit exceeded
4. Clean up old rate limit records (>24h)

**Database Tracking:**
- `ContactFormRateLimit` model stores submission counts
- Uses sliding window algorithm
- Automatic cleanup of expired records

---

## Spam Protection

### Honeypot Field
Hidden field `website` in form:
- Not visible to humans
- Bots often auto-fill all fields
- Submission rejected if field is not empty

### Disposable Email Blocking
Common disposable email domains blocked:
- tempmail.com
- guerrillamail.com
- 10minutemail.com
- mailinator.com
- throwaway.email

### Message Validation
- Minimum 10 characters
- Maximum 5000 characters
- HTML stripped for security

---

## Admin Dashboard (Django Admin)

Access: `/admin/contact/contactmessage/`

**Features:**
- List view with filters (status, subject, assigned_to)
- Search by name, email, message
- Bulk actions (assign, change status)
- Inline reply creation
- Ticket ID display

**List Display:**
- Ticket ID
- Name
- Email
- Subject
- Status (colored)
- Assigned To
- Created At

**Filters:**
- Status
- Subject
- Assigned To
- Created Date

---

## Settings Configuration

Add to `core/settings.py` or `.env`:

```python
# Contact Form Settings
CONTACT_NOTIFICATION_EMAIL = 'support@example.com'
CONTACT_AUTO_REPLY_ENABLED = True
CONTACT_RATE_LIMIT_PER_HOUR = 5
CONTACT_RATE_LIMIT_PER_DAY = 20
CONTACT_MAX_MESSAGE_LENGTH = 5000

# Email Settings (required for notifications)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'YEA Poultry <noreply@example.com>'

# Celery Settings (for async emails)
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
```

---

## Frontend Integration

### Contact Form Example (React)

```jsx
import { useState } from 'react';
import axios from 'axios';

function ContactForm() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone_number: '',
    subject: 'general',
    message: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await axios.post(
        'http://localhost:8000/api/contact/submit',
        formData
      );
      setSuccess(`Thank you! Your ticket ID is: ${response.data.ticket_id}`);
      setFormData({ name: '', email: '', phone_number: '', subject: 'general', message: '' });
    } catch (err) {
      if (err.response?.status === 429) {
        setError('Too many submissions. Please try again later.');
      } else {
        setError(err.response?.data?.error || 'Submission failed');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {error && <div className="error">{error}</div>}
      {success && <div className="success">{success}</div>}
      
      <input
        type="text"
        placeholder="Name"
        value={formData.name}
        onChange={(e) => setFormData({...formData, name: e.target.value})}
        required
      />
      
      <input
        type="email"
        placeholder="Email"
        value={formData.email}
        onChange={(e) => setFormData({...formData, email: e.target.value})}
        required
      />
      
      <input
        type="tel"
        placeholder="Phone (optional)"
        value={formData.phone_number}
        onChange={(e) => setFormData({...formData, phone_number: e.target.value})}
      />
      
      <select
        value={formData.subject}
        onChange={(e) => setFormData({...formData, subject: e.target.value})}
        required
      >
        <option value="general">General Inquiry</option>
        <option value="support">Technical Support</option>
        <option value="feedback">Feedback</option>
        <option value="complaint">Complaint</option>
        <option value="partnership">Partnership</option>
        <option value="other">Other</option>
      </select>
      
      <textarea
        placeholder="Your message (minimum 10 characters)"
        value={formData.message}
        onChange={(e) => setFormData({...formData, message: e.target.value})}
        rows={5}
        required
      />
      
      <button type="submit" disabled={loading}>
        {loading ? 'Submitting...' : 'Submit'}
      </button>
    </form>
  );
}
```

### Admin Message List Example

```jsx
import { useEffect, useState } from 'react';
import axios from 'axios';

function AdminContactList() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const token = localStorage.getItem('access_token');

  useEffect(() => {
    const fetchMessages = async () => {
      try {
        const response = await axios.get(
          'http://localhost:8000/api/admin/contact-messages/',
          {
            headers: { Authorization: `Bearer ${token}` }
          }
        );
        setMessages(response.data.results);
      } catch (err) {
        console.error('Failed to fetch messages:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchMessages();
  }, [token]);

  if (loading) return <div>Loading...</div>;

  return (
    <table>
      <thead>
        <tr>
          <th>Ticket ID</th>
          <th>Name</th>
          <th>Subject</th>
          <th>Status</th>
          <th>Created</th>
        </tr>
      </thead>
      <tbody>
        {messages.map(msg => (
          <tr key={msg.id}>
            <td>{msg.ticket_id}</td>
            <td>{msg.name}</td>
            <td>{msg.subject_display}</td>
            <td>{msg.status_display}</td>
            <td>{new Date(msg.created_at).toLocaleDateString()}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

---

## Testing

### Run Tests
```bash
# All contact tests
pytest contact/tests.py -v

# Specific test class
pytest contact/tests.py::TestContactFormSubmission -v

# With coverage
pytest contact/tests.py --cov=contact --cov-report=html
```

### Test Coverage
- ✅ Form submission validation
- ✅ Rate limiting enforcement
- ✅ Honeypot spam detection
- ✅ Email format validation
- ✅ Message length validation
- ✅ Admin authentication
- ✅ Role-based permissions
- ✅ Status transitions
- ✅ Staff assignment
- ✅ Reply creation
- ✅ Statistics aggregation

---

## Deployment Checklist

- [ ] Run migrations: `python manage.py migrate`
- [ ] Configure email settings in `.env`
- [ ] Set `CONTACT_NOTIFICATION_EMAIL`
- [ ] Start Celery workers: `celery -A core worker -l info`
- [ ] Create email templates (HTML versions)
- [ ] Test contact form submission
- [ ] Test admin endpoints
- [ ] Configure Redis for rate limiting
- [ ] Set up monitoring for email delivery
- [ ] Add reCAPTCHA (optional, future)
- [ ] Configure CORS for frontend domain
- [ ] Enable HTTPS in production
- [ ] Set up log aggregation for error tracking

---

## Troubleshooting

### Issue: Emails not sending
**Solution:** Check Celery worker is running and email settings are correct
```bash
celery -A core worker -l info
python manage.py shell
>>> from core.tasks import send_contact_auto_reply
>>> send_contact_auto_reply.delay('test@example.com', 'Test', 'CNT-12345678', 'Test message')
```

### Issue: Rate limit not working
**Solution:** Ensure Redis is running and accessible
```bash
redis-cli ping  # Should return PONG
python manage.py shell
>>> from contact.models import ContactFormRateLimit
>>> ContactFormRateLimit.objects.all()  # Check records
```

### Issue: 403 Forbidden on admin endpoints
**Solution:** Verify user role is SUPER_ADMIN, NATIONAL_ADMIN, or REGIONAL_COORDINATOR
```bash
python manage.py shell
>>> from accounts.models import User
>>> user = User.objects.get(email='admin@example.com')
>>> user.role  # Should be SUPER_ADMIN, NATIONAL_ADMIN, or REGIONAL_COORDINATOR
```

---

## Future Enhancements

- [ ] **reCAPTCHA Integration** - Google reCAPTCHA v3 for bot protection
- [ ] **File Attachments** - Allow users to upload screenshots/documents
- [ ] **Live Chat Integration** - Real-time chat option
- [ ] **SMS Notifications** - Notify staff via SMS for urgent messages
- [ ] **Auto-Assignment** - Automatically assign messages based on subject
- [ ] **SLA Tracking** - Track response time SLAs
- [ ] **Customer Satisfaction** - Survey after resolution
- [ ] **Knowledge Base Integration** - Suggest articles before submission
- [ ] **Multi-language Support** - i18n for email templates
- [ ] **Analytics Dashboard** - Advanced reporting and charts

---

## References

- Django Documentation: https://docs.djangoproject.com/
- Django REST Framework: https://www.django-rest-framework.org/
- Celery Documentation: https://docs.celeryproject.org/
- Redis Documentation: https://redis.io/documentation
