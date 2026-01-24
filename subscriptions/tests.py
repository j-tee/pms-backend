"""
Comprehensive Tests for Subscription and Payment Lifecycle

These tests cover:
1. Subscription creation and activation
2. Payment processing
3. Subscription expiration and grace period
4. Subscription suspension
5. Subscription cancellation
6. Reactivation after payment
7. Consistency between Farm model and Subscription model
8. Marketplace visibility rules

Edge cases covered:
- Farm subscription_type stays in sync with Subscription status
- marketplace_enabled reflects actual access
- has_marketplace_access property returns correct value
- Visibility in public marketplace is correctly determined
"""

import pytest
import uuid
from decimal import Decimal
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase
from rest_framework import status

from subscriptions.models import SubscriptionPlan, Subscription, SubscriptionPayment
from farms.models import Farm

User = get_user_model()


def create_test_farm(user, unique_id=None, **kwargs):
    """
    Factory function to create a Farm with all required fields.
    
    This centralizes farm creation to avoid duplicating the complex
    required fields across multiple tests.
    """
    if unique_id is None:
        unique_id = uuid.uuid4().hex[:8]
    
    defaults = {
        'user': user,
        # Section 1.1: Basic Info
        'first_name': 'Test',
        'last_name': 'Farmer',
        'date_of_birth': '1985-06-15',
        'gender': 'Male',
        'ghana_card_number': f'GHA-{unique_id.upper()[:9]}-X',
        # Section 1.2: Contact
        'primary_phone': f'+23324555{unique_id[:4]}',
        'residential_address': 'Test Farm, Accra',
        'primary_constituency': 'Tema West',  # Important: region derived from this
        # Section 1.3: Next of Kin
        'nok_full_name': 'Test NOK',
        'nok_relationship': 'Spouse',
        'nok_phone': '+233241000000',
        # Section 1.4: Education
        'education_level': 'Tertiary',
        'literacy_level': 'Can Read & Write',
        'years_in_poultry': Decimal('5.0'),
        # Section 2: Farm Info
        'farm_name': f'Test Farm {unique_id}',
        'ownership_type': 'Sole Proprietorship',
        'tin': f'T{unique_id.upper()[:10]}',
        # Section 4: Infrastructure
        'number_of_poultry_houses': 1,
        'total_bird_capacity': 500,
        'current_bird_count': 400,
        'housing_type': 'Deep Litter',
        'total_infrastructure_value_ghs': Decimal('15000.00'),  # Required field
        # Section 5: Production
        'primary_production_type': 'Layers',
        'planned_production_start_date': '2025-01-01',
        # Section 7: Financial
        'initial_investment_amount': Decimal('30000.00'),
        'funding_source': ['Personal Savings'],
        'monthly_operating_budget': Decimal('5000.00'),
        'expected_monthly_revenue': Decimal('8000.00'),
        # Status
        'application_status': 'Approved',
        'farm_status': 'Active',
        # Marketplace
        'marketplace_enabled': False,
        'subscription_type': 'none',
    }
    
    # Override with any provided kwargs
    defaults.update(kwargs)
    
    return Farm.objects.create(**defaults)


