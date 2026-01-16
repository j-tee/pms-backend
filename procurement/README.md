# Government Procurement System - API Documentation

> **B2G (Business-to-Government) Procurement API**
> 
> Manage government bulk orders from approved poultry farms including order creation, farm assignment, delivery tracking, and payment processing.

---

## ⚠️ IMPORTANT: API Implementation Status

> **Last Updated: January 2025**

### URL Structure

The procurement module uses clear URL naming:

| Audience | URL Prefix | Description |
|----------|------------|-------------|
| **Farmers** | `/api/procurement/` | Farmer's view of assignments, deliveries, earnings |
| **Admin/Staff** | `/api/admin/procurement/` | YEA Staff & Admin order management |

### Currently Available Endpoints ✅

#### Farmer Procurement Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/procurement/` | GET | Farmer procurement dashboard |
| `/api/procurement/overview/` | GET | Farmer overview stats only |
| `/api/procurement/assignments/` | GET | Farmer assignments list |
| `/api/procurement/earnings/` | GET | Farmer earnings breakdown |
| `/api/procurement/pending-actions/` | GET | Farmer pending actions |

#### Admin/Staff Procurement Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/admin/procurement/` | GET | Admin procurement dashboard |
| `/api/admin/procurement/overview/` | GET | Admin overview stats only |
| `/api/admin/procurement/orders/` | GET | List procurement orders |
| `/api/admin/procurement/orders/{order_id}/timeline/` | GET | Order timeline details |
| `/api/admin/procurement/orders/{order_id}/recommend-farms/` | GET | **Get farm recommendations prioritized by distress** |
| `/api/admin/procurement/invoices/` | GET | List procurement invoices |
| `/api/admin/procurement/deliveries/` | GET | List delivery confirmations |
| `/api/admin/procurement/distressed-farmers/` | GET | **List farmers in distress (priority purchasing)** |
| `/api/admin/procurement/farms/{farm_id}/distress/` | GET | **Get distress details for a specific farm** |

---

## 🆕 Farmer Distress Scoring System

The procurement system includes a **Farmer Distress Score** to help government officers identify and prioritize purchasing from farmers who are struggling the most.

### Distress Score Levels

| Score Range | Level | Priority | Description |
|-------------|-------|----------|-------------|
| 76-100 | **Critical** | Urgent | Farmer needs immediate intervention |
| 51-75 | **High** | High | Farmer is struggling significantly |
| 26-50 | **Moderate** | Normal | Some concerns, monitor closely |
| 0-25 | **Healthy** | Low | Farmer is doing well |

### Distress Indicators

The score is calculated from multiple factors:

| Factor | Weight | Description |
|--------|--------|-------------|
| Inventory Aging | 25% | Unsold inventory, aging eggs/birds |
| Sales Activity | 25% | Recent sales volume (low = distress) |
| Mortality Rate | 15% | Recent bird deaths |
| Marketplace Engagement | 15% | Platform usage (not using = may need help) |
| Capacity Utilization | 10% | Overstocking or underutilization |
| Payment History | 10% | Pending payments from government |

### Workflow for Officers

1. **View Distressed Farmers**: `GET /api/admin/procurement/distressed-farmers/`
2. **Create Order**: Target product type and region
3. **Get Recommendations**: `GET /api/admin/procurement/orders/{id}/recommend-farms/`
   - Returns farms sorted by distress score (highest first)
4. **Assign Farms**: Start with most distressed farmers
5. **Track Deliveries**: Monitor fulfillment

### Planned (Coming Soon) 🚧

CRUD operations for orders, assignments, and invoices are coming soon.

---

## Table of Contents

