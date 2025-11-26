"""
Procurement SMS Notification Service.
Sends SMS notifications for procurement events.
"""
from typing import Optional
from django.conf import settings
from django.utils import timezone
from core.sms_service import get_sms_service


class ProcurementNotificationService:
    """
    Service for sending SMS notifications related to procurement workflow.
    """
    
    def __init__(self):
        self.sms_service = get_sms_service()
        self.enabled = getattr(settings, 'SMS_ENABLED', False)
    
    def notify_farm_assignment(self, assignment) -> dict:
        """
        Notify farm about new procurement order assignment.
        
        Args:
            assignment: OrderAssignment instance
        
        Returns:
            dict: SMS sending result
        """
        if not self.enabled:
            return {'success': False, 'error': 'SMS notifications disabled'}
        
        farmer = assignment.farm.owner
        if not farmer or not farmer.phone:
            return {'success': False, 'error': 'No phone number for farmer'}
        
        message = (
            f"YEA PMS: New order assigned!\n"
            f"Order: {assignment.order.order_number}\n"
            f"Quantity: {assignment.quantity_assigned:,} birds\n"
            f"Type: {assignment.order.production_type}\n"
            f"Deadline: {assignment.order.delivery_deadline.strftime('%d %b %Y')}\n"
            f"Please respond within 24 hours."
        )
        
        return self.sms_service.send_sms(
            phone_number=farmer.phone.as_e164,
            message=message,
            reference=f'ASSIGN-{assignment.assignment_number}'
        )
    
    def notify_assignment_accepted(self, assignment) -> dict:
        """
        Notify procurement officer that farm accepted assignment.
        
        Args:
            assignment: OrderAssignment instance
        
        Returns:
            dict: SMS sending result
        """
        if not self.enabled:
            return {'success': False, 'error': 'SMS notifications disabled'}
        
        officer = assignment.order.assigned_procurement_officer or assignment.order.created_by
        if not officer or not officer.phone:
            return {'success': False, 'error': 'No phone number for officer'}
        
        message = (
            f"YEA PMS: Assignment accepted!\n"
            f"Farm: {assignment.farm.farm_name}\n"
            f"Order: {assignment.order.order_number}\n"
            f"Quantity: {assignment.quantity_assigned:,} birds\n"
            f"Expected ready: {assignment.expected_ready_date.strftime('%d %b %Y') if assignment.expected_ready_date else 'TBD'}"
        )
        
        return self.sms_service.send_sms(
            phone_number=officer.phone.as_e164,
            message=message,
            reference=f'ACCEPT-{assignment.assignment_number}'
        )
    
    def notify_assignment_rejected(self, assignment, reason: str) -> dict:
        """
        Notify procurement officer that farm rejected assignment.
        
        Args:
            assignment: OrderAssignment instance
            reason: Rejection reason
        
        Returns:
            dict: SMS sending result
        """
        if not self.enabled:
            return {'success': False, 'error': 'SMS notifications disabled'}
        
        officer = assignment.order.assigned_procurement_officer or assignment.order.created_by
        if not officer or not officer.phone:
            return {'success': False, 'error': 'No phone number for officer'}
        
        message = (
            f"YEA PMS: Assignment REJECTED!\n"
            f"Farm: {assignment.farm.farm_name}\n"
            f"Order: {assignment.order.order_number}\n"
            f"Reason: {reason[:100]}\n"
            f"Action required: Reassign to another farm."
        )
        
        return self.sms_service.send_sms(
            phone_number=officer.phone.as_e164,
            message=message,
            reference=f'REJECT-{assignment.assignment_number}'
        )
    
    def notify_ready_for_delivery(self, assignment) -> dict:
        """
        Notify procurement officer that order is ready for delivery.
        
        Args:
            assignment: OrderAssignment instance
        
        Returns:
            dict: SMS sending result
        """
        if not self.enabled:
            return {'success': False, 'error': 'SMS notifications disabled'}
        
        officer = assignment.order.assigned_procurement_officer or assignment.order.created_by
        if not officer or not officer.phone:
            return {'success': False, 'error': 'No phone number for officer'}
        
        message = (
            f"YEA PMS: Order ready for delivery!\n"
            f"Farm: {assignment.farm.farm_name}\n"
            f"Order: {assignment.order.order_number}\n"
            f"Quantity: {assignment.quantity_assigned:,} birds\n"
            f"Ready since: {assignment.actual_ready_date.strftime('%d %b %Y') if assignment.actual_ready_date else 'Today'}\n"
            f"Schedule pickup ASAP."
        )
        
        return self.sms_service.send_sms(
            phone_number=officer.phone.as_e164,
            message=message,
            reference=f'READY-{assignment.assignment_number}'
        )
    
    def notify_delivery_confirmed(self, delivery) -> dict:
        """
        Notify farm owner about delivery confirmation and quality results.
        
        Args:
            delivery: DeliveryConfirmation instance
        
        Returns:
            dict: SMS sending result
        """
        if not self.enabled:
            return {'success': False, 'error': 'SMS notifications disabled'}
        
        farmer = delivery.assignment.farm.owner
        if not farmer or not farmer.phone:
            return {'success': False, 'error': 'No phone number for farmer'}
        
        quality_status = "PASSED ✓" if delivery.quality_passed else "FAILED ✗"
        
        message = (
            f"YEA PMS: Delivery confirmed!\n"
            f"Order: {delivery.assignment.order.order_number}\n"
            f"Quantity: {delivery.quantity_delivered:,} birds\n"
            f"Quality: {quality_status}\n"
        )
        
        if delivery.average_weight_per_bird:
            message += f"Avg weight: {delivery.average_weight_per_bird:.2f}kg\n"
        
        if delivery.quality_passed:
            message += "Invoice will be generated soon."
        else:
            message += f"Issues: {delivery.quality_notes[:50]}"
        
        return self.sms_service.send_sms(
            phone_number=farmer.phone.as_e164,
            message=message,
            reference=f'DELIVERY-{delivery.delivery_number}'
        )
    
    def notify_invoice_generated(self, invoice) -> dict:
        """
        Notify farm owner about invoice generation.
        
        Args:
            invoice: ProcurementInvoice instance
        
        Returns:
            dict: SMS sending result
        """
        if not self.enabled:
            return {'success': False, 'error': 'SMS notifications disabled'}
        
        farmer = invoice.farm.owner
        if not farmer or not farmer.phone:
            return {'success': False, 'error': 'No phone number for farmer'}
        
        message = (
            f"YEA PMS: Invoice generated!\n"
            f"Invoice: {invoice.invoice_number}\n"
            f"Order: {invoice.order.order_number}\n"
            f"Amount: GHS {invoice.total_amount:,.2f}\n"
        )
        
        if invoice.quality_deduction > 0:
            message += f"Quality deduction: GHS {invoice.quality_deduction:,.2f}\n"
        
        message += f"Due date: {invoice.due_date.strftime('%d %b %Y')}"
        
        return self.sms_service.send_sms(
            phone_number=farmer.phone.as_e164,
            message=message,
            reference=f'INVOICE-{invoice.invoice_number}'
        )
    
    def notify_payment_processed(self, invoice) -> dict:
        """
        Notify farm owner about payment processing.
        
        Args:
            invoice: ProcurementInvoice instance
        
        Returns:
            dict: SMS sending result
        """
        if not self.enabled:
            return {'success': False, 'error': 'SMS notifications disabled'}
        
        farmer = invoice.farm.owner
        if not farmer or not farmer.phone:
            return {'success': False, 'error': 'No phone number for farmer'}
        
        message = (
            f"YEA PMS: Payment processed! 💰\n"
            f"Invoice: {invoice.invoice_number}\n"
            f"Amount paid: GHS {invoice.total_amount:,.2f}\n"
            f"Payment date: {invoice.payment_date.strftime('%d %b %Y')}\n"
        )
        
        if invoice.payment_reference:
            message += f"Reference: {invoice.payment_reference}"
        
        message += "\nThank you for your service!"
        
        return self.sms_service.send_sms(
            phone_number=farmer.phone.as_e164,
            message=message,
            reference=f'PAYMENT-{invoice.invoice_number}'
        )
    
    def notify_order_overdue(self, assignment) -> dict:
        """
        Notify farm owner about overdue order.
        
        Args:
            assignment: OrderAssignment instance
        
        Returns:
            dict: SMS sending result
        """
        if not self.enabled:
            return {'success': False, 'error': 'SMS notifications disabled'}
        
        farmer = assignment.farm.owner
        if not farmer or not farmer.phone:
            return {'success': False, 'error': 'No phone number for farmer'}
        
        days_overdue = abs(assignment.order.days_until_deadline)
        
        message = (
            f"YEA PMS: URGENT - Order overdue!\n"
            f"Order: {assignment.order.order_number}\n"
            f"Days overdue: {days_overdue}\n"
            f"Quantity: {assignment.quantity_assigned:,} birds\n"
            f"Please update status immediately."
        )
        
        return self.sms_service.send_sms(
            phone_number=farmer.phone.as_e164,
            message=message,
            reference=f'OVERDUE-{assignment.assignment_number}'
        )
    
    def notify_farm_approved(self, farm) -> dict:
        """
        Notify farm owner about farm application approval.
        
        Args:
            farm: Farm instance
        
        Returns:
            dict: SMS sending result
        """
        if not self.enabled:
            return {'success': False, 'error': 'SMS notifications disabled'}
        
        farmer = farm.owner
        if not farmer or not farmer.phone:
            return {'success': False, 'error': 'No phone number for farmer'}
        
        message = (
            f"YEA PMS: Congratulations! 🎉\n"
            f"Your farm '{farm.farm_name}' has been APPROVED!\n"
            f"Farm ID: {farm.farm_id}\n"
            f"You can now receive procurement orders.\n"
            f"Welcome to the YEA Poultry Program!"
        )
        
        return self.sms_service.send_sms(
            phone_number=farmer.phone.as_e164,
            message=message,
            reference=f'FARM-APPROVED-{farm.farm_id}'
        )
    
    def notify_farm_rejected(self, farm, reason: str) -> dict:
        """
        Notify farm owner about farm application rejection.
        
        Args:
            farm: Farm instance
            reason: Rejection reason
        
        Returns:
            dict: SMS sending result
        """
        if not self.enabled:
            return {'success': False, 'error': 'SMS notifications disabled'}
        
        farmer = farm.owner
        if not farmer or not farmer.phone:
            return {'success': False, 'error': 'No phone number for farmer'}
        
        message = (
            f"YEA PMS: Farm application update\n"
            f"Farm: {farm.farm_name}\n"
            f"Status: Not approved\n"
            f"Reason: {reason[:100]}\n"
            f"You may reapply after addressing the issues."
        )
        
        return self.sms_service.send_sms(
            phone_number=farmer.phone.as_e164,
            message=message,
            reference=f'FARM-REJECTED-{farm.application_number}'
        )
    
    def send_bulk_reminders(self, assignments, message_template: str) -> dict:
        """
        Send bulk SMS reminders to multiple farms.
        
        Args:
            assignments: List of OrderAssignment instances
            message_template: Template string (can include {farm_name}, {order_number}, etc.)
        
        Returns:
            dict: Bulk sending results
        """
        if not self.enabled:
            return {'success': False, 'error': 'SMS notifications disabled'}
        
        recipients = []
        
        for assignment in assignments:
            farmer = assignment.farm.owner
            if not farmer or not farmer.phone:
                continue
            
            # Format message with assignment data
            message = message_template.format(
                farm_name=assignment.farm.farm_name,
                order_number=assignment.order.order_number,
                quantity=f"{assignment.quantity_assigned:,}",
                deadline=assignment.order.delivery_deadline.strftime('%d %b %Y'),
                days_left=assignment.order.days_until_deadline,
            )
            
            recipients.append({
                'phone': farmer.phone.as_e164,
                'message': message,
                'reference': f'REMINDER-{assignment.assignment_number}'
            })
        
        return self.sms_service.send_bulk_sms(recipients)


# Singleton instance
_notification_service = None


def get_notification_service() -> ProcurementNotificationService:
    """Get or create singleton notification service instance."""
    global _notification_service
    if _notification_service is None:
        _notification_service = ProcurementNotificationService()
    return _notification_service
