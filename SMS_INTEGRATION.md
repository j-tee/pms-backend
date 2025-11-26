# Hubtel SMS Integration - Complete Guide

## Overview

The YEA PMS system is now integrated with **Hubtel SMS API** for sending automated notifications to farmers, procurement officers, and administrators throughout the procurement workflow.

## Features

✅ **Automated SMS Notifications**
- Farm assignment notifications
- Assignment acceptance/rejection alerts
- Ready for delivery notifications
- Delivery confirmations
- Invoice generation alerts
- Payment confirmations
- Farm approval/rejection notices
- Overdue order reminders

✅ **Smart Message Handling**
- Automatic phone number normalization (Ghana format)
- SMS page calculation (single/multi-page messages)
- Cost estimation before sending
- Delivery status tracking
- Bulk SMS support

✅ **Development-Friendly**
- Console simulation mode (no API calls)
- Test commands for all notification types
- Detailed logging
- Error handling

## Quick Start

### 1. Get Hubtel Credentials

1. Create account at https://hubtel.com/
2. Access developer portal: https://developers.hubtel.com/
3. Get your API credentials:
   - Client ID
   - Client Secret
4. Register a Sender ID (e.g., "YEA-PMS")

### 2. Configure Environment

Add to your `.env` file:

```bash
# Enable SMS
SMS_ENABLED=True

# Hubtel Credentials
HUBTEL_CLIENT_ID=your_client_id_here
HUBTEL_CLIENT_SECRET=your_client_secret_here
HUBTEL_SENDER_ID=YEA-PMS

# Provider
SMS_PROVIDER=hubtel
```

### 3. Test Integration

```bash
# Check configuration
python manage.py test_sms

# Send test message
python manage.py test_sms --phone +233244123456

# Test all notification types
python manage.py test_sms --phone +233244123456 --test-all

# Check account balance
python manage.py test_sms --check-balance
```

## Notification Types

### 1. Farm Assignment
**Sent when:** Farm is assigned to a procurement order  
**Recipient:** Farmer  
**Message:**
```
YEA PMS: New order assigned!
Order: ORD-2025-00001
Quantity: 5,000 birds
Type: Broilers
Deadline: 15 Nov 2025
Please respond within 24 hours.
```
**Pages:** 3 | **Cost:** ~GHS 0.12

### 2. Assignment Accepted
**Sent when:** Farm accepts an assignment  
**Recipient:** Procurement Officer  
**Message:**
```
YEA PMS: Assignment accepted!
Farm: Nkwanta Poultry Farm
Order: ORD-2025-00001
Quantity: 5,000 birds
Expected ready: 15 Nov 2025
```
**Pages:** 2 | **Cost:** ~GHS 0.08

### 3. Assignment Rejected
**Sent when:** Farm rejects an assignment  
**Recipient:** Procurement Officer  
**Message:**
```
YEA PMS: Assignment REJECTED!
Farm: Nkwanta Poultry Farm
Order: ORD-2025-00001
Reason: Insufficient capacity
Action required: Reassign to another farm.
```
**Pages:** 2-3 | **Cost:** ~GHS 0.08-0.12

### 4. Ready for Delivery
**Sent when:** Farm marks order ready  
**Recipient:** Procurement Officer  
**Message:**
```
YEA PMS: Order ready for delivery!
Farm: Nkwanta Poultry Farm
Order: ORD-2025-00001
Quantity: 5,000 birds
Ready since: 14 Nov 2025
Schedule pickup ASAP.
```
**Pages:** 3 | **Cost:** ~GHS 0.12

### 5. Delivery Confirmed
**Sent when:** Delivery is verified  
**Recipient:** Farmer  
**Message:**
```
YEA PMS: Delivery confirmed!
Order: ORD-2025-00001
Quantity: 5,000 birds
Quality: PASSED ✓
Avg weight: 2.5kg
Invoice will be generated soon.
```
**Pages:** 3 | **Cost:** ~GHS 0.12

### 6. Invoice Generated
**Sent when:** Invoice is created  
**Recipient:** Farmer  
**Message:**
```
YEA PMS: Invoice generated!
Invoice: INV-2025-00001
Order: ORD-2025-00001
Amount: GHS 50,000.00
Due date: 30 Nov 2025
```
**Pages:** 2 | **Cost:** ~GHS 0.08

### 7. Payment Processed
**Sent when:** Payment is completed  
**Recipient:** Farmer  
**Message:**
```
YEA PMS: Payment processed! 💰
Invoice: INV-2025-00001
Amount paid: GHS 50,000.00
Payment date: 28 Nov 2025
Reference: PAY-2025-00001
Thank you for your service!
```
**Pages:** 3 | **Cost:** ~GHS 0.12

