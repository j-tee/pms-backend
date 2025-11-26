# PHASE 5: SALES & REVENUE MODULE - PLANNING DOCUMENT

**Date:** October 26, 2025  
**Status:** Planning Phase  
**Previous Phases:** 1-4 Complete (26 models, 50 database tables)

---

## 1. EXECUTIVE SUMMARY

Phase 5 introduces comprehensive sales and revenue tracking for both **Egg Sales** and **Live Bird Sales**. This module completes the business cycle by tracking revenue generation, customer relationships, payment collection, and profitability analysis.

### Key Objectives:
- Track all sales transactions (eggs and birds)
- Manage customer relationships
- Monitor payment status and collections
- Calculate profitability and ROI
- Generate sales reports and analytics

---

## 2. MODULE ANALYSIS

### 2.1 Core Entities

#### **Customer**
- Purpose: Store buyer information for both egg and bird sales
- Key Fields:
  - Customer type (Individual, Restaurant, Hotel, Retailer, Wholesaler, Processor)
  - Contact information (name, phone, email, address)
  - Credit limit and payment terms
  - Customer status (active/inactive)
  - Total purchases and outstanding balance
  - Payment history score

#### **EggSale**
- Purpose: Record egg sales transactions
- Key Fields:
  - Farm and customer references
  - Sale date and delivery date
  - Quantity (crates/trays), pricing, total amount
  - Egg grading (Small, Medium, Large, Extra Large, Mixed)
  - Payment status and collection tracking
  - Invoice number
  - Delivery status

#### **BirdSale**
- Purpose: Record live bird sales
- Key Fields:
  - Farm and flock references
  - Customer reference
  - Sale date and collection date
  - Quantity of birds, average weight
  - Price per kg or per bird
  - Bird condition (healthy, culled)
  - Purpose (meat, breeding, replacement)
  - Payment and delivery status

#### **Invoice** (Optional - Can be integrated into sales)
- Purpose: Generate formal invoices
- Key Fields:
  - Invoice number (auto-generated)
  - Sale references (eggs or birds)
  - Line items with quantities and prices
  - Tax calculations (if applicable)
  - Payment terms
  - Due date

#### **Payment**
- Purpose: Track all payment transactions
- Key Fields:
  - Related sale (egg or bird)
  - Payment date and amount
  - Payment method (Cash, Mobile Money, Bank Transfer, Cheque)
  - Transaction reference
  - Payment status (Pending, Completed, Failed, Refunded)

---

## 3. REDUNDANCY ANALYSIS

### 3.1 Overlap with Existing Modules

#### DailyProduction (flock_management)
- **Existing:** Tracks eggs_collected, good_eggs, broken_eggs per day
- **New EggSale:** Records actual sales of eggs
- **Relationship:** NOT redundant - Production ≠ Sales
  - Production = what's collected from birds
  - Sales = what's sold to customers
  - Difference = eggs in storage, spoilage, farm consumption
- **Integration:** Link EggSale to production dates for inventory tracking

#### Flock Model
- **Existing:** Tracks current_count, birds_sold, birds_culled
- **New BirdSale:** Records detailed bird sales
- **Relationship:** Complementary
  - Flock.birds_sold is a summary counter
  - BirdSale provides transaction-level detail
  - BirdSale should update Flock.birds_sold on save()

#### FeedPurchase & MedicationRecord
- **Existing:** Track costs (expenses)
- **New Sales:** Track revenue (income)
- **Relationship:** Together enable profitability analysis
  - Revenue - (Feed Costs + Medication Costs + Other) = Profit

### 3.2 Integration Points

1. **Daily Production → Egg Sales**
   - Production records feed available eggs for sale
   - Sales reduce available inventory

2. **Flock → Bird Sales**
   - Bird sales update flock.current_count
   - Bird sales record bird removals

3. **Farm → All Sales**
   - All sales reference the farm
   - Farm-level revenue aggregation

