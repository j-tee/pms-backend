# Fraud Detection System Guide

## Overview

The Poultry Management System includes a comprehensive fraud detection system designed to identify farmers who may be selling eggs and birds off-platform to avoid paying commission fees. This system analyzes production data, mortality rates, sales patterns, and behavioral changes to detect suspicious activities.

## The Problem

**Revenue Leakage Risk:**
- Farmers may bypass the platform and sell directly to customers to avoid commission fees
- Platform loses revenue from untracked sales
- Difficult to detect without proper monitoring

**How Farmers Might Cheat:**
1. **Under-reporting sales:** Sell 1000 eggs but only report 700 on platform
2. **Inflating mortality:** Report birds as dead when actually sold off-platform
3. **Direct customer sales:** Keep profitable customers off-platform
4. **Price manipulation:** Set high prices to push customers away, then sell directly
5. **Inventory hoarding:** Accumulate eggs to sell in bulk off-platform

## Detection Algorithms

The system uses 7 sophisticated algorithms to detect fraud:

### 1. Production vs Sales Mismatch
**What it detects:** Eggs produced but not sold on platform

**How it works:**
```
Expected pattern: 90% of eggs should be sold (10% waste/consumption)
Suspicious: Only 60% sold = 30% gap = HIGH RISK

Calculation:
- Production: 3000 eggs
- Sales: 2000 eggs  
- Expected loss: 300 eggs (10%)
- Actual gap: 1000 eggs (33%)
- Suspicious loss: 23% → Triggers HIGH alert
```

**Threshold:** >15% unexplained gap

**Risk weight:** +30 points

### 2. Mortality Anomalies
**What it detects:** Suspiciously high death rates

**How it works:**
```
Normal mortality: 0.05% per day (5 deaths per 10,000 birds)
Suspicious: 0.15% per day = 3x normal rate

Possible fraud:
- Farmer reports birds as "dead" 
- Actually sold off-platform
- Avoids paying commission
```

**Threshold:** >0.1% daily mortality rate

**Risk weight:** +25 points

### 3. Sudden Sales Drop
**What it detects:** Sales plummet while production remains stable

**How it works:**
```
Week 1: 2000 eggs sold
Week 2: 1200 eggs sold (-40%)
Production: Stable at 2500/week

Possible explanation:
- Farmer found direct customers
- Selling off-platform at higher margins
```

**Threshold:** >30% drop with stable/growing production

**Risk weight:** +35 points (HIGHEST - strong fraud indicator)

### 4. Inventory Hoarding
**What it detects:** Excessive unsold inventory accumulation

**How it works:**
```
Last 7 days:
- Produced: 5000 eggs
- Sold: 1000 eggs (20%)
- Unsold: 4000 eggs (80%)

Possible fraud:
- Accumulating for bulk off-platform sale
- Weekend market sales not reported
```

**Threshold:** >70% unsold inventory

**Risk weight:** +20 points

### 5. Reporting Gaps
**What it detects:** Missing daily production/mortality reports

**How it works:**
```
Last 30 days:
- Expected reports: 30
- Actual reports: 22
- Missing: 8 days (27%)

Possible fraud:
- Skipping reports on days with off-platform sales
- Avoiding data trail
```

**Threshold:** >20% missing reports

**Risk weight:** +15 points

### 6. Price Manipulation
**What it detects:** Pricing significantly above market to discourage platform sales

**How it works:**
```
Market average: GHS 0.60/egg
Farmer price: GHS 0.80/egg (+33%)

Strategy:
- High platform prices push customers away
- Farmer contacts customers directly offline
- Offers "discount" below platform price
- Bypasses commission entirely
```

**Threshold:** >15% above market average

**Risk weight:** +10 points

### 7. Customer Contact Pattern Changes
**What it detects:** Shift from platform to direct contact (Future implementation)

**Risk weight:** TBD

## Risk Scoring System

### Score Calculation
```python
total_score = 0

# Each algorithm adds points if triggered
if production_mismatch > 15%:
    total_score += 30
    
if mortality_rate > 0.1%:
    total_score += 25
    
if sales_drop > 30%:
    total_score += 35
    
# ... etc

# Final score: 0-100+
```

### Risk Levels

| Level | Score Range | Color | Action Required |
|-------|------------|-------|----------------|
| 🟢 **CLEAN** | 0-9 | Green | Continue normal monitoring |
| 🟡 **LOW** | 10-19 | Yellow | Monitor more closely |
| 🟠 **MEDIUM** | 20-39 | Orange | Customer verification surveys |
| 🔴 **HIGH** | 40-59 | Red | Schedule physical audit |
| 🚨 **CRITICAL** | 60+ | Dark Red | Immediate investigation required |

### Example Scenarios

**Scenario 1: Clean Farmer**
```
✓ Production: 2000 eggs, Sales: 1800 eggs (90%)
✓ Mortality: 0.03% per day (normal)
✓ Sales trend: Steady growth
✓ No inventory buildup
✓ 100% reporting compliance

Risk Score: 0 points → CLEAN
```

