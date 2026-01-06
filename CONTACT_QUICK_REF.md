# Contact System - Quick Reference Card

## 🚀 Quick Start Commands

```bash
# 1. Start Redis
sudo systemctl start redis

# 2. Start Celery Worker
celery -A core worker -l info

# 3. Run Django Server
python manage.py runserver

# 4. Test Contact Form
curl -X POST http://localhost:8000/api/contact/submit \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","email":"test@example.com","subject":"support","message":"Test message here"}'
```

---

## 📡 API Endpoints

### Public (No Auth)
- **POST** `/api/contact/submit` - Submit contact form

### Admin (Requires JWT Token)
- **GET** `/api/admin/contact-messages/` - List messages
- **GET** `/api/admin/contact-messages/{id}/` - Message details
- **PATCH** `/api/admin/contact-messages/{id}/update/` - Update message
- **POST** `/api/admin/contact-messages/{id}/reply/` - Reply to message
- **GET** `/api/admin/contact-stats/` - Statistics

---

## 🔑 Subject Options

| Value | Display |
|-------|---------|
| `general` | General Inquiries |
| `support` | Technical Support |
| `feedback` | Feedback & Suggestions |
| `complaint` | Complaints |
| `partnership` | Partnership Opportunities |
| `other` | Other |

---

## 📊 Status Values

| Status | Description |
|--------|-------------|
| `new` | Newly received |
| `assigned` | Assigned to staff |
| `in_progress` | Being handled |
| `resolved` | Issue resolved |
| `closed` | Ticket closed |

---

## 🚦 Rate Limits

- **5 submissions per hour** per IP address
- **20 submissions per day** per email address

---

## ✉️ Email Templates Location

```
templates/contact/emails/
├── auto_reply.txt / .html       (Sent to submitter)
├── staff_notification.txt / .html (Sent to support team)
└── reply.txt / .html             (Sent on staff reply)
```

---

## 🔒 Permissions

### Admin Endpoints Access
- `SUPER_ADMIN` - Full access
- `NATIONAL_ADMIN` - Full access
- `REGIONAL_COORDINATOR` - Full access
- Other roles - **403 Forbidden**

---

## 🛠️ Environment Variables

```bash
CONTACT_NOTIFICATION_EMAIL=support@yeapoultry.gov.gh
CONTACT_AUTO_REPLY_ENABLED=True
CONTACT_RATE_LIMIT_PER_HOUR=5
CONTACT_RATE_LIMIT_PER_DAY=20

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

CELERY_BROKER_URL=redis://localhost:6379/0
REDIS_URL=redis://localhost:6379/1
```

---

## 🧪 Test Commands

```bash
# Run all contact tests
pytest contact/tests.py -v

# Run specific test class
pytest contact/tests.py::TestContactFormSubmission -v

# Run with coverage
pytest contact/tests.py --cov=contact

# Check Celery worker
celery -A core inspect active

# Check Redis
redis-cli ping
```

---

## 📝 Common Tasks

### Check Contact Messages
```python
python manage.py shell
>>> from contact.models import ContactMessage
>>> ContactMessage.objects.all()
>>> ContactMessage.objects.filter(status='new').count()
```

### Send Test Email
```python
>>> from contact.tasks import send_contact_auto_reply
>>> send_contact_auto_reply.delay('test@example.com', 'Test User', 'CNT-12345678', 'Test message')
```

### Create Admin User
```bash
python manage.py createsuperuser
# OR
python create_admin.py
```

### View Contact Messages in Django Admin
```
http://localhost:8000/admin/contact/contactmessage/
```

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| Emails not sending | Check Celery worker is running |
| Rate limit not working | Ensure Redis is running |
| 403 on admin endpoints | Check user role is admin/coordinator |
| 429 Too Many Requests | Wait 1 hour or change IP/email |

---

## 📚 Documentation

- **Full API Docs:** `docs/CONTACT_SYSTEM_DOCS.md`
- **Deployment Guide:** `docs/CONTACT_DEPLOYMENT_GUIDE.md`
- **Implementation Summary:** `docs/CONTACT_IMPLEMENTATION_SUMMARY.md`
- **Tests:** `contact/tests.py`

---

## 🎯 Frontend Integration

### Submit Form
```javascript
const response = await fetch('http://localhost:8000/api/contact/submit', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'John Doe',
    email: 'john@example.com',
    subject: 'support',
    message: 'I need help with my account'
  })
});

const data = await response.json();
console.log(data.ticket_id); // CNT-20250115
```

### List Messages (Admin)
```javascript
const response = await fetch('http://localhost:8000/api/admin/contact-messages/', {
  headers: { 
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  }
});

const data = await response.json();
console.log(data.results); // Array of messages
```

---

## 📞 Support

**Email:** support@yeapoultry.gov.gh  
**GitHub:** j-tee/pms-backend  
**Branch:** development  
**Commit:** d38f04a  

---

**Last Updated:** January 15, 2025