### 8. Farm Approved
**Sent when:** Farm application approved  
**Recipient:** Farmer  
**Message:**
```
YEA PMS: Congratulations! 🎉
Your farm 'Nkwanta Poultry Farm' has been APPROVED!
Farm ID: F-2025-0001
You can now receive procurement orders.
Welcome to the YEA Poultry Program!
```
**Pages:** 3 | **Cost:** ~GHS 0.12

### 9. Order Overdue
**Sent when:** Order deadline passed  
**Recipient:** Farmer  
**Message:**
```
YEA PMS: URGENT - Order overdue!
Order: ORD-2025-00001
Days overdue: 3
Quantity: 5,000 birds
Please update status immediately.
```
**Pages:** 2 | **Cost:** ~GHS 0.08

## Cost Estimation

### Pricing (Current Hubtel Rates)
- **Per SMS Page:** ~GHS 0.04 (4 pesewas)
- **Standard SMS:** 160 characters = 1 page
- **Unicode/Emoji:** 70 characters = 1 page
- **Concatenated SMS:** 153 chars/page (standard), 67 chars/page (unicode)

### Monthly Cost Estimates

**For 100 Active Farms:**
- Farm assignments: 100 × GHS 0.12 = GHS 12.00
- Assignment responses: 100 × GHS 0.08 = GHS 8.00
- Delivery notifications: 100 × GHS 0.12 = GHS 12.00
- Invoice notifications: 100 × GHS 0.08 = GHS 8.00
- Payment confirmations: 100 × GHS 0.12 = GHS 12.00

**Total: ~GHS 52/month** for moderate usage

**For 500 Active Farms:**
- **Total: ~GHS 260/month**

**For 1000 Active Farms:**
- **Total: ~GHS 520/month**

## Technical Implementation

### Service Architecture

```python
# SMS Service (core/sms_service.py)
- HubtelSMSService: Low-level Hubtel API integration
  - send_sms()
  - send_bulk_sms()
  - get_account_balance()
  - Phone number normalization
  - SMS page calculation

# Notification Service (procurement/services/notification_service.py)
- ProcurementNotificationService: High-level business logic
  - notify_farm_assignment()
  - notify_assignment_accepted()
  - notify_assignment_rejected()
  - notify_ready_for_delivery()
  - notify_delivery_confirmed()
  - notify_invoice_generated()
  - notify_payment_processed()
  - notify_farm_approved()
  - notify_farm_rejected()
  - notify_order_overdue()
  - send_bulk_reminders()
```

### Integration Points

SMS notifications are automatically sent from:

1. **ProcurementWorkflowService**
   - `assign_farm_to_order()` → `notify_farm_assignment()`
   - `farm_accept_assignment()` → `notify_assignment_accepted()`
   - `farm_reject_assignment()` → `notify_assignment_rejected()`
   - `mark_ready_for_delivery()` → `notify_ready_for_delivery()`
   - `approve_invoice()` → `notify_invoice_generated()`
   - `process_payment()` → `notify_payment_processed()`

2. **Farm Approval Workflow**
   - Farm approved → `notify_farm_approved()`
   - Farm rejected → `notify_farm_rejected()`

3. **Scheduled Tasks** (via Celery)
   - Overdue order reminders
   - Bulk reminder campaigns

### Error Handling

All SMS sending is wrapped in try-except blocks:
```python
try:
    notification_service.notify_farm_assignment(assignment)
except Exception as e:
    logger.warning(f"Failed to send notification: {str(e)}")
    # System continues - SMS failure doesn't break workflow
```

## Development Mode

### Console Simulation
When SMS is not configured, messages are printed to console:

```python
SMS_ENABLED=False  # or credentials not set
# Output:
============================================================
📱 SIMULATED SMS
To: +233244123456
Message: YEA PMS: New order assigned! ...
Estimated Cost: GHS 0.1200
============================================================
```

### Testing Without Real SMS
```bash
# Set in .env
SMS_ENABLED=False

# All notifications will be logged but not sent
# Perfect for development and testing
```

## Production Deployment

### Pre-Launch Checklist

- [ ] **Hubtel Account**
  - [ ] Account created and verified
  - [ ] API credentials obtained
  - [ ] Sender ID registered and approved
  - [ ] Initial account top-up completed

- [ ] **Configuration**
  - [ ] Environment variables set in production
  - [ ] SMS_ENABLED=True
  - [ ] Credentials validated