**Scenario 2: Suspicious Farmer**
```
⚠ Production: 3000 eggs, Sales: 2000 eggs (67% - gap of 23%)
⚠ Mortality: 0.12% per day (high)
⚠ Sales dropped 35% this week
✓ No inventory issues
⚠ 5 days missing reports (17%)

Risk Score: 30 + 25 + 35 + 15 = 105 points → CRITICAL
```

## Using the System

### 1. Manual Fraud Detection

Run on-demand fraud scans:

```bash
# Scan all farms
python manage.py detect_fraud

# Scan specific farm
python manage.py detect_fraud --farm-id abc-123-xyz

# Analyze last 60 days
python manage.py detect_fraud --days 60

# Only show HIGH+ alerts
python manage.py detect_fraud --min-risk HIGH

# Only active farms
python manage.py detect_fraud --active-only

# Save all results (including CLEAN farms)
python manage.py detect_fraud --save-all
```

### 2. Admin Interface

Access fraud alerts in Django Admin:

1. Navigate to **Sales & Revenue > Fraud Alerts**
2. View alerts sorted by risk level
3. Filter by:
   - Risk level (CRITICAL, HIGH, etc.)
   - Status (PENDING, UNDER_INVESTIGATION, CONFIRMED, etc.)
   - Date range
4. Review alert details with formatted display
5. Take actions:
   - **Mark as False Positive:** No fraud detected
   - **Schedule Audit:** Send team for physical verification
   - **Confirm Fraud:** Take penalty action

### 3. Automated Monitoring (Recommended)

Set up nightly Celery task:

```python
# tasks.py
from celery import shared_task
from django.core.management import call_command

@shared_task
def nightly_fraud_scan():
    """Run fraud detection every night at 2 AM"""
    call_command('detect_fraud', '--save-all', '--min-risk', 'MEDIUM')
```

Configure in `settings.py`:
```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'nightly-fraud-detection': {
        'task': 'sales_revenue.tasks.nightly_fraud_scan',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
}
```

### 4. Alert Workflow

**Step 1: Detection**
- System runs analysis (manual or automated)
- Generates FraudAlert if risk score > 10
- Stores detailed alert information

**Step 2: Review**
- Admin reviews alert in Django Admin
- Examines formatted alert details
- Checks production vs sales data
- Reviews farmer history

**Step 3: Investigation**
- **LOW/MEDIUM:** Send customer verification survey
- **HIGH:** Schedule physical farm audit
- **CRITICAL:** Immediate investigation + account freeze

**Step 4: Resolution**
- Mark as **False Positive** if legitimate
- Mark as **Confirmed** if fraud detected
- Record action taken and notes

**Step 5: Enforcement**
- Warning for first offense
- Commission increase for repeat offenders
- Account suspension for severe cases
- Blacklist for egregious violations

## Prevention Strategies

Beyond detection, implement these preventive measures:

### 1. Random Audits
```python
# Monthly random audits
- Select 10% of farms randomly
- Include mix of all risk levels
- Physical inventory verification
- Customer contact verification
- Builds culture of accountability
```

### 2. Customer Verification
```python
# SMS surveys to random customers
"Hi! You purchased eggs from [Farm Name] on [Date]. 
Was this through our platform? Reply YES/NO"

# Analyze responses
- NO responses → Investigate farm
- Pattern of NO → High fraud risk
```

### 3. Incentive Alignment
```python
# Loyalty rewards
Tier 1 (New): 5% commission
Tier 2 (6mo, clean record): 3% commission  
Tier 3 (1yr, clean record): 2% commission

# Makes platform sales MORE profitable than cheating
```

### 4. Transparency Tools
```python
# Farmer dashboard showing their risk score
"Your Trust Score: 95/100 (Excellent)"

# Benefits of maintaining score:
- Lower commission rates
- Faster payouts
- Featured farm status
- Access to premium customers
```

### 5. Blockchain-Style Audit Trail
```python
# Immutable production records
- Each record linked to previous via hash
- Cannot be altered retroactively
- Tampering immediately detectable
```

### 6. Smart Contracts for Payouts
```python
# Automatic penalty deduction
if fraud_confirmed:
    payout_amount *= 0.5  # 50% penalty
    remaining_balance.freeze()
    require_manual_review = True
```

## Alert Details Structure

FraudAlerts store detailed information in JSON format:

```json
{
  "alerts": [
    {
      "type": "Production-Sales Mismatch",
      "severity": "HIGH",
      "message": "33.3% of eggs unaccounted for (expected <15%)",
      "details": {
        "total_production": 3000,
        "total_sales": 2000,
        "expected_loss_pct": 10,
        "actual_gap_pct": 33.3,
        "suspicious_loss": 23.3,
        "threshold": 15
      }
    },
    {
      "type": "Mortality Anomaly",
      "severity": "HIGH",
      "message": "Daily mortality rate 0.12% exceeds normal 0.05%",
      "details": {
        "avg_daily_mortality_rate": 0.12,
        "normal_rate": 0.05,
        "threshold": 0.1,
        "total_deaths": 120,
        "period_days": 30
      }
    }
  ],
  "risk_score": 55,
  "risk_level": "HIGH"
}
```

