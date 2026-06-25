# QOT API Documentation

## 1. Overview

QOT is a classified ads platform API similar to OLX/Jiji. It supports user accounts, listing creation, categories, locations, chats, favorites, seller reviews, saved searches, notifications, payments, featured listings, moderation, and admin management.

Local development base URL:

```txt
http://127.0.0.1:8000/api/v1/
```

Future production base URL:

```txt
https://qot.ug/api/v1/
```

---

## 2. Authentication

Protected endpoints require JWT authentication.

Use this header:

```txt
Authorization: Bearer ACCESS_TOKEN
```

For JSON requests:

```txt
Content-Type: application/json
```

For file uploads:

```txt
Content-Type: multipart/form-data
```

---

## 3. Common Status Codes

```txt
200 OK
201 Created
204 No Content
400 Bad Request
401 Unauthorized
403 Forbidden
404 Not Found
500 Server Error
```

Common error response:

```json
{
  "detail": "Error message here."
}
```

---

# AUTH ENDPOINTS

## Register User

```txt
POST /auth/register/
```

Example body:

```json
{
  "phone": "+256700000001",
  "email": "seller@example.com",
  "full_name": "Brian Seller",
  "password": "StrongPass123"
}
```

---

## Login

```txt
POST /auth/login/
```

Example body:

```json
{
  "phone": "+256700000001",
  "password": "StrongPass123"
}
```

---

## Refresh Token

```txt
POST /auth/token/refresh/
```

Example body:

```json
{
  "refresh": "REFRESH_TOKEN"
}
```

---

## Logout

```txt
POST /auth/logout/
```

Requires authentication.

---

## Current User

```txt
GET /auth/me/
PATCH /auth/me/
```

Requires authentication.

---

## Password Reset Request

```txt
POST /auth/password-reset/request/
```

---

## Password Reset Confirm

```txt
POST /auth/password-reset/confirm/
```

---

## Send Verification Code

```txt
POST /auth/verification/send/
```

---

## Confirm Verification Code

```txt
POST /auth/verification/confirm/
```

---

# LOCATIONS

## List Regions

```txt
GET /locations/regions/
```

---

## List Cities

```txt
GET /locations/cities/
```

Filter by region:

```txt
GET /locations/cities/?region=central-region
```

---

# CATEGORIES

## List Categories

```txt
GET /categories/
```

---

## Category Detail

```txt
GET /categories/{slug}/
```

---

## Category Filters

```txt
GET /categories/{slug}/filters/
```

---

# LISTINGS

## Public Listing List

```txt
GET /listings/
```

Supported filters:

```txt
?q=toyota
?category=cars
?city=kampala
?region=central-region
?min_price=10000000
?max_price=30000000
?condition=used
?sort=newest
?sort=oldest
?sort=price_low
?sort=price_high
?sort=popular
```

Dynamic category filters are supported:

```txt
GET /listings/?brand=Toyota
GET /listings/?ram=16GB
GET /listings/?bedrooms=2
```

Public listing results only show active, non-expired listings.

---

## Create Listing

```txt
POST /listings/
```

Requires authentication and verified account.

Example body:

```json
{
  "category": 1,
  "city": 1,
  "title": "Toyota Premio 2012",
  "description": "Clean car in good condition.",
  "price": "25000000",
  "currency": "UGX",
  "condition": "used",
  "is_negotiable": true,
  "attributes": [
    {
      "category_filter_id": 1,
      "value_text": "Toyota"
    }
  ]
}
```

---

## My Listings

```txt
GET /listings/?mine=true
```

Requires authentication.

---

## Listing Detail

```txt
GET /listings/{id}/
```

---

## Update Listing

```txt
PATCH /listings/{id}/
```

Only the listing owner can update the listing.

---

## Delete Listing

```txt
DELETE /listings/{id}/
```

Soft deletes the listing.

---

## Upload Listing Image

```txt
POST /listings/{id}/images/
```

Requires form-data:

```txt
image = file
```

---

## Delete Listing Image

```txt
DELETE /listings/{id}/images/{image_id}/
```

---

## Set Primary Image

```txt
POST /listings/{id}/images/{image_id}/set-primary/
```

---

## Mark Listing Sold

```txt
POST /listings/{id}/mark-sold/
```

---

## Mark Listing Available

```txt
POST /listings/{id}/mark-available/
```

---

## Mark Listing Unavailable

```txt
POST /listings/{id}/mark-unavailable/
```

---

## Relist Listing

```txt
POST /listings/{id}/relist/
```

---

## Renew Listing

```txt
POST /listings/{id}/renew/
```

---

