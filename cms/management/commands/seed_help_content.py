"""
Management command to seed help/knowledge base content.

Usage:
    python manage.py seed_help_content
    python manage.py seed_help_content --clear  # Clear existing and reseed
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from cms.help_models import HelpCategory, HelpArticle


class Command(BaseCommand):
    help = 'Seed the knowledge base with help categories and articles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing help content before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing help content...')
            HelpArticle.objects.all().delete()
            HelpCategory.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Cleared existing content'))

        self.stdout.write('Seeding help categories and articles...')
        
        # Create categories and articles
        categories_data = self.get_categories_data()
        
        for cat_data in categories_data:
            category, created = HelpCategory.objects.update_or_create(
                slug=cat_data['slug'],
                defaults={
                    'name': cat_data['name'],
                    'description': cat_data['description'],
                    'icon': cat_data.get('icon', '📚'),
                    'display_order': cat_data.get('order', 0),
                    'is_active': True,
                }
            )
            
            if created:
                self.stdout.write(f'  Created category: {category.name}')
            else:
                self.stdout.write(f'  Updated category: {category.name}')
            
            # Create articles for this category
            for article_data in cat_data.get('articles', []):
                article, art_created = HelpArticle.objects.update_or_create(
                    slug=article_data['slug'],
                    defaults={
                        'category': category,
                        'title': article_data['title'],
                        'summary': article_data['summary'],
                        'content': article_data['content'],
                        'keywords': article_data.get('keywords', ''),
                        'target_audience': article_data.get('target_audience', 'all'),
                        'status': 'published',
                        'published_at': timezone.now(),
                    }
                )
                
                if art_created:
                    self.stdout.write(f'    Created article: {article.title}')
                else:
                    self.stdout.write(f'    Updated article: {article.title}')
        
        # Summary
        total_categories = HelpCategory.objects.count()
        total_articles = HelpArticle.objects.filter(status='published').count()
        
        self.stdout.write(self.style.SUCCESS(
            f'\nSeeding complete! {total_categories} categories, {total_articles} articles'
        ))

    def get_categories_data(self):
        """Return all categories and articles data."""
        return [
            # ==========================================
            # GETTING STARTED
            # ==========================================
            {
                'name': 'Getting Started',
                'slug': 'getting-started',
                'description': 'New to YEA Poultry? Start here to learn the basics of setting up your account and farm.',
                'icon': '🚀',
                'order': 1,
                'articles': [
                    {
                        'slug': 'welcome-to-yea-poultry',
                        'title': 'Welcome to YEA Poultry Management System',
                        'summary': 'An introduction to the YEA Poultry Development Program and how this platform helps farmers succeed.',
                        'content': '''# Welcome to YEA Poultry Management System

The YEA Poultry Management System is Ghana's premier platform for poultry farmers participating in the Youth Employment Agency's Poultry Development Program.

## What is the YEA Poultry Program?

The YEA Poultry Development Program is a government initiative designed to:
- **Empower youth** through poultry farming opportunities
- **Provide support** including training, resources, and market access
- **Track progress** of farms across all constituencies
- **Connect farmers** with buyers through our marketplace

## What Can You Do on This Platform?

### For Farmers
- Register your farm and track your flock
- Record daily production (eggs, mortality, feed)
- List products on the marketplace
- Track sales and revenue
- Connect with extension officers for support

### For Buyers
- Browse available poultry products
- Find farms in your area
- Contact farmers directly
- Place orders

### For Extension Officers
- Register and support farmers in your constituency
- Verify farm data and production records
- Monitor farm performance
- Provide technical assistance

## Getting Help

If you need assistance at any time:
- Browse this Help Center for guides and tutorials
- Contact your assigned Extension Officer
- Use the Contact form in the app

We're here to help you succeed in your poultry farming journey!''',
                        'keywords': 'welcome, introduction, about, yea, program, poultry, ghana',
                        'target_audience': 'all',
                        'is_featured': True,
                    },
                    {
                        'slug': 'creating-your-account',
                        'title': 'Creating Your Account',
                        'summary': 'Different ways to get an account on the YEA Poultry platform depending on your role.',
                        'content': '''# Creating Your Account

How you get an account depends on your role in the system.

## Who Needs an Account?

| User Type | How to Get Account |
|-----------|-------------------|
| **Farmers** | Apply online OR Field Officer registration |
| **Buyers** | Browse marketplace (no account needed) OR create account for order tracking |
| **Extension Officers** | Email invitation from Administrator |
| **Veterinary Officers** | Email invitation from Administrator |
| **YEA Officials** | Email invitation from Administrator |
| **Administrators** | Email invitation from higher-level Admin |

---

## For Farmers: Online Application

### Step 1: Start Your Application

On the homepage, click the **"Apply Now"** button to begin your farm application.

### Step 2: Enter Your Information

Fill in the required details:
- **First Name** - Your legal first name
- **Last Name** - Your legal surname
- **Phone Number** - Your active mobile number (used for login and SMS updates)
- **Email** (optional) - For notifications and updates
- **Ghana Card Number** - Your national ID
- **Password** - Create a strong password

### Step 3: Verify Your Phone

You'll receive an SMS with a 6-digit verification code. Enter this code to verify your phone number.

### Step 4: Complete Farm Details

Provide your farm information:
- Farm name and location (Region, District, Constituency)
- Production type (Layers, Broilers, or Both)
- Housing type and bird capacity
- Current bird count

### Step 5: Submit Application

Review your information and submit. You'll receive a confirmation SMS with your application number.

### What Happens Next?

1. **Application submitted** - You'll get an application reference number
2. **Review period** - YEA officials in your constituency will review your application
3. **Track progress** - Use the **"Track Application"** button on the homepage to check status
4. **Approval notification** - You'll receive an SMS when approved
5. **Access granted** - Log in and start using all farmer features!

---

## For Farmers: Field Officer Registration

Extension Officers can register farmers during field visits. This is faster because:
- ✅ Immediate account creation
- ✅ Pre-approved status (no waiting period)
- ✅ No separate farm application needed
- ✅ Extension officer automatically assigned to your farm

**You will receive an SMS** with your login credentials (username and temporary password).

---

## For Staff & Officials: Email Invitation

YEA staff members and officials don't apply online. Instead:

### Step 1: Receive Email Invitation

Your administrator will create your account and you'll receive an **email invitation** containing:
- Welcome message
- Your assigned role
- A secure activation link
- Link expiry information (usually 7 days)

### Step 2: Click the Activation Link

The link takes you to a page where you'll:
- Set your password
- Complete your profile information

### Step 3: First Login

After setting your password:
1. Go to the login page and click **"Login"**
2. Enter your email and new password
3. You're ready to start working!

> **Note**: The invitation link expires after 7 days. If it expires, ask your administrator to resend the invitation.

---

## Troubleshooting

### Didn't receive SMS verification code?
- Check your phone number is correct
- Wait 60 seconds and request a new code
- Make sure your phone has network coverage

### Phone number already registered?
- You may already have an account - try logging in
- Use **"Track Application"** to check existing application status
- Contact support if you need help accessing your existing account

### Didn't receive staff invitation email?
- Check your spam/junk folder
- Verify your administrator used the correct email address
- Ask your administrator to resend the invitation

### Invitation link expired?
- Contact your administrator to send a new invitation
- Invitation links are valid for 7 days

### Forgot your password?
- Use the "Forgot Password" link on the login page
- A reset code will be sent to your phone or email''',
                        'keywords': 'apply, application, create account, new user, phone verification, invitation, staff, email, track application',
                        'target_audience': 'all',
                        'is_featured': True,
                    },
                    {
                        'slug': 'registering-your-farm',
                        'title': 'Registering Your Farm',
                        'summary': 'How to register your poultry farm after creating your account.',
                        'content': '''# Registering Your Farm

Once you have an account, you need to register your farm to access all farmer features.

## Farm Registration Steps

### Step 1: Start Registration

From your dashboard, click **"Register Farm"** or complete the farm registration prompt.

### Step 2: Farm Details

Enter your farm information:
- **Farm Name** - A name for your farm
- **Location** - Region, District, Constituency, Town
- **Residential Address** - Physical location of the farm

### Step 3: Production Information

Tell us about your farm setup:
- **Production Type** - Layers, Broilers, or Both
- **Housing Type** - Deep Litter, Battery Cage, Free Range
- **Number of Poultry Houses** - How many structures
- **Total Bird Capacity** - Maximum birds you can house
- **Current Bird Count** - How many birds you have now

### Step 4: Contact Information

- **Primary Phone** - Main contact number
- **Alternate Phone** (optional) - Backup number
- **Email** (optional) - For communications

### Step 5: Upload Documents

You may need to provide:
- Ghana Card photo
- Farm photos
- Any relevant certificates

### Step 6: Submit for Review

Your application will be reviewed by officials in your constituency.

## After Submission

- **Pending**: Your application is awaiting review
- **Approved**: Congratulations! You can now use all features
- **Needs Revision**: Check feedback and update your application

## Tips for Quick Approval

1. Provide accurate information
2. Upload clear photos
3. Ensure your contact details are correct
4. Respond promptly to any requests for additional information''',
                        'keywords': 'farm registration, register farm, new farm, application, approval',
                        'target_audience': 'farmers',
                        'is_featured': True,
                    },
                    {
                        'slug': 'understanding-your-dashboard',
                        'title': 'Understanding Your Dashboard',
                        'summary': 'A tour of the farmer dashboard and what each section shows.',
                        'content': '''# Understanding Your Dashboard

Your dashboard is your command center for managing your poultry farm. Here's what each section shows.

## Dashboard Overview

When you log in, you'll see a summary of your farm's key metrics:

### Production Summary
- **Today's Egg Collection** - Eggs collected today
- **Current Flock Size** - Total birds across all flocks
- **Weekly Production** - Eggs collected this week
- **Mortality Rate** - Recent mortality percentage

### Financial Summary
- **Revenue This Month** - Total sales this month
- **Pending Payments** - Money owed to you
- **Expenses** - Feed and other costs

### Quick Actions
- Record Daily Production
- Add New Sale
- View Inventory
- Check Marketplace

## Navigation Menu

### Farm Management
- **Flocks** - View and manage your bird flocks
- **Production** - Record daily egg collection and mortality
- **Feed Inventory** - Track feed stock and purchases

### Sales & Revenue
- **Sales** - Record and view all sales
- **Customers** - Manage your customer list
- **Payments** - Track payment status

### Marketplace
- **My Products** - Products you're selling
- **Orders** - Orders from buyers
- **Analytics** - Sales performance data

### Reports
- **Production Reports** - Egg and flock performance
- **Financial Reports** - Revenue and expense summaries
- **Export Data** - Download your records

## Notifications

Check the bell icon for:
- New orders
- Payment confirmations
- System announcements
- Messages from extension officers

## Profile & Settings

Access your profile to:
- Update personal information
- Change password
- Manage notification preferences
- View subscription status''',
                        'keywords': 'dashboard, overview, navigation, menu, home, metrics',
                        'target_audience': 'farmers',
                        'is_featured': False,
                    },
                ],
            },
            
            # ==========================================
            # FLOCK MANAGEMENT
            # ==========================================
            {
                'name': 'Flock Management',
                'slug': 'flock-management',
                'description': 'Learn how to manage your poultry flocks, record production, and track bird health.',
                'icon': '🐔',
                'order': 2,
                'articles': [
                    {
                        'slug': 'adding-a-new-flock',
                        'title': 'Adding a New Flock',
                        'summary': 'How to register a new batch of birds in the system.',
                        'content': '''# Adding a New Flock

A flock represents a group of birds that you manage together. Here's how to add a new flock.

## When to Create a New Flock

Create a new flock when you:
- Receive a new batch of day-old chicks
- Purchase birds from another farm
- Want to track a group of birds separately

## Steps to Add a Flock

### Step 1: Navigate to Flocks

Go to **Farm Management** → **Flocks** → **Add New Flock**

### Step 2: Enter Flock Details

- **Flock Name** - Give it a memorable name (e.g., "Batch January 2026")
- **Flock Type** - Layers or Broilers
- **Breed** - Select the breed (Isa Brown, Lohmann, etc.)
- **Date Acquired** - When you got the birds
- **Initial Count** - Number of birds received
- **Source** - Where you got the birds from

### Step 3: Additional Information

- **Age at Acquisition** - Days old when received
- **Cost per Bird** (optional) - For expense tracking
- **Notes** - Any relevant information

### Step 4: Save

Click **Save** to create the flock.

## After Creating a Flock

- The flock will appear in your flock list
- You can start recording daily production
- Monitor mortality and health status
- Track feed consumption

## Managing Multiple Flocks

If you have multiple flocks:
- Keep them organized with clear names
- Each flock tracks its own production
- Reports can show individual or combined data
- Mark flocks as inactive when they're culled or sold''',
                        'keywords': 'flock, batch, birds, add, new, create, chickens',
                        'target_audience': 'farmers',
                        'is_featured': False,
                    },
                    {
                        'slug': 'recording-daily-production',
                        'title': 'Recording Daily Production',
                        'summary': 'How to record your daily egg collection and other production data.',
                        'content': '''# Recording Daily Production

Keeping accurate daily records is essential for tracking your farm's performance.

## What to Record Daily

For **Layer Flocks**:
- Eggs collected (total count)
- Cracked/broken eggs
- Mortality (deaths)
- Feed consumed
- Water consumed (optional)
- Any observations

For **Broiler Flocks**:
- Mortality
- Feed consumed
- Average weight (weekly)
- Health observations

## How to Record Production

### Step 1: Go to Production

Navigate to **Farm Management** → **Production** → **Add Daily Record**

Or use the **Quick Action** button on your dashboard.

### Step 2: Select Date and Flock

- Choose the date (defaults to today)
- Select the flock

### Step 3: Enter Data

- **Eggs Collected** - Total good eggs
- **Broken Eggs** - Eggs that can't be sold
- **Mortality** - Birds that died today
- **Feed Consumed (kg)** - Amount of feed used
- **Notes** - Any observations (health issues, weather, etc.)

### Step 4: Save

Click **Save** to record the data.

## Tips for Accurate Recording

1. **Record at the same time each day** - Consistency helps tracking
2. **Count carefully** - Accurate numbers are important
3. **Note any issues** - Document health problems, unusual behavior
4. **Don't skip days** - Even if production is zero, record it

## Viewing Production History

- Go to **Farm Management** → **Production**
- Use filters to view by date range or flock
- Export data for your records

## What If I Miss a Day?

You can add records for past dates:
1. Go to Add Daily Record
2. Change the date to the missed day
3. Enter the data
4. Save

Your extension officer may verify backdated entries.''',
                        'keywords': 'production, eggs, daily record, collection, mortality, feed',
                        'target_audience': 'farmers',
                        'is_featured': True,
                    },
                    {
                        'slug': 'recording-mortality',
                        'title': 'Recording Bird Mortality',
                        'summary': 'How to properly record and categorize bird deaths.',
                        'content': '''# Recording Bird Mortality

Accurate mortality records help you monitor flock health and identify problems early.

## Why Record Mortality?

- Track flock health trends
- Identify disease outbreaks early
- Calculate true production costs
- Meet program requirements
- Get timely veterinary support

## How to Record Mortality

### Daily Recording (Recommended)

Include mortality in your daily production record:
1. Count birds that died
2. Enter the count in the mortality field
3. Note the suspected cause if known

### Separate Mortality Record

For significant events or detailed tracking:
1. Go to **Flocks** → Select Flock → **Record Mortality**
2. Enter:
   - Date
   - Number of birds
   - Cause (if known)
   - Symptoms observed
   - Actions taken

## Common Mortality Causes

- **Disease** - Newcastle, Gumboro, Coccidiosis, etc.
- **Predators** - Snakes, hawks, thieves
- **Heat Stress** - High temperatures
- **Suffocation** - Overcrowding, piling
- **Injury** - Fighting, accidents
- **Unknown** - When cause isn't clear

## When to Alert Your Extension Officer

Contact your extension officer immediately if you see:
- Sudden spike in deaths (more than 2-3% in a day)
- Multiple birds showing same symptoms
- Unusual symptoms you don't recognize
- Deaths across multiple age groups

## Disposing of Dead Birds

Proper disposal is important:
- Remove dead birds immediately
- Don't throw in open areas
- Options: burial, burning, composting
- Follow local guidelines

## Preventing Mortality

- Maintain good biosecurity
- Vaccinate on schedule
- Provide clean water and quality feed
- Ensure proper ventilation
- Avoid overcrowding''',
                        'keywords': 'mortality, death, birds, died, record, health, disease',
                        'target_audience': 'farmers',
                        'is_featured': False,
                    },
                ],
            },
            
            # ==========================================
            # FEED & INVENTORY
            # ==========================================
            {
                'name': 'Feed & Inventory',
                'slug': 'feed-inventory',
                'description': 'Track your feed stock, purchases, and consumption to optimize costs.',
                'icon': '🌾',
                'order': 3,
                'articles': [
                    {
                        'slug': 'managing-feed-inventory',
                        'title': 'Managing Feed Inventory',
                        'summary': 'How to track your feed stock and purchases.',
                        'content': '''# Managing Feed Inventory

Feed is your largest expense. Tracking it carefully helps control costs and ensure your birds are always fed.

## Feed Inventory Features

- Track different feed types (Starter, Grower, Layer, Broiler)
- Record purchases with costs
- Monitor current stock levels
- Get low stock alerts
- Analyze feed consumption rates

## Adding Feed to Inventory

### Recording a Purchase

1. Go to **Feed & Inventory** → **Add Purchase**
2. Enter:
   - Feed type
   - Quantity (bags or kg)
   - Cost per unit
   - Supplier name
   - Purchase date
   - Invoice/receipt number (optional)
3. Save

### Current Stock

Your dashboard shows:
- Total feed in stock by type
- Days of feed remaining (estimated)
- Recent purchases

## Recording Feed Consumption

You can record feed used:
- **In daily production** - Enter feed consumed when recording eggs
- **Manually** - Go to Feed Inventory → Record Usage

## Low Stock Alerts

Set alert thresholds:
1. Go to **Feed & Inventory** → **Settings**
2. Set minimum stock levels for each feed type
3. You'll be notified when stock drops below threshold

## Feed Analysis

View reports showing:
- Feed consumption per bird
- Feed cost per egg
- Feed conversion ratio
- Spending trends

## Tips for Feed Management

1. **Buy in bulk** when possible for better prices
2. **Store properly** to prevent spoilage
3. **Track consumption** to catch theft or waste
4. **Compare suppliers** to get best prices
5. **Match feed to bird age** - don't give layer feed to chicks''',
                        'keywords': 'feed, inventory, stock, purchase, consumption, bags',
                        'target_audience': 'farmers',
                        'is_featured': False,
                    },
                    {
                        'slug': 'tracking-expenses',
                        'title': 'Tracking Farm Expenses',
                        'summary': 'Record all your farm expenses to understand your true costs.',
                        'content': '''# Tracking Farm Expenses

Understanding your expenses is key to running a profitable farm.

## Types of Expenses

### Feed Expenses
Automatically tracked when you record feed purchases:
- Starter feed
- Grower feed
- Layer feed
- Broiler feed

### Other Expenses
Record manually:
- **Medication & Vaccines** - Health products
- **Utilities** - Electricity, water
- **Labor** - Workers' wages
- **Bedding** - Wood shavings, sawdust
- **Transport** - Delivery costs
- **Equipment** - Feeders, drinkers, repairs
- **Other** - Miscellaneous costs

## Recording an Expense

1. Go to **Expenses** → **Add Expense**
2. Enter:
   - Category
   - Amount
   - Date
   - Description
   - Receipt reference (optional)
3. Save

## Viewing Expense Reports

See your spending:
- **By Category** - Where your money goes
- **By Period** - Weekly, monthly, yearly trends
- **By Flock** - Costs per flock (if allocated)

## Calculating Profitability

The system helps calculate:
- **Cost per Egg** = Total Expenses ÷ Eggs Produced
- **Cost per Bird** = Total Expenses ÷ Birds Sold
- **Profit Margin** = Revenue - Expenses

## Tips for Expense Management

1. **Record everything** - Even small expenses add up
2. **Keep receipts** - For verification and tax purposes
3. **Review monthly** - Identify areas to cut costs
4. **Compare periods** - See if expenses are increasing
5. **Budget ahead** - Plan for expected costs''',
                        'keywords': 'expenses, costs, spending, budget, money, track',
                        'target_audience': 'farmers',
                        'is_featured': False,
                    },
                ],
            },
            
            # ==========================================
            # MARKETPLACE
            # ==========================================
            {
                'name': 'Marketplace',
                'slug': 'marketplace',
                'description': 'Learn how to list products, manage orders, and sell through the YEA marketplace.',
                'icon': '🛒',
                'order': 4,
                'articles': [
                    {
                        'slug': 'marketplace-overview',
                        'title': 'Marketplace Overview',
                        'summary': 'Introduction to the YEA Poultry Marketplace and how it works.',
                        'content': '''# Marketplace Overview

The YEA Poultry Marketplace connects farmers with buyers across Ghana.

## How It Works

1. **Farmers list products** - Eggs, birds, and processed products
2. **Buyers browse and search** - Find products in their area
3. **Contact and order** - Buyers reach out to farmers
4. **Fulfill orders** - Farmers deliver or buyers pick up
5. **Record sales** - Track all transactions

## What You Can Sell

- **Eggs** - Fresh table eggs, fertilized eggs
- **Live Birds** - Layers, broilers, point-of-lay
- **Processed Products** - Dressed chicken, egg products
- **By-products** - Manure, feathers (where applicable)

## Marketplace Features

### For Farmers
- Create product listings
- Set prices and quantities
- Manage incoming orders
- Track sales and revenue
- View analytics

### For Buyers
- Search by product, location, price
- View farm details and ratings
- Contact farmers directly
- Save favorite products
- View order history

## Marketplace vs Direct Sales

You can use both:
- **Marketplace** - Reach new customers
- **Direct Sales** - Sell to existing customers

Both can be tracked in the system.

## Getting Started

1. Activate your marketplace subscription
2. Create your first product listing
3. Set competitive prices
4. Respond quickly to inquiries

See the following articles for detailed guides on each step.''',
                        'keywords': 'marketplace, selling, buying, products, overview, introduction',
                        'target_audience': 'all',
                        'is_featured': True,
                    },
                    {
                        'slug': 'listing-products',
                        'title': 'Listing Products for Sale',
                        'summary': 'How to create and manage product listings on the marketplace.',
                        'content': '''# Listing Products for Sale

A good product listing helps buyers find and choose your products.

## Creating a Product Listing

### Step 1: Go to Products

Navigate to **Marketplace** → **My Products** → **Add Product**

### Step 2: Basic Information

- **Product Name** - Clear, descriptive name
- **Category** - Eggs, Live Birds, or Processed Products
- **Description** - Detailed description of the product

### Step 3: Pricing

- **Price** - Your selling price
- **Unit** - Per crate, per bird, per kg, etc.
- **Minimum Order** - Smallest quantity you'll sell

### Step 4: Stock Information

- **Quantity Available** - How much you have
- **Track Inventory** - Auto-update when orders are placed

### Step 5: Photos

Good photos increase sales:
- Clear, well-lit images
- Show the actual product
- Multiple angles help

### Step 6: Publish

Click **Publish** to make your listing visible.

## Writing Good Descriptions

Include:
- Product quality (farm-fresh, organic, etc.)
- Source (your farm details)
- Freshness (collection date for eggs)
- Any certifications
- Delivery/pickup options

Example:
> "Fresh free-range eggs from our layer flock. Collected daily and delivered within 24 hours. Deep brown shells, rich yolks. Perfect for families and restaurants."

## Managing Listings

- **Edit** - Update prices, descriptions, stock
- **Pause** - Temporarily hide without deleting
- **Delete** - Remove listing completely
- **Duplicate** - Copy to create similar listing

## Tips for Success

1. **Competitive pricing** - Check what others charge
2. **Quality photos** - First impression matters
3. **Keep stock updated** - Don't list what you don't have
4. **Respond quickly** - Buyers expect fast replies
5. **Good descriptions** - Help buyers understand value''',
                        'keywords': 'listing, products, sell, create, add, publish, pricing',
                        'target_audience': 'farmers',
                        'is_featured': False,
                    },
                    {
                        'slug': 'managing-orders',
                        'title': 'Managing Orders',
                        'summary': 'How to view, process, and fulfill customer orders.',
                        'content': '''# Managing Orders

When buyers order your products, you'll need to process and fulfill those orders.

## Order Workflow

1. **Pending** - New order received
2. **Confirmed** - You accepted the order
3. **Processing** - Preparing the order
4. **Ready** - Ready for pickup/delivery
5. **Completed** - Order delivered and paid
6. **Cancelled** - Order was cancelled

## Receiving Orders

You'll be notified when you get an order:
- Push notification (if enabled)
- SMS notification
- Dashboard notification

## Processing an Order

### Step 1: View Order Details

Go to **Marketplace** → **Orders** → Click on the order

Review:
- Products ordered
- Quantities
- Customer details
- Delivery address or pickup preference
- Payment status

### Step 2: Confirm or Reject

- **Confirm** - If you can fulfill the order
- **Reject** - If you can't (explain why)

### Step 3: Prepare Order

- Gather the products
- Check quality
- Package appropriately

### Step 4: Mark Ready

Update status to **Ready** when the order is prepared.

### Step 5: Deliver or Arrange Pickup

- Contact customer for delivery/pickup
- Ensure safe delivery of products

### Step 6: Complete Order

After delivery and payment:
- Mark order as **Completed**
- Stock is automatically updated
- Sale is recorded

## Handling Issues

### Customer wants to cancel
- If not yet prepared: Cancel and refund
- If prepared: Discuss alternatives

### Product unavailable
- Contact customer immediately
- Offer alternatives or partial fulfillment
- Update your listings

### Payment issues
- Don't release products without payment
- Use the dispute process if needed

## Order Analytics

Track your performance:
- Total orders this month
- Completion rate
- Average order value
- Customer ratings''',
                        'keywords': 'orders, manage, process, fulfill, delivery, confirm',
                        'target_audience': 'farmers',
                        'is_featured': False,
                    },
                    {
                        'slug': 'marketplace-subscription',
                        'title': 'Marketplace Subscription',
                        'summary': 'Understanding marketplace activation fees and subscription plans.',
                        'content': '''# Marketplace Subscription

To have your products visible to buyers on the public marketplace, you need an active subscription.

## How It Works

- **All farmers** can use marketplace features (list products, track sales)
- **Subscribed farmers** appear in public marketplace searches
- **No commission** - Just a flat monthly fee

## Subscription Cost

**GHS 50 per month** - Marketplace Activation Fee

This is the only fee. We do NOT charge:
- Commission on sales
- Listing fees
- Transaction fees

## Benefits of Subscription

1. **Visibility** - Appear in buyer searches
2. **Reach** - Access buyers across Ghana
3. **Credibility** - Verified seller badge
4. **Analytics** - Detailed sales insights
5. **Support** - Priority customer support

## How to Subscribe

1. Go to **Marketplace** → **Subscription**
2. Choose payment method (Mobile Money)
3. Complete payment
4. Subscription activates immediately

## Trial Period

New farmers may get a free trial:
- Usually 7-14 days
- Full marketplace visibility
- No payment required

## Subscription Status

Check your status on the Marketplace Dashboard:
- **Active** - You're visible in searches
- **Trial** - Using free trial period
- **Past Due** - Payment overdue
- **Expired** - Not visible, please renew

## Renewing Your Subscription

- You'll be notified before expiry
- Renew to maintain visibility
- Auto-renewal can be enabled

## Cancellation

- You can cancel anytime
- Access continues until period ends
- Products remain but are hidden from public search
- Your sales data is preserved

## Payment Methods

Currently accepted:
- MTN Mobile Money
- Vodafone Cash
- AirtelTigo Money

More options coming soon!''',
                        'keywords': 'subscription, payment, fees, activate, monthly, cost, price',
                        'target_audience': 'farmers',
                        'is_featured': True,
                    },
                ],
            },
            
            # ==========================================
            # SALES & REVENUE
            # ==========================================
            {
                'name': 'Sales & Revenue',
                'slug': 'sales-revenue',
                'description': 'Track your sales, manage customers, and monitor your farm revenue.',
                'icon': '💰',
                'order': 5,
                'articles': [
                    {
                        'slug': 'recording-sales',
                        'title': 'Recording Sales',
                        'summary': 'How to record sales transactions including marketplace and direct sales.',
                        'content': '''# Recording Sales

Keeping accurate sales records helps you understand your farm's financial performance.

## Types of Sales

### Marketplace Sales
- Automatically recorded when orders are completed
- Linked to buyer account
- Inventory updated automatically

### Direct Sales
- Sales to walk-in customers
- Sales to regular buyers not through marketplace
- Recorded manually

## Recording a Direct Sale

### Egg Sales

1. Go to **Sales** → **Record Egg Sale**
2. Enter:
   - Date
   - Customer (select or add new)
   - Quantity (crates)
   - Price per crate
   - Payment status (Paid, Partial, Credit)
3. Save

### Bird Sales

1. Go to **Sales** → **Record Bird Sale**
2. Enter:
   - Date
   - Customer
   - Bird type (Layer, Broiler, POL)
   - Quantity
   - Price per bird
   - Payment status
3. Save

## Managing Customers

### Adding a Customer

1. Go to **Sales** → **Customers** → **Add Customer**
2. Enter:
   - Name
   - Phone number
   - Business name (optional)
   - Address (optional)
3. Save

### Customer History

View for each customer:
- Total purchases
- Outstanding balance
- Order history
- Contact information

## Tracking Payments

### Payment Status

- **Paid** - Full payment received
- **Partial** - Some payment received
- **Credit** - No payment yet (credit sale)

### Recording Payments

For credit sales:
1. Go to the sale record
2. Click **Add Payment**
3. Enter amount received
4. Save

## Sales Reports

View your sales performance:
- Daily, weekly, monthly totals
- By product type
- By customer
- Payment summaries''',
                        'keywords': 'sales, record, revenue, eggs, birds, direct sale, customer',
                        'target_audience': 'farmers',
                        'is_featured': False,
                    },
                    {
                        'slug': 'understanding-reports',
                        'title': 'Understanding Your Reports',
                        'summary': 'How to read and use the financial and production reports.',
                        'content': '''# Understanding Your Reports

Reports help you understand how your farm is performing and make better decisions.

## Available Reports

### Production Reports

**Daily Production Summary**
- Eggs collected per day
- Mortality per day
- Feed consumption
- Production percentage

**Flock Performance**
- Each flock's production rate
- Mortality trends
- Feed conversion ratio

### Financial Reports

**Revenue Summary**
- Total sales by period
- Revenue by product type
- Top customers

**Expense Summary**
- Total expenses by category
- Feed costs analysis
- Monthly comparisons

**Profit & Loss**
- Revenue minus expenses
- Net profit/loss
- Profit margins

### Marketplace Reports

**Sales Analytics**
- Orders received and completed
- Average order value
- Customer acquisition

## Reading Key Metrics

### Production Rate
Formula: (Eggs Collected ÷ Hen Count) × 100

- Above 80% = Excellent
- 70-80% = Good
- 60-70% = Fair
- Below 60% = Needs attention

### Feed Conversion Ratio (Layers)
Formula: Feed Consumed (kg) ÷ Eggs Produced (kg)

- Lower is better
- Target: 2.0-2.5 for layers

### Mortality Rate
Formula: (Deaths ÷ Starting Count) × 100

- Below 5% = Normal
- 5-10% = Monitor closely
- Above 10% = Investigate

## Exporting Reports

Download your data:
1. Go to any report
2. Click **Export**
3. Choose format (PDF, Excel, CSV)
4. Download

## Using Reports for Decisions

- **High mortality?** - Check health, feed quality, housing
- **Low production?** - Review feed, lighting, bird age
- **High expenses?** - Look for cost-cutting opportunities
- **Strong sales?** - Consider expanding''',
                        'keywords': 'reports, analytics, performance, metrics, data, summary',
                        'target_audience': 'farmers',
                        'is_featured': False,
                    },
                ],
            },
            
            # ==========================================
            # FOR BUYERS
            # ==========================================
            {
                'name': 'For Buyers',
                'slug': 'for-buyers',
                'description': 'Guides for buyers looking to purchase poultry products on the marketplace.',
                'icon': '🛍️',
                'order': 6,
                'articles': [
                    {
                        'slug': 'finding-products',
                        'title': 'Finding Products',
                        'summary': 'How to search and browse products on the marketplace.',
                        'content': '''# Finding Products

The YEA Marketplace makes it easy to find quality poultry products from verified farmers.

## Browsing the Marketplace

### Home Page

View featured products:
- Popular items
- Recent listings
- Farms near you

### Categories

Browse by type:
- **Eggs** - Fresh table eggs, fertilized eggs
- **Live Birds** - Layers, broilers, point-of-lay
- **Processed Products** - Dressed chicken

## Searching for Products

### Basic Search

1. Click the search bar
2. Enter what you're looking for
3. View results

### Advanced Filters

Narrow your search:
- **Location** - Region, District, Constituency
- **Price Range** - Min and max price
- **Quantity** - Available stock
- **Product Type** - Specific categories

## Understanding Listings

Each listing shows:
- Product name and photo
- Price per unit
- Available quantity
- Farm name and location
- Farm rating (if available)
- Distance from you (if location enabled)

## Contacting Farmers

To inquire or order:
1. Click on a product
2. View full details
3. Click **Contact Farmer**
4. Send a message or call directly

## Saving Favorites

Save products for later:
1. Click the heart/save icon
2. Find them in **My Favorites**

## Tips for Buyers

1. **Compare prices** across multiple farms
2. **Check farm profiles** for credibility
3. **Read descriptions** carefully
4. **Ask questions** before ordering
5. **Start small** with new farmers''',
                        'keywords': 'buy, search, find, products, marketplace, browse, shop',
                        'target_audience': 'buyers',
                        'is_featured': True,
                    },
                    {
                        'slug': 'placing-orders',
                        'title': 'Placing Orders',
                        'summary': 'How to order products from farmers on the marketplace.',
                        'content': '''# Placing Orders

Here's how to order poultry products from farmers on the YEA Marketplace.

## Order Process

### Step 1: Select Products

- Browse or search for products
- Click on a product to view details
- Check price, quantity, and description

### Step 2: Add to Cart

- Enter quantity you want
- Click **Add to Cart**
- Continue shopping or proceed to checkout

### Step 3: Review Cart

- View all selected items
- Adjust quantities if needed
- See total cost

### Step 4: Checkout

- Confirm delivery address
- Add any special instructions
- Review order summary

### Step 5: Payment

- Choose payment method
- Complete payment
- Receive order confirmation

## Delivery Options

### Pickup
- Collect from the farm
- No delivery fee
- Coordinate with farmer

### Delivery
- Farmer delivers to you
- Delivery fee may apply
- Confirm delivery time

## After Ordering

You'll receive:
- Order confirmation via SMS
- Updates as order progresses
- Delivery/pickup notification

Track your order in **My Orders**.

## Payment Methods

- Mobile Money (MTN, Vodafone, AirtelTigo)
- Cash on Delivery (where offered)
- Cash on Pickup

## Cancelling an Order

To cancel:
1. Go to **My Orders**
2. Find the order
3. Click **Cancel** (if available)
4. Provide reason

Note: You may not be able to cancel if the order is already being prepared.

## Problems with Orders?

If there's an issue:
1. Contact the farmer first
2. Try to resolve amicably
3. If needed, use the dispute process''',
                        'keywords': 'order, buy, purchase, checkout, cart, delivery, pickup',
                        'target_audience': 'buyers',
                        'is_featured': False,
                    },
                ],
            },
            
            # ==========================================
            # EXTENSION OFFICERS
            # ==========================================
            {
                'name': 'For Extension Officers',
                'slug': 'extension-officers',
                'description': 'Guides for extension officers supporting farmers in the program.',
                'icon': '👨‍🌾',
                'order': 7,
                'articles': [
                    {
                        'slug': 'extension-officer-overview',
                        'title': 'Extension Officer Overview',
                        'summary': 'Understanding your role as an extension officer in the YEA Poultry Program.',
                        'content': '''# Extension Officer Overview

As an extension officer, you play a vital role in supporting farmers in the YEA Poultry Program.

## Your Role

### Primary Responsibilities

1. **Data Verification** - Ensure farmers enter accurate production data
2. **Farmer Support** - Help farmers use the system effectively
3. **Field Registration** - Register farmers during farm visits
4. **Technical Advice** - Provide poultry farming guidance
5. **Issue Escalation** - Report problems to regional/national level

## Types of Field Officers

- **Extension Officers** - General technical support
- **Veterinary Officers** - Animal health focus
- **YEA Officials** - Program administration, farmer onboarding

## Your Dashboard

Access key information:
- Farms in your jurisdiction
- Pending tasks
- Recent activities
- Data quality overview

## Key Functions

### Farmer Registration
Register farmers during field visits:
- Create account on farmer's behalf
- Enter farm details
- Verify information firsthand

### Data Verification
Review farmer-entered data:
- Check production records
- Verify mortality reports
- Flag suspicious entries

### Farm Updates
Update farm information:
- After field assessments
- When changes occur
- Readiness and biosecurity scores

## Getting Started

1. Log in with your officer credentials
2. View your assigned farms
3. Check pending tasks
4. Start supporting farmers!

See the following guides for detailed instructions on each function.''',
                        'keywords': 'extension officer, field officer, vet, yea official, role, responsibilities',
                        'target_audience': 'staff',
                        'is_featured': True,
                    },
                    {
                        'slug': 'registering-farmers',
                        'title': 'Registering Farmers (Field Registration)',
                        'summary': 'How to register a new farmer during a field visit.',
                        'content': '''# Registering Farmers (Field Registration)

Register farmers on their behalf during field visits to streamline onboarding.

## When to Use Field Registration

- Farmer doesn't have a smartphone
- Farmer needs help with registration
- Bulk registration during field visits
- Farmer verification is easier in person

## Registration Steps

### Step 1: Verify Identity

Confirm farmer's identity:
- Check Ghana Card
- Verify phone number
- Confirm they own/manage a poultry farm

### Step 2: Start Registration

Go to **Extension** → **Register Farmer**

### Step 3: Enter Farmer Details

**Personal Information:**
- First name
- Last name
- Phone number
- Ghana Card number
- Email (optional)

**Location:**
- Region
- District
- Constituency

### Step 4: Enter Farm Details

**Farm Information:**
- Farm name
- Town/village
- Address
- Production type (Layers/Broilers)
- Housing type
- Bird capacity
- Current bird count

### Step 5: Submit

Click **Register**

The farmer:
- Gets an account created
- Receives SMS with login details
- Farm is marked as approved
- You're assigned as their extension officer

## After Registration

**For the Farmer:**
- They can log in using phone + temporary password
- Should change password on first login
- Can start using all features

**For You:**
- Farm appears in your assigned farms
- You can verify their data
- Provide ongoing support

## Tips for Field Registration

1. **Double-check phone number** - Critical for login
2. **Take photos** if required
3. **Explain the system** to the farmer
4. **Help them log in** for the first time
5. **Record accurate data** - Verify during visit''',
                        'keywords': 'register farmer, field registration, onboard, new farmer, extension',
                        'target_audience': 'staff',
                        'is_featured': False,
                    },
                    {
                        'slug': 'verifying-farm-data',
                        'title': 'Verifying Farm Data',
                        'summary': 'How to review and verify farmer-entered production data.',
                        'content': '''# Verifying Farm Data

Your key responsibility is ensuring farmers enter accurate data. Here's how to verify their records.

## Why Verify Data?

- Ensures program statistics are accurate
- Identifies farms needing support
- Detects potential issues early
- Maintains data integrity

## Accessing Data for Review

### Farm Data Review

1. Go to **Extension** → **Farms**
2. Select a farm
3. Click **Data Review**

### What to Review

**Production Records:**
- Daily egg collection
- Feed consumption
- Mortality records
- Consistency over time

**Red Flags to Look For:**
- Missing days (gaps in records)
- Sudden changes (unrealistic jumps)
- Perfect numbers (always same value)
- Zero entries (no activity recorded)

## Verification Actions

### Verify Records

If data looks correct:
1. Select records to verify
2. Click **Verify**
3. Add notes if needed

### Flag Issues

If data looks wrong:
1. Select the records
2. Click **Flag**
3. Enter reason for flagging
4. Follow up with farmer

## Data Quality Dashboard

View overall data quality:
- Farms with good data entry
- Farms needing attention
- Data completeness scores
- Recent activity

## Helping Farmers Improve

When data quality is poor:
1. Contact the farmer
2. Understand why (forgot, doesn't understand, etc.)
3. Train them on proper recording
4. Enter data on their behalf if needed
5. Follow up to ensure improvement

## Entering Data on Behalf

If a farmer needs help:
1. Go to **Extension** → **Assist Entry**
2. Select the farm
3. Enter production or mortality data
4. Data is auto-verified (entered by officer)

Use this sparingly - farmers should enter their own data.''',
                        'keywords': 'verify, data, review, check, flag, quality, extension',
                        'target_audience': 'staff',
                        'is_featured': False,
                    },
                ],
            },
            
            # ==========================================
            # ACCOUNT & SECURITY
            # ==========================================
            {
                'name': 'Account & Security',
                'slug': 'account-security',
                'description': 'Manage your account settings, password, and security options.',
                'icon': '🔐',
                'order': 8,
                'articles': [
                    {
                        'slug': 'changing-password',
                        'title': 'Changing Your Password',
                        'summary': 'How to change your account password.',
                        'content': '''# Changing Your Password

Keep your account secure by using a strong password and changing it regularly.

## How to Change Password

### From Settings

1. Go to **Profile** → **Security**
2. Click **Change Password**
3. Enter current password
4. Enter new password
5. Confirm new password
6. Click **Save**

### Password Requirements

Your password must have:
- At least 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character (!@#$%^&*)

### Tips for Strong Passwords

- Don't use personal information (name, birthday)
- Don't use common words
- Use a unique password for this account
- Consider using a password manager

## Forgot Password?

If you can't remember your password:
1. Go to the login page
2. Click **Forgot Password**
3. Enter your phone number
4. Receive reset code via SMS
5. Enter code and create new password

## Security Tips

1. **Never share your password** with anyone
2. **Log out** on shared devices
3. **Change password** if you suspect compromise
4. **Enable MFA** for extra security (if available)''',
                        'keywords': 'password, change, reset, forgot, security, login',
                        'target_audience': 'all',
                        'is_featured': False,
                    },
                    {
                        'slug': 'updating-profile',
                        'title': 'Updating Your Profile',
                        'summary': 'How to update your personal information and farm details.',
                        'content': '''# Updating Your Profile

Keep your profile information current for better communication and support.

## Updating Personal Information

### Access Profile

Go to **Profile** → **Edit Profile**

### What You Can Update

**Personal Details:**
- First name
- Last name
- Email address
- Profile photo

**Contact Information:**
- Phone number (may require verification)
- Alternate phone
- Address

### Saving Changes

Click **Save** after making changes.

## Updating Farm Information

### Access Farm Settings

Go to **Farm Settings** or **My Farm** → **Edit**

### What You Can Update

**Farm Details:**
- Farm name
- Address
- Production type
- Housing type
- Bird capacity

**Some fields may require verification:**
- Location changes
- Capacity changes
- Major updates

## What You Cannot Change

Some information is locked after registration:
- Ghana Card number
- Primary phone (without verification)
- Constituency (requires re-registration)

Contact support if you need to change locked fields.

## Profile Visibility

On the marketplace, buyers can see:
- Farm name
- General location (district/region)
- Products listed
- Ratings and reviews

They cannot see:
- Your personal phone (unless you share)
- Your home address
- Your Ghana Card details

## Keeping Information Current

Update your profile when:
- You move to a new location
- Your phone number changes
- Your email changes
- Farm details change''',
                        'keywords': 'profile, update, edit, personal, information, settings',
                        'target_audience': 'all',
                        'is_featured': False,
                    },
                ],
            },
            
            # ==========================================
            # TROUBLESHOOTING
            # ==========================================
            {
                'name': 'Troubleshooting',
                'slug': 'troubleshooting',
                'description': 'Solutions to common problems and how to get help when you need it.',
                'icon': '🔧',
                'order': 9,
                'articles': [
                    {
                        'slug': 'common-issues',
                        'title': 'Common Issues and Solutions',
                        'summary': 'Quick fixes for the most common problems users experience.',
                        'content': '''# Common Issues and Solutions

Here are solutions to the most common problems users experience.

## Login Issues

### Can't log in

**Check:**
- Phone number is correct
- Password is correct (case-sensitive)
- Caps Lock is off

**Solution:**
- Use "Forgot Password" to reset
- Contact support if locked out

### Session expired

You're automatically logged out for security after inactivity.

**Solution:**
- Log in again
- Check "Remember Me" to stay logged in longer

## App Issues

### App is slow

**Causes:**
- Poor internet connection
- Browser cache full
- Old browser version

**Solutions:**
- Check your internet
- Clear browser cache
- Update your browser
- Try a different browser

### Features not loading

**Solutions:**
- Refresh the page
- Clear cache and cookies
- Log out and log back in
- Check internet connection

### Error messages

If you see an error:
1. Note the error message
2. Refresh the page
3. Try again
4. If persistent, contact support with the error details

## Data Issues

### Data not saving

**Check:**
- All required fields are filled
- Internet connection is stable
- You have permission for the action

**Solution:**
- Fill all required fields
- Wait for good connection
- Try again

### Wrong data entered

To correct data:
1. Find the record
2. Click Edit
3. Make corrections
4. Save

Some historical data may need officer approval to edit.

## Payment Issues

### Payment not going through

**Check:**
- Sufficient balance
- Network connectivity
- Correct phone number

**Solution:**
- Try again
- Use a different payment method
- Contact your mobile money provider

### Payment made but not reflected

**Wait:**
- Allow 5-10 minutes for processing

**If still not showing:**
1. Check your mobile money transaction history
2. Note the transaction ID
3. Contact support with details

## Getting More Help

If none of these solutions work:
1. Go to **Help** → **Contact Support**
2. Describe your issue in detail
3. Include any error messages
4. Include your phone number''',
                        'keywords': 'problem, issue, error, fix, help, trouble, not working',
                        'target_audience': 'all',
                        'is_featured': True,
                    },
                    {
                        'slug': 'contacting-support',
                        'title': 'Contacting Support',
                        'summary': 'How to reach out for help when you need it.',
                        'content': '''# Contacting Support

We're here to help! Here's how to reach us.

## Before Contacting Support

1. **Check this Help Center** - Your answer may be here
2. **Check common issues** - Review troubleshooting guides
3. **Ask your Extension Officer** - They can help with many issues

## Contact Methods

### In-App Contact Form

Best for non-urgent issues:
1. Go to **Help** → **Contact Us**
2. Select issue category
3. Describe your problem
4. Include relevant details
5. Submit

We'll respond within 24-48 hours.

### Phone Support

For urgent issues:
- Coming soon!

### Your Extension Officer

For farm-related questions:
- Find their contact in your dashboard
- Call or message them directly
- Best for local issues

## What to Include

When contacting support:
1. **Your name and phone number**
2. **Description of the issue**
3. **Steps to reproduce** (what you were doing)
4. **Error messages** (exact text or screenshot)
5. **Device and browser** (if web issue)

## Response Times

- **Contact Form**: 24-48 hours
- **Urgent Issues**: Mark as urgent for faster response
- **Extension Officer**: Usually same day

## Issue Categories

When submitting, select the right category:
- **Account Issues** - Login, password, profile
- **Technical Issues** - Bugs, errors, performance
- **Farm Management** - Flock, production, data
- **Marketplace** - Listings, orders, payments
- **Billing** - Subscription, payments, refunds
- **Feature Requests** - Suggestions for improvement
- **Other** - Anything else

## Feedback

We love feedback!
- Suggestions for improvement
- Features you'd like to see
- What's working well

Send feedback through the contact form with category "Feature Requests".''',
                        'keywords': 'support, help, contact, phone, email, issue, problem',
                        'target_audience': 'all',
                        'is_featured': False,
                    },
                ],
            },
        ]