## Tuning the System

### Adjusting Thresholds

If you get too many false positives, adjust thresholds in `fraud_detection_service.py`:

```python
# Current thresholds (conservative)
PRODUCTION_MISMATCH_THRESHOLD = 0.15  # 15%
MORTALITY_THRESHOLD = 0.001           # 0.1%
SALES_DROP_THRESHOLD = 0.30           # 30%
INVENTORY_THRESHOLD = 0.70            # 70%

# More aggressive (catches more but more false positives)
PRODUCTION_MISMATCH_THRESHOLD = 0.10  # 10%
MORTALITY_THRESHOLD = 0.0008          # 0.08%

# More lenient (fewer false positives but might miss fraud)
PRODUCTION_MISMATCH_THRESHOLD = 0.20  # 20%
MORTALITY_THRESHOLD = 0.0015          # 0.15%
```

### Adjusting Risk Weights

Change point values for each algorithm:

```python
# Current weights
PRODUCTION_MISMATCH: 30 points
MORTALITY_ANOMALY: 25 points
SUDDEN_SALES_DROP: 35 points  # Highest weight
INVENTORY_HOARDING: 20 points
REPORTING_GAPS: 15 points
PRICE_MANIPULATION: 10 points

# Example: Increase weight of production mismatch
PRODUCTION_MISMATCH: 40 points
```

### Regional Variations

Different markets may need different thresholds:

```python
# Urban areas (higher sales velocity)
INVENTORY_THRESHOLD = 0.50  # Lower threshold

# Rural areas (slower sales)
INVENTORY_THRESHOLD = 0.80  # Higher threshold

# Seasonal adjustments
if month in [11, 12]:  # Holiday season
    SALES_DROP_THRESHOLD = 0.40  # Allow bigger drops
```

## Best Practices

### 1. Start Gentle
- Run analysis without enforcement for 2 weeks
- Calibrate thresholds based on real data
- Communicate with farmers about the system

### 2. Be Transparent
- Show farmers their risk scores
- Explain how scores are calculated
- Provide appeals process

### 3. Combine with Education
- Train farmers on platform benefits
- Show long-term value of compliance
- Highlight success stories

### 4. Review Regularly
- Weekly review of HIGH+ alerts
- Monthly analysis of false positive rate
- Quarterly threshold adjustments

### 5. Document Everything
- Record all investigations
- Track false positive rates
- Maintain audit trail

## Technical Implementation

### FraudAlert Model
```python
class FraudAlert(models.Model):
    farm = models.ForeignKey(Farm)
    detection_date = models.DateTimeField()
    risk_score = models.IntegerField()  # 0-100+
    risk_level = models.CharField()      # CLEAN/LOW/MEDIUM/HIGH/CRITICAL
    alerts = models.JSONField()          # Detailed alert data
    status = models.CharField()          # PENDING/REVIEWED/etc
    reviewed_by_name = models.CharField()
    review_notes = models.TextField()
    action_taken = models.TextField()
```

### FraudDetectionService
```python
class FraudDetectionService:
    def analyze_farm(farm, days=30):
        """
        Analyze farm for fraud indicators
        Returns: FraudAlert if risk > 10, None otherwise
        """
        # Run all detection algorithms
        # Calculate total risk score
        # Generate detailed alert data
        # Save to database if significant
```

## Support & Troubleshooting

### Common Issues

**Issue: Too many false positives**
- Solution: Increase thresholds or adjust weights
- Review: Check if seasonal/regional factors apply

**Issue: Missing legitimate fraud**
- Solution: Decrease thresholds or add more algorithms
- Review: Analyze missed cases to improve detection

**Issue: Farmers complaining**
- Solution: Increase transparency, show benefits
- Review: Ensure appeals process is working

### Getting Help

1. Review this guide thoroughly
2. Check Django Admin logs for alerts
3. Run manual scans with `--help` for options
4. Review code in `fraud_detection_service.py`

## Future Enhancements

Planned improvements:

1. **Machine Learning:** Train ML model on confirmed fraud cases
2. **Customer Network Analysis:** Detect collusion patterns
3. **GPS Verification:** Confirm farm location during sales
4. **Photo Evidence:** Require inventory photos for audits
5. **Blockchain Integration:** Immutable production ledger
6. **Predictive Alerts:** Warn farmers before reaching HIGH risk
7. **Mobile App Integration:** Real-time risk score in farmer app

---

**Remember:** The goal isn't to punish farmers—it's to create a fair, sustainable platform where honest farmers thrive and everyone pays their fair share. Detection is just the first step; prevention through incentives and transparency is the long-term solution.