## Report Listing

```txt
POST /listings/{listing_id}/report/
```

Example body:

```json
{
  "reason": "scam",
  "description": "This listing looks suspicious."
}
```

---

# FAVORITES

## Toggle Favorite

```txt
POST /favorites/listings/{listing_id}/toggle/
```

Requires authentication.

---

## My Favorites

```txt
GET /favorites/
```

Requires authentication.

---

# CHATS

## List Chat Threads

```txt
GET /chats/threads/
```

Requires authentication.

Each thread includes unread count.

---

## Create Chat Thread

```txt
POST /chats/threads/
```

Example body:

```json
{
  "listing": 42
}
```

---

## Thread Detail

```txt
GET /chats/threads/{id}/
```

---

## List Thread Messages

```txt
GET /chats/threads/{thread_id}/messages/
```

---

## Send Text Message

```txt
POST /chats/threads/{thread_id}/messages/
```

Example body:

```json
{
  "body": "Hello, is this still available?"
}
```

Blocked users cannot send messages in that thread.

---

## Mark Messages Read

```txt
POST /chats/threads/{thread_id}/mark-read/
```

---

## Upload Chat Attachment

```txt
POST /chats/threads/{thread_id}/attachments/
```

Use form-data:

```txt
message = Here is the receipt
file = receipt.jpg
```

Allowed files:

```txt
JPG, JPEG, PNG, WEBP, PDF, DOC, DOCX
```

Maximum size:

```txt
10MB
```

---

## Block Chat User

```txt
POST /chats/threads/{thread_id}/block/
```

Example body:

```json
{
  "reason": "Suspicious conversation"
}
```

---

## Unblock Chat User

```txt
POST /chats/threads/{thread_id}/unblock/
```

---

## Report Chat Thread

```txt
POST /chats/threads/{thread_id}/report/
```

Example body:

```json
{
  "reason": "scam",
  "description": "User is asking for payment outside the platform."
}
```

Supported reasons:

```txt
spam
scam
abuse
harassment
other
```

---

# NOTIFICATIONS

## My Notifications

```txt
GET /notifications/
```

Requires authentication.

---

## Mark Notification Read

```txt
POST /notifications/{id}/read/
```

---

## Mark All Notifications Read

```txt
POST /notifications/read-all/
```

---

# SELLER ENDPOINTS

## Seller Dashboard

```txt
GET /seller/dashboard/
```

Returns seller listing summary, active listings, pending listings, sold listings, expired listings, total views, favorites, best listing, weakest listing, recent listings, and active featured listings.

---

## Seller Listings

```txt
GET /seller/listings/
```

---

## Seller Analytics

```txt
GET /seller/analytics/
```

---

## Single Listing Analytics

```txt
GET /seller/listings/{id}/analytics/
```

---

# PUBLIC SELLER PROFILE

## Seller Profile

```txt
GET /sellers/{seller_id}/
```

Returns seller public details, trust score, average rating, total reviews, and active listing count.

---

## Seller Public Listings

```txt
GET /sellers/{seller_id}/listings/
```

---

# REVIEWS

## Create Seller Review

```txt
POST /reviews/
```

Requires authentication and verified account.

Example body:

```json
{
  "seller": 5,
  "listing": 42,
  "rating": 5,
  "comment": "Good seller. Item was as described."
}
```

Rating must be between 1 and 5.

---

## Seller Reviews

```txt
GET /reviews/sellers/{seller_id}/
```

---

## Seller Review Summary

```txt
GET /reviews/sellers/{seller_id}/summary/
```

Example response:

```json
{
  "seller": 5,
  "seller_name": "Brian Seller",
  "average_rating": 5.0,
  "total_reviews": 3
}
```

---

## My Given Reviews

```txt
GET /reviews/me/
```

Requires authentication.

---

# SEARCHES

## Save Recent Search

```txt
POST /searches/recent/
```

Example body:

```json
{
  "query": "Toyota",
  "filters": {
    "category": "cars",
    "city": "kampala"
  }
}
```

---

## My Recent Searches

```txt
GET /searches/recent/
```

---

## Clear Recent Searches

```txt
DELETE /searches/recent/clear/
```

---

## Create Saved Search

```txt
POST /searches/saved/
```

Example body:

```json
{
  "name": "Toyota cars in Kampala",
  "query": "Toyota",
  "filters": {
    "category": "cars",
    "city": "kampala",
    "min_price": "10000000",
    "max_price": "30000000"
  },
  "notify_user": true
}
```

When `notify_user` is true, the user can receive notifications when a new matching listing becomes active.

---

## My Saved Searches

