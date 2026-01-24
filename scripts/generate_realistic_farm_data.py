"""
Realistic Farm Data Generator for YEA Poultry Management System

Generates realistic, coherent data for a farmer to test analytics and dashboards.
Data is designed to tell a consistent story of a well-performing layer farm.

Usage:
    python manage.py shell < scripts/generate_realistic_farm_data.py
    
Or:
    python scripts/generate_realistic_farm_data.py

Author: AI Assistant
Date: January 2026
"""

import os
import sys
import random
from decimal import Decimal
from datetime import datetime, timedelta, date

# Django setup
if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    import django
    django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from farms.models import Farm
from flock_management.models import Flock, DailyProduction, MortalityRecord
from feed_inventory.models import FeedPurchase, FeedType, FeedInventory
from sales_revenue.marketplace_models import Product, ProductCategory, MarketplaceOrder, OrderItem
from sales_revenue.models import Customer
from sales_revenue.processing_models import ProcessingOutput


# =============================================================================
# CONFIGURATION
# =============================================================================

FARMER_EMAIL = 'juliustetteh@gmail.com'
CLEAR_EXISTING_DATA = True  # Set to False to add to existing data
DATA_PERIOD_DAYS = 90  # Generate 90 days of data (3 months)

# Realistic Ghanaian names for customers
GHANAIAN_NAMES = [
    ('Kofi', 'Mensah'), ('Ama', 'Owusu'), ('Kwame', 'Asante'), ('Akua', 'Boateng'),
    ('Yaw', 'Adjei'), ('Abena', 'Osei'), ('Kwadwo', 'Amoah'), ('Afua', 'Danso'),
    ('Kweku', 'Appiah'), ('Esi', 'Ankrah'), ('Kojo', 'Baffoe'), ('Afia', 'Darko'),
    ('Nana', 'Frimpong'), ('Adwoa', 'Gyasi'), ('Akwasi', 'Kusi'), ('Adjoa', 'Manu'),
    ('Yaw', 'Nkrumah'), ('Efua', 'Opoku'), ('Papa', 'Quartey'), ('Serwaa', 'Sarfo'),
]

SUPPLIER_NAMES = [
    'Agri Feed Ghana Ltd', 'Farmers Choice Feeds', 'Accra Poultry Supplies',
    'Golden Chick Feeds', 'Kumasi Agro Suppliers', 'Quality Feeds GH',
]

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_random_phone():
    """Generate realistic Ghana phone number."""
    prefixes = ['024', '054', '055', '020', '050', '027', '057', '026', '056']
    return f"+233{random.choice(prefixes)[1:]}{random.randint(1000000, 9999999)}"


def generate_laying_rate(age_weeks, base_rate=0.85):
    """
    Calculate realistic laying rate based on bird age.
    
    Peak production (85-92%) at 25-45 weeks
    Gradual decline after 45 weeks
    Lower at start of laying (18-24 weeks)
    """
    if age_weeks < 18:
        return 0  # Not laying yet
    elif age_weeks < 22:
        # Ramping up production
        return base_rate * 0.6 + (age_weeks - 18) * 0.08
    elif age_weeks < 25:
        return base_rate * 0.9 + (age_weeks - 22) * 0.03
    elif age_weeks <= 45:
        # Peak production
        return base_rate + random.uniform(-0.05, 0.05)
    elif age_weeks <= 60:
        # Gradual decline
        decline = (age_weeks - 45) * 0.008
        return max(0.65, base_rate - decline + random.uniform(-0.03, 0.03))
    else:
        # Older birds - lower production
        decline = (age_weeks - 45) * 0.01
        return max(0.50, base_rate - decline + random.uniform(-0.03, 0.03))