4. **Financial Analysis**
   - Feed costs (FeedPurchase, FeedConsumption)
   - Medication costs (MedicationRecord, VaccinationRecord)
   - Vet costs (VetVisit)
   - Revenue (EggSale, BirdSale)
   - = Net Profit

---

## 4. PROPOSED MODELS

### 4.1 Customer Model

```python
class Customer(models.Model):
    """Customer/Buyer information for sales tracking."""
    
    CUSTOMER_TYPE_CHOICES = [
        ('INDIVIDUAL', 'Individual Consumer'),
        ('RESTAURANT', 'Restaurant/Hotel'),
        ('RETAILER', 'Retail Shop'),
        ('WHOLESALER', 'Wholesaler/Distributor'),
        ('PROCESSOR', 'Processing Company'),
        ('FARM', 'Other Farm'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    
    # Basic Information
    name = models.CharField(max_length=200)
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPE_CHOICES)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = PhoneNumberField(region='GH')
    alternate_phone = PhoneNumberField(region='GH', blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField()
    gps_address = models.CharField(max_length=50, blank=True)
    
    # Business Terms
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_terms_days = models.PositiveSmallIntegerField(default=0)  # 0=cash, 7/14/30=credit
    
    # Status
    is_active = models.BooleanField(default=True)
    registration_date = models.DateField(auto_now_add=True)
    
    # Financial Tracking (Auto-calculated)
    total_purchases = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    outstanding_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_purchase_date = models.DateField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### 4.2 EggSale Model

```python
class EggSale(models.Model):
    """Egg sales transaction records."""
    
    EGG_GRADE_CHOICES = [
        ('SMALL', 'Small (< 53g)'),
        ('MEDIUM', 'Medium (53-63g)'),
        ('LARGE', 'Large (63-73g)'),
        ('EXTRA_LARGE', 'Extra Large (> 73g)'),
        ('MIXED', 'Mixed Grades'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Payment Pending'),
        ('PARTIAL', 'Partially Paid'),
        ('PAID', 'Fully Paid'),
        ('OVERDUE', 'Overdue'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    
    # Relationships
    farm = models.ForeignKey('farms.Farm', on_delete=models.PROTECT, related_name='egg_sales')
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='egg_purchases')
    flock = models.ForeignKey('flock_management.Flock', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Sale Details
    sale_date = models.DateField(db_index=True)
    invoice_number = models.CharField(max_length=50, unique=True, editable=False)
    
    # Quantity
    quantity_crates = models.PositiveIntegerField(help_text="Number of crates (30 eggs each)")
    eggs_per_crate = models.PositiveSmallIntegerField(default=30)
    total_eggs = models.PositiveIntegerField(help_text="Auto-calculated: crates × eggs_per_crate")
    
    # Grading & Pricing
    egg_grade = models.CharField(max_length=15, choices=EGG_GRADE_CHOICES, default='MIXED')
    price_per_crate = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Payment
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_due_date = models.DateField(null=True, blank=True)
    
    # Delivery
    delivery_date = models.DateField(null=True, blank=True)
    delivery_status = models.CharField(max_length=20, default='PENDING')
    delivered_by = models.CharField(max_length=100, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Auto-calculate totals
        self.total_eggs = self.quantity_crates * self.eggs_per_crate
        self.total_amount = self.quantity_crates * self.price_per_crate
        
        # Update payment status
        if self.amount_paid >= self.total_amount:
            self.payment_status = 'PAID'
        elif self.amount_paid > 0:
            self.payment_status = 'PARTIAL'
        
        super().save(*args, **kwargs)
```

### 4.3 BirdSale Model

```python
class BirdSale(models.Model):
    """Live bird sales transaction records."""
    
    BIRD_CONDITION_CHOICES = [
        ('HEALTHY', 'Healthy Birds'),
        ('CULLED', 'Culled Birds'),
        ('SPENT', 'Spent Layers'),
    ]
    
    PURPOSE_CHOICES = [
        ('MEAT', 'For Meat/Consumption'),
        ('BREEDING', 'For Breeding'),
        ('REPLACEMENT', 'Replacement Stock'),
        ('PET', 'Pet/Hobby'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    
    # Relationships
    farm = models.ForeignKey('farms.Farm', on_delete=models.PROTECT, related_name='bird_sales')
    flock = models.ForeignKey('flock_management.Flock', on_delete=models.PROTECT, related_name='bird_sales')
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='bird_purchases')
    
    # Sale Details
    sale_date = models.DateField(db_index=True)
    invoice_number = models.CharField(max_length=50, unique=True, editable=False)
    
    # Birds
    quantity_sold = models.PositiveIntegerField()
    bird_condition = models.CharField(max_length=10, choices=BIRD_CONDITION_CHOICES)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    average_weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Pricing
    pricing_method = models.CharField(max_length=10, choices=[('PER_BIRD', 'Per Bird'), ('PER_KG', 'Per Kilogram')])
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Payment
    payment_status = models.CharField(max_length=10, choices=EggSale.PAYMENT_STATUS_CHOICES, default='PENDING')
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Collection
    collection_date = models.DateField(null=True, blank=True)
    collected_by = models.CharField(max_length=100, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Auto-calculate total
        if self.pricing_method == 'PER_BIRD':
            self.total_amount = self.quantity_sold * self.price_per_unit
        else:  # PER_KG
            self.total_amount = (self.quantity_sold * self.average_weight_kg) * self.price_per_unit
        
        # Update flock count
        if self.pk is None:  # New sale
            self.flock.current_count -= self.quantity_sold
            self.flock.birds_sold += self.quantity_sold
            self.flock.save()
        
        super().save(*args, **kwargs)
```

### 4.4 Payment Model

```python
class Payment(models.Model):
    """Payment transaction records for sales."""
    
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('MOMO_MTN', 'MTN Mobile Money'),
        ('MOMO_VODAFONE', 'Vodafone Cash'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CHEQUE', 'Cheque'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    
    # Relationships (Polymorphic - payment can be for egg or bird sale)
    egg_sale = models.ForeignKey(EggSale, on_delete=models.PROTECT, null=True, blank=True, related_name='payments')
    bird_sale = models.ForeignKey(BirdSale, on_delete=models.PROTECT, null=True, blank=True, related_name='payments')
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='payments')
    
    # Payment Details
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    reference_number = models.CharField(max_length=100, blank=True)
    
    # Status
    status = models.CharField(max_length=20, default='COMPLETED')
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Metadata
    received_by = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def clean(self):
        if not self.egg_sale and not self.bird_sale:
            raise ValidationError("Payment must be linked to either an egg sale or bird sale")
```

---

## 5. BUSINESS RULES & VALIDATIONS

### 5.1 Customer Validations
- Phone number required
- Credit limit cannot be negative
- Outstanding balance cannot exceed credit limit for credit customers

### 5.2 EggSale Validations
- Sale date cannot be in the future
- Quantity crates must be > 0
- Price per crate must be > 0
- Amount paid cannot exceed total amount
- If payment_terms_days > 0, calculate payment_due_date

### 5.3 BirdSale Validations
- Cannot sell more birds than flock.current_count
- Quantity sold must be > 0
- If pricing_method = 'PER_KG', average_weight_kg is required
- Auto-update flock.current_count and flock.birds_sold

### 5.4 Payment Validations
- Payment amount must be > 0
- Payment must reference either egg_sale or bird_sale (not both)
- Payment date cannot be before sale date
- Sum of payments cannot exceed sale total

---

## 6. CALCULATED FIELDS & METRICS

### 6.1 Customer Level
- `total_purchases`: Sum of all sales
- `outstanding_balance`: Sum(unpaid amounts)
- `payment_reliability_score`: Percentage of on-time payments

### 6.2 Farm Level (Revenue)
- Total egg sales revenue
- Total bird sales revenue
- Total revenue (eggs + birds)
- Average revenue per flock
- Revenue trend (monthly/quarterly)

### 6.3 Profitability Analysis
```python
# Cost Calculation
feed_cost = FeedConsumption.objects.filter(farm=farm).aggregate(Sum('total_cost'))
medication_cost = MedicationRecord.objects.filter(farm=farm).aggregate(Sum('total_cost'))
vet_cost = VetVisit.objects.filter(farm=farm).aggregate(Sum('visit_fee'))
total_costs = feed_cost + medication_cost + vet_cost

# Revenue Calculation
egg_revenue = EggSale.objects.filter(farm=farm, payment_status='PAID').aggregate(Sum('total_amount'))
bird_revenue = BirdSale.objects.filter(farm=farm, payment_status='PAID').aggregate(Sum('total_amount'))
total_revenue = egg_revenue + bird_revenue

# Profitability
net_profit = total_revenue - total_costs
roi = (net_profit / total_costs) * 100
```

---

## 7. ADMIN INTERFACE FEATURES

### 7.1 Customer Admin
- List display: name, customer_type, phone, total_purchases, outstanding_balance
- Filters: customer_type, is_active
- Search: name, phone
- Actions: Mark as inactive, Send payment reminder

### 7.2 EggSale Admin
- List display: invoice_number, sale_date, customer, quantity_crates, total_amount, payment_status
- Filters: payment_status, sale_date, egg_grade
- Search: invoice_number, customer name
- Inline: Payments
- Color-coded badges for payment_status

### 7.3 BirdSale Admin
- List display: invoice_number, sale_date, customer, quantity_sold, total_amount, payment_status
- Filters: payment_status, bird_condition, purpose
- Search: invoice_number, customer name
- Inline: Payments

---

## 8. INTEGRATION PLAN

### Phase 5A: Customer & Egg Sales (Week 1)
1. Create `sales_revenue` Django app
2. Implement Customer model
3. Implement EggSale model
4. Create admin interfaces
5. Add sample data generation

### Phase 5B: Bird Sales & Payments (Week 2)
1. Implement BirdSale model
2. Implement Payment model
3. Create admin interfaces
4. Add validations and business logic
5. Test flock integration

### Phase 5C: Reports & Analytics (Week 3)
1. Revenue dashboard
2. Customer analytics
3. Profitability reports
4. Payment collection reports
5. Export functionality (PDF/Excel)

---

## 9. DATABASE IMPACT

### New Tables:
- `sales_revenue_customer` (~20 fields)
- `sales_revenue_eggsale` (~25 fields)
- `sales_revenue_birdsale` (~22 fields)
- `sales_revenue_payment` (~15 fields)

### Total After Phase 5:
- **Models:** 30 (26 current + 4 new)
- **Tables:** 54 (50 current + 4 new)
- **Fields:** ~650 total

---

## 10. RISKS & MITIGATION

### Risk 1: Payment Tracking Complexity
- **Mitigation:** Implement robust Payment model with clear validation
- **Strategy:** Use signals to auto-update sale payment_status

### Risk 2: Inventory Mismatch (Eggs)
- **Mitigation:** Implement egg inventory tracking
- **Strategy:** Daily reconciliation between production and sales

### Risk 3: Flock Count Errors
- **Mitigation:** Validate bird sales against flock.current_count
- **Strategy:** Use database transactions for atomic updates

---

## 11. SUCCESS CRITERIA

✅ All 4 models implemented with UUID primary keys  
✅ Admin interfaces with filtering and search  
✅ Payment tracking functional  
✅ Flock integration working (bird sales update counts)  
✅ Sample data generation command  
✅ Zero database migration errors  
✅ Profitability calculations accurate  
✅ Customer credit limit enforcement  

---

## 12. NEXT STEPS

1. **Review & Approval:** Get stakeholder approval on model design
2. **Create App:** `python manage.py startapp sales_revenue`
3. **Implement Models:** Start with Customer, then EggSale
4. **Write Tests:** Comprehensive test coverage
5. **Generate Sample Data:** Extend `generate_sample_data` command
6. **Documentation:** Update API docs and user guides

---

**End of Phase 5 Planning Document**