1. [Overview](#overview)
2. [User Roles & Permissions](#user-roles--permissions)
3. [Core Concepts](#core-concepts)
4. [Farmer Procurement API](#farmer-procurement-api)
5. [Admin Procurement API](#admin-procurement-api)
6. [Workflow Examples](#workflow-examples)
7. [TypeScript Integration](#typescript-integration)
8. [Error Handling](#error-handling)

---

## Overview

### Base URLs

| Environment | URL |
|-------------|-----|
| Production | `https://pmsapi.alphalogiquetechnologies.com` |
| Development | `http://localhost:8000` |

### API Prefixes

| Prefix | Purpose | Authentication | Status |
|--------|---------|----------------|--------|
| `/api/procurement/` | Farmer procurement view | JWT (FARMER) | ✅ **AVAILABLE** |
| `/api/admin/procurement/` | Admin order management | JWT (PROCUREMENT_OFFICER, NATIONAL_ADMIN, SUPER_ADMIN) | ✅ **AVAILABLE** |

---

## User Roles & Permissions

### National Admin

**Capabilities:**
- Create/manage Procurement Officer accounts
- View all procurement orders
- Override procurement decisions
- Access procurement analytics

**Account Creation:**
```http
POST /api/admin/staff/invite/
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "email": "officer@yeapoultry.gov.gh",
  "first_name": "Kwame",
  "last_name": "Asante",
  "phone": "+233244123456",
  "role": "PROCUREMENT_OFFICER",
  "region": "Greater Accra",
  "constituency": "Ablekuma South"
}
```

### Procurement Officer

**Capabilities:**
- Create government procurement orders
- Assign orders to farms (manual or auto)
- Verify deliveries and quality
- Approve invoices
- Process payments
- View assigned orders only

**Role Code:** `PROCUREMENT_OFFICER`

### Farmer

**Capabilities:**
- View assigned procurement orders
- Accept/reject assignments
- Update order preparation status
- Mark orders ready for delivery
- View earnings and invoices
- View delivery history

**Role Code:** `FARMER`

---

## Core Concepts

### Order Lifecycle

```
1. DRAFT → Officer creates order
2. PUBLISHED → Order visible, farms can be assigned
3. ASSIGNING → Farms being assigned (auto or manual)
4. ASSIGNED → All farms assigned, awaiting acceptance
5. IN_PROGRESS → Farms preparing orders
6. PARTIALLY_DELIVERED → Some farms delivered
7. FULLY_DELIVERED → All quantities received
8. COMPLETED → All payments processed
```

### Assignment Lifecycle

```
1. PENDING → Farm notified, awaiting response
2. ACCEPTED → Farm confirmed fulfillment
3. PREPARING → Farm preparing birds
4. READY → Ready for pickup/delivery
5. IN_TRANSIT → On the way
6. DELIVERED → Received at destination
7. VERIFIED → Quality inspection passed
8. PAID → Farm received payment
```

### Auto-Assignment Algorithm

The system recommends farms based on:

| Factor | Weight | Description |
|--------|--------|-------------|
| **Production Type Match** | Required | Must match order type (Broilers/Layers/Both) |
| **Business Registration** | +100 points | Registered businesses prioritized |
| **Paystack Subaccount** | +50 points | Easier payment processing |
| **Current Inventory** | Proportional | Farms with available stock |
| **Approval Status** | Required | Must be "Approved - Farm ID Assigned" |
| **Preferred Region** | Sorting | If specified by officer |

**Example:**
```json
{
  "order": {
    "quantity_needed": 10000,
    "production_type": "Broilers",
    "preferred_region": "Greater Accra"
  },
  "recommended_farms": [
    {
      "farm_name": "Addo Poultry Farm",
      "recommended_quantity": 3000,
      "priority_score": 150,
      "current_inventory": 3500,
      "region": "Greater Accra"
    },
    {
      "farm_name": "Mensah Broilers Ltd",
      "recommended_quantity": 2500,
      "priority_score": 150,
      "current_inventory": 3000,
      "region": "Greater Accra"
    }
  ]
}
```

---

## Available Dashboard Endpoints

> ✅ **These endpoints are currently implemented and working**

### Officer Dashboard (Procurement Officers)

#### Full Dashboard

**`GET /api/dashboards/officer/`**

Returns comprehensive dashboard with overview, orders, pending approvals, overdue items, and performance.

**Authentication:** JWT (Procurement Officer, National Admin)

**Example Response:**
```json
{
  "overview": {
    "orders": { "total": 45, "active": 12, "draft": 3, "completed": 28, "overdue": 2 },
    "pending_actions": { "deliveries": 5, "verifications": 3, "total": 8 },
    "budget": { "allocated": 500000.00, "spent": 385000.00, "remaining": 115000.00 }
  },
  "my_orders": [...],
  "pending_approvals": {...},
  "overdue_items": {...},
  "performance": {...}
}
```

#### Overview Only

**`GET /api/dashboards/officer/overview/`**

Returns just the overview statistics (lightweight, for quick loading).

#### Orders List

**`GET /api/dashboards/officer/orders/`**

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status (active, completed, etc.) |
| `limit` | integer | Max results (default: 50) |

#### Order Timeline

**`GET /api/dashboards/officer/orders/{order_id}/timeline/`**

Returns timeline events for a specific order.

---

### Farmer Dashboard

#### Full Dashboard

**`GET /api/dashboards/farmer/`**

Returns comprehensive farmer dashboard with overview, assignments, earnings, delivery history.

**Authentication:** JWT (Farmer role)

**Example Response:**
```json
{
  "overview": {
    "farm": { "farm_name": "Addo Poultry Farm", "farm_id": "YEA-GA-2025-0123" },
    "assignments": { "total": 12, "pending": 1, "accepted": 2, "completed": 8 },
    "earnings": { "total": 680000.00, "pending": 127500.00 }
  },
  "my_assignments": [...],
  "pending_actions": {...},
  "earnings_breakdown": {...},
  "delivery_history": [...]
}
```

#### Overview Only

**`GET /api/dashboards/farmer/overview/`**

#### Assignments List

**`GET /api/dashboards/farmer/assignments/`**

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by assignment status |
| `limit` | integer | Max results (default: 50) |

#### Earnings

**`GET /api/dashboards/farmer/earnings/`**

Returns earnings breakdown by status, monthly trend, and invoice list.

#### Pending Actions

**`GET /api/dashboards/farmer/pending-actions/`**

Returns list of items requiring farmer attention.

---

## Planned Officer Endpoints

> ⚠️ **NOT YET IMPLEMENTED** - The following endpoints are planned but not available

### Dashboard Overview

**Endpoint:** `GET /api/dashboards/officer/`

**Authentication:** JWT (Procurement Officer, National Admin)

**Response:**

```json
{
  "overview": {
    "orders": {
      "total": 45,
      "active": 12,
      "draft": 3,
      "completed": 28,
      "overdue": 2
    },
    "pending_actions": {
      "deliveries": 5,
      "verifications": 3,
      "total": 8
    },
    "budget": {
      "allocated": 500000.00,
      "spent": 385000.00,
      "remaining": 115000.00,
      "utilization": 77.0
    },
    "performance": {
      "total_assignments": 120,
      "accepted_rate": 92.5
    }
  },
  "my_orders": [
    {
      "order_number": "ORD-2026-00012",
      "title": "Broilers for National School Feeding Program",
      "status": "In Progress - Farms Preparing",
      "status_code": "in_progress",
      "production_type": "Broilers",
      "quantity_needed": 5000,
      "quantity_assigned": 5000,
      "quantity_delivered": 1500,
      "fulfillment_percentage": 30.0,
      "total_budget": 425000.00,
      "delivery_deadline": "2026-01-20",
      "days_until_deadline": 11,
      "is_overdue": false,
      "priority": "High Priority",
      "created_at": "2026-01-05T09:00:00Z",
      "farms_assigned": 3
    }
  ],
  "pending_approvals": {
    "pending_verifications": [
      {
        "delivery_number": "DEL-2026-00085",
        "order_number": "ORD-2026-00012",
        "farm_name": "Addo Poultry Farm",
        "quantity": 1500,
        "delivery_date": "2026-01-08",
        "quality_passed": true,
        "requires_attention": false
      }
    ],
    "ready_for_delivery": [
      {
        "assignment_number": "ORD-2026-00012-A02",
        "order_number": "ORD-2026-00012",
        "farm_name": "Mensah Broilers Ltd",
        "quantity": 2000,
        "ready_date": "2026-01-09"
      }
    ]
  },
  "overdue_items": {
    "orders": [
      {
        "order_number": "ORD-2026-00008",
        "title": "Layer Birds for Government Hatchery",
        "deadline": "2026-01-05",
        "days_overdue": 4,
        "fulfillment_percentage": 60.0
      }
    ],
    "invoices": []
  },
  "performance": {
    "period_days": 30,
    "total_orders": 8,
    "completed_orders": 6,
    "completion_rate": 75.0,
    "avg_fulfillment_days": 12.3,
    "on_time_delivery_rate": 83.33
  }
}
```

---

### Create Procurement Order

> ⚠️ **NOT YET IMPLEMENTED** - Use Django Admin at `/admin/procurement/procurementorder/` instead

**Endpoint:** `POST /api/admin/procurement/orders/`

**Authentication:** JWT (Procurement Officer, National Admin)

**Request Body:**

```json
{
  "title": "Broilers for National School Feeding Program",
  "description": "Supply of broiler chickens for Phase 2 school feeding program in Greater Accra region",
  "production_type": "Broilers",
  "quantity_needed": 5000,
  "unit": "birds",
  "min_weight_per_bird_kg": 1.8,
  "quality_requirements": "Average weight 1.8-2.2kg, healthy birds only, no visible defects",
  "price_per_unit": 85.00,
  "delivery_location": "Ministry of Education Warehouse, Accra",
  "delivery_location_gps": "GA-123-4567",
  "delivery_deadline": "2026-01-20",
  "delivery_instructions": "Delivery between 6am-12pm, contact warehouse manager",
  "auto_assign": true,
  "preferred_region": "Greater Accra",
  "max_farms": 5,
  "priority": "high"
}
```

**Response (201 Created):**

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "order_number": "ORD-2026-00013",
  "title": "Broilers for National School Feeding Program",
  "status": "draft",
  "status_display": "Draft",
  "production_type": "Broilers",
  "quantity_needed": 5000,
  "unit": "birds",
  "quantity_assigned": 0,
  "quantity_delivered": 0,
  "fulfillment_percentage": 0.0,
  "total_budget": 425000.00,
  "delivery_deadline": "2026-01-20",
  "created_at": "2026-01-09T10:00:00Z",
  "created_by": {
    "id": "uuid",
    "full_name": "Kwame Asante",
    "email": "officer@yeapoultry.gov.gh"
  }
}
```

---

### Publish Order

**Endpoint:** `POST /api/admin/procurement/orders/{order_id}/publish/`

**Authentication:** JWT (Procurement Officer, National Admin)

**Response:**

```json
{
  "message": "Order ORD-2026-00013 published successfully",
  "order": {
    "order_number": "ORD-2026-00013",
    "status": "published",
    "status_display": "Published - Accepting Bids",
    "published_at": "2026-01-09T10:05:00Z"
  }
}
```

---

### Get Farm Recommendations

**Endpoint:** `GET /api/admin/procurement/orders/{order_id}/recommend-farms/`

**Authentication:** JWT (Procurement Officer, National Admin)

**Response:**

```json
{
  "order": {
    "order_number": "ORD-2026-00013",
    "quantity_needed": 5000,
    "production_type": "Broilers",
    "preferred_region": "Greater Accra"
  },
  "recommended_farms": [
    {
      "farm_id": "uuid",
      "farm_name": "Addo Poultry Farm",
      "farm_id_number": "YEA-GA-2025-0123",
      "owner": "Kofi Addo",
      "region": "Greater Accra",
      "constituency": "Ablekuma South",
      "production_type": "Both",
      "current_inventory": 3500,
      "recommended_quantity": 1800,
      "priority_score": 150,
      "business_registered": true,
      "paystack_subaccount": true,
      "quality_history": {
        "avg_quality_score": 95.5,
        "on_time_delivery_rate": 100.0
      }
    },
    {
      "farm_id": "uuid",
      "farm_name": "Mensah Broilers Ltd",
      "farm_id_number": "YEA-GA-2025-0089",
      "owner": "Ama Mensah",
      "region": "Greater Accra",
      "constituency": "Tema East",
      "production_type": "Broilers",
      "current_inventory": 3000,
      "recommended_quantity": 1500,
      "priority_score": 150,
      "business_registered": true,
      "paystack_subaccount": true,
      "quality_history": {
        "avg_quality_score": 92.0,
        "on_time_delivery_rate": 95.5
      }
    }
  ],
  "total_available": 18500,
  "farms_count": 5
}
```

---

### Auto-Assign Order

**Endpoint:** `POST /api/admin/procurement/orders/{order_id}/auto-assign/`

**Authentication:** JWT (Procurement Officer, National Admin)

**Response:**

```json
{
  "message": "Order ORD-2026-00013 auto-assigned to 3 farms",
  "order": {
    "order_number": "ORD-2026-00013",
    "status": "assigned",
    "status_display": "Assigned to Farms",
    "quantity_assigned": 5000,
    "assigned_at": "2026-01-09T10:10:00Z"
  },
  "assignments": [
    {
      "assignment_number": "ORD-2026-00013-A01",
      "farm_name": "Addo Poultry Farm",
      "quantity": 1800,
      "value": 153000.00,
      "status": "pending"
    },
    {
      "assignment_number": "ORD-2026-00013-A02",
      "farm_name": "Mensah Broilers Ltd",
      "quantity": 1500,
      "value": 127500.00,
      "status": "pending"
    },
    {
      "assignment_number": "ORD-2026-00013-A03",
      "farm_name": "Osei Farms",
      "quantity": 1700,
      "value": 144500.00,
      "status": "pending"
    }
  ],
  "notifications_sent": 3
}
```

---

### Manual Farm Assignment

**Endpoint:** `POST /api/admin/procurement/orders/{order_id}/assign-farm/`

**Authentication:** JWT (Procurement Officer, National Admin)

**Request Body:**

```json
{
  "farm_id": "uuid",
  "quantity": 2000,
  "price_per_unit": 85.00
}
```

**Response (201 Created):**

```json
{
  "assignment_number": "ORD-2026-00013-A04",
  "farm": {
    "id": "uuid",
    "farm_name": "Kwabena Poultry",
    "farm_id_number": "YEA-AS-2025-0234"
  },
  "quantity_assigned": 2000,
  "price_per_unit": 85.00,
  "total_value": 170000.00,
  "status": "pending",
  "assigned_at": "2026-01-09T11:00:00Z"
}
```

---

### Verify Delivery

**Endpoint:** `POST /api/admin/procurement/deliveries/{delivery_id}/verify/`

**Authentication:** JWT (Procurement Officer, National Admin)

**Request Body:**

```json
{
  "quality_passed": true,
  "average_weight_per_bird": 1.95,
  "mortality_count": 5,
  "quality_issues": "",
  "quality_photos": [
    "https://storage.example.com/delivery-photos/del-001.jpg",
    "https://storage.example.com/delivery-photos/del-002.jpg"
  ]
}
```

**Response:**

```json
{
  "message": "Delivery DEL-2026-00085 verified successfully",
  "delivery": {
    "delivery_number": "DEL-2026-00085",
    "verified_at": "2026-01-09T14:30:00Z",
    "quality_passed": true,
    "average_weight_per_bird": 1.95,
    "verified_by": "Kwame Asante"
  },
  "invoice_generated": true,
  "invoice_number": "INV-2026-00042"
}
```

---

### Approve Invoice

**Endpoint:** `POST /api/admin/procurement/invoices/{invoice_id}/approve/`

**Authentication:** JWT (Procurement Officer, National Admin)

**Response:**

```json
{
  "message": "Invoice INV-2026-00042 approved for payment",
  "invoice": {
    "invoice_number": "INV-2026-00042",
    "farm_name": "Addo Poultry Farm",
    "total_amount": 152575.00,
    "payment_status": "approved",
    "approved_by": "Kwame Asante",
    "approved_at": "2026-01-09T15:00:00Z",
    "due_date": "2026-02-08"
  },
  "notification_sent": true
}
```

---

### Process Payment

**Endpoint:** `POST /api/admin/procurement/invoices/{invoice_id}/process-payment/`

**Authentication:** JWT (Procurement Officer, National Admin)

**Request Body:**

```json
{
  "payment_method": "bank_transfer",
  "payment_reference": "TXN-20260109-GHS152575",
  "payment_date": "2026-01-09",
  "paid_to_account": "1234567890 (GCB Bank)"
}
```

**Response:**

```json
{
  "message": "Payment processed for invoice INV-2026-00042",
  "invoice": {
    "invoice_number": "INV-2026-00042",
    "payment_status": "paid",
    "payment_method": "Bank Transfer",
    "payment_reference": "TXN-20260109-GHS152575",
    "payment_date": "2026-01-09",
    "total_amount": 152575.00
  },
  "assignment_status": "paid",
  "order_status": "partially_delivered",
  "notification_sent": true
}
```

---

### Get Order Timeline

**Endpoint:** `GET /api/dashboards/officer/orders/{order_id}/timeline/`

**Authentication:** JWT (Procurement Officer, National Admin)

**Response:**

```json
{
  "order": {
    "order_number": "ORD-2026-00013",
    "title": "Broilers for National School Feeding Program",
    "status": "In Progress - Farms Preparing"
  },
  "timeline": [
    {
      "event": "Order Created",
      "timestamp": "2026-01-09T10:00:00Z",
      "user": "Kwame Asante",
      "icon": "add_circle",
      "color": "primary"
    },
    {
      "event": "Order Published",
      "timestamp": "2026-01-09T10:05:00Z",
      "icon": "publish",
      "color": "info"
    },
    {
      "event": "Assigned to 3 Farms",
      "timestamp": "2026-01-09T10:10:00Z",
      "icon": "assignment_ind",
      "color": "success"
    },
    {
      "event": "Delivery from Addo Poultry Farm",
      "timestamp": "2026-01-12T08:30:00Z",
      "details": "1800 units delivered",
      "icon": "local_shipping",
      "color": "success"
    }
  ]
}
```

---

## Farmer Endpoints

### Farmer Dashboard

**Endpoint:** `GET /api/dashboards/farmer/`

**Authentication:** JWT (Farmer)

**Response:**

```json
{
  "overview": {
    "farm": {
      "farm_name": "Addo Poultry Farm",
      "farm_id": "YEA-GA-2025-0123",
      "primary_production_type": "Both",
      "total_bird_capacity": 5000,
      "current_bird_count": 3500,
      "capacity_utilization": 70.0,
      "active_flocks": 3
    },
    "production": {
      "total_eggs_last_30_days": 84000,
      "avg_daily_eggs": 2800,
      "total_mortality_last_30_days": 45,
      "mortality_rate_percent": 1.29,
      "total_feed_consumed_kg": 4200.0,
      "avg_daily_feed_kg": 140.0
    },
    "assignments": {
      "total": 12,
      "pending": 1,
      "accepted": 2,
      "completed": 8,
      "acceptance_rate": 91.67
    },
    "earnings": {
      "total": 680000.00,
      "pending": 127500.00,
      "last_payment_amount": 153000.00,
      "last_payment_date": "2025-12-28"
    },
    "deliveries": {
      "total": 10,
      "pending": 1
    },
    "performance": {
      "avg_quality": 1.92,
      "quality_pass_rate": 100.0
    }
  },
  "my_assignments": [
    {
      "assignment_number": "ORD-2026-00013-A01",
      "order_number": "ORD-2026-00013",
      "order_title": "Broilers for National School Feeding Program",
      "status": "Pending Farm Response",
      "status_code": "pending",
      "quantity_assigned": 1800,
      "quantity_delivered": 0,
      "fulfillment_percentage": 0.0,
      "price_per_unit": 85.00,
      "total_value": 153000.00,
      "assigned_at": "2026-01-09T10:10:00Z",
      "expected_ready_date": null,
      "actual_ready_date": null,
      "delivery_deadline": "2026-01-20",
      "requires_action": true
    }
  ],
  "pending_actions": {
    "pending_responses": [
      {
        "assignment_number": "ORD-2026-00013-A01",
        "order_number": "ORD-2026-00013",
        "order_title": "Broilers for National School Feeding Program",
        "quantity": 1800,
        "value": 153000.00,
        "delivery_deadline": "2026-01-20",
        "days_until_deadline": 11
      }
    ],
    "preparing_orders": [],
    "ready_for_delivery": []
  },
  "earnings_breakdown": {
    "by_status": {
      "paid": 680000.00,
      "approved": 0.00,
      "pending": 127500.00
    },
    "deductions": {
      "quality": 0.00,
      "mortality": 425.00,
      "other": 0.00,
      "total": 425.00
    },
    "monthly_trend": [
      {
        "month": "Aug 2025",
        "earnings": 85000.00,
        "orders": 1
      },
      {
        "month": "Sep 2025",
        "earnings": 170000.00,
        "orders": 2
      },
      {
        "month": "Oct 2025",
        "earnings": 127500.00,
        "orders": 2
      },
      {
        "month": "Nov 2025",
        "earnings": 144500.00,
        "orders": 2
      },
      {
        "month": "Dec 2025",
        "earnings": 153000.00,
        "orders": 1
      }
    ]
  },
  "delivery_history": [
    {
      "delivery_number": "DEL-2025-00142",
      "order_number": "ORD-2025-00178",
      "quantity": 1800,
      "delivery_date": "2025-12-20",
      "quality_passed": true,
      "average_weight": 1.92,
      "mortality_count": 5,
      "verified": true,
      "verified_at": "2025-12-20T14:30:00Z",
      "received_by": "Kwame Asante"
    }
  ],
  "performance_summary": {
    "total_assignments": 12,
    "completion_rate": 91.67,
    "on_time_rate": 100.0,
    "rejection_rate": 8.33,
    "avg_quality_score": 1.92
  }
}
```

---

### Accept Assignment

**Endpoint:** `POST /api/farmer/assignments/{assignment_id}/accept/`

**Authentication:** JWT (Farmer)

**Request Body:**

```json
{
  "expected_ready_date": "2026-01-18"
}
```

**Response:**

```json
{
  "message": "Assignment ORD-2026-00013-A01 accepted successfully",
  "assignment": {
    "assignment_number": "ORD-2026-00013-A01",
    "status": "accepted",
    "status_display": "Accepted by Farm",
    "accepted_at": "2026-01-09T16:00:00Z",
    "expected_ready_date": "2026-01-18",
    "quantity": 1800,
    "total_value": 153000.00
  },
  "notification_sent": true
}
```

---

### Reject Assignment

**Endpoint:** `POST /api/farmer/assignments/{assignment_id}/reject/`

**Authentication:** JWT (Farmer)

**Request Body:**

```json
{
  "reason": "Insufficient inventory at this time. Recent disease outbreak reduced flock size."
}
```

**Response:**

```json
{
  "message": "Assignment ORD-2026-00013-A01 rejected",
  "assignment": {
    "assignment_number": "ORD-2026-00013-A01",
    "status": "rejected",
    "status_display": "Rejected by Farm",
    "rejected_at": "2026-01-09T16:00:00Z",
    "rejection_reason": "Insufficient inventory at this time. Recent disease outbreak reduced flock size."
  },
  "order_updated": true,
  "notification_sent": true
}
```

---

### Mark Ready for Delivery

**Endpoint:** `POST /api/farmer/assignments/{assignment_id}/mark-ready/`

**Authentication:** JWT (Farmer)

**Request Body:**

```json
{
  "actual_ready_date": "2026-01-17",
  "notes": "All 1800 birds ready. Average weight 1.9kg. Contact for pickup arrangement."
}
```

**Response:**

```json
{
  "message": "Assignment ORD-2026-00013-A01 marked as ready for delivery",
  "assignment": {
    "assignment_number": "ORD-2026-00013-A01",
    "status": "ready",
    "status_display": "Ready for Delivery",
    "actual_ready_date": "2026-01-17",
    "quantity": 1800
  },
  "notification_sent": true
}
```

---

### View My Assignments

**Endpoint:** `GET /api/dashboards/farmer/assignments/`

**Authentication:** JWT (Farmer)

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status (pending, accepted, preparing, etc.) |
| `limit` | integer | Max results (default: 50) |

**Response:**

```json
{
  "assignments": [
    {
      "assignment_number": "ORD-2026-00013-A01",
      "order_number": "ORD-2026-00013",
      "order_title": "Broilers for National School Feeding Program",
      "status": "Accepted by Farm",
      "status_code": "accepted",
      "quantity_assigned": 1800,
      "quantity_delivered": 0,
      "fulfillment_percentage": 0.0,
      "price_per_unit": 85.00,
      "total_value": 153000.00,
      "assigned_at": "2026-01-09T10:10:00Z",
      "expected_ready_date": "2026-01-18",
      "delivery_deadline": "2026-01-20",
      "requires_action": false
    }
  ],
  "count": 1
}
```

---

### View Earnings

**Endpoint:** `GET /api/dashboards/farmer/earnings/`

**Authentication:** JWT (Farmer)

**Response:**

```json
{
  "total_earnings": 680000.00,
  "pending_payments": 127500.00,
  "by_status": {
    "paid": 680000.00,
    "approved": 0.00,
    "pending": 127500.00
  },
  "deductions": {
    "quality": 0.00,
    "mortality": 425.00,
    "other": 0.00,
    "total": 425.00
  },
  "monthly_trend": [
    {
      "month": "Dec 2025",
      "earnings": 153000.00,
      "orders": 1
    },
    {
      "month": "Jan 2026",
      "earnings": 127500.00,
      "orders": 1
    }
  ],
  "invoices": [
    {
      "invoice_number": "INV-2025-00234",
      "order_number": "ORD-2025-00178",
      "quantity": 1800,
      "unit_price": 85.00,
      "subtotal": 153000.00,
      "quality_deduction": 0.00,
      "mortality_deduction": 425.00,
      "total_amount": 152575.00,
      "payment_status": "paid",
      "payment_method": "Bank Transfer",
      "payment_date": "2025-12-28",
      "invoice_date": "2025-12-22",
      "due_date": "2026-01-21"
    }
  ]
}
```

---

## Admin Management

### Create Procurement Officer

**Endpoint:** `POST /api/admin/staff/invite/`

**Authentication:** JWT (National Admin, Super Admin)

**Request Body:**

```json
{
  "email": "officer@yeapoultry.gov.gh",
  "first_name": "Kwame",
  "last_name": "Asante",
  "phone": "+233244123456",
  "role": "PROCUREMENT_OFFICER",
  "region": "Greater Accra",
  "constituency": "Ablekuma South",
  "send_invitation": true
}
```

**Response (201 Created):**

```json
{
  "message": "Staff invitation sent successfully",
  "invitation": {
    "id": "uuid",
    "email": "officer@yeapoultry.gov.gh",
    "first_name": "Kwame",
    "last_name": "Asante",
    "role": "PROCUREMENT_OFFICER",
    "role_display": "Procurement Officer",
    "status": "pending",
    "invitation_code": "ABC123XYZ789",
    "expires_at": "2026-01-16T10:00:00Z"
  }
}
```

---

### List All Orders (Admin)

**Endpoint:** `GET /api/admin/procurement/orders/`

**Authentication:** JWT (National Admin, Super Admin)

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status |
| `priority` | string | Filter by priority |
| `production_type` | string | Filter by production type |
| `officer` | uuid | Filter by assigned officer |
| `search` | string | Search in title, order number |
| `page` | integer | Page number |
| `page_size` | integer | Results per page (default: 20) |

**Response:**

```json
{
  "count": 45,
  "next": "http://localhost:8000/api/admin/procurement/orders/?page=2",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "order_number": "ORD-2026-00013",
      "title": "Broilers for National School Feeding Program",
      "status": "assigned",
      "status_display": "Assigned to Farms",
      "priority": "high",
      "priority_display": "High Priority",
      "production_type": "Broilers",
      "quantity_needed": 5000,
      "quantity_assigned": 5000,
      "quantity_delivered": 0,
      "total_budget": 425000.00,
      "delivery_deadline": "2026-01-20",
      "created_by": "Kwame Asante",
      "assigned_officer": "Kwame Asante",
      "farms_assigned": 3,
      "created_at": "2026-01-09T10:00:00Z"
    }
  ]
}
```

---

### Order Analytics

**Endpoint:** `GET /api/admin/procurement/analytics/`

**Authentication:** JWT (National Admin, Super Admin)

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 30 | Analysis period |

**Response:**

```json
{
  "period": {
    "start_date": "2025-12-10",
    "end_date": "2026-01-09",
    "days": 30
  },
  "orders": {
    "total": 12,
    "by_status": {
      "draft": 2,
      "published": 1,
      "assigned": 3,
      "in_progress": 4,
      "completed": 2
    },
    "by_priority": {
      "low": 2,
      "normal": 6,
      "high": 3,
      "urgent": 1
    },
    "by_production_type": {
      "Broilers": 8,
      "Layers": 3,
      "Both": 1
    }
  },
  "quantities": {
    "total_needed": 45000,
    "total_assigned": 42000,
    "total_delivered": 28000,
    "fulfillment_rate": 66.67
  },
  "budget": {
    "total_allocated": 3825000.00,
    "total_spent": 2380000.00,
    "utilization": 62.22
  },
  "farms": {
    "total_participating": 28,
    "total_assignments": 67,
    "avg_assignments_per_farm": 2.39,
    "acceptance_rate": 89.55
  },
  "performance": {
    "avg_fulfillment_days": 14.5,
    "on_time_delivery_rate": 85.71,
    "quality_pass_rate": 96.43
  }
}
```

---

## Workflow Examples

### Complete Order Workflow (Officer Perspective)

```typescript
// 1. Create order
const createResponse = await fetch('/api/admin/procurement/orders/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${jwtToken}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    title: "Broilers for School Feeding",
    production_type: "Broilers",
    quantity_needed: 5000,
    price_per_unit: 85.00,
    delivery_deadline: "2026-01-20",
    auto_assign: true,
    preferred_region: "Greater Accra",
  }),
});
const order = await createResponse.json();

// 2. Publish order
await fetch(`/api/admin/procurement/orders/${order.id}/publish/`, {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${jwtToken}` },
});

// 3. Auto-assign farms
const assignResponse = await fetch(
  `/api/admin/procurement/orders/${order.id}/auto-assign/`,
  {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${jwtToken}` },
  }
);
const { assignments } = await assignResponse.json();

// 4. Monitor progress via dashboard
const dashboard = await fetch('/api/dashboards/officer/', {
  headers: { 'Authorization': `Bearer ${jwtToken}` },
}).then(r => r.json());

// 5. Verify delivery
const verifyResponse = await fetch(
  `/api/admin/procurement/deliveries/${deliveryId}/verify/`,
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${jwtToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      quality_passed: true,
      average_weight_per_bird: 1.95,
      mortality_count: 5,
    }),
  }
);