def generate_mortality_count(bird_count, week_number, is_summer=False):
    """
    Generate realistic daily mortality based on flock size and conditions.
    
    Normal mortality: 0.05-0.1% per week for healthy flock
    Higher in summer (heat stress) or during disease outbreaks
    """
    base_weekly_rate = 0.0007  # 0.07% per week = ~3.6% per year
    
    if is_summer:
        base_weekly_rate *= 1.5  # Heat stress
    
    daily_rate = base_weekly_rate / 7
    expected = bird_count * daily_rate
    
    # Most days have 0-2 deaths, occasional spikes
    if random.random() < 0.7:  # 70% of days
        return random.randint(0, 2)
    elif random.random() < 0.95:  # 25% of days
        return random.randint(2, 5)
    else:  # 5% of days - disease/stress event
        return random.randint(5, 15)


# =============================================================================
# MAIN DATA GENERATION
# =============================================================================

@transaction.atomic
def generate_farm_data():
    """Generate comprehensive realistic farm data."""
    
    User = get_user_model()
    
    # Get the farmer
    try:
        user = User.objects.get(email=FARMER_EMAIL)
        print(f"✓ Found user: {user.first_name} {user.last_name}")
    except User.DoesNotExist:
        print(f"✗ User {FARMER_EMAIL} not found!")
        return
    
    # Get or create farm
    farm = Farm.objects.filter(user=user).first()
    if not farm:
        print("✗ No farm found for user!")
        return
    
    print(f"✓ Found farm: {farm.farm_name}")
    
    # Update farm settings for marketplace
    farm.marketplace_enabled = True
    farm.subscription_type = 'standard'
    farm.total_bird_capacity = 2500
    farm.save()
    print("✓ Updated farm settings (marketplace enabled)")
    
    # ==========================================================================
    # CLEAR EXISTING DATA (if configured)
    # ==========================================================================
    
    if CLEAR_EXISTING_DATA:
        print("\n--- Clearing existing data ---")
        
        # Import processing models for cleanup
        from sales_revenue.processing_models import ProcessingBatch, ProcessingOutput
        
        # Clear processing data first (protected foreign keys)
        ProcessingOutput.objects.filter(processing_batch__farm=farm).delete()
        ProcessingBatch.objects.filter(farm=farm).delete()
        print("  - Cleared processing batches")
        
        DailyProduction.objects.filter(flock__farm=farm).delete()
        MortalityRecord.objects.filter(flock__farm=farm).delete()
        Flock.objects.filter(farm=farm).delete()
        FeedPurchase.objects.filter(farm=farm).delete()
        FeedInventory.objects.filter(farm=farm).delete()
        OrderItem.objects.filter(order__farm=farm).delete()
        MarketplaceOrder.objects.filter(farm=farm).delete()
        Product.objects.filter(farm=farm).delete()
        Customer.objects.filter(farm=farm).delete()
        print("✓ Cleared existing data")
    
    # ==========================================================================
    # CREATE FLOCKS
    # ==========================================================================
    
    print("\n--- Creating Flocks ---")
    
    today = date.today()
    
    # Flock 1: Main layer flock - 30 weeks old, peak production
    flock1_arrival = today - timedelta(weeks=30)
    flock1 = Flock.objects.create(
        farm=farm,
        flock_number='FLOCK-2025-001',
        flock_type='Layers',
        breed='Isa Brown',
        source='YEA Program',
        supplier_name='Akate Farms Hatchery',
        arrival_date=flock1_arrival,
        initial_count=1200,
        age_at_arrival_weeks=Decimal('1'),
        purchase_price_per_bird=Decimal('25.00'),
        total_acquisition_cost=Decimal('30000.00'),
        current_count=1156,  # Realistic mortality over 30 weeks
        status='Active',
        production_start_date=flock1_arrival + timedelta(weeks=18),
        is_currently_producing=True,
    )
    print(f"  ✓ Created {flock1.flock_number}: {flock1.breed}, {flock1.initial_count} birds")
    
    # Flock 2: Second batch - 45 weeks old, declining production  
    flock2_arrival = today - timedelta(weeks=45)
    flock2 = Flock.objects.create(
        farm=farm,
        flock_number='FLOCK-2024-003',
        flock_type='Layers',
        breed='Lohmann Brown',
        source='Purchased',
        supplier_name='Darko Farms',
        arrival_date=flock2_arrival,
        initial_count=800,
        age_at_arrival_weeks=Decimal('16'),
        purchase_price_per_bird=Decimal('45.00'),
        total_acquisition_cost=Decimal('36000.00'),
        current_count=724,
        status='Active',
        production_start_date=flock2_arrival + timedelta(weeks=3),
        is_currently_producing=True,
    )
    print(f"  ✓ Created {flock2.flock_number}: {flock2.breed}, {flock2.initial_count} birds")
    
    # Flock 3: Young pullets - 12 weeks old, not yet laying
    flock3_arrival = today - timedelta(weeks=12)
    flock3 = Flock.objects.create(
        farm=farm,
        flock_number='FLOCK-2025-002',
        flock_type='Pullets',
        breed='Isa Brown',
        source='YEA Program',
        supplier_name='Akate Farms Hatchery',
        arrival_date=flock3_arrival,
        initial_count=500,
        age_at_arrival_weeks=Decimal('1'),
        purchase_price_per_bird=Decimal('22.00'),
        total_acquisition_cost=Decimal('11000.00'),
        current_count=488,
        status='Active',
        production_start_date=None,
        is_currently_producing=False,
    )
    print(f"  ✓ Created {flock3.flock_number}: {flock3.breed} (pullets), {flock3.initial_count} birds")
    
    flocks = [flock1, flock2, flock3]
    
    # ==========================================================================
    # CREATE DAILY PRODUCTION DATA
    # ==========================================================================
    
    print("\n--- Creating Production Data ---")
    
    production_records = []
    mortality_records = []
    
    # Current bird counts (will be updated backwards)
    bird_counts = {
        flock1.id: flock1.current_count,
        flock2.id: flock2.current_count,
        flock3.id: flock3.current_count,
    }
    
    for day_offset in range(DATA_PERIOD_DAYS, -1, -1):
        current_date = today - timedelta(days=day_offset)
        is_summer = current_date.month in [2, 3, 4]  # Ghana dry season = heat stress
        
        for flock in flocks:
            # Calculate flock age on this date
            days_since_arrival = (current_date - flock.arrival_date).days
            if days_since_arrival < 0:
                continue  # Flock hadn't arrived yet
            
            age_weeks = float(flock.age_at_arrival_weeks) + (days_since_arrival / 7)
            bird_count = bird_counts[flock.id]
            
            # Calculate laying rate
            laying_rate = generate_laying_rate(age_weeks)
            
            if laying_rate > 0:
                # Production record
                base_eggs = int(bird_count * laying_rate)
                daily_variation = random.uniform(-0.05, 0.05)
                eggs_collected = max(0, int(base_eggs * (1 + daily_variation)))
                
                # Quality breakdown (realistic: ~97% good, 1.5% broken, 1.5% dirty)
                broken = int(eggs_collected * random.uniform(0.01, 0.025))
                dirty = int(eggs_collected * random.uniform(0.01, 0.02))
                small = int(eggs_collected * random.uniform(0.02, 0.04))
                soft_shell = int(eggs_collected * random.uniform(0.005, 0.015))
                good_eggs = eggs_collected - broken - dirty - small - soft_shell
                
                # Feed consumed (avg 110-120g per layer per day)
                feed_per_bird = random.uniform(0.11, 0.12)  # kg
                feed_consumed = round(bird_count * feed_per_bird, 2)
                
                production_records.append(DailyProduction(
                    flock=flock,
                    farm=farm,
                    production_date=current_date,
                    eggs_collected=eggs_collected,
                    good_eggs=good_eggs,
                    broken_eggs=broken,
                    dirty_eggs=dirty,
                    small_eggs=small,
                    soft_shell_eggs=soft_shell,
                    feed_consumed_kg=Decimal(str(feed_consumed)),
                    production_rate_percent=Decimal(str(round(laying_rate * 100, 1))),
                    birds_died=0,  # Tracked in MortalityRecord
                    general_health='Good' if random.random() > 0.1 else 'Fair',
                ))
            
            # Mortality (happens regardless of production)
            daily_deaths = generate_mortality_count(bird_count, age_weeks, is_summer)
            if daily_deaths > 0:
                bird_counts[flock.id] = max(0, bird_count - daily_deaths)
                
                causes = ['Natural Causes', 'Disease', 'Predator', 'Heat Stress', 'Unknown']
                weights = [0.4, 0.2, 0.1, 0.2 if is_summer else 0.05, 0.1]
                cause = random.choices(causes, weights=weights)[0]
                
                mortality_records.append(MortalityRecord(
                    flock=flock,
                    farm=farm,
                    date_discovered=current_date,
                    number_of_birds=daily_deaths,
                    probable_cause=cause,
                    symptoms_observed=cause == 'Disease',
                    symptoms_description='Lethargy, reduced appetite' if cause == 'Disease' else '',
                    disposal_method='Burial',
                    estimated_value_per_bird=Decimal('75.00'),
                    total_estimated_loss=Decimal(str(daily_deaths * 75)),
                ))
    
    # Bulk create
    DailyProduction.objects.bulk_create(production_records)
    MortalityRecord.objects.bulk_create(mortality_records)
    print(f"  ✓ Created {len(production_records)} production records")
    print(f"  ✓ Created {len(mortality_records)} mortality records")
    
    # ==========================================================================
    # CREATE FEED DATA
    # ==========================================================================
    
    print("\n--- Creating Feed Data ---")
    
    # Get or create feed types
    layer_feed, _ = FeedType.objects.get_or_create(
        name='Layer Mash 16%',
        defaults={
            'category': 'LAYER',
            'form': 'MASH',
            'manufacturer': 'Agri Feed Ghana',
            'protein_content': Decimal('16.00'),
            'energy_content': Decimal('2750.00'),
            'calcium_content': Decimal('4.00'),
            'daily_consumption_per_bird_grams': 115,
            'standard_price_per_kg': Decimal('3.50'),
        }
    )
    
    grower_feed, _ = FeedType.objects.get_or_create(
        name='Grower Mash 18%',
        defaults={
            'category': 'GROWER',
            'form': 'MASH',
            'manufacturer': 'Agri Feed Ghana',
            'protein_content': Decimal('18.00'),
            'energy_content': Decimal('2850.00'),
            'daily_consumption_per_bird_grams': 90,
            'standard_price_per_kg': Decimal('3.80'),
        }
    )
    
    # Create feed purchases (monthly purchases)
    purchase_dates = [
        today - timedelta(days=75),
        today - timedelta(days=45),
        today - timedelta(days=15),
    ]
    
    for i, pdate in enumerate(purchase_dates):
        # Layer feed purchase
        FeedPurchase.objects.create(
            farm=farm,
            feed_type=layer_feed,
            supplier=random.choice(SUPPLIER_NAMES),
            purchase_date=pdate,
            quantity_bags=40,
            bag_weight_kg=Decimal('50.00'),
            quantity_kg=Decimal('2000.00'),
            stock_balance_kg=Decimal(str(2000 - (i * 600))),
            unit_cost_ghs=Decimal('175.00'),
            unit_price=Decimal('3.50'),
            total_cost=Decimal('7000.00'),
            payment_status='PAID',
        )
        
        # Grower feed for pullets (smaller quantities)
        FeedPurchase.objects.create(
            farm=farm,
            feed_type=grower_feed,
            supplier=random.choice(SUPPLIER_NAMES),
            purchase_date=pdate,
            quantity_bags=10,
            bag_weight_kg=Decimal('50.00'),
            quantity_kg=Decimal('500.00'),
            stock_balance_kg=Decimal(str(max(0, 500 - (i * 150)))),
            unit_cost_ghs=Decimal('190.00'),
            unit_price=Decimal('3.80'),
            total_cost=Decimal('1900.00'),
            payment_status='PAID',
        )
    
    # Create current inventory
    FeedInventory.objects.create(
        farm=farm,
        feed_type=layer_feed,
        current_stock_kg=Decimal('850.00'),
        min_stock_level=Decimal('500.00'),
        max_stock_level=Decimal('3000.00'),
        average_cost_per_kg=Decimal('3.50'),
        total_value=Decimal('2975.00'),  # 850 * 3.50
    )
    FeedInventory.objects.create(
        farm=farm,
        feed_type=grower_feed,
        current_stock_kg=Decimal('200.00'),
        min_stock_level=Decimal('150.00'),
        max_stock_level=Decimal('1000.00'),
        average_cost_per_kg=Decimal('3.80'),
        total_value=Decimal('760.00'),  # 200 * 3.80
    )
    
    print(f"  ✓ Created 6 feed purchases")
    print(f"  ✓ Created 2 feed inventory records")
    
    # ==========================================================================
    # CREATE CUSTOMERS
    # ==========================================================================
    
    print("\n--- Creating Customers ---")
    
    customers = []
    momo_providers = ['mtn', 'vodafone', 'airteltigo']
    customer_types = ['individual', 'business', 'retailer', 'wholesaler']
    
    for first, last in GHANAIAN_NAMES[:12]:
        phone = get_random_phone()
        customer = Customer.objects.create(
            farm=farm,
            first_name=first,
            last_name=last,
            customer_type=random.choice(customer_types),
            phone_number=phone,
            email=f"{first.lower()}.{last.lower()}@email.com" if random.random() > 0.5 else '',
            mobile_money_number=phone,
            mobile_money_provider=random.choice(momo_providers),
            mobile_money_account_name=f"{first} {last}",
            location=random.choice(['Accra', 'Tema', 'Madina', 'Kasoa', 'Spintex']),
            delivery_address=f"{random.randint(1, 99)} {random.choice(['Main St', 'Market Rd', 'Church Lane', 'Station Rd'])}, Accra",
            is_active=True,
        )
        customers.append(customer)
    
    print(f"  ✓ Created {len(customers)} customers")
    
    # ==========================================================================
    # CREATE PRODUCTS
    # ==========================================================================
    
    print("\n--- Creating Products ---")
    
    # Get or create product categories
    eggs_cat, _ = ProductCategory.objects.get_or_create(
        name='Fresh Eggs',
        defaults={'description': 'Farm fresh eggs'}
    )
    birds_cat, _ = ProductCategory.objects.get_or_create(
        name='Live Birds',
        defaults={'description': 'Live poultry'}
    )
    
    products = []
    
    # Fresh eggs - main product
    products.append(Product.objects.create(
        farm=farm,
        category=eggs_cat,
        name='Fresh Eggs (Crate of 30)',
        description='Farm fresh brown eggs from free-range Isa Brown hens. Collected daily.',
        price=Decimal('48.00'),
        min_price=Decimal('45.00'),
        stock_quantity=150,
        unit='crate',
        status='active',
        price_negotiable=True,
    ))
    
    products.append(Product.objects.create(
        farm=farm,
        category=eggs_cat,
        name='Premium Eggs (Crate of 30)',
        description='Extra large premium eggs, hand-selected for quality.',
        price=Decimal('55.00'),
        min_price=Decimal('52.00'),
        stock_quantity=40,
        unit='crate',
        status='active',
        price_negotiable=False,
    ))
    
    # Live birds
    products.append(Product.objects.create(
        farm=farm,
        category=birds_cat,
        name='Spent Layers (Live)',
        description='Mature laying hens (60+ weeks). Ideal for local stew.',
        price=Decimal('90.00'),
        min_price=Decimal('85.00'),
        stock_quantity=50,
        unit='bird',
        status='active',
        price_negotiable=True,
    ))
    
    products.append(Product.objects.create(
        farm=farm,
        category=birds_cat,
        name='Point-of-Lay Pullets',
        description='Ready-to-lay pullets (16-18 weeks). Start producing within 2-4 weeks.',
        price=Decimal('130.00'),
        min_price=Decimal('120.00'),
        stock_quantity=0,  # Currently not available
        unit='bird',
        status='out_of_stock',
        price_negotiable=True,
    ))
    
    print(f"  ✓ Created {len(products)} products")
    
    # ==========================================================================
    # CREATE ORDERS
    # ==========================================================================
    
    print("\n--- Creating Orders ---")
    
    orders_created = 0
    order_statuses = ['pending', 'confirmed', 'processing', 'ready', 'delivered', 'completed']
    
    # Generate orders over the past 90 days
    for day_offset in range(DATA_PERIOD_DAYS, 0, -1):
        order_date = today - timedelta(days=day_offset)
        
        # 1-4 orders per day
        num_orders = random.randint(1, 4)
        
        for _ in range(num_orders):
            customer = random.choice(customers)
            
            # Determine order status based on age
            if day_offset > 60:
                status = 'completed'
            elif day_offset > 30:
                status = random.choice(['completed', 'delivered'])
            elif day_offset > 7:
                status = random.choice(['completed', 'delivered', 'ready', 'processing'])
            else:
                status = random.choice(order_statuses)
            
            # Create order
            subtotal = Decimal('0.00')
            order = MarketplaceOrder.objects.create(
                farm=farm,
                customer=customer,
                status=status,
                delivery_method=random.choice(['pickup', 'delivery']),
                delivery_address=customer.delivery_address if random.random() > 0.5 else '',
                delivery_contact_name=f"{customer.first_name} {customer.last_name}",
                delivery_contact_phone=customer.phone_number,
                delivery_fee=Decimal('15.00') if random.random() > 0.5 else Decimal('0.00'),
                subtotal=Decimal('0.00'),  # Will update
                total_amount=Decimal('0.00'),  # Will update
                payment_status=random.choice(['pending', 'paid', 'paid']),
                created_at=timezone.make_aware(datetime.combine(order_date, datetime.min.time())),
            )
            
            # Add 1-3 items per order
            available_products = [p for p in products if p.status == 'active']
            num_items = random.randint(1, min(3, len(available_products)))
            selected_products = random.sample(available_products, num_items)
            
            for product in selected_products:
                quantity = random.randint(1, 10) if 'Eggs' in product.name else random.randint(1, 5)
                unit_price = product.price
                line_total = unit_price * quantity
                subtotal += line_total
                
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=product.name,
                    product_sku=product.sku or '',
                    unit=product.unit,
                    quantity=quantity,
                    unit_price=unit_price,
                    line_total=line_total,
                )
            
            # Update order totals
            order.subtotal = subtotal
            order.total_amount = subtotal + order.delivery_fee
            order.save()
            orders_created += 1
    
    print(f"  ✓ Created {orders_created} orders")
    
    # ==========================================================================
    # SUMMARY
    # ==========================================================================
    
    print("\n" + "=" * 60)
    print("DATA GENERATION COMPLETE")
    print("=" * 60)
    
    total_eggs = sum(p.eggs_collected for p in production_records)
    total_deaths = sum(m.number_of_birds for m in mortality_records)
    total_birds = sum(f.current_count for f in flocks)
    
    print(f"""
Farm: {farm.farm_name}
Owner: {user.first_name} {user.last_name}

FLOCK SUMMARY:
  - Total flocks: {len(flocks)}
  - Total birds: {total_birds}
  - Producing flocks: 2 (Layers)
  - Pullets (future layers): 1

PRODUCTION (Last {DATA_PERIOD_DAYS} days):
  - Total eggs: {total_eggs:,}
  - Daily average: {total_eggs // DATA_PERIOD_DAYS:,} eggs
  - Production records: {len(production_records)}

MORTALITY:
  - Total deaths: {total_deaths}
  - Mortality rate: {(total_deaths / (flock1.initial_count + flock2.initial_count + flock3.initial_count)) * 100:.2f}%

FEED:
  - Purchases: 6 (2 feed types × 3 months)
  - Current inventory: Layer Mash 850kg, Grower Mash 200kg

MARKETPLACE:
  - Products: {len(products)}
  - Customers: {len(customers)}
  - Orders: {orders_created}
""")


if __name__ == '__main__':
    generate_farm_data()