```txt
GET /searches/saved/
```

---

## Delete Saved Search

```txt
DELETE /searches/saved/{id}/
```

---

# PAYMENTS AND PROMOTION PACKAGES

## Public Promotion Packages

```txt
GET /payments/packages/
```

Optional filter:

```txt
?package_type=featured_listing
```

---

## Create Payment

```txt
POST /payments/
```

Requires authentication and verified account.

Example body:

```json
{
  "listing": 42,
  "package": 1,
  "purpose": "featured_listing",
  "amount": "1",
  "currency": "UGX",
  "payment_method": "manual"
}
```

When a package is selected, the backend overrides amount, currency, and purpose using the package.

Supported purposes:

```txt
featured_listing
boost_listing
subscription
```

Supported payment methods:

```txt
mtn_mobile_money
airtel_money
card
cash
manual
```

---

## My Payments

```txt
GET /payments/me/
```

---

# MODERATION

## Admin Listing Reports

```txt
GET /moderation/reports/
```

Requires admin or moderator.

Supported filters:

```txt
?search=Toyota
?reason=scam
?is_resolved=false
?reporter=5
?listing=42
?date_from=2026-06-01
?date_to=2026-06-24
```

---

## Listing Report Detail

```txt
GET /moderation/reports/{id}/
```

---

## Resolve Listing Report

```txt
POST /moderation/reports/{id}/resolve/
```

Example body:

```json
{
  "note": "Reviewed and resolved."
}
```

---

## Reject Reported Listing

```txt
POST /moderation/reports/{id}/reject-listing/
```

Example body:

```json
{
  "rejection_reason": "The listing contains misleading information."
}
```

---

## Delete Reported Listing

```txt
POST /moderation/reports/{id}/delete-listing/
```

---

# ADMIN ENDPOINTS

All admin endpoints require admin or moderator access.

Header:

```txt
Authorization: Bearer ADMIN_ACCESS_TOKEN
```

---

## Admin Dashboard

```txt
GET /admin-panel/dashboard/
```

Returns users, listings, reports, payments, revenue, and period analytics.

---

## Admin User List

```txt
GET /admin-panel/users/
```

Supported filters:

```txt
?search=Brian
?role=user
?role=admin
?role=moderator
?is_banned=true
?is_verified=false
```

---

## Ban User

```txt
POST /admin-panel/users/{id}/ban/
```

Example body:

```json
{
  "reason": "Fraudulent activity"
}
```

---

## Unban User

```txt
POST /admin-panel/users/{id}/unban/
```

---

## Admin Listing List

```txt
GET /admin-panel/listings/
```

Supported filters:

```txt
?search=Toyota
?status=active
?seller=5
?category=cars
?city=kampala
?is_featured=true
?date_from=2026-06-01
?date_to=2026-06-24
```

---

## Pending Listings

```txt
GET /admin-panel/listings/pending/
```

---

## Approve Listing

```txt
POST /admin-panel/listings/{id}/approve/
```

Approving a listing can trigger saved-search alerts for matching saved searches.

---

## Reject Listing

```txt
POST /admin-panel/listings/{id}/reject/
```

Example body:

```json
{
  "rejection_reason": "The listing has misleading information."
}
```

---

## Feature Listing Manually

```txt
POST /admin-panel/listings/{id}/feature/
```

Example body:

```json
{
  "days": 7
}
```

---

## Unfeature Listing

```txt
POST /admin-panel/listings/{id}/unfeature/
```

---

# ADMIN PAYMENTS

## List Payments

```txt
GET /admin-panel/payments/
```

Supported filters:

```txt
?search=QOT
?status=paid
?purpose=featured_listing
?user=5
?listing=42
?payment_method=manual
?date_from=2026-06-01
?date_to=2026-06-24
```

---

## Mark Payment Paid

```txt
POST /admin-panel/payments/{id}/mark-paid/
```

Example body:

```json
{
  "provider_reference": "MANUAL-001",
  "notes": "Paid manually for testing."
}
```

If the payment purpose is `featured_listing`, the related listing becomes featured automatically.

---

## Mark Payment Failed

```txt
POST /admin-panel/payments/{id}/mark-failed/
```

Example body:

```json
{
  "notes": "Payment was not received."
}
```

---

## Cancel Payment

```txt
POST /admin-panel/payments/{id}/cancel/
```

Example body:

```json
{
  "notes": "Seller requested cancellation."
}
```

---

# ADMIN PROMOTION PACKAGES

## List Packages

```txt
GET /admin-panel/packages/
```

Supported filters:

```txt
?package_type=featured_listing
?is_active=true
```