// 6. Approve invoice
await fetch(`/api/admin/procurement/invoices/${invoiceId}/approve/`, {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${jwtToken}` },
});

// 7. Process payment
await fetch(`/api/admin/procurement/invoices/${invoiceId}/process-payment/`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${jwtToken}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    payment_method: "bank_transfer",
    payment_reference: "TXN-12345",
    payment_date: "2026-01-20",
  }),
});
```

---

### Farm Assignment Workflow (Farmer Perspective)

```typescript
// 1. Check dashboard for new assignments
const dashboard = await fetch('/api/dashboards/farmer/', {
  headers: { 'Authorization': `Bearer ${farmerJwtToken}` },
}).then(r => r.json());

const pendingAssignments = dashboard.pending_actions.pending_responses;

// 2. Review assignment details
const assignment = pendingAssignments[0];
console.log(`New order: ${assignment.order_title}`);
console.log(`Quantity: ${assignment.quantity} birds`);
console.log(`Value: GHS ${assignment.value}`);
console.log(`Deadline: ${assignment.delivery_deadline}`);

// 3. Accept assignment
const acceptResponse = await fetch(
  `/api/farmer/assignments/${assignment.assignment_number}/accept/`,
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${farmerJwtToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      expected_ready_date: "2026-01-18",
    }),
  }
);

// 4. Mark ready when prepared
await fetch(
  `/api/farmer/assignments/${assignment.assignment_number}/mark-ready/`,
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${farmerJwtToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      actual_ready_date: "2026-01-17",
      notes: "All birds ready for pickup",
    }),
  }
);

// 5. Check earnings after payment
const earnings = await fetch('/api/dashboards/farmer/earnings/', {
  headers: { 'Authorization': `Bearer ${farmerJwtToken}` },
}).then(r => r.json());

console.log(`Total earnings: GHS ${earnings.total_earnings}`);
console.log(`Pending: GHS ${earnings.pending_payments}`);
```

---

## Frontend Integration Guide

### Project Structure

```
src/
├── services/
│   ├── procurementOfficer.ts       # Officer API calls
│   ├── procurementFarmer.ts        # Farmer API calls
│   └── procurementAdmin.ts         # Admin API calls
├── types/
│   └── procurement.ts              # TypeScript interfaces
├── components/
│   ├── officer/
│   │   ├── OfficerDashboard.tsx
│   │   ├── CreateOrderForm.tsx
│   │   ├── OrderList.tsx
│   │   ├── FarmRecommendations.tsx
│   │   ├── DeliveryVerification.tsx
│   │   ├── InvoiceApproval.tsx
│   │   └── OrderTimeline.tsx
│   ├── farmer/
│   │   ├── FarmerDashboard.tsx
│   │   ├── AssignmentList.tsx
│   │   ├── AssignmentActions.tsx
│   │   ├── EarningsView.tsx
│   │   └── DeliveryHistory.tsx
│   └── admin/
│       ├── ProcurementAnalytics.tsx
│       ├── CreateOfficerForm.tsx
│       └── OrderManagement.tsx
└── hooks/
    ├── useProcurementOrders.ts
    ├── useFarmAssignments.ts
    └── useEarnings.ts
```

---

## TypeScript Types

```typescript
// types/procurement.ts

export interface ProcurementOrder {
  id: string;
  order_number: string;
  title: string;
  description: string;
  status: OrderStatus;
  status_display: string;
  priority: OrderPriority;
  priority_display: string;
  production_type: 'Broilers' | 'Layers' | 'Both';
  quantity_needed: number;
  quantity_assigned: number;
  quantity_delivered: number;
  unit: 'birds' | 'crates' | 'kg';
  fulfillment_percentage: number;
  total_budget: number;
  total_cost_actual: number;
  delivery_location: string;
  delivery_deadline: string;
  days_until_deadline: number;
  is_overdue: boolean;
  created_by: UserSummary;
  assigned_officer?: UserSummary;
  farms_assigned: number;
  created_at: string;
  updated_at: string;
}

export type OrderStatus = 
  | 'draft'
  | 'published'
  | 'assigning'
  | 'assigned'
  | 'in_progress'
  | 'partially_delivered'
  | 'fully_delivered'
  | 'completed'
  | 'cancelled';

export type OrderPriority = 'low' | 'normal' | 'high' | 'urgent';

export interface OrderAssignment {
  id: string;
  assignment_number: string;
  order_number: string;
  order_title: string;
  farm: FarmSummary;
  status: AssignmentStatus;
  status_display: string;
  quantity_assigned: number;
  quantity_delivered: number;
  fulfillment_percentage: number;
  price_per_unit: number;
  total_value: number;
  assigned_at: string;
  accepted_at?: string;
  rejected_at?: string;
  rejection_reason?: string;
  expected_ready_date?: string;
  actual_ready_date?: string;
  delivery_date?: string;
}

export type AssignmentStatus =
  | 'pending'
  | 'accepted'
  | 'rejected'
  | 'preparing'
  | 'ready'
  | 'in_transit'
  | 'delivered'
  | 'verified'
  | 'paid'
  | 'cancelled';

export interface DeliveryConfirmation {
  id: string;
  delivery_number: string;
  assignment: string;
  quantity_delivered: number;
  delivery_date: string;
  delivery_time: string;
  received_by?: UserSummary;
  verified_by?: UserSummary;
  verified_at?: string;
  quality_passed: boolean;
  average_weight_per_bird?: number;
  mortality_count: number;
  quality_issues?: string;
  quality_photos: string[];
}

export interface ProcurementInvoice {
  id: string;
  invoice_number: string;
  farm: FarmSummary;
  order_number: string;
  quantity_invoiced: number;
  unit_price: number;
  subtotal: number;
  quality_deduction: number;
  mortality_deduction: number;
  other_deductions: number;
  deduction_notes?: string;
  total_amount: number;
  payment_status: PaymentStatus;
  payment_method?: PaymentMethod;
  payment_reference?: string;
  payment_date?: string;
  invoice_date: string;
  due_date: string;
  is_overdue: boolean;
  approved_by?: UserSummary;
  approved_at?: string;
}

export type PaymentStatus = 
  | 'pending'
  | 'approved'
  | 'processing'
  | 'paid'
  | 'failed'
  | 'disputed';

export type PaymentMethod =
  | 'bank_transfer'
  | 'mobile_money'
  | 'paystack'
  | 'cheque';

export interface FarmRecommendation {
  farm_id: string;
  farm_name: string;
  farm_id_number: string;
  owner: string;
  region: string;
  constituency: string;
  production_type: string;
  current_inventory: number;
  recommended_quantity: number;
  priority_score: number;
  business_registered: boolean;
  paystack_subaccount: boolean;
  quality_history: {
    avg_quality_score: number;
    on_time_delivery_rate: number;
  };
}

export interface OfficerDashboard {
  overview: {
    orders: {
      total: number;
      active: number;
      draft: number;
      completed: number;
      overdue: number;
    };
    pending_actions: {
      deliveries: number;
      verifications: number;
      total: number;
    };
    budget: {
      allocated: number;
      spent: number;
      remaining: number;
      utilization: number;
    };
    performance: {
      total_assignments: number;
      accepted_rate: number;
    };
  };
  my_orders: ProcurementOrder[];
  pending_approvals: {
    pending_verifications: DeliveryConfirmation[];
    ready_for_delivery: OrderAssignment[];
  };
  overdue_items: {
    orders: ProcurementOrder[];
    invoices: ProcurementInvoice[];
  };
  performance: {
    period_days: number;
    total_orders: number;
    completed_orders: number;
    completion_rate: number;
    avg_fulfillment_days: number;
    on_time_delivery_rate: number;
  };
}

export interface FarmerDashboard {
  overview: {
    farm: FarmInfo;
    production: ProductionStats;
    assignments: AssignmentStats;
    earnings: EarningsStats;
    deliveries: DeliveryStats;
    performance: PerformanceStats;
  };
  my_assignments: OrderAssignment[];
  pending_actions: {
    pending_responses: PendingAssignment[];
    preparing_orders: PreparingOrder[];
    ready_for_delivery: ReadyOrder[];
  };
  earnings_breakdown: EarningsBreakdown;
  delivery_history: DeliveryConfirmation[];
  performance_summary: PerformanceSummary;
}

interface UserSummary {
  id: string;
  full_name: string;
  email: string;
}

interface FarmSummary {
  id: string;
  farm_name: string;
  farm_id: string;
}
```

---

## Error Handling

### Error Response Format

```json
{
  "error": "Human-readable error message",
  "code": "ERROR_CODE",
  "detail": "Additional details (optional)"
}
```

### Common Error Codes

| Status Code | Code | Description |
|-------------|------|-------------|
| 400 | `invalid_request` | Invalid request data |
| 401 | `authentication_required` | JWT token missing/invalid |
| 403 | `permission_denied` | User lacks required permissions |
| 404 | `not_found` | Resource not found |
| 409 | `already_exists` | Assignment already exists |
| 422 | `validation_error` | Field validation failed |

### Error Handler Example

```typescript
// utils/procurementErrorHandler.ts
import { AxiosError } from 'axios';

interface APIError {
  error: string;
  code?: string;
  detail?: string;
}

export function handleProcurementError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<APIError>;
    const status = axiosError.response?.status;
    const data = axiosError.response?.data;
    
    switch (status) {
      case 400:
        return data?.error || 'Invalid request data';
      case 401:
        return 'Please log in to access procurement features';
      case 403:
        return data?.error || 'You do not have permission for this action';
      case 404:
        return data?.error || 'Order or assignment not found';
      case 409:
        return data?.error || 'This farm is already assigned to this order';
      default:
        return data?.error || 'An unexpected error occurred';
    }
  }
  
  return 'Network error. Please check your connection.';
}
```

---

## SMS Notifications

The system automatically sends SMS notifications at key events:

| Event | Recipient | Message |
|-------|-----------|---------|
| New assignment created | Farmer | "New order assigned: ORD-XXXX - Qty: X birds - Deadline: XX/XX/XXXX" |
| Assignment accepted | Procurement Officer | "Farm [Name] accepted order ORD-XXXX for X birds" |
| Assignment rejected | Procurement Officer | "Farm [Name] rejected order ORD-XXXX - Reason: [text]" |
| Ready for delivery | Procurement Officer | "Farm [Name] ready for delivery - ORD-XXXX" |
| Invoice generated | Farmer | "Invoice INV-XXXX generated - GHS X.XX - Due: XX/XX/XXXX" |
| Payment processed | Farmer | "Payment of GHS X.XX processed for INV-XXXX" |

---

## Contact & Support

| Role | Support Channel | Response Time |
|------|-----------------|---------------|
| Procurement Officer | procurement@yeapoultry.gov.gh | 4 hours |
| Farmer | farmer-support@yeapoultry.gov.gh | 24 hours |
| Admin | admin@yeapoultry.gov.gh | Immediate |

---

## Transaction Safety & Concurrency Protection

> **Added in January 2026**
> 
> The Government Procurement System includes robust transaction safety mechanisms to prevent financial discrepancies, duplicate payments, and race conditions during high-volume operations.

### State Machine Validation

All status transitions are validated server-side to prevent invalid state changes:

#### Order Status State Machine

```
ORDER STATES:
┌───────┐   publish   ┌───────────┐   assign   ┌──────────┐   accept   ┌─────────────┐
│ draft ├────────────►│ published ├───────────►│ assigned ├──────────►│ in_progress │
└───────┘             └─────┬─────┘            └──────────┘           └──────┬──────┘
                            │                                                 │
                            │  cancel                                        │ partial
                            ▼                                                ▼
                      ┌───────────┐                              ┌─────────────────────┐
                      │ cancelled │                              │ partially_delivered │
                      └───────────┘                              └──────────┬──────────┘
                                                                            │ all delivered
                                                                            ▼
                                                                   ┌─────────────────┐
                                                                   │ fully_delivered │
                                                                   └────────┬────────┘
                                                                            │ all paid
                                                                            ▼
                                                                     ┌───────────┐
                                                                     │ completed │
                                                                     └───────────┘
```

**Valid Order Transitions:**
| Current Status | Allowed Next States |
|----------------|---------------------|
| `draft` | `published`, `cancelled` |
| `published` | `assigning`, `assigned`, `cancelled` |
| `assigning` | `assigned`, `cancelled` |
| `assigned` | `in_progress`, `cancelled` |
| `in_progress` | `partially_delivered`, `fully_delivered` |
| `partially_delivered` | `fully_delivered` |
| `fully_delivered` | `completed` |
| `completed` | *(terminal)* |
| `cancelled` | *(terminal)* |

#### Assignment Status State Machine

```
ASSIGNMENT STATES:
┌─────────┐   accept   ┌──────────┐   prepare   ┌───────────┐   ready   ┌───────┐
│ pending ├───────────►│ accepted ├────────────►│ preparing ├─────────►│ ready │
└────┬────┘            └──────────┘             └───────────┘          └───┬───┘
     │                                                                     │
     │  reject                                                            │ ship
     ▼                                                                    ▼
┌──────────┐                                                       ┌────────────┐
│ rejected │                                                       │ in_transit │
└──────────┘                                                       └─────┬──────┘
                                                                         │ deliver
                                                                         ▼
                                                                   ┌───────────┐
                                                                   │ delivered │
                                                                   └─────┬─────┘
                                                                         │ verify
                                                                         ▼
                                                                    ┌──────────┐
                                                                    │ verified │
                                                                    └────┬─────┘
                                                                         │ pay
                                                                         ▼
                                                                      ┌──────┐
                                                                      │ paid │
                                                                      └──────┘
```

#### Invoice Status State Machine

```
INVOICE STATES:
┌─────────┐   submit   ┌───────────┐   approve   ┌──────────┐   pay   ┌──────┐
│ pending ├───────────►│ submitted ├────────────►│ approved ├────────►│ paid │
└────┬────┘            └─────┬─────┘             └──────────┘         └──────┘
     │                       │
     │  reject               │  reject
     ▼                       ▼
┌──────────┐            ┌──────────┐
│ rejected │            │ rejected │
└──────────┘            └──────────┘
```

**Frontend Handling:**
```typescript
// Handle state transition errors
try {
  await procurementApi.publishOrder(orderId);
} catch (error) {
  if (error.code === 'INVALID_STATE_TRANSITION') {
    // e.g., "Cannot publish order - current status is 'completed'"
    showToast('This order cannot be published in its current state', 'warning');
    refreshOrderDetails(); // Get fresh state from server
  }
}
```

### Idempotency Protection

Critical financial operations are protected against duplicate execution:

#### Payment Processing

```typescript
// First request
POST /api/admin/procurement/invoices/{id}/process-payment/
→ 200 OK { "payment_id": "uuid", "amount": "152575.00" }

// Duplicate request (same invoice)
POST /api/admin/procurement/invoices/{id}/process-payment/
→ 200 OK { "is_duplicate": true, "existing_payment_id": "uuid", "message": "Payment already processed" }
```

The backend uses an **idempotency key** system:
- Payments are tracked with unique keys per invoice
- Duplicate payment attempts return the existing payment instead of creating a new one
- Cache-based checking provides fast duplicate detection

#### Delivery Confirmation

```json
// Duplicate delivery confirmation
{
  "message": "Delivery already confirmed",
  "is_duplicate": true,
  "existing_delivery": {
    "delivery_id": "uuid",
    "confirmed_at": "2026-01-15T10:30:00Z",
    "quantity": 1800
  }
}
```

#### Farm Assignment

```json
// Duplicate farm assignment attempt
{
  "error": "Farm already assigned to this order",
  "code": "DUPLICATE_ASSIGNMENT",
  "existing_assignment": {
    "assignment_number": "ORD-2026-00013-A01",
    "quantity": 1800,
    "assigned_at": "2026-01-09T10:10:00Z"
  }
}
```

### Concurrent Request Protection

The backend uses distributed locking to prevent race conditions in multi-user environments:

**Protected Operations:**
| Operation | Lock Scope | Timeout |
|-----------|------------|---------|
| Publish Order | Per Order | 30s |
| Auto-Assign Farms | Per Order | 60s |
| Manual Farm Assignment | Per Order | 30s |
| Accept/Reject Assignment | Per Assignment | 30s |
| Confirm Delivery | Per Assignment | 30s |
| Verify Delivery | Per Delivery | 30s |
| Approve Invoice | Per Invoice | 30s |
| Process Payment | Per Invoice | 60s |

**Frontend Best Practices:**

```typescript
// 1. Immediately disable action buttons
const handleProcessPayment = async (invoiceId: string) => {
  setProcessingInvoices(prev => [...prev, invoiceId]);
  
  try {
    const result = await procurementApi.processPayment(invoiceId, paymentData);
    
    if (result.is_duplicate) {
      showToast('Payment was already processed', 'info');
    } else {
      showToast('Payment processed successfully', 'success');
    }
    
    refreshInvoiceList();
  } catch (error) {
    if (error.message.includes('locked') || error.status === 423) {
      showToast('Another user is processing this payment. Please wait.', 'warning');
      // Retry after delay
      setTimeout(() => refreshInvoiceList(), 3000);
    } else {
      showToast(error.message, 'error');
    }
  } finally {
    setProcessingInvoices(prev => prev.filter(id => id !== invoiceId));
  }
};

// 2. Show processing indicator for locked resources
const InvoiceRow = ({ invoice }) => {
  const isLocked = processingInvoices.includes(invoice.id);
  
  return (
    <tr className={isLocked ? 'opacity-50' : ''}>
      {/* ... */}
      <td>
        <button 
          disabled={isLocked}
          onClick={() => handleProcessPayment(invoice.id)}
        >
          {isLocked ? <Spinner /> : 'Process Payment'}
        </button>
      </td>
    </tr>
  );
};
```

### Atomic Operations

All critical operations are wrapped in database transactions:

```
┌──────────────────────────────────────────────────────────────┐
│                    ATOMIC: processPayment()                   │
├──────────────────────────────────────────────────────────────┤
│  1. Lock invoice row (SELECT FOR UPDATE)                      │
│  2. Validate invoice status (must be 'approved')              │
│  3. Check idempotency (has payment already been made?)        │
│  4. Create payment record                                     │
│  5. Update invoice status to 'paid'                           │
│  6. Update assignment status to 'paid'                        │
│  7. Update order fulfillment stats                            │
│  8. Create audit log entry                                    │
│  9. Send SMS notification to farmer                           │
│                                                               │
│  ⚡ All or nothing - partial updates are impossible           │
└──────────────────────────────────────────────────────────────┘
```

### Audit Trail

All procurement operations are logged for compliance, debugging, and dispute resolution:

```json
{
  "id": "uuid",
  "operation": "process_payment",
  "order_id": "uuid",
  "invoice_id": "uuid",
  "user_id": "uuid",
  "user_role": "PROCUREMENT_OFFICER",
  "timestamp": "2026-01-15T14:30:00Z",
  "previous_state": {
    "invoice_status": "approved",
    "assignment_status": "verified"
  },
  "new_state": {
    "invoice_status": "paid",
    "assignment_status": "paid",
    "payment_amount": "152575.00",
    "payment_reference": "TXN-20260115-001"
  },
  "ip_address": "192.168.1.100",
  "details": {
    "payment_method": "bank_transfer",
    "farm_id": "uuid",
    "farm_name": "Addo Poultry Farm"
  }
}
```

**Audit Log Queries (Admin Only):**

```http
GET /api/admin/procurement/audit-logs/?order_id={uuid}
GET /api/admin/procurement/audit-logs/?operation=process_payment&date_from=2026-01-01
GET /api/admin/procurement/audit-logs/?user_id={uuid}
```

### Error Response Codes (New)

| HTTP Status | Error Code | Description | Frontend Action |
|-------------|------------|-------------|-----------------|
| 400 | `INVALID_STATE_TRANSITION` | Invalid status change | Refresh, show current state |
| 409 | `DUPLICATE_ASSIGNMENT` | Farm already assigned | Show existing assignment |
| 409 | `DUPLICATE_PAYMENT` | Payment already processed | Show existing payment |
| 409 | `DUPLICATE_DELIVERY` | Delivery already confirmed | Show existing delivery |
| 423 | `RESOURCE_LOCKED` | Resource being modified | Wait and retry |
| 500 | `TRANSACTION_FAILED` | Database transaction failed | Show error, allow retry |

### Separation of Duties

The system enforces financial separation of duties through role-based permissions:

```
┌─────────────────────────────────────────────────────────────┐
│                    PROCUREMENT WORKFLOW                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  PROCUREMENT_OFFICER                                         │
│  ├── Create orders                                           │
│  ├── Assign farms                                            │
│  ├── Verify deliveries                                       │
│  └── Create invoices                                         │
│                                                              │
│  FINANCE_OFFICER (cannot create orders)                      │
│  ├── Approve invoices                                        │
│  ├── Process payments                                        │
│  └── View financial reports                                  │
│                                                              │
│  AUDITOR (read-only access)                                  │
│  ├── View all orders and invoices                            │
│  ├── View audit logs                                         │
│  └── Export reports                                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

This prevents:
- Same person creating and paying invoices
- Unauthorized payment processing
- Audit trail manipulation

### Real-Time Status Updates

For dashboard pages showing multiple orders/assignments, consider implementing polling or WebSocket updates:

```typescript
// Polling approach (recommended for this system)
const useProcurementDashboard = () => {
  const [data, setData] = useState(null);
  
  useEffect(() => {
    const fetchData = async () => {
      const result = await procurementApi.getDashboard();
      setData(result);
    };
    
    fetchData();
    
    // Poll every 30 seconds for updates
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);
  
  return data;
};

// Manual refresh after actions
const handlePaymentProcessed = async (invoiceId: string) => {
  await processPayment(invoiceId);
  // Force immediate refresh
  await refetchDashboard();
};
```

---

*Last Updated: January 2026*