class SubscriptionModelTestCase(TestCase):
    """Test cases for Subscription model methods and properties"""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data for all test methods"""
        cls.unique_id = uuid.uuid4().hex[:8]
        
        # Create subscription plan
        cls.plan = SubscriptionPlan.objects.create(
            name='Standard Marketplace',
            description='Standard marketplace access',
            price_monthly=Decimal('50.00'),
            trial_period_days=14,
            is_active=True,
        )
        
        # Create farmer user
        cls.farmer_user = User.objects.create_user(
            username=f'testfarmer_{cls.unique_id}',
            email=f'farmer_{cls.unique_id}@test.com',
            phone=f'+23324111{cls.unique_id[:4]}',
            password='testpass123',
            role='FARMER',
        )
    
    def setUp(self):
        """Set up for each test method"""
        self.test_uid = uuid.uuid4().hex[:8]
        
        # Create farm for farmer using factory function
        self.farm = create_test_farm(
            user=self.farmer_user,
            unique_id=self.test_uid,
            primary_phone=f'+23324222{self.test_uid[:4]}',
        )
        
        # Create subscription
        today = timezone.now().date()
        self.subscription = Subscription.objects.create(
            farm=self.farm,
            plan=self.plan,
            status='active',
            start_date=today,
            current_period_start=today,
            current_period_end=today + relativedelta(months=1),
            next_billing_date=today + relativedelta(months=1),
        )
        
        # Update farm to reflect active subscription
        self.farm.marketplace_enabled = True
        self.farm.subscription_type = 'standard'
        self.farm.save()
    
    def tearDown(self):
        """Clean up after each test"""
        Subscription.objects.filter(farm=self.farm).delete()
        self.farm.delete()
    
    # =========================================================================
    # SUBSCRIPTION STATUS TESTS
    # =========================================================================
    
    def test_is_active_property_active_status(self):
        """Test is_active property returns True for active subscription"""
        self.subscription.status = 'active'
        self.subscription.save()
        
        self.assertTrue(self.subscription.is_active)
    
    def test_is_active_property_trial_status(self):
        """Test is_active property returns True for trial subscription"""
        self.subscription.status = 'trial'
        self.subscription.save()
        
        self.assertTrue(self.subscription.is_active)
    
    def test_is_active_property_suspended_status(self):
        """Test is_active property returns False for suspended subscription"""
        self.subscription.status = 'suspended'
        self.subscription.save()
        
        self.assertFalse(self.subscription.is_active)
    
    def test_is_active_property_cancelled_status(self):
        """Test is_active property returns False for cancelled subscription"""
        self.subscription.status = 'cancelled'
        self.subscription.save()
        
        self.assertFalse(self.subscription.is_active)
    
    def test_is_active_property_past_due_status(self):
        """Test is_active property returns False for past_due subscription"""
        self.subscription.status = 'past_due'
        self.subscription.save()
        
        self.assertFalse(self.subscription.is_active)
    
    def test_is_in_grace_period_property(self):
        """Test is_in_grace_period property"""
        self.subscription.status = 'past_due'
        self.subscription.save()
        
        self.assertTrue(self.subscription.is_in_grace_period)
        
        self.subscription.status = 'active'
        self.subscription.save()
        
        self.assertFalse(self.subscription.is_in_grace_period)
    
    # =========================================================================
    # SUSPENSION TESTS - CRITICAL: Verify farm sync
    # =========================================================================
    
    def test_suspend_updates_subscription_status(self):
        """Test suspend() method updates subscription status"""
        self.subscription.suspend(reason="Test suspension")
        
        self.assertEqual(self.subscription.status, 'suspended')
        self.assertIsNotNone(self.subscription.suspension_date)
    
    def test_suspend_disables_farm_marketplace(self):
        """Test suspend() disables farm marketplace_enabled"""
        self.farm.marketplace_enabled = True
        self.farm.subscription_type = 'standard'
        self.farm.save()
        
        self.subscription.suspend(reason="Test suspension")
        
        self.farm.refresh_from_db()
        self.assertFalse(self.farm.marketplace_enabled)
    
    def test_suspend_keeps_subscription_type_as_standard(self):
        """
        Test suspend() keeps subscription_type as 'standard'.
        
        This is intentional: suspended users can easily reactivate,
        so we keep their subscription_type to indicate they were subscribed.
        """
        self.farm.subscription_type = 'standard'
        self.farm.save()
        
        self.subscription.suspend(reason="Test suspension")
        
        self.farm.refresh_from_db()
        # subscription_type should still be 'standard' (not 'none')
        self.assertEqual(self.farm.subscription_type, 'standard')
    
    # =========================================================================
    # CANCELLATION TESTS - CRITICAL: Verify farm sync
    # =========================================================================
    
    def test_cancel_updates_subscription_status(self):
        """Test cancel() method updates subscription status"""
        self.subscription.cancel(reason="Test cancellation")
        
        self.assertEqual(self.subscription.status, 'cancelled')
        self.assertIsNotNone(self.subscription.cancelled_at)
        self.assertEqual(self.subscription.cancellation_reason, "Test cancellation")
    
    def test_cancel_disables_farm_marketplace(self):
        """Test cancel() disables farm marketplace_enabled"""
        self.farm.marketplace_enabled = True
        self.farm.save()
        
        self.subscription.cancel(reason="Test cancellation")
        
        self.farm.refresh_from_db()
        self.assertFalse(self.farm.marketplace_enabled)
    
    def test_cancel_resets_subscription_type_to_none(self):
        """
        Test cancel() resets subscription_type to 'none'.
        
        Unlike suspend, cancel means the user has chosen to not continue,
        so we fully reset their subscription state.
        """
        self.farm.subscription_type = 'standard'
        self.farm.save()
        
        self.subscription.cancel(reason="Test cancellation")
        
        self.farm.refresh_from_db()
        self.assertEqual(self.farm.subscription_type, 'none')
    
    def test_cancel_stores_cancelled_by_user(self):
        """Test cancel() stores the user who cancelled"""
        self.subscription.cancel(reason="Test", cancelled_by=self.farmer_user)
        
        self.assertEqual(self.subscription.cancelled_by, self.farmer_user)
    
    # =========================================================================
    # REACTIVATION TESTS - CRITICAL: Verify farm sync
    # =========================================================================
    
    def test_reactivate_updates_subscription_status(self):
        """Test reactivate() changes status to active"""
        self.subscription.status = 'suspended'
        self.subscription.suspension_date = timezone.now().date()
        self.subscription.save()
        
        self.subscription.reactivate()
        
        self.assertEqual(self.subscription.status, 'active')
        self.assertIsNone(self.subscription.suspension_date)
    
    def test_reactivate_enables_farm_marketplace(self):
        """Test reactivate() enables farm marketplace_enabled"""
        self.subscription.status = 'suspended'
        self.farm.marketplace_enabled = False
        self.farm.save()
        
        self.subscription.reactivate()
        
        self.farm.refresh_from_db()
        self.assertTrue(self.farm.marketplace_enabled)
    
    def test_reactivate_sets_subscription_type_to_standard(self):
        """Test reactivate() sets subscription_type to 'standard'"""
        self.subscription.status = 'suspended'
        self.farm.subscription_type = 'none'
        self.farm.save()
        
        self.subscription.reactivate()
        
        self.farm.refresh_from_db()
        self.assertEqual(self.farm.subscription_type, 'standard')
    
    def test_reactivate_extends_billing_period(self):
        """Test reactivate() extends the billing period by 1 month"""
        self.subscription.status = 'suspended'
        self.subscription.save()
        
        before_reactivate = timezone.now().date()
        self.subscription.reactivate()
        
        self.assertEqual(self.subscription.current_period_start, before_reactivate)
        self.assertEqual(
            self.subscription.current_period_end,
            before_reactivate + relativedelta(months=1)
        )


class FarmMarketplaceAccessTestCase(TestCase):
    """Test cases for Farm model marketplace access properties"""
    
    @classmethod
    def setUpTestData(cls):
        cls.unique_id = uuid.uuid4().hex[:8]
        
        cls.plan = SubscriptionPlan.objects.create(
            name='Standard MKT',
            price_monthly=Decimal('50.00'),
            is_active=True,
        )
        
        cls.farmer_user = User.objects.create_user(
            username=f'marketplacetester_{cls.unique_id}',
            phone=f'+23324999{cls.unique_id[:4]}',
            password='testpass123',
            role='FARMER',
        )
    
    def setUp(self):
        self.test_uid = uuid.uuid4().hex[:8]
        self.farm = create_test_farm(
            user=self.farmer_user,
            unique_id=self.test_uid,
            primary_phone=f'+23324888{self.test_uid[:4]}',
        )
    
    def tearDown(self):
        Subscription.objects.filter(farm=self.farm).delete()
        self.farm.delete()
    
    # =========================================================================
    # has_marketplace_access PROPERTY TESTS
    # =========================================================================
    
    def test_has_marketplace_access_no_subscription(self):
        """Test has_marketplace_access is False when no subscription"""
        self.farm.marketplace_enabled = False
        self.farm.subscription_type = 'none'
        self.farm.save()
        
        self.assertFalse(self.farm.has_marketplace_access)
    
    def test_has_marketplace_access_standard_subscription_with_active_subscription(self):
        """Test has_marketplace_access is True with standard subscription and active Subscription"""
        today = timezone.now().date()
        Subscription.objects.create(
            farm=self.farm,
            plan=self.plan,
            status='active',
            start_date=today,
            current_period_start=today,
            current_period_end=today + relativedelta(months=1),
            next_billing_date=today + relativedelta(months=1),
        )
        
        self.farm.marketplace_enabled = True
        self.farm.subscription_type = 'standard'
        self.farm.save()
        self.farm.refresh_from_db()
        
        self.assertTrue(self.farm.has_marketplace_access)
    
    def test_has_marketplace_access_standard_subscription_no_subscription_object(self):
        """
        Test has_marketplace_access is False when subscription_type='standard'
        but there's no actual Subscription object with active/trial status.
        
        This is the bug scenario: Farm thinks it has access but Subscription
        object is missing or in wrong status.
        """
        # No Subscription object - only farm fields set
        self.farm.marketplace_enabled = True
        self.farm.subscription_type = 'standard'
        self.farm.save()
        self.farm.refresh_from_db()
        
        # Should be False because there's no Subscription object
        self.assertFalse(self.farm.has_marketplace_access)
    
    def test_has_marketplace_access_marketplace_disabled(self):
        """Test has_marketplace_access is False even with subscription_type if marketplace_enabled is False"""
        self.farm.marketplace_enabled = False
        self.farm.subscription_type = 'standard'
        self.farm.save()
        
        # Both must be true: marketplace_enabled AND valid subscription
        self.assertFalse(self.farm.has_marketplace_access)
    
    # =========================================================================
    # CONSISTENCY TESTS - Farm and Subscription must stay in sync
    # =========================================================================
    
    def test_consistency_active_subscription(self):
        """Test that active subscription keeps farm fields in sync"""
        today = timezone.now().date()
        subscription = Subscription.objects.create(
            farm=self.farm,
            plan=self.plan,
            status='active',
            start_date=today,
            current_period_start=today,
            current_period_end=today + relativedelta(months=1),
            next_billing_date=today + relativedelta(months=1),
        )
        
        # Simulate payment completion
        self.farm.marketplace_enabled = True
        self.farm.subscription_type = 'standard'
        self.farm.save()
        
        # Both should indicate active access
        self.assertTrue(subscription.is_active)
        self.assertTrue(self.farm.has_marketplace_access)
    
    def test_consistency_after_suspension(self):
        """Test consistency after subscription suspension"""
        today = timezone.now().date()
        subscription = Subscription.objects.create(
            farm=self.farm,
            plan=self.plan,
            status='active',
            start_date=today,
            current_period_start=today,
            current_period_end=today + relativedelta(months=1),
            next_billing_date=today + relativedelta(months=1),
        )
        
        self.farm.marketplace_enabled = True
        self.farm.subscription_type = 'standard'
        self.farm.save()
        
        # Suspend
        subscription.suspend(reason="Test")
        self.farm.refresh_from_db()
        
        # Subscription shows suspended
        self.assertFalse(subscription.is_active)
        self.assertEqual(subscription.status, 'suspended')
        
        # Farm marketplace should be disabled but subscription_type remains 'standard'
        self.assertFalse(self.farm.marketplace_enabled)
        self.assertEqual(self.farm.subscription_type, 'standard')
        
        # has_marketplace_access should be False (marketplace_enabled is False)
        self.assertFalse(self.farm.has_marketplace_access)
    
    def test_consistency_after_cancellation(self):
        """Test consistency after subscription cancellation"""
        today = timezone.now().date()
        subscription = Subscription.objects.create(
            farm=self.farm,
            plan=self.plan,
            status='active',
            start_date=today,
            current_period_start=today,
            current_period_end=today + relativedelta(months=1),
            next_billing_date=today + relativedelta(months=1),
        )
        
        self.farm.marketplace_enabled = True
        self.farm.subscription_type = 'standard'
        self.farm.save()
        
        # Cancel
        subscription.cancel(reason="User cancelled")
        self.farm.refresh_from_db()
        
        # Subscription shows cancelled
        self.assertFalse(subscription.is_active)
        self.assertEqual(subscription.status, 'cancelled')
        
        # Farm should be fully reset
        self.assertFalse(self.farm.marketplace_enabled)
        self.assertEqual(self.farm.subscription_type, 'none')
        self.assertFalse(self.farm.has_marketplace_access)
    
    def test_consistency_after_reactivation(self):
        """Test consistency after subscription reactivation"""
        today = timezone.now().date()
        subscription = Subscription.objects.create(
            farm=self.farm,
            plan=self.plan,
            status='suspended',
            start_date=today - timedelta(days=30),
            current_period_start=today - timedelta(days=30),
            current_period_end=today - timedelta(days=1),
            next_billing_date=today - timedelta(days=1),
            suspension_date=today,
        )
        
        self.farm.marketplace_enabled = False
        self.farm.subscription_type = 'standard'  # Kept as standard even when suspended
        self.farm.save()
        
        # Reactivate
        subscription.reactivate()
        self.farm.refresh_from_db()
        
        # Everything should be active
        self.assertTrue(subscription.is_active)
        self.assertEqual(subscription.status, 'active')
        self.assertTrue(self.farm.marketplace_enabled)
        self.assertEqual(self.farm.subscription_type, 'standard')
        self.assertTrue(self.farm.has_marketplace_access)


class PaymentCompletionTestCase(TestCase):
    """Test cases for payment completion and subscription activation"""
    
    @classmethod
    def setUpTestData(cls):
        cls.unique_id = uuid.uuid4().hex[:8]
        
        cls.plan = SubscriptionPlan.objects.create(
            name='Standard PAY',
            price_monthly=Decimal('50.00'),
            is_active=True,
        )
        
        cls.farmer_user = User.objects.create_user(
            username=f'paymenttester_{cls.unique_id}',
            phone=f'+23324888{cls.unique_id[:4]}',
            password='testpass123',
            role='FARMER',
        )
    
    def setUp(self):
        self.test_uid = uuid.uuid4().hex[:8]
        self.farm = create_test_farm(
            user=self.farmer_user,
            unique_id=self.test_uid,
            primary_phone=f'+23324777{self.test_uid[:4]}',
        )
        
        today = timezone.now().date()
        self.subscription = Subscription.objects.create(
            farm=self.farm,
            plan=self.plan,
            status='trial',
            start_date=today,
            current_period_start=today,
            current_period_end=today + relativedelta(months=1),
            next_billing_date=today + relativedelta(months=1),
        )
    
    def tearDown(self):
        SubscriptionPayment.objects.filter(subscription=self.subscription).delete()
        self.subscription.delete()
        self.farm.delete()
    
    def test_mark_as_completed_activates_subscription(self):
        """Test that payment completion activates subscription"""
        today = timezone.now().date()
        payment = SubscriptionPayment.objects.create(
            subscription=self.subscription,
            amount=Decimal('50.00'),
            payment_method='mobile_money',
            payment_reference='SUB-TEST-12345678',
            momo_phone='0248888888',
            momo_provider='mtn',
            status='pending',
            payment_date=today,
            period_start=today,
            period_end=today + relativedelta(months=1),
        )
        
        # Complete payment
        payment.mark_as_completed(gateway_response={'id': 'test_txn_123'})
        
        # Refresh from DB
        self.subscription.refresh_from_db()
        self.farm.refresh_from_db()
        
        # Payment should be completed
        self.assertEqual(payment.status, 'completed')
        
        # Subscription should be active
        self.assertEqual(self.subscription.status, 'active')
        
        # Farm should have marketplace access
        self.assertTrue(self.farm.marketplace_enabled)
        self.assertEqual(self.farm.subscription_type, 'standard')
        self.assertTrue(self.farm.has_marketplace_access)
    
    def test_mark_as_completed_updates_billing_dates(self):
        """Test that payment completion updates billing dates"""
        today = timezone.now().date()
        period_end = today + relativedelta(months=1)
        
        payment = SubscriptionPayment.objects.create(
            subscription=self.subscription,
            amount=Decimal('50.00'),
            payment_method='mobile_money',
            payment_reference='SUB-TEST-DATES123',
            status='pending',
            payment_date=today,
            period_start=today,
            period_end=period_end,
        )
        
        payment.mark_as_completed()
        self.subscription.refresh_from_db()
        
        self.assertEqual(self.subscription.current_period_end, period_end)
        self.assertEqual(self.subscription.next_billing_date, period_end)
    
    def test_mark_as_failed_does_not_activate(self):
        """Test that failed payment does not activate subscription"""
        today = timezone.now().date()
        payment = SubscriptionPayment.objects.create(
            subscription=self.subscription,
            amount=Decimal('50.00'),
            payment_method='mobile_money',
            payment_reference='SUB-TEST-FAIL1234',
            status='pending',
            payment_date=today,
            period_start=today,
            period_end=today + relativedelta(months=1),
        )
        
        # Keep original values
        original_status = self.subscription.status
        original_marketplace = self.farm.marketplace_enabled
        original_sub_type = self.farm.subscription_type
        
        # Fail payment
        payment.mark_as_failed(reason="Test failure")
        
        # Refresh from DB
        self.subscription.refresh_from_db()
        self.farm.refresh_from_db()
        
        # Payment should be failed
        self.assertEqual(payment.status, 'failed')
        
        # Subscription should not change
        self.assertEqual(self.subscription.status, original_status)
        
        # Farm should not change
        self.assertEqual(self.farm.marketplace_enabled, original_marketplace)
        self.assertEqual(self.farm.subscription_type, original_sub_type)


class MarketplaceVisibilityTestCase(TestCase):
    """Test cases for marketplace visibility logic"""
    
    @classmethod
    def setUpTestData(cls):
        cls.unique_id = uuid.uuid4().hex[:8]
        
        cls.plan = SubscriptionPlan.objects.create(
            name='Standard VIS',
            price_monthly=Decimal('50.00'),
            is_active=True,
        )
        
        cls.farmer_user = User.objects.create_user(
            username=f'visibilitytester_{cls.unique_id}',
            phone=f'+23324777{cls.unique_id[:4]}',
            password='testpass123',
            role='FARMER',
        )
    
    def setUp(self):
        self.test_uid = uuid.uuid4().hex[:8]
        self.farm = create_test_farm(
            user=self.farmer_user,
            unique_id=self.test_uid,
            primary_phone=f'+23324666{self.test_uid[:4]}',
        )
    
    def tearDown(self):
        Subscription.objects.filter(farm=self.farm).delete()
        self.farm.delete()
    
    def _check_visibility(self):
        """
        Check visibility using the same logic as MarketplaceDashboardView.
        
        This replicates the exact check used in the view:
        - farm.marketplace_enabled AND
        - hasattr(farm, 'subscription') AND farm.subscription is not None AND
        - subscription.status in ['trial', 'active']
        """
        has_subscription = hasattr(self.farm, 'subscription') and self.farm.subscription is not None
        subscription_status = self.farm.subscription.status if has_subscription else None
        
        return (
            self.farm.marketplace_enabled and
            has_subscription and
            subscription_status in ['trial', 'active']
        )
    
    def test_visibility_no_subscription(self):
        """Test not visible without subscription"""
        self.farm.marketplace_enabled = True
        self.farm.subscription_type = 'standard'
        self.farm.save()
        
        # No Subscription object - should not be visible
        self.assertFalse(self._check_visibility())
    
    def test_visibility_trial_subscription(self):
        """Test visible during trial period"""
        today = timezone.now().date()
        Subscription.objects.create(
            farm=self.farm,
            plan=self.plan,
            status='trial',
            start_date=today,
            current_period_start=today,
            current_period_end=today + timedelta(days=14),
            next_billing_date=today + timedelta(days=14),
            trial_start=today,
            trial_end=today + timedelta(days=14),
        )
        
        self.farm.marketplace_enabled = True
        self.farm.subscription_type = 'standard'
        self.farm.save()
        self.farm.refresh_from_db()
        
        self.assertTrue(self._check_visibility())
    
    def test_visibility_active_subscription(self):
        """Test visible with active subscription"""
        today = timezone.now().date()
        Subscription.objects.create(
            farm=self.farm,
            plan=self.plan,
            status='active',
            start_date=today,
            current_period_start=today,
            current_period_end=today + relativedelta(months=1),
            next_billing_date=today + relativedelta(months=1),
        )
        
        self.farm.marketplace_enabled = True
        self.farm.subscription_type = 'standard'
        self.farm.save()
        self.farm.refresh_from_db()
        
        self.assertTrue(self._check_visibility())
    
    def test_visibility_past_due_subscription(self):
        """Test NOT visible with past_due subscription"""
        today = timezone.now().date()
        Subscription.objects.create(
            farm=self.farm,
            plan=self.plan,
            status='past_due',
            start_date=today - timedelta(days=30),
            current_period_start=today - timedelta(days=30),
            current_period_end=today - timedelta(days=1),
            next_billing_date=today - timedelta(days=1),
        )
        
        self.farm.marketplace_enabled = True
        self.farm.subscription_type = 'standard'
        self.farm.save()
        self.farm.refresh_from_db()
        
        self.assertFalse(self._check_visibility())
    
    def test_visibility_suspended_subscription(self):
        """Test NOT visible with suspended subscription"""
        today = timezone.now().date()
        Subscription.objects.create(
            farm=self.farm,
            plan=self.plan,
            status='suspended',
            start_date=today - timedelta(days=45),
            current_period_start=today - timedelta(days=45),
            current_period_end=today - timedelta(days=15),
            next_billing_date=today - timedelta(days=15),
            suspension_date=today - timedelta(days=10),
        )
        
        # Even with these fields set, visibility should be False
        self.farm.marketplace_enabled = False  # Would be set by suspend()
        self.farm.subscription_type = 'standard'  # Kept as standard
        self.farm.save()
        self.farm.refresh_from_db()
        
        self.assertFalse(self._check_visibility())
    
    def test_visibility_cancelled_subscription(self):
        """Test NOT visible with cancelled subscription"""
        today = timezone.now().date()
        Subscription.objects.create(
            farm=self.farm,
            plan=self.plan,
            status='cancelled',
            start_date=today - timedelta(days=60),
            current_period_start=today - timedelta(days=30),
            current_period_end=today - timedelta(days=1),
            next_billing_date=today - timedelta(days=1),
            cancelled_at=timezone.now() - timedelta(days=1),
        )
        
        # After cancellation, farm should be fully reset
        self.farm.marketplace_enabled = False
        self.farm.subscription_type = 'none'
        self.farm.save()
        self.farm.refresh_from_db()
        
        self.assertFalse(self._check_visibility())
    
    def test_visibility_marketplace_disabled(self):
        """Test NOT visible when marketplace_enabled is False even with active subscription"""
        today = timezone.now().date()
        Subscription.objects.create(
            farm=self.farm,
            plan=self.plan,
            status='active',
            start_date=today,
            current_period_start=today,
            current_period_end=today + relativedelta(months=1),
            next_billing_date=today + relativedelta(months=1),
        )
        
        # Even with active subscription, if marketplace_enabled is False, not visible
        self.farm.marketplace_enabled = False
        self.farm.subscription_type = 'standard'
        self.farm.save()
        self.farm.refresh_from_db()
        
        self.assertFalse(self._check_visibility())


class SubscriptionAPITestCase(APITestCase):
    """API-level tests for subscription endpoints"""
    
    @classmethod
    def setUpTestData(cls):
        cls.unique_id = uuid.uuid4().hex[:8]
        
        cls.plan = SubscriptionPlan.objects.create(
            name='Standard API',
            price_monthly=Decimal('50.00'),
            is_active=True,
        )
        
        cls.farmer_user = User.objects.create_user(
            username=f'apitester_{cls.unique_id}',
            phone=f'+23324666{cls.unique_id[:4]}',
            password='testpass123',
            role='FARMER',
        )
    
    def setUp(self):
        self.client = APIClient()
        self.test_uid = uuid.uuid4().hex[:8]
        self.farm = create_test_farm(
            user=self.farmer_user,
            unique_id=self.test_uid,
            primary_phone=f'+23324555{self.test_uid[:4]}',
            marketplace_enabled=True,
            subscription_type='standard',
        )
        
        today = timezone.now().date()
        self.subscription = Subscription.objects.create(
            farm=self.farm,
            plan=self.plan,
            status='active',
            start_date=today,
            current_period_start=today,
            current_period_end=today + relativedelta(months=1),
            next_billing_date=today + relativedelta(months=1),
        )
        
        self.client.force_authenticate(user=self.farmer_user)
    
    def tearDown(self):
        self.subscription.delete()
        self.farm.delete()
    
    def test_cancel_subscription_api(self):
        """Test subscription cancellation via API"""
        url = '/api/subscriptions/cancel/'
        
        response = self.client.post(url, {
            'reason': 'too_expensive',
            'confirm_cancellation': True,
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'cancelled')
        
        # Verify subscription was cancelled
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, 'cancelled')
        
        # Verify farm was updated
        self.farm.refresh_from_db()
        self.assertFalse(self.farm.marketplace_enabled)
        self.assertEqual(self.farm.subscription_type, 'none')
    
    def test_current_subscription_api(self):
        """Test getting current subscription status"""
        url = '/api/subscriptions/current/'
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'active')
        self.assertTrue(response.data['is_active'])
    
    def test_marketplace_access_info_api(self):
        """Test marketplace access info endpoint"""
        url = '/api/subscriptions/marketplace-access/'
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['has_marketplace_access'])
        self.assertEqual(response.data['subscription_status'], 'active')


class EdgeCasesTestCase(TestCase):
    """Edge cases and regression tests"""
    
    @classmethod
    def setUpTestData(cls):
        cls.unique_id = uuid.uuid4().hex[:8]
        
        cls.plan = SubscriptionPlan.objects.create(
            name='Standard EDGE',
            price_monthly=Decimal('50.00'),
            is_active=True,
        )
        
        cls.farmer_user = User.objects.create_user(
            username=f'edgecasetester_{cls.unique_id}',
            phone=f'+23324555{cls.unique_id[:4]}',
            password='testpass123',
            role='FARMER',
        )
    
    def setUp(self):
        self.test_uid = uuid.uuid4().hex[:8]
        self.farm = create_test_farm(
            user=self.farmer_user,
            unique_id=self.test_uid,
            primary_phone=f'+23324444{self.test_uid[:4]}',
        )
    
    def tearDown(self):
        Subscription.objects.filter(farm=self.farm).delete()
        self.farm.delete()
    
    def test_suspend_then_reactivate_then_cancel(self):
        """Test full lifecycle: active -> suspend -> reactivate -> cancel"""
        today = timezone.now().date()
        subscription = Subscription.objects.create(
            farm=self.farm,
            plan=self.plan,
            status='active',
            start_date=today,
            current_period_start=today,
            current_period_end=today + relativedelta(months=1),
            next_billing_date=today + relativedelta(months=1),
        )
        
        self.farm.marketplace_enabled = True
        self.farm.subscription_type = 'standard'
        self.farm.save()
        
        # Step 1: Suspend
        subscription.suspend(reason="Non-payment")
        self.farm.refresh_from_db()
        
        self.assertEqual(subscription.status, 'suspended')
        self.assertFalse(self.farm.marketplace_enabled)
        self.assertEqual(self.farm.subscription_type, 'standard')  # Kept
        
        # Step 2: Reactivate
        subscription.reactivate()
        self.farm.refresh_from_db()
        
        self.assertEqual(subscription.status, 'active')
        self.assertTrue(self.farm.marketplace_enabled)
        self.assertEqual(self.farm.subscription_type, 'standard')
        
        # Step 3: Cancel
        subscription.cancel(reason="User cancelled")
        self.farm.refresh_from_db()
        
        self.assertEqual(subscription.status, 'cancelled')
        self.assertFalse(self.farm.marketplace_enabled)
        self.assertEqual(self.farm.subscription_type, 'none')  # Reset
    
    def test_multiple_suspend_calls(self):
        """Test calling suspend multiple times doesn't cause issues"""
        today = timezone.now().date()
        subscription = Subscription.objects.create(
            farm=self.farm,
            plan=self.plan,
            status='active',
            start_date=today,
            current_period_start=today,
            current_period_end=today + relativedelta(months=1),
            next_billing_date=today + relativedelta(months=1),
        )
        
        self.farm.marketplace_enabled = True
        self.farm.subscription_type = 'standard'
        self.farm.save()
        
        # Suspend multiple times
        subscription.suspend(reason="First suspend")
        subscription.suspend(reason="Second suspend")
        subscription.suspend(reason="Third suspend")
        
        self.farm.refresh_from_db()
        
        # Should still be in correct state
        self.assertEqual(subscription.status, 'suspended')
        self.assertFalse(self.farm.marketplace_enabled)
    
    def test_cancel_already_cancelled(self):
        """Test cancelling an already cancelled subscription"""
        today = timezone.now().date()
        subscription = Subscription.objects.create(
            farm=self.farm,
            plan=self.plan,
            status='cancelled',
            start_date=today,
            current_period_start=today,
            current_period_end=today + relativedelta(months=1),
            next_billing_date=today + relativedelta(months=1),
            cancelled_at=timezone.now(),
        )
        
        self.farm.marketplace_enabled = False
        self.farm.subscription_type = 'none'
        self.farm.save()
        
        # Cancel again
        subscription.cancel(reason="Double cancel")
        
        self.farm.refresh_from_db()
        
        # Should still be cancelled
        self.assertEqual(subscription.status, 'cancelled')
        self.assertFalse(self.farm.marketplace_enabled)
        self.assertEqual(self.farm.subscription_type, 'none')
    
    def test_farm_without_subscription_object(self):
        """
        Test that farm without Subscription object behaves correctly.
        
        After fix: has_marketplace_access now checks actual Subscription status,
        so it should be False when no Subscription object exists.
        """
        # Farm claims to have standard subscription but no Subscription object
        self.farm.marketplace_enabled = True
        self.farm.subscription_type = 'standard'
        self.farm.save()
        self.farm.refresh_from_db()
        
        # After fix: has_marketplace_access now correctly checks Subscription
        # Since no Subscription exists, it should be False
        self.assertFalse(self.farm.has_marketplace_access)
        
        # Verify no Subscription object exists
        has_subscription = hasattr(self.farm, 'subscription')
        try:
            _ = self.farm.subscription
            has_subscription = True
        except Exception:
            has_subscription = False
        
        # This confirms no Subscription object
        self.assertFalse(has_subscription)
        
        # has_marketplace_access_legacy would still return True (old behavior)
        # This shows the fix - new property is consistent with visibility check
        self.assertTrue(self.farm.has_marketplace_access_legacy)
    
    def test_subscription_status_mismatch(self):
        """
        Test scenario where subscription_type says 'standard' but Subscription.status
        is not 'active' or 'trial'.
        
        After fix: has_marketplace_access now correctly returns False in this case.
        """
        today = timezone.now().date()
        subscription = Subscription.objects.create(
            farm=self.farm,
            plan=self.plan,
            status='past_due',  # Not active!
            start_date=today - timedelta(days=30),
            current_period_start=today - timedelta(days=30),
            current_period_end=today - timedelta(days=1),  # Expired
            next_billing_date=today - timedelta(days=1),
        )
        
        # Farm shows it has subscription type but status is past_due
        self.farm.marketplace_enabled = True
        self.farm.subscription_type = 'standard'
        self.farm.save()
        self.farm.refresh_from_db()
        
        # After fix: has_marketplace_access now correctly returns False
        # because Subscription.status is 'past_due' (not 'active' or 'trial')
        self.assertFalse(self.farm.has_marketplace_access)
        
        # Subscription.is_active confirms subscription is not active
        self.assertFalse(subscription.is_active)
        
        # Subscription status is past_due
        subscription_status = self.farm.subscription.status
        self.assertEqual(subscription_status, 'past_due')
        
        # has_marketplace_access_legacy would still return True (old buggy behavior)
        self.assertTrue(self.farm.has_marketplace_access_legacy)
