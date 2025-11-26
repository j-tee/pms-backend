"""
Farm Notification Service

Handles sending notifications to farmers and officers via:
- Email
- SMS (integration ready - needs provider config)
- In-app notifications
"""

from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
import logging

from farms.models import FarmNotification

logger = logging.getLogger(__name__)


class FarmNotificationService:
    """Service for sending farm-related notifications"""
    
    def __init__(self):
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@yea-pms.gov.gh')
        self.sms_enabled = getattr(settings, 'SMS_ENABLED', False)
        self.sms_provider = getattr(settings, 'SMS_PROVIDER', None)  # 'hubtel', 'arkesel', etc.
    
    def send_application_submitted(self, farm):
        """
        Notify farmer that application was successfully submitted.
        """
        subject = f"Application Submitted - {farm.application_id}"
        message = f"""
Dear {farm.first_name},

Your farm application has been successfully submitted for review.

Application ID: {farm.application_id}
Farm Name: {farm.farm_name}
Status: Pending Constituency Review

Your application will be reviewed by a constituency officer within 7 days.
You will receive notifications as your application progresses through the review stages.

Next Steps:
1. Constituency Review (7 days)
2. Regional Review (5 days)
3. National Final Approval (3 days)

You can track your application status by logging into your account.

If you have any questions, please contact your local constituency office.

Thank you for your interest in the YEA Poultry Development Program.

Best regards,
YEA Poultry Management Team
        """.strip()
        
        # Email
        self._create_and_send_notification(
            user=farm.user,
            farm=farm,
            notification_type='application_submitted',
            channel='email',
            subject=subject,
            message=message,
            action_url=f'/farms/{farm.id}/'
        )
        
        # SMS (if enabled)
        if self.sms_enabled:
            sms_message = f"YEA PMS: Application {farm.application_id} submitted. Review pending. Track status online."
            self._create_and_send_notification(
                user=farm.user,
                farm=farm,
                notification_type='application_submitted',
                channel='sms',
                subject='Application Submitted',
                message=sms_message
            )
        
        # In-app
        self._create_and_send_notification(
            user=farm.user,
            farm=farm,
            notification_type='application_submitted',
            channel='in_app',
            subject=subject,
            message=message,
            action_url=f'/farms/{farm.id}/'
        )
    
    def send_review_started(self, farm, officer, review_level):
        """
        Notify farmer that review has started at a specific level.
        """
        level_name = review_level.title()
        subject = f"{level_name} Review Started - {farm.application_id}"
        message = f"""
Dear {farm.first_name},

Your farm application is now under {level_name} review.

Application ID: {farm.application_id}
Farm Name: {farm.farm_name}
Review Level: {level_name}
Reviewer: {officer.get_full_name()}

The review process typically takes 3-7 days depending on the level.
You will be notified of the outcome.

Thank you for your patience.

Best regards,
YEA Poultry Management Team
        """.strip()
        
        # Email to farmer
        self._create_and_send_notification(
            user=farm.user,
            farm=farm,
            notification_type='review_started',
            channel='email',
            subject=subject,
            message=message,
            action_url=f'/farms/{farm.id}/'
        )
        
        # In-app
        self._create_and_send_notification(
            user=farm.user,
            farm=farm,
            notification_type='review_started',
            channel='in_app',
            subject=subject,
            message=f"{level_name} review started by {officer.get_full_name()}",
            action_url=f'/farms/{farm.id}/'
        )
    
    def send_approved_next_level(self, farm, officer, current_level, next_level):
        """
        Notify farmer that application was approved and forwarded.
        """
        current_name = current_level.title()
        next_name = next_level.title()
        
        subject = f"Approved at {current_name} - Now in {next_name} Review"
        message = f"""
Dear {farm.first_name},

Great news! Your farm application has been approved at the {current_name} level.

Application ID: {farm.application_id}
Farm Name: {farm.farm_name}
Status: Forwarded to {next_name} Review

Your application has been forwarded to the {next_name} level for the next stage of review.

Progress:
✅ Constituency Review - Approved
{'✅ Regional Review - Approved' if next_level == 'national' else '⏳ Regional Review - In Progress' if next_level == 'regional' else ''}
{'⏳ National Review - Pending' if next_level == 'national' else ''}

You will be notified when the {next_name} review begins.

Thank you for your patience.

Best regards,
YEA Poultry Management Team
        """.strip()
        
        # Email
        self._create_and_send_notification(
            user=farm.user,
            farm=farm,
            notification_type='approved_next_level',
            channel='email',
            subject=subject,
            message=message,
            action_url=f'/farms/{farm.id}/'
        )
        
        # SMS (if enabled)
        if self.sms_enabled:
            sms_message = f"YEA PMS: {farm.application_id} approved at {current_name}. Forwarded to {next_name} review."
            self._create_and_send_notification(
                user=farm.user,
                farm=farm,
                notification_type='approved_next_level',
                channel='sms',
                subject=subject,
                message=sms_message
            )
        
        # In-app
        self._create_and_send_notification(
            user=farm.user,
            farm=farm,
            notification_type='approved_next_level',
            channel='in_app',
            subject=subject,
            message=f"Approved at {current_name}! Now in {next_name} review.",
            action_url=f'/farms/{farm.id}/'
        )
    
    def send_final_approval(self, farm, officer, farm_id):
        """
        Notify farmer of final approval and Farm ID assignment.
        """
        subject = f"🎉 APPROVED! Farm ID Assigned: {farm_id}"
        message = f"""
Dear {farm.first_name},

Congratulations! Your farm application has been APPROVED!

Application ID: {farm.application_id}
Farm Name: {farm.farm_name}
OFFICIAL FARM ID: {farm_id}

Your farm is now officially registered in the YEA Poultry Development Program.

Next Steps:
1. Log in to your account to view your farm dashboard
2. Complete your farm profile if needed
3. Start recording your flock and production data
4. You can now participate in government procurement programs

Important Information:
- Your Farm ID ({farm_id}) will be used for all program activities
- Keep your production records up to date
- You may be eligible for support services and training
- Government procurement officers can now find your farm for orders

Welcome to the YEA Poultry Development Program!

Best regards,
YEA Poultry Management Team
        """.strip()
        
        # Email
        self._create_and_send_notification(
            user=farm.user,
            farm=farm,
            notification_type='final_approval',
            channel='email',
            subject=subject,
            message=message,
            action_url=f'/farms/{farm.id}/'
        )
        
        # SMS (if enabled)
        if self.sms_enabled:
            sms_message = f"YEA PMS: APPROVED! Farm ID: {farm_id}. Welcome to the program. Login to view details."
            self._create_and_send_notification(
                user=farm.user,
                farm=farm,
                notification_type='final_approval',
                channel='sms',
                subject='Farm Approved!',
                message=sms_message
            )
        
        # In-app
        self._create_and_send_notification(
            user=farm.user,
            farm=farm,
            notification_type='final_approval',
            channel='in_app',
            subject=subject,
            message=f"Your farm has been approved! Farm ID: {farm_id}",
            action_url=f'/farms/{farm.id}/'
        )
    
    def send_rejection(self, farm, officer, review_level, reason):
        """
        Notify farmer of application rejection.
        """
        level_name = review_level.title()
        subject = f"Application Review Decision - {farm.application_id}"
        message = f"""
Dear {farm.first_name},

After careful review, we regret to inform you that your farm application was not approved at the {level_name} level.

Application ID: {farm.application_id}
Farm Name: {farm.farm_name}
Review Level: {level_name}
Status: Not Approved

Reason:
{reason}

What's Next?
You may reapply after addressing the issues mentioned above. Please ensure all requirements are met before resubmitting.

If you have questions or need clarification, please contact:
- Your local constituency agriculture office
- YEA Poultry Program support team

We encourage you to work on the feedback provided and consider reapplying in the future.

Best regards,
YEA Poultry Management Team
        """.strip()
        
        # Email
        self._create_and_send_notification(
            user=farm.user,
            farm=farm,
            notification_type='rejected',
            channel='email',
            subject=subject,
            message=message,
            action_url=f'/farms/{farm.id}/'
        )
        
        # SMS (if enabled)
        if self.sms_enabled:
            sms_message = f"YEA PMS: {farm.application_id} not approved. Login for details and feedback."
            self._create_and_send_notification(
                user=farm.user,
                farm=farm,
                notification_type='rejected',
                channel='sms',
                subject='Application Decision',
                message=sms_message
            )
        
        # In-app
        self._create_and_send_notification(
            user=farm.user,
            farm=farm,
            notification_type='rejected',
            channel='in_app',
            subject=subject,
            message=f"Application not approved at {level_name} level. View feedback.",
            action_url=f'/farms/{farm.id}/'
        )
    
    def send_changes_requested(self, farm, officer, review_level, feedback, changes_list, deadline):
        """
        Notify farmer that reviewer requested changes.
        """
        level_name = review_level.title()
        changes_formatted = '\n'.join([f"• {change}" for change in changes_list])
        
        subject = f"Changes Requested - {farm.application_id}"
        message = f"""
Dear {farm.first_name},

The {level_name} reviewer has requested some changes to your farm application.

Application ID: {farm.application_id}
Farm Name: {farm.farm_name}
Deadline: {deadline.strftime('%B %d, %Y')}

Reviewer Feedback:
{feedback}

Required Changes:
{changes_formatted}

What to Do:
1. Log in to your account
2. Edit your farm application
3. Address all the points mentioned above
4. Resubmit your application

The deadline for submitting changes is {deadline.strftime('%B %d, %Y')}.

If you have questions about the requested changes, please contact the review office.

Best regards,
YEA Poultry Management Team
        """.strip()
        
        # Email
        self._create_and_send_notification(
            user=farm.user,
            farm=farm,
            notification_type='changes_requested',
            channel='email',
            subject=subject,
            message=message,
            action_url=f'/farms/{farm.id}/edit/'
        )
        
        # SMS (if enabled)
        if self.sms_enabled:
            sms_message = f"YEA PMS: Changes requested for {farm.application_id}. Deadline: {deadline.strftime('%b %d')}. Login to view details."
            self._create_and_send_notification(
                user=farm.user,
                farm=farm,
                notification_type='changes_requested',
                channel='sms',
                subject='Changes Requested',
                message=sms_message
            )
        
        # In-app
        self._create_and_send_notification(
            user=farm.user,
            farm=farm,
            notification_type='changes_requested',
            channel='in_app',
            subject=subject,
            message=f"Changes requested by {level_name} reviewer. Deadline: {deadline.strftime('%b %d')}",
            action_url=f'/farms/{farm.id}/edit/'
        )
    
    def send_changes_resubmitted(self, farm, officer, review_level):
        """
        Notify officer that farmer has resubmitted changes.
        """
        level_name = review_level.title()
        subject = f"Changes Resubmitted - {farm.farm_name}"
        message = f"""
Dear {officer.get_full_name()},

The farmer has resubmitted their application with the requested changes.

Farm: {farm.farm_name}
Application ID: {farm.application_id}
Farmer: {farm.first_name} {farm.last_name}
Review Level: {level_name}

The application is ready for your re-review.

Please log in to continue the review process.

Best regards,
YEA PMS System
        """.strip()
        
        # Email to officer
        self._create_and_send_notification(
            user=officer,
            farm=farm,
            notification_type='reminder',
            channel='email',
            subject=subject,
            message=message,
            action_url=f'/admin/farms/farmapprovalqueue/'
        )
        
        # In-app to officer
        self._create_and_send_notification(
            user=officer,
            farm=farm,
            notification_type='reminder',
            channel='in_app',
            subject=subject,
            message=f"{farm.farm_name} - Changes resubmitted for review",
            action_url=f'/admin/farms/farm/{farm.id}/'
        )
    
    def _create_and_send_notification(self, user, farm, notification_type, channel, subject, message, action_url=''):
        """
        Internal method to create and send notification.
        """
        # Create notification record
        notification = FarmNotification.objects.create(
            user=user,
            farm=farm,
            notification_type=notification_type,
            channel=channel,
            subject=subject,
            message=message,
            action_url=action_url,
            status='pending'
        )
        
        # Send based on channel
        try:
            if channel == 'email':
                self._send_email(notification)
            elif channel == 'sms':
                self._send_sms(notification)
            elif channel == 'in_app':
                # In-app notifications are just stored in DB
                notification.mark_as_sent()
                notification.status = 'delivered'  # Immediately available
                notification.delivered_at = timezone.now()
                notification.save()
        except Exception as e:
            logger.error(f"Failed to send {channel} notification: {str(e)}")
            notification.mark_as_failed(str(e))
        
        return notification
    
    def _send_email(self, notification):
        """Send email notification"""
        try:
            send_mail(
                subject=notification.subject,
                message=notification.message,
                from_email=self.from_email,
                recipient_list=[notification.user.email],
                fail_silently=False,
            )
            notification.mark_as_sent()
            notification.mark_as_delivered()
            logger.info(f"Email sent to {notification.user.email}: {notification.subject}")
        except Exception as e:
            logger.error(f"Email send failed: {str(e)}")
            raise
    
    def _send_sms(self, notification):
        """
        Send SMS notification.
        
        NOTE: SMS integration is prepared but not active.
        Requires SMS provider credentials in settings:
        - SMS_ENABLED = True
        - SMS_PROVIDER = 'hubtel' | 'arkesel' | 'mnotify'
        - SMS_API_KEY = 'your-api-key'
        - SMS_SENDER_ID = 'YEA-PMS'
        """
        if not self.sms_enabled:
            logger.info(f"SMS not enabled. Would send to {notification.user.phone}: {notification.message}")
            notification.mark_as_failed("SMS not enabled in settings")
            return
        
        # Get phone number
        phone = str(notification.user.phone)
        if not phone:
            notification.mark_as_failed("User has no phone number")
            return
        
        # Provider-specific logic (ready for future implementation)
        if self.sms_provider == 'hubtel':
            success, message_id, cost = self._send_via_hubtel(phone, notification.message)
        elif self.sms_provider == 'arkesel':
            success, message_id, cost = self._send_via_arkesel(phone, notification.message)
        elif self.sms_provider == 'mnotify':
            success, message_id, cost = self._send_via_mnotify(phone, notification.message)
        else:
            notification.mark_as_failed(f"Unknown SMS provider: {self.sms_provider}")
            return
        
        if success:
            notification.sms_provider = self.sms_provider
            notification.sms_message_id = message_id
            notification.sms_cost = cost
            notification.mark_as_sent()
            notification.mark_as_delivered()
            logger.info(f"SMS sent via {self.sms_provider} to {phone}: {message_id}")
        else:
            notification.mark_as_failed(f"SMS send failed: {message_id}")  # message_id contains error
    
    def _send_via_hubtel(self, phone, message):
        """Send via Hubtel SMS API (Ghana)"""
        # TODO: Implement when SMS credentials are available
        # import requests
        # api_key = settings.SMS_API_KEY
        # sender_id = settings.SMS_SENDER_ID
        # 
        # response = requests.post(
        #     'https://smsc.hubtel.com/v1/messages/send',
        #     auth=(api_key, ''),
        #     json={
        #         'From': sender_id,
        #         'To': phone,
        #         'Content': message
        #     }
        # )
        # 
        # if response.status_code == 200:
        #     data = response.json()
        #     return True, data['MessageId'], 0.035  # ~GHS 0.035 per SMS
        # else:
        #     return False, response.text, 0
        
        logger.info(f"[Hubtel] Would send to {phone}: {message}")
        return False, "Hubtel not configured", 0
    
    def _send_via_arkesel(self, phone, message):
        """Send via Arkesel SMS API (Ghana)"""
        # TODO: Implement when SMS credentials are available
        logger.info(f"[Arkesel] Would send to {phone}: {message}")
        return False, "Arkesel not configured", 0
    
    def _send_via_mnotify(self, phone, message):
        """Send via MNotify SMS API (Ghana)"""
        # TODO: Implement when SMS credentials are available
        logger.info(f"[MNotify] Would send to {phone}: {message}")
        return False, "MNotify not configured", 0
