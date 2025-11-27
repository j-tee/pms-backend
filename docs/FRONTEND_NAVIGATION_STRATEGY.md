# Frontend Navigation & User Interaction Strategy
## Complete System Architecture for User-Friendly Design

**Last Updated:** November 26, 2025  
**Version:** 1.0  
**Target Audience:** Frontend Developers, UI/UX Designers, Product Team

---

## Table of Contents

1. [System Overview](#system-overview)
2. [User Types & Dashboards](#user-types--dashboards)
3. [Navigation Structure](#navigation-structure)
4. [Sales & Marketing Features](#sales--marketing-features)
5. [Public vs Authenticated Areas](#public-vs-authenticated-areas)
6. [Mobile-First Design Strategy](#mobile-first-design-strategy)
7. [User Flows](#user-flows)
8. [Dashboard Specifications](#dashboard-specifications)

---

## System Overview

### Three-Tier User Experience

```
┌─────────────────────────────────────────────────────────────┐
│                      PUBLIC SPACE                            │
│  • Landing Page                                              │
│  • Application Submission (EOI)                             │
│  • Application Tracking                                     │
│  • Public Marketplace (Browse Products)                     │
│  • Product Search & Filtering                              │
│  • Statistics & Success Stories                            │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  FARMER DASHBOARD                            │
│  • Farm Management (Core - FREE for ALL)                    │
│  • Production Tracking                                      │
│  • Marketplace Selling (OPTIONAL subscription - GHS 100)   │
│  • Sales & Revenue Analytics                               │
│  • Extension Officer Communication                         │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│               ADMIN DASHBOARDS (Multi-Level)                │
│  • Constituency Officers                                    │
│  • Regional Officers                                        │
│  • National Administrators                                  │
│  • Veterinary Officers                                      │
│  • Procurement Officers                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## User Types & Dashboards

### 1. **Prospective Farmers (Public Users)**
**Access:** No authentication required  
**Primary Goal:** Submit application and track status

**Features:**
- Submit farm application (EOI)
- Track application status via Ghana Card
- Browse public marketplace
- View platform statistics
- Read success stories

**Navigation:**
```
┌─ Home
├─ Apply Now (Primary CTA)
├─ Track Application
├─ Marketplace (Public View)
│  ├─ Browse Eggs
│  ├─ Browse Birds
│  └─ Search Products
├─ About
└─ Contact
```

---

### 2. **Farmers (Authenticated)**
**Access:** Account required (post-approval)  
**Primary Goals:** Manage farm, track production, **sell products**

#### 2a. **FREE Tier Farmers**
- Core farm management
- Production tracking
- Flock management
- Feed & medication tracking
- View own data & analytics
- No marketplace selling

#### 2b. **PAID Tier Farmers (Marketplace Subscription)**
- Everything in FREE tier +
- Marketplace product listings
- Customer management
- Order management
- Sales & revenue analytics
- Payment tracking
- Fraud detection insights

#### 2c. **Government Farmers**
- Everything in FREE tier +
- Extension officer supervision
- Training schedules
- Support package tracking
- Subsidized marketplace (if opted in)
- Compliance reporting

**Core Navigation (All Farmers):**
```
┌─ Dashboard (Overview)
├─ Farm Management ✓ FREE
│  ├─ Farm Profile
│  ├─ Farm Locations
│  ├─ Infrastructure
│  ├─ Equipment
│  └─ Documents
├─ Flock Management ✓ FREE
│  ├─ Active Flocks
│  ├─ Production Records
│  ├─ Mortality Tracking
│  └─ Health Records
├─ Feed Inventory ✓ FREE
│  ├─ Current Stock
│  ├─ Feed Purchases
│  └─ Consumption Tracking
├─ Medication & Vaccination ✓ FREE
│  ├─ Medication Records
│  ├─ Vaccination Schedule
│  └─ Vet Visits
├─ 💰 MARKETPLACE (Subscription) 🔒
│  ├─ My Products
│  ├─ Orders
│  ├─ Customers
│  ├─ Sales Analytics
│  └─ Payments & Payouts
├─ Analytics & Reports ✓ FREE
│  ├─ Production Performance
│  ├─ Financial Overview
│  ├─ Feed Efficiency
│  └─ Export Reports
├─ Extension Officer (Gov't Farmers)
│  ├─ Scheduled Visits
│  ├─ Training Sessions
│  └─ Support Packages
└─ Account Settings
   ├─ Profile
   ├─ Security & MFA
   ├─ Subscription (if applicable)
   └─ Notifications
```

---

### 3. **Constituency Officers**
**Access:** Authenticated (Role-based)  
**Primary Goals:** Review applications, support farmers, monitor constituency

**Navigation:**
```
┌─ Dashboard
│  ├─ My Queue (Applications)
│  ├─ Performance Metrics
│  └─ Alerts & Notifications
├─ Applications
│  ├─ Pending Review
│  ├─ Approved
│  ├─ Rejected
│  └─ Changes Requested
├─ Farmers (Approved)
│  ├─ Active Farms
│  ├─ Farm Performance
│  ├─ Visits Scheduled
│  └─ Support Requests
├─ Program Enrollment
│  ├─ Pending Applications
│  └─ Enrolled Farmers
├─ Reports
│  ├─ Constituency Overview
│  ├─ Production Statistics
│  └─ Compliance Status
└─ Settings
```

---

### 4. **Regional Officers**
**Access:** Authenticated (Role-based)  
**Primary Goals:** Oversee multiple constituencies, approve regional applications

**Navigation:**
```
┌─ Dashboard
│  ├─ Regional Overview
│  ├─ Constituency Performance
│  └─ Key Metrics
├─ Applications
│  ├─ Regional Queue
│  ├─ Review History
│  └─ Analytics
├─ Constituencies
│  ├─ List All
│  ├─ Performance Comparison
│  └─ Officer Management
├─ Farmers
│  ├─ Regional Directory
│  ├─ Production Trends
│  └─ Support Needs
├─ Program Management
│  ├─ Enrollment Overview
│  └─ Budget Tracking
└─ Reports
   ├─ Regional Performance
   ├─ Budget Utilization
   └─ Export Data
```

---

### 5. **National Administrators**
**Access:** Authenticated (Highest level)  
**Primary Goals:** Platform management, policy implementation, national oversight

**Navigation:**
```
┌─ Dashboard
│  ├─ National Overview
│  ├─ Real-time Statistics
│  └─ Critical Alerts
├─ Applications
│  ├─ National Queue
│  ├─ Final Approvals
│  └─ Review Analytics
├─ User Management
│  ├─ Farmers
│  ├─ Officers
│  ├─ Roles & Permissions
│  └─ Account Actions
├─ Platform Settings
│  ├─ Commission Rates
│  ├─ Subscription Settings
│  ├─ Feature Flags
│  └─ System Configuration
├─ Programs
│  ├─ Government Programs
│  ├─ Enrollment Management
│  └─ Budget Allocation
├─ Marketplace Management
│  ├─ Product Categories
│  ├─ Fraud Alerts
│  ├─ Payment Issues
│  └─ Settlements
├─ Analytics & BI
│  ├─ National Production
│  ├─ Revenue & Sales
│  ├─ Farmer Performance
│  ├─ Program Impact
│  └─ Export Reports
└─ System Admin
   ├─ Audit Logs
   ├─ Security Settings
   └─ Backup & Maintenance
```

---

### 6. **Veterinary Officers**
**Access:** Authenticated (Specialized role)  
**Primary Goals:** Health monitoring, disease surveillance, compliance

**Navigation:**
```
┌─ Dashboard
│  ├─ Visit Schedule
│  ├─ Urgent Cases
│  └─ Disease Alerts
├─ Farms
│  ├─ Assigned Farms
│  ├─ Visit History
│  └─ Health Status
├─ Mortality Investigation
│  ├─ Pending Reviews
│  ├─ Lab Test Tracking
│  └─ Disease Patterns
├─ Vaccination Campaigns
│  ├─ Scheduled Campaigns
│  ├─ Compliance Tracking
│  └─ Coverage Statistics
├─ Reports
│  ├─ Disease Surveillance
│  ├─ Compliance Summary
│  └─ Recommendations
└─ Resources
   ├─ Treatment Protocols
   └─ Emergency Contacts
```

---

### 7. **Procurement Officers**
**Access:** Authenticated (Specialized role)  
**Primary Goals:** Bulk orders, supplier management

**Navigation:**
```
┌─ Dashboard
│  ├─ Active Orders
│  ├─ Pending Approvals
│  └─ Delivery Schedule
├─ Farmers
│  ├─ Eligible Suppliers
│  ├─ Production Capacity
│  └─ Quality Ratings
├─ Orders
│  ├─ Create Bulk Order
│  ├─ Order History
│  └─ Payment Tracking
├─ Suppliers
│  ├─ Supplier Directory
│  ├─ Performance Metrics
│  └─ Contract Management
└─ Reports
   ├─ Procurement Summary
   └─ Budget Tracking
```

---

## Navigation Structure

### Top-Level Navigation Patterns

#### **Farmer Dashboard** (Primary)
```
┌───────────────────────────────────────────────────────────┐
│ [Logo]  Dashboard  Flocks  Marketplace  Analytics  [👤]   │
└───────────────────────────────────────────────────────────┘
```

**Desktop (Sidebar + Top Bar):**
- **Left Sidebar:** Primary navigation (always visible)
- **Top Bar:** User profile, notifications, quick actions
- **Breadcrumbs:** Context navigation
- **Bottom Bar (Mobile):** Quick access to key features

**Mobile (Bottom Nav + Hamburger):**
- **Bottom Navigation:** 4-5 primary items
- **Hamburger Menu:** Secondary navigation
- **Floating Action Button:** Primary action (Add Product, Record Production)

---

### Navigation Components

#### 1. **Sidebar Navigation (Desktop)**
```
┌─────────────────────┐
│ [Logo]              │
│                     │
│ 🏠 Dashboard        │
│ 🐔 Flocks          │
│ 🌾 Feed            │
│ 💊 Medication       │
│ 💰 Marketplace 🔒   │
│ 📊 Analytics        │
│ ⚙️  Settings        │
│                     │
│ ─────────────────  │
│ 💳 Upgrade Plan    │
└─────────────────────┘
```

#### 2. **Bottom Navigation (Mobile)**
```
┌────────────────────────────────────────┐
│  🏠      🐔      ➕       💰      👤   │
│ Home   Flocks   Add   Marketplace  Me  │
└────────────────────────────────────────┘
```

#### 3. **Breadcrumb Navigation**
```
Dashboard > Flocks > Flock-2025-001 > Daily Production > Edit
```

---

## Sales & Marketing Features

### 🎯 **PRIORITY: Marketplace is Key to Farmer Success**

Farmers need to **SELL** their products easily. This is the most important feature for revenue generation.

### Marketplace Architecture

```
PUBLIC MARKETPLACE (Browse Only)
          ↓
[Customer Discovers Products]
          ↓
[Customer Places Order]
          ↓
FARMER DASHBOARD (Marketplace Subscription Required)
          ↓
[Farmer Receives Order Notification]
          ↓
[Farmer Confirms Order]
          ↓
[Customer Pays via Mobile Money/Card]
          ↓
[Payment Split: Platform Commission | Farmer Payout]
          ↓
[Farmer Ships/Delivers Product]
          ↓
[Order Complete]
```

---

### Farmer Marketplace Dashboard (Detailed)

#### **Dashboard Overview Card**
```
┌───────────────────────────────────────────────────────┐
│ 💰 Today's Sales: GHS 450.00                          │
│ 📦 Pending Orders: 3                                  │
│ 🥚 Eggs in Stock: 120 crates                         │
│ 👥 New Customers: 2                                   │
└───────────────────────────────────────────────────────┘
```

#### **Product Management**
```
┌─ My Products
│  ├─ Active Listings (12)
│  ├─ Out of Stock (2)
│  ├─ Draft (1)
│  └─ Archived (5)
│
│  Actions:
│  • Add New Product
│  • Bulk Edit Prices
│  • Update Stock Levels
│  • Upload Product Images (Max 20)
```

**Product Listing Form:**
```
Product Type: [Eggs ▼]
Category: [Layer Eggs ▼]
Quantity: [50] crates
Price per Unit: GHS [25.00]
Description: [Free-range layer eggs, fresh daily...]
Images: [Upload] (Up to 20 images)
Location: [Auto-filled from farm]
Delivery Options: [✓] Farm Pickup [ ] Delivery
```

#### **Order Management**
```
┌─ Orders
│  ├─ New Orders (Badge: 3)
│  │  └─ Requires immediate action
│  ├─ Processing (5)
│  ├─ Ready for Pickup (2)
│  ├─ Completed (145)
│  └─ Cancelled (7)
```

**Order Detail View:**
```
Order #ORD-2025-00456
Customer: Kofi Mensah (+233244111222)
Date: Nov 26, 2025 10:30 AM

Items:
• Layer Eggs (Brown) - 5 crates @ GHS 25.00 = GHS 125.00

Subtotal: GHS 125.00
Platform Fee (2%): GHS 2.50
Customer Pays: GHS 125.00
You Receive: GHS 122.50

Delivery: Farm Pickup
Status: [New Order]

Actions:
[Accept Order] [Reject Order] [Message Customer]
```

#### **Customer Management**
```
┌─ Customers (87 total)
│  ├─ Top Customers (by revenue)
│  │  1. Akosua Traders - GHS 12,450 (24 orders)
│  │  2. Market Vendors Coop - GHS 8,920 (18 orders)
│  │  3. Kofi Restaurant - GHS 6,780 (15 orders)
│  │
│  ├─ Recent Customers
│  └─ Customer Groups
│     • Retailers
│     • Wholesalers
│     • Individual Buyers
```

**Customer Profile:**
```
Akosua Traders
Contact: +233244567890
Email: akosua@example.com
Location: Tema Market
Customer Since: Jan 15, 2025

Purchase History:
• Total Orders: 24
• Total Spent: GHS 12,450
• Average Order: GHS 518.75
• Favorite Product: Layer Eggs (Brown)

Last Order: Nov 20, 2025
Next Expected Order: Nov 28, 2025 (based on pattern)

Actions:
[Send Message] [Create Invoice] [View Orders]
```

#### **Sales Analytics**
```
┌─ Sales Dashboard
│  ├─ Revenue Trends
│  │  • Today: GHS 450
│  │  • This Week: GHS 3,200
│  │  • This Month: GHS 12,800
│  │  • Last Month: GHS 11,500 (+11.3%)
│  │
│  ├─ Top Products
│  │  1. Layer Eggs (Brown) - 450 crates - GHS 11,250
│  │  2. Broiler Chickens - 85 birds - GHS 8,500
│  │  3. Layer Eggs (White) - 220 crates - GHS 5,280
│  │
│  ├─ Sales by Customer Type
│  │  • Retailers: 45% (GHS 5,760)
│  │  • Wholesalers: 35% (GHS 4,480)
│  │  • Individual: 20% (GHS 2,560)
│  │
│  └─ Peak Sales Days
│     • Thursday (Market Day)
│     • Sunday (Church buyers)
```

**Revenue Chart:**
```
GHS 
5000│              ▲
4000│         ▲    │
3000│    ▲    │    │  ▲
2000│ ▲  │  ▲ │  ▲ │  │
1000│ │  │  │ │  │ │  │
    └─────────────────────
     Mon Tue Wed Thu Fri
```

#### **Payment & Payout Tracking**
```
┌─ Payments & Payouts
│  ├─ Pending Settlements
│  │  └─ GHS 2,450 (from 8 orders)
│  │     Expected: Nov 28, 2025
│  │
│  ├─ Recent Payouts
│  │  • Nov 20 - GHS 3,200 ✓ Paid
│  │  • Nov 13 - GHS 2,890 ✓ Paid
│  │  • Nov 6 - GHS 4,120 ✓ Paid
│  │
│  ├─ Payment Method
│  │  MTN Mobile Money: 024-XXX-X890
│  │  Status: ✓ Verified
│  │
│  └─ Commission Summary
│     • Total Sales (Month): GHS 12,800
│     • Platform Commission: GHS 256 (2%)
│     • Your Earnings: GHS 12,544
```

---

### Public Marketplace (Customer View)

```
┌────────────────────────────────────────────────────────┐
│ [🔍 Search: eggs, chickens, by location...]            │
└────────────────────────────────────────────────────────┘

Filters:
✓ Product Type
  [ ] Eggs
  [ ] Chickens (Broilers)
  [ ] Chickens (Layers)
  [ ] Spent Hens

✓ Location
  Region: [Greater Accra ▼]
  Constituency: [Tema East ▼]

✓ Price Range
  [GHS 20] ─────── [GHS 100]

✓ Delivery Options
  [ ] Farm Pickup Available
  [ ] Home Delivery Available

✓ Stock Status
  [ ] In Stock Only

──────────────────────────────────────────────────────────

Product Grid:
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ [Product Image]  │ │ [Product Image]  │ │ [Product Image]  │
│ Layer Eggs       │ │ Broiler Chickens │ │ Layer Eggs       │
│ (Brown)          │ │ Ready to Harvest │ │ (White)          │
│                  │ │                  │ │                  │
│ GHS 25 /crate    │ │ GHS 45 /bird     │ │ GHS 23 /crate    │
│ ⭐ 4.8 (24)      │ │ ⭐ 4.9 (12)      │ │ ⭐ 4.7 (18)      │
│ 📍 Tema East     │ │ 📍 Tema West     │ │ 📍 Tema Central  │
│ 🚚 Pickup        │ │ 🚚 Pickup        │ │ 🚚 Delivery      │
│ [View Details]   │ │ [View Details]   │ │ [View Details]   │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

**Product Detail Page:**
```
┌────────────────────────────────────────────────────────────┐
│ [Image Gallery - 5 images]                                 │
│                                                             │
│ Layer Eggs (Brown) - Fresh from Asante Farms               │
│ ⭐ 4.8 (24 reviews)                                        │
│                                                             │
│ GHS 25.00 per crate (30 eggs)                             │
│ In Stock: 50 crates                                        │
│                                                             │
│ Description:                                                │
│ Fresh free-range layer eggs from certified farm.           │
│ Collected daily. Rich brown shells. Perfect for retail.    │
│                                                             │
│ Farm: Asante Poultry Farm                                  │
│ Location: Tema East, Greater Accra                         │
│ Flock Type: Isa Brown Layers                              │
│ Production Method: Free Range                              │
│                                                             │
│ Delivery Options:                                           │
│ ✓ Farm Pickup (Free)                                       │
│ ✓ Delivery to Tema (GHS 5)                                │
│                                                             │
│ Quantity: [___] crates                                     │
│                                                             │
│ [Add to Cart] [Contact Seller] [Call: +233244567890]      │
└────────────────────────────────────────────────────────────┘

Customer Reviews:
⭐⭐⭐⭐⭐ Kofi M. - Nov 20, 2025
"Excellent quality. Always fresh. Highly recommend!"

⭐⭐⭐⭐⭐ Akosua T. - Nov 18, 2025
"Best eggs in Tema! Consistent quality."
```

---

## Public vs Authenticated Areas

### Access Control Matrix

| Feature | Public | Farmer (FREE) | Farmer (PAID) | Govt Farmer | Officers | Admin |
|---------|--------|---------------|---------------|-------------|----------|-------|
| **Browse Marketplace** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Submit Application** | ✓ | - | - | - | - | - |
| **Track Application** | ✓ | - | - | - | - | - |
| **Farm Management** | - | ✓ | ✓ | ✓ | View Only | ✓ |
| **Production Tracking** | - | ✓ | ✓ | ✓ | View Only | ✓ |
| **Sell on Marketplace** | - | - | ✓ | ✓* | - | - |
| **Order Management** | - | - | ✓ | ✓* | - | View |
| **Sales Analytics** | - | - | ✓ | ✓* | - | ✓ |
| **Review Applications** | - | - | - | - | ✓ | ✓ |
| **Platform Settings** | - | - | - | - | - | ✓ |

*Government farmers must opt into marketplace (subsidized if applicable)

---

## Mobile-First Design Strategy

### Design Principles

1. **Touch-Friendly:** Minimum 44px tap targets
2. **One-Handed Use:** Bottom navigation for primary actions
3. **Offline Capability:** Cache critical data
4. **Progressive Web App:** Install on home screen
5. **Fast Loading:** <3s initial load on 3G

### Mobile Layouts

#### **Farmer Dashboard (Mobile)**
```
┌────────────────────────────────┐
│ ☰  Dashboard           🔔 (2)  │ ← Header
├────────────────────────────────┤
│ 💰 Today: GHS 450              │
│ 📦 Orders: 3 pending           │ ← Quick Stats Card
│ 🐔 Flocks: 2 active            │
├────────────────────────────────┤
│ Recent Activity ▼              │ ← Collapsible Section
│                                │
│ • Order #456 - GHS 125         │
│ • Production recorded          │
│ • Payment received GHS 890     │
├────────────────────────────────┤
│ Quick Actions                  │
│ [➕ Record Production]         │ ← Primary Action
│ [📦 View Orders]               │
│ [💰 Check Sales]               │
└────────────────────────────────┘
  🏠  🐔  ➕  💰  👤             ← Bottom Nav
 Home Flocks Add Market Profile
```

#### **Product Listing (Mobile)**
```
┌────────────────────────────────┐
│ ←  My Products          [➕]   │
├────────────────────────────────┤
│ ┌────────────────────────────┐│
│ │ [Image]  Layer Eggs (Brown)││
│ │          GHS 25/crate      ││
│ │          In Stock: 50      ││
│ │          [Edit] [Share]    ││
│ └────────────────────────────┘│
│ ┌────────────────────────────┐│
│ │ [Image]  Broiler Chickens  ││
│ │          GHS 45/bird       ││
│ │          In Stock: 25      ││
│ │          [Edit] [Share]    ││
│ └────────────────────────────┘│
└────────────────────────────────┘
```

### Responsive Breakpoints

```css
/* Mobile First */
Default: 320px - 767px

/* Tablet */
@media (min-width: 768px) { ... }

/* Desktop */
@media (min-width: 1024px) { ... }

/* Large Desktop */
@media (min-width: 1440px) { ... }
```

---

## User Flows

### Critical User Journeys

#### **Journey 1: Prospective Farmer → Active Marketplace Seller**

```
1. Visit Public Website
   ↓
2. Read About Program
   ↓
3. Click "Apply Now"
   ↓
4. Fill Application Form (7 steps)
   ↓
5. Submit Application
   ↓
6. Track Status (via Ghana Card)
   ↓
7. Receive Approval Notification
   ↓
8. Create Account (via invitation)
   ↓
9. Complete Farm Profile
   ↓
10. Explore FREE Dashboard
    ↓
11. See Marketplace Features (Locked)
    ↓
12. Subscribe to Marketplace (GHS 100/month)
    ↓
13. Add First Product
    ↓
14. Receive First Order!
    ↓
15. Get First Payout
    ↓
16. SUCCESS! 🎉
```

**Timeframe:** 15-21 days from application to first sale

---

#### **Journey 2: Daily Farm Management (Existing Farmer)**

```
Morning Routine:
1. Open App (Mobile)
   ↓
2. Check New Orders (3 pending)
   ↓
3. Accept Orders
   ↓
4. Record Daily Production
   - Eggs collected: 450
   - Mortality: 2
   - Feed consumed: 25kg
   ↓
5. Update Product Stock
   ↓
6. Check Sales Dashboard
   ↓
7. Done! (< 10 minutes)
```

---

#### **Journey 3: Selling First Product**

```
1. Login to Farmer Dashboard
   ↓
2. Navigate to Marketplace
   ↓
3. Click "Add New Product"
   ↓
4. Fill Product Form:
   - Type: Eggs
   - Category: Layer (Brown)
   - Quantity: 50 crates
   - Price: GHS 25/crate
   - Upload 5 photos
   - Delivery: Farm pickup
   ↓
5. Preview Product Listing
   ↓
6. Publish Product
   ↓
7. Product appears on Public Marketplace
   ↓
8. Share product link (WhatsApp, Facebook)
   ↓
9. Wait for orders...
   ↓
10. Order notification arrives!
    ↓
11. Accept order
    ↓
12. Customer pays
    ↓
13. Fulfill order
    ↓
14. Mark as complete
    ↓
15. Money in account! 💰
```

---

## Dashboard Specifications

### Farmer Dashboard Widgets (Detailed)

#### **1. Overview Widget**
```
┌─────────────────────────────────────────────────┐
│ Today's Snapshot                  Nov 26, 2025  │
├─────────────────────────────────────────────────┤
│ 💰 Revenue          🥚 Eggs         🐔 Birds    │
│    GHS 450             450          1,240       │
│    ↑ 12%              ↓ 5%          → 0%       │
│                                                  │
│ 📦 Orders           💵 Pending      ⚠️ Alerts   │
│    3 new               GHS 2,450      2         │
│    [View]              [Details]     [View]     │
└─────────────────────────────────────────────────┘
```

#### **2. Production Summary**
```
┌─────────────────────────────────────────────────┐
│ Production This Month              [View All →] │
├─────────────────────────────────────────────────┤
│ Flock: LAYER-2025-001 (Isa Brown)              │
│ Current Count: 480 birds                        │
│ Eggs: 11,450 (avg 382/day)                     │
│ Mortality: 18 (3.75% rate) ⚠️                   │
│ Feed Efficiency: 2.1 FCR ✓                     │
│                                                  │
│ [Record Today's Production]                     │
└─────────────────────────────────────────────────┘
```

#### **3. Marketplace Performance (PAID Tier)**
```
┌─────────────────────────────────────────────────┐
│ Marketplace Sales                  [Details →]  │
├─────────────────────────────────────────────────┤
│ This Month:  GHS 12,800  ↑ 11% vs last month   │
│ Orders:      45          ↑ 8 more              │
│ Customers:   28          ↑ 4 new               │
│                                                  │
│ Top Product: Layer Eggs (Brown)                 │
│ Revenue: GHS 11,250 from 450 crates            │
│                                                  │
│ [View Full Analytics]                           │
└─────────────────────────────────────────────────┘
```

#### **4. Financial Overview**
```
┌─────────────────────────────────────────────────┐
│ Financial Health                   Nov 2025     │
├─────────────────────────────────────────────────┤
│ Income                                           │
│ • Sales Revenue:       GHS 12,800              │
│ • Government Subsidy:  GHS 0                   │
│ Total Income:          GHS 12,800              │
│                                                  │
│ Expenses                                         │
│ • Feed:                GHS 4,200               │
│ • Medication:          GHS 850                 │
│ • Labor:               GHS 1,500               │
│ • Subscription:        GHS 100                 │
│ Total Expenses:        GHS 6,650               │
│                                                  │
│ Net Profit:            GHS 6,150  (48% margin) │
│                                                  │
│ [Download Statement]                            │
└─────────────────────────────────────────────────┘
```

#### **5. Alerts & Notifications**
```
┌─────────────────────────────────────────────────┐
│ Alerts & Notifications               [Clear All]│
├─────────────────────────────────────────────────┤
│ ⚠️  Low Feed Stock                   2 hours ago│
│     Feed inventory below minimum (80kg left)    │
│     [Order Feed]                                │
│                                                  │
│ 💰 Payment Received                  1 day ago  │
│     GHS 890 deposited to your account          │
│     [View Details]                              │
│                                                  │
│ 📦 New Order                         2 days ago │
│     Akosua Traders ordered 10 crates eggs      │
│     [View Order]                                │
└─────────────────────────────────────────────────┘
```

---

### Officer Dashboard Widgets

#### **Constituency Officer Dashboard**
```
┌─────────────────────────────────────────────────┐
│ My Queue                          Tema East     │
├─────────────────────────────────────────────────┤
│ Applications Pending:  12                       │
│ • New (unassigned):    5  [Claim]              │
│ • In Review:           4  [Continue]           │
│ • Changes Requested:   3  [Follow Up]          │
│                                                  │
│ Overdue:              2  ⚠️ [Review Now]        │
│ SLA Compliance:       87% ✓                    │
│                                                  │
│ [View All Applications]                         │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ Active Farms in Constituency      [View All →] │
├─────────────────────────────────────────────────┤
│ Total Farms:        45                          │
│ Production Today:                                │
│ • Eggs: 12,450 collected                       │
│ • Birds Sold: 85                               │
│                                                  │
│ Alerts:                                          │
│ • Disease outbreak suspected (1 farm) ⚠️        │
│ • Mortality spike (3 farms) ⚠️                  │
│                                                  │
│ [View Details]                                  │
└─────────────────────────────────────────────────┘
```

---

## Next Steps for Frontend Team

### Phase 1: Foundation (Weeks 1-2)
- [ ] Design System & Component Library
- [ ] Authentication & Authorization
- [ ] Public Landing Page
- [ ] Application Form (EOI)

### Phase 2: Core Features (Weeks 3-5)
- [ ] Farmer Dashboard Layout
- [ ] Production Tracking Interface
- [ ] Flock Management UI
- [ ] Feed & Medication Tracking

### Phase 3: Marketplace (Weeks 6-8) 🎯
- [ ] Public Marketplace Browse
- [ ] Product Listing Management
- [ ] Order Management System
- [ ] Customer Management
- [ ] Sales Analytics Dashboard

### Phase 4: Officers & Admin (Weeks 9-10)
- [ ] Application Review Workflows
- [ ] Officer Dashboards (3 levels)
- [ ] Admin Platform Settings
- [ ] Reporting & Analytics

### Phase 5: Polish (Weeks 11-12)
- [ ] Mobile Optimization
- [ ] Performance Tuning
- [ ] Accessibility (WCAG 2.1 AA)
- [ ] User Testing & Refinement

---

## Design Resources

### Color Palette Suggestions

**Primary (Trust & Growth):**
- Primary Green: `#2D7A3F` (Agriculture, growth)
- Primary Blue: `#1E5C8B` (Trust, stability)

**Secondary:**
- Warning: `#F59E0B` (Alerts, low stock)
- Danger: `#DC2626` (Critical alerts, rejections)
- Success: `#10B981` (Approvals, profits)

**Neutral:**
- Background: `#F9FAFB`
- Card: `#FFFFFF`
- Border: `#E5E7EB`
- Text: `#111827`
- Muted: `#6B7280`

### Typography
```
Primary Font: Inter (Clean, modern, readable)
Headings: 600-700 weight
Body: 400 weight
Code/Numbers: 500 weight (Tabular figures)
```

### Icons
- **Recommended:** Heroicons (MIT license, matches Tailwind)
- **Alternative:** Feather Icons, Lucide

---

## Technical Recommendations

### Frontend Stack
- **Framework:** React + TypeScript / Next.js 14+
- **Styling:** Tailwind CSS
- **State:** Zustand / React Query
- **Forms:** React Hook Form + Zod
- **Charts:** Recharts / Chart.js
- **Tables:** TanStack Table
- **Notifications:** React Toastify

### Best Practices
1. **Component-Driven:** Build reusable components
2. **Accessibility:** ARIA labels, keyboard nav, screen readers
3. **Performance:** Lazy loading, code splitting, image optimization
4. **SEO:** Next.js SSR/SSG for public pages
5. **Testing:** Jest + React Testing Library

---

**End of Document**

**Questions? Contact Backend Team:**
- Technical Lead: backend@pms.gov.gh
- Slack: #frontend-backend-integration
