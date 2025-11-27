"""
Example: Testing Platform Settings

This script demonstrates how platform settings work.
Run in Django shell: python manage.py shell
"""

# Import models
from sales_revenue.models import PlatformSettings

# Get settings (creates defaults if none exist)
settings = PlatformSettings.get_settings()

print("=" * 60)
print("CURRENT PLATFORM SETTINGS")
print("=" * 60)

# Commission Structure
print("\n📊 COMMISSION STRUCTURE:")
print(f"  Tier 1: {settings.commission_tier_1_percentage}% (< GHS {settings.commission_tier_1_threshold})")
print(f"  Tier 2: {settings.commission_tier_2_percentage}% (GHS {settings.commission_tier_1_threshold}-{settings.commission_tier_2_threshold})")
print(f"  Tier 3: {settings.commission_tier_3_percentage}% (> GHS {settings.commission_tier_2_threshold})")
print(f"  Minimum: GHS {settings.commission_minimum_amount}")

# Test commission calculation
print("\n💰 COMMISSION CALCULATOR:")
test_amounts = [50, 100, 200, 500, 1000]
for amount in test_amounts:
    commission = settings.calculate_commission(amount)
    farmer_gets = amount - commission
    print(f"  GHS {amount:>4} → Commission: GHS {commission:>5.2f} | Farmer gets: GHS {farmer_gets:>6.2f}")

# Payment Configuration
print("\n⚙️  PAYMENT CONFIGURATION:")
print(f"  Fee bearer: {settings.get_paystack_fee_bearer_display()}")
print(f"  Settlement: {settings.get_paystack_settlement_schedule_display()}")
print(f"  Max retries: {settings.payment_retry_max_attempts}")
print(f"  Retry delay: {settings.payment_retry_delay_seconds}s")

# Refund Policy
print("\n🔄 REFUND POLICY:")
print(f"  Request window: {settings.refund_eligibility_hours} hours")
print(f"  Auto-refund after: {settings.payment_auto_refund_hours} hours")
print(f"  Refunds enabled: {'✅ Yes' if settings.enable_refunds else '❌ No'}")
print(f"  Auto-refunds: {'✅ Yes' if settings.enable_auto_refunds else '❌ No'}")

# Features
print("\n🚀 FEATURES:")
print(f"  Instant settlements: {'✅ Enabled' if settings.enable_instant_settlements else '❌ Disabled'}")

print("\n" + "=" * 60)
print("To modify settings: Django Admin > Platform Settings")
print("=" * 60)

# Example: Modify settings (admin only)
print("\n📝 EXAMPLE: How to change commission rates")
print("""
# In Django admin or shell:
settings.commission_tier_1_percentage = 6.0  # Increase from 5% to 6%
settings.commission_tier_2_percentage = 4.0  # Increase from 3% to 4%
settings.notes = "Increased commission to cover rising Paystack fees"
settings.save()

# New commission calculation:
commission = settings.calculate_commission(200)  # Now GHS 8.00 (was GHS 6.00)
""")