- [ ] **Testing**
  - [ ] Test all notification types
  - [ ] Verify phone number formats
  - [ ] Check message content
  - [ ] Confirm delivery reports

- [ ] **Monitoring**
  - [ ] Set up account balance alerts
  - [ ] Configure delivery report webhook
  - [ ] Log rotation configured
  - [ ] Error alerting in place

- [ ] **Documentation**
  - [ ] Team trained on SMS system
  - [ ] Emergency contact procedures
  - [ ] Cost monitoring process

### Monitoring & Maintenance

#### Check Account Balance
```bash
python manage.py test_sms --check-balance
```

#### View SMS Logs
```bash
# In Django logs
grep "SMS" logs/django.log

# In Hubtel dashboard
# Visit https://developers.hubtel.com/dashboard
```

#### Cost Monitoring
- Set up monthly budget alerts in Hubtel dashboard
- Review usage reports weekly
- Track cost per notification type

### Scaling Considerations

**Bulk Sending**
```python
from procurement.services.notification_service import get_notification_service

notification_service = get_notification_service()

# Send to multiple farms
assignments = OrderAssignment.objects.filter(status='pending')
notification_service.send_bulk_reminders(
    assignments=assignments,
    message_template="YEA PMS: Reminder - Order {order_number} deadline is {deadline}"
)
```

**Rate Limiting**
Hubtel has API rate limits:
- Check current limits in documentation
- Implement delays for bulk operations if needed
- Use Celery tasks for large batches

## Troubleshooting

### Common Issues

**1. SMS Not Sending**
```
Error: Hubtel credentials not configured
```
**Solution:** Set HUBTEL_CLIENT_ID and HUBTEL_CLIENT_SECRET in .env

**2. Invalid Phone Number**
```
Error: Invalid phone number format
```
**Solution:** Ensure phone numbers are in E.164 format (+233XXXXXXXXX)

**3. Insufficient Balance**
```
Error: Insufficient account balance
```
**Solution:** Top up Hubtel account

**4. Sender ID Not Approved**
```
Error: Sender ID not authorized
```
**Solution:** Register and wait for Hubtel to approve your Sender ID

### Debug Mode

Enable detailed logging:
```python
# settings.py
LOGGING = {
    'loggers': {
        'core.sms_service': {
            'level': 'DEBUG',
        },
        'procurement.services.notification_service': {
            'level': 'DEBUG',
        },
    },
}
```

## API Reference

### HubtelSMSService

```python
from core.sms_service import get_sms_service

sms_service = get_sms_service()

# Send single SMS
result = sms_service.send_sms(
    phone_number="+233244123456",
    message="Your message here",
    reference="ORDER-001"  # Optional
)

# Send bulk SMS
recipients = [
    {'phone': '+233244123456', 'message': 'Message 1'},
    {'phone': '+233244789012', 'message': 'Message 2'},
]
result = sms_service.send_bulk_sms(recipients)

# Check balance
balance = sms_service.get_account_balance()
```

### ProcurementNotificationService

```python
from procurement.services.notification_service import get_notification_service

notification_service = get_notification_service()

# Notify about assignment
notification_service.notify_farm_assignment(assignment)

# Notify about payment
notification_service.notify_payment_processed(invoice)

# Send bulk reminders
notification_service.send_bulk_reminders(
    assignments=pending_assignments,
    message_template="Reminder: {order_number} due {deadline}"
)
```

## Support

### Hubtel Support
- **Email:** support@hubtel.com
- **Phone:** +233 30 281 0100
- **Documentation:** https://developers.hubtel.com/
- **Developer Portal:** https://developers.hubtel.com/

### Internal Support
- Check `logs/django.log` for SMS errors
- Review `.env.hubtel.example` for configuration
- Run `python manage.py test_sms` for diagnostics

## Future Enhancements

### Planned Features
- [ ] Delivery report webhook handling
- [ ] SMS templates management interface
- [ ] Multi-language SMS support (English, Twi, Ewe)
- [ ] SMS scheduling (send at specific time)
- [ ] Opt-out management
- [ ] SMS analytics dashboard
- [ ] A/B testing for message templates
- [ ] WhatsApp Business API integration

### Alternative Providers
The system is designed to support multiple SMS providers:
- Hubtel (Current)
- Arkesel
- Twilio
- Africa's Talking

To switch providers, update `SMS_PROVIDER` in settings.

---

**Last Updated:** October 26, 2025  
**Version:** 1.0.0  
**Status:** Production Ready ✅