---

## Create Package

```txt
POST /admin-panel/packages/
```

Example body:

```json
{
  "name": "Featured 7 Days",
  "package_type": "featured_listing",
  "description": "Feature your listing for 7 days.",
  "duration_days": 7,
  "price": "10000",
  "currency": "UGX",
  "is_active": true,
  "sort_order": 1
}
```

---

## Update Package

```txt
PATCH /admin-panel/packages/{id}/
```

---

# ADMIN REVIEW MODERATION

## List Reviews

```txt
GET /admin-panel/reviews/
```

Supported filters:

```txt
?search=Toyota
?rating=1
?seller=5
?reviewer=6
?listing=42
?is_visible=false
?date_from=2026-06-01
?date_to=2026-06-24
```

---

## Hide Review

```txt
POST /admin-panel/reviews/{id}/hide/
```

---

## Show Review

```txt
POST /admin-panel/reviews/{id}/show/
```

---

# ADMIN CHAT REPORTS

## List Chat Reports

```txt
GET /admin-panel/chat-reports/
```

Supported filters:

```txt
?search=scam
?reason=scam
?is_resolved=false
?reporter=5
?reported_user=6
?thread=1
?listing=42
?date_from=2026-06-01
?date_to=2026-06-24
```

---

## Chat Report Detail

```txt
GET /admin-panel/chat-reports/{id}/
```

---

## Resolve Chat Report

```txt
POST /admin-panel/chat-reports/{id}/resolve/
```

Example body:

```json
{
  "note": "Reviewed by admin. User warned."
}
```

---

# ADMIN CHAT BLOCKS

## List Chat Blocks

```txt
GET /admin-panel/chat-blocks/
```

Supported filters:

```txt
?search=suspicious
?blocker=5
?blocked_user=6
?thread=1
?listing=42
?is_active=true
?date_from=2026-06-01
?date_to=2026-06-24
```

---

# HOME ENDPOINT

## Homepage Data

```txt
GET /home/
```

Returns:

```txt
featured_listings
latest_listings
popular_listings
popular_categories
recent_cars
recent_phones
recent_laptops
```

---

# ME ENDPOINTS

## My Counts

```txt
GET /me/counts/
```

Returns unread counts for notifications, chats, favorites, and other user-level badges.

---

# WEBSOCKET ENDPOINTS

## Chat WebSocket

```txt
ws://127.0.0.1:8000/ws/chats/threads/{thread_id}/?token=ACCESS_TOKEN
```

---

## Notification WebSocket

```txt
ws://127.0.0.1:8000/ws/notifications/?token=ACCESS_TOKEN
```

---

# MANAGEMENT COMMANDS

Run expired listing cleanup:

```bash
./venv/bin/python manage.py expire_listings
```

Run expired featured listing cleanup:

```bash
./venv/bin/python manage.py expire_featured_listings
```

Recalculate trust scores:

```bash
./venv/bin/python manage.py sync_trust_scores
```

Seed dummy data:

```bash
./venv/bin/python manage.py seed_dummy_data
```

Seed promotion packages:

```bash
./venv/bin/python manage.py seed_packages
```

---

# IMPORTANT BUSINESS RULES

1. Public users can view only active and non-expired listings.
2. Listings created by users are pending until approved by admin or moderator.
3. Verified users can create listings and send seller actions.
4. Deleted listings are soft-deleted.
5. Sold, expired, unavailable, rejected, and deleted listings are hidden from public results.
6. Featured listings appear higher and can expire automatically.
7. Paid featured-listing payments can automatically feature a listing.
8. Saved-search alerts notify users when matching listings become active.
9. Duplicate saved-search alerts are prevented using alert logs.
10. Users can block and report chat participants.
11. Blocked users cannot send normal messages or attachments in that thread.
12. Admins can view reports, reviews, payments, chat reports, and chat blocks.
13. Seller trust score is recalculated after reviews, approvals, rejections, bans, and unbans.

---

# DEVELOPMENT NOTES

Local check command:

```bash
./venv/bin/python manage.py check
```

Make migrations:

```bash
./venv/bin/python manage.py makemigrations
```

Apply migrations:

```bash
./venv/bin/python manage.py migrate
```

Run local server:

```bash
./venv/bin/python manage.py runserver 8000
```

Kill busy port 8000:

```bash
kill -9 $(lsof -ti :8000)
```

---

# CURRENT PROJECT STATUS

Approximate backend completion:

```txt
Core API:                   90%+
Mobile app API readiness:   85%+
Production readiness:       paused
```

Production setup will be done afresh later after local API testing and cleanup.
