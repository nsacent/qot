# QOT API Testing Checklist

## Base URL

Local development:

```txt
http://127.0.0.1:8000/api/v1/
```

Authentication header:

```txt
Authorization: Bearer ACCESS_TOKEN
```

---

# 1. Authentication Tests

## Register User

Endpoint:

```txt
POST /auth/register/
```

Checklist:

```txt
[ Tested] User can register with phone, email, full name, and password.
[ Tested] Duplicate phone number is rejected.
[ Tested] Duplicate email is rejected.
[ Tested] Weak password is rejected.
[ Tested] User profile is created automatically.
```

---

## Login

Endpoint:

```txt
POST /auth/login/
```

Checklist:

```txt
[ Tested] User can login with correct phone and password.
[ Tested] Wrong password is rejected.
[Tested ] Login response returns access token.
[Tested ] Login response returns refresh token.
[ Tested] Banned user cannot login or cannot access protected actions.
```

---

## Token Refresh

Endpoint:

```txt
POST /auth/token/refresh/
```

Checklist:

```txt
[Tested ] Valid refresh token returns new access token.
[Tested ] Invalid refresh token is rejected.
```

---

## Current User

Endpoint:

```txt
GET /auth/me/
PATCH /auth/me/
```

Checklist:

```txt
[Tested ] Authenticated user can view profile.
[ ] Authenticated user can update profile.
[Tested ] Unauthenticated request is rejected.
```

---

# 2. Location Tests

## Regions

Endpoint:

```txt
GET /locations/regions/
```

Checklist:

```txt
[Tested ] Regions list loads successfully.
[Tested ] Response includes region name and slug.
```

---

## Cities

Endpoint:

```txt
GET /locations/cities/
GET /locations/cities/?region=central-region
```

Checklist:

```txt
[ Tested] Cities list loads successfully.
[ Tested] Cities can be filtered by region.
[Tested ] Response includes city name, slug, and region.
```

---

# 3. Category Tests

## Categories

Endpoint:

```txt
GET /categories/
```

Checklist:

```txt
[ ] Categories list loads successfully.
[ ] Parent categories appear.
[ ] Child categories appear correctly.
```

---

## Category Detail

Endpoint:

```txt
GET /categories/{slug}/
```

Checklist:

```txt
[ ] Category detail loads by slug.
[ ] Invalid slug returns 404.
```

---

## Category Filters

Endpoint:

```txt
GET /categories/{slug}/filters/
```

Checklist:

```txt
[ ] Category filters load correctly.
[ ] Filter options load correctly.
[ ] Invalid category returns 404.
```

---

# 4. Listing Tests

## Public Listing List

Endpoint:

```txt
GET /listings/
```

Checklist:

```txt
[ ] Public users can view active listings.
[ ] Pending listings do not show publicly.
[ ] Rejected listings do not show publicly.
[ ] Sold listings do not show publicly.
[ ] Expired listings do not show publicly.
[ ] Deleted listings do not show publicly.
[ ] Unavailable listings do not show publicly.
```

---

## Listing Search and Filters

Endpoint examples:

```txt
GET /listings/?q=toyota
GET /listings/?category=cars
GET /listings/?city=kampala
GET /listings/?min_price=10000000&max_price=30000000
GET /listings/?sort=price_low
GET /listings/?brand=Toyota
```

Checklist:

```txt
[ ] Search by keyword works.
[ ] Filter by category works.
[ ] Filter by city works.
[ ] Filter by region works.
[ ] Filter by minimum price works.
[ ] Filter by maximum price works.
[ ] Sort by newest works.
[ ] Sort by oldest works.
[ ] Sort by price low works.
[ ] Sort by price high works.
[ ] Sort by popular works.
[ ] Dynamic attribute filter works.
```

---

## Create Listing

Endpoint:

```txt
POST /listings/
```

Checklist:

```txt
[ ] Verified user can create listing.
[ ] Unverified user cannot create listing.
[ ] Banned user cannot create listing.
[ ] Listing is created as pending.
[ ] Listing slug is generated.
[ ] Dynamic attributes are saved.
[ ] Missing required fields are rejected.
[ ] Invalid category is rejected.
[ ] Invalid city is rejected.
```

---

## My Listings

Endpoint:

```txt
GET /listings/?mine=true
```

Checklist:

```txt
[ ] Authenticated user can view own listings.
[ ] User cannot view another user's private pending listings through mine=true.
```

---

## Listing Detail

Endpoint:

```txt
GET /listings/{id}/
```

Checklist:

```txt
[ ] Active listing detail loads.
[ ] Listing images are included.
[ ] Listing attributes are included.
[ ] View count increases correctly if implemented.
```

---

## Update Listing

Endpoint:

```txt
PATCH /listings/{id}/
```

Checklist:

```txt
[ ] Owner can update own listing.
[ ] Non-owner cannot update listing.
[ ] Banned user cannot update listing.
[ ] Dynamic attributes can be updated.
```

---

## Delete Listing

Endpoint:

```txt
DELETE /listings/{id}/
```

Checklist:

```txt
[ ] Owner can soft-delete listing.
[ ] Deleted listing disappears from public list.
[ ] Non-owner cannot delete listing.
```

---

# 5. Listing Image Tests

## Upload Image

Endpoint:

```txt
POST /listings/{id}/images/
```

Checklist:

```txt
[ ] Owner can upload image.
[ ] First image becomes primary.
[ ] JPG upload works.
[ ] PNG upload works.
[ ] WEBP upload works.
[ ] File above 5MB is rejected.
[ ] Unsupported file type is rejected.
[ ] User cannot upload image to another user's listing.
[ ] More than maximum allowed images is rejected.
```

---

## Set Primary Image

Endpoint:

```txt
POST /listings/{id}/images/{image_id}/set-primary/
```

Checklist:

```txt
[ ] Owner can set primary image.
[ ] Previous primary image becomes non-primary.
[ ] Non-owner cannot set primary image.
```

---

## Delete Image

Endpoint:

```txt
DELETE /listings/{id}/images/{image_id}/
```

Checklist:

```txt
[ ] Owner can delete image.
[ ] Non-owner cannot delete image.
[ ] Deleted image is removed from listing response.
```

---

# 6. Listing Status Workflow Tests

## Mark Sold

Endpoint:

```txt
POST /listings/{id}/mark-sold/
```

Checklist:

```txt
[ ] Owner can mark listing as sold.
[ ] sold_at is saved.
[ ] Sold listing disappears from public listing list.
```

---

## Mark Available

Endpoint:

```txt
POST /listings/{id}/mark-available/
```

Checklist:

```txt
[ ] Owner can mark listing available again.
[ ] sold_at is cleared.
[ ] Listing becomes active.
```

---

## Mark Unavailable

Endpoint:

```txt
POST /listings/{id}/mark-unavailable/
```

Checklist:

```txt
[ ] Owner can mark active listing unavailable.
[ ] Unavailable listing disappears from public listing list.
```

---

## Relist

Endpoint:

```txt
POST /listings/{id}/relist/
```

Checklist:

```txt
[ ] Owner can relist listing.
[ ] Listing becomes active.
[ ] Expiry date is extended.
```

---

## Renew

Endpoint:

```txt
POST /listings/{id}/renew/
```

Checklist:

```txt
[ ] Owner can renew expired listing.
[ ] Listing becomes active.
[ ] Expiry date is extended.
```

---

# 7. Favorites Tests

## Toggle Favorite

Endpoint:

```txt
POST /favorites/listings/{listing_id}/toggle/
```

Checklist:

```txt
[ ] User can add listing to favorites.
[ ] User can remove listing from favorites.
[ ] favorites_count increases.
[ ] favorites_count decreases.
[ ] User cannot favorite deleted listing.
```

---

## My Favorites

Endpoint:

```txt
GET /favorites/
```

Checklist:

```txt
[ ] User can view own favorite listings.
[ ] Favorite listing details are included.
```

---

# 8. Chat Tests

## Create Chat Thread

Endpoint:

```txt
POST /chats/threads/
```

Checklist:

```txt
[ ] Buyer can create chat thread for listing.
[ ] Duplicate thread is not created.
[ ] Seller cannot start chat with self on own listing.
[ ] Banned user cannot create thread.
[ ] Unverified user cannot create thread if verification is required.
```

---

## List Chat Threads

Endpoint:

```txt
GET /chats/threads/
```

Checklist:

```txt
[ ] User sees only own chat threads.
[ ] Thread includes listing details.
[ ] Thread includes buyer and seller.
[ ] Thread includes unread_count.
[ ] Threads are ordered by last message time.
```

---

## Send Message

Endpoint:

```txt
POST /chats/threads/{thread_id}/messages/
```

Checklist:

```txt
[ ] Buyer can send message.
[ ] Seller can send message.
[ ] User outside thread cannot send message.
[ ] Message body is saved.
[ ] Thread last_message is updated.
[ ] Thread last_message_at is updated.
[ ] Receiver unread count increases.
[ ] Notification is created for receiver.
[ ] Blocked user cannot send message.
```

---

## Mark Messages Read

Endpoint:

```txt
POST /chats/threads/{thread_id}/mark-read/
```

Checklist:

```txt
[ ] User can mark received messages as read.
[ ] Own sent messages are not affected.
[ ] User unread count becomes zero.
```

---

## Upload Chat Attachment

Endpoint:

```txt
POST /chats/threads/{thread_id}/attachments/
```

Checklist:

```txt
[ ] Image attachment uploads successfully.
[ ] PDF attachment uploads successfully.
[ ] DOC/DOCX attachment uploads successfully.
[ ] Attachment creates chat message.
[ ] Attachment appears in message response.
[ ] File above 10MB is rejected.
[ ] Unsupported file type is rejected.
[ ] User outside thread cannot upload attachment.
[ ] Blocked user cannot upload attachment.
```

---

## Block Chat User

Endpoint:

```txt
POST /chats/threads/{thread_id}/block/
```

Checklist:

```txt
[ ] User can block other participant.
[ ] Block record is created.
[ ] Blocked user cannot send messages.
[ ] Blocked user cannot send attachments.
```

---

## Unblock Chat User

Endpoint:

```txt
POST /chats/threads/{thread_id}/unblock/
```

Checklist:

```txt
[ ] User can unblock participant.
[ ] Block becomes inactive.
[ ] Unblocked user can send messages again.
```

---

## Report Chat

Endpoint:

```txt
POST /chats/threads/{thread_id}/report/
```

Checklist:

```txt
[ ] User can report chat thread.
[ ] Report includes reason.
[ ] Report includes description.
[ ] User outside thread cannot report thread.
```

---

# 9. Notification Tests

## My Notifications

Endpoint:

```txt
GET /notifications/
```

Checklist:

```txt
[ ] User can view own notifications.
[ ] User cannot view another user's notifications.
[ ] Notifications are ordered newest first.
```

---

## Mark Notification Read

Endpoint:

```txt
POST /notifications/{id}/read/
```

Checklist:

```txt
[ ] User can mark own notification as read.
[ ] User cannot mark another user's notification.
```

---

## Mark All Read

Endpoint:

```txt
POST /notifications/read-all/
```

Checklist:

```txt
[ ] All unread notifications become read.
```

---

# 10. Seller Dashboard Tests

## Seller Dashboard

Endpoint:

```txt
GET /seller/dashboard/
```

Checklist:

```txt
[ ] Seller can view dashboard.
[ ] Total listings count is correct.
[ ] Active listings count is correct.
[ ] Pending listings count is correct.
[ ] Sold listings count is correct.
[ ] Expired listings count is correct.
[ ] Unavailable listings count is correct.
[ ] Total views are correct.
[ ] Total favorites are correct.
[ ] Best listing is returned.
[ ] Weakest listing is returned.
[ ] Recent listings are returned.
```

---

## Seller Analytics

Endpoint:

```txt
GET /seller/analytics/
```

Checklist:

```txt
[ ] Seller analytics summary loads.
[ ] Total chat threads count is correct.
[ ] Views and favorites totals are correct.
```

---

## Single Listing Analytics

Endpoint:

```txt
GET /seller/listings/{id}/analytics/
```

Checklist:

```txt
[ ] Owner can view listing analytics.
[ ] Non-owner cannot view listing analytics.
[ ] Chat count is correct.
[ ] Views count is correct.
[ ] Favorites count is correct.
```

---

# 11. Public Seller Profile Tests

## Seller Profile

Endpoint:

```txt
GET /sellers/{seller_id}/
```

Checklist:

```txt
[ ] Public seller profile loads.
[ ] Trust score is included.
[ ] Average rating is included.
[ ] Total reviews is included.
[ ] Active listing count is included.
```

---

## Seller Listings

Endpoint:

```txt
GET /sellers/{seller_id}/listings/
```

Checklist:

```txt
[ ] Only active seller listings show.
[ ] Sold listings do not show.
[ ] Expired listings do not show.
[ ] Deleted listings do not show.
```

---

# 12. Review Tests

## Create Review

Endpoint:

```txt
POST /reviews/
```

Checklist:

```txt
[ ] User can review seller.
[ ] User cannot review self.
[ ] Rating below 1 is rejected.
[ ] Rating above 5 is rejected.
[ ] Duplicate review for same seller/listing is rejected.
[ ] Review updates seller trust score.
```

---

## Seller Reviews

Endpoint:

```txt
GET /reviews/sellers/{seller_id}/
```

Checklist:

```txt
[ ] Public can view visible seller reviews.
[ ] Hidden reviews do not show.
```

---

## Review Summary

Endpoint:

```txt
GET /reviews/sellers/{seller_id}/summary/
```

Checklist:

```txt
[ ] Average rating is correct.
[ ] Total visible reviews count is correct.
```

---

# 13. Search Tests

## Recent Searches

Endpoint:

```txt
GET /searches/recent/
POST /searches/recent/
DELETE /searches/recent/clear/
```

Checklist:

```txt
[ ] User can save recent search.
[ ] User can view recent searches.
[ ] User can clear recent searches.
```

---

## Saved Searches

Endpoint:

```txt
GET /searches/saved/
POST /searches/saved/
DELETE /searches/saved/{id}/
```

Checklist:

```txt
[ ] User can create saved search.
[ ] User can view saved searches.
[ ] User can delete saved search.
[ ] Duplicate saved search name for same user is rejected.
[ ] notify_user true enables saved-search alerts.
```

---

## Saved Search Alerts

Checklist:

```txt
[ ] Matching listing approval creates notification.
[ ] Matching relisted listing creates notification.
[ ] Seller does not receive alert for own listing.
[ ] Duplicate alert for same saved search and listing is prevented.
```

---

# 14. Payment Tests

## Public Packages

Endpoint:

```txt
GET /payments/packages/
```

Checklist:

```txt
[ ] Active packages show publicly.
[ ] Inactive packages do not show publicly.
[ ] Package type filter works.
```

---

## Create Payment

Endpoint:

```txt
POST /payments/
```

Checklist:

```txt
[ ] Verified user can create payment.
[ ] Unverified user cannot create payment.
[ ] Payment reference is generated.
[ ] Payment status is pending.
[ ] User can only pay for own listing.
[ ] If package is selected, amount is overridden.
[ ] If package is selected, currency is overridden.
[ ] If package is selected, purpose is overridden.
```

---

## My Payments

Endpoint:

```txt
GET /payments/me/
```

Checklist:

```txt
[ ] User can view own payments.
[ ] User cannot view another user's payments.
```

---

# 15. Admin Dashboard Tests

## Dashboard

Endpoint:

```txt
GET /admin-panel/dashboard/
```

Checklist:

```txt
[ ] Admin can view dashboard.
[ ] Moderator can view dashboard if allowed.
[ ] Normal user cannot view dashboard.
[ ] User counts are correct.
[ ] Listing counts are correct.
[ ] Report counts are correct.
[ ] Payment counts are correct.
[ ] Revenue totals are correct.
[ ] Today revenue is correct.
[ ] This week revenue is correct.
[ ] This month revenue is correct.
```

---

# 16. Admin User Tests

## User List

Endpoint:

```txt
GET /admin-panel/users/
```

Checklist:

```txt
[ ] Admin can list users.
[ ] Search by name works.
[ ] Search by phone works.
[ ] Search by email works.
[ ] Filter by role works.
[ ] Filter by banned status works.
[ ] Filter by verified status works.
```

---

## Ban User

Endpoint:

```txt
POST /admin-panel/users/{id}/ban/
```

Checklist:

```txt
[ ] Admin can ban user.
[ ] Banned user trust score becomes zero.
[ ] Banned user cannot perform protected actions.
```

---

## Unban User

Endpoint:

```txt
POST /admin-panel/users/{id}/unban/
```

Checklist:

```txt
[ ] Admin can unban user.
[ ] Trust score recalculates.
```

---

# 17. Admin Listing Tests

## Admin Listing List

Endpoint:

```txt
GET /admin-panel/listings/
```

Checklist:

```txt
[ ] Admin can view all non-deleted listings.
[ ] Search by title works.
[ ] Search by seller works.
[ ] Filter by status works.
[ ] Filter by category works.
[ ] Filter by city works.
[ ] Filter by featured status works.
[ ] Filter by date works.
```

---

## Pending Listings

Endpoint:

```txt
GET /admin-panel/listings/pending/
```

Checklist:

```txt
[ ] Pending listings show.
[ ] Search pending listings works.
```

---

## Approve Listing

Endpoint:

```txt
POST /admin-panel/listings/{id}/approve/
```

Checklist:

```txt
[ ] Admin can approve listing.
[ ] Listing becomes active.
[ ] Seller receives approval notification.
[ ] Seller trust score recalculates.
[ ] Saved-search alerts are triggered.
```

---

## Reject Listing

Endpoint:

```txt
POST /admin-panel/listings/{id}/reject/
```

Checklist:

```txt
[ ] Admin can reject listing.
[ ] Rejection reason is saved.
[ ] Seller receives rejection notification.
[ ] Seller trust score recalculates.
```

---

## Feature Listing

Endpoint:

```txt
POST /admin-panel/listings/{id}/feature/
```

Checklist:

```txt
[ ] Admin can feature listing manually.
[ ] featured_until is saved.
[ ] Featured listing appears in homepage featured list.
```

---

## Unfeature Listing

Endpoint:

```txt
POST /admin-panel/listings/{id}/unfeature/
```

Checklist:

```txt
[ ] Admin can remove featured status.
[ ] featured_until becomes null.
```

---

# 18. Admin Payment Tests

## Payment List

Endpoint:

```txt
GET /admin-panel/payments/
```

Checklist:

```txt
[ ] Admin can list payments.
[ ] Search by reference works.
[ ] Search by provider reference works.
[ ] Search by user works.
[ ] Search by listing title works.
[ ] Filter by status works.
[ ] Filter by purpose works.
[ ] Filter by payment method works.
[ ] Filter by date works.
```

---

## Mark Payment Paid

Endpoint:

```txt
POST /admin-panel/payments/{id}/mark-paid/
```

Checklist:

```txt
[ ] Admin can mark pending payment as paid.
[ ] paid_at is saved.
[ ] Provider reference is saved.
[ ] User receives payment confirmed notification.
[ ] Featured listing payment activates featured listing.
[ ] Already paid payment cannot be marked paid again.
[ ] Cancelled payment cannot be marked paid.
```

---

## Mark Payment Failed

Endpoint:

```txt
POST /admin-panel/payments/{id}/mark-failed/
```

Checklist:

```txt
[ ] Admin can mark pending payment as failed.
[ ] User receives payment failed notification.
[ ] Paid payment cannot be marked failed.
[ ] Cancelled payment cannot be marked failed.
```

---

## Cancel Payment

Endpoint:

```txt
POST /admin-panel/payments/{id}/cancel/
```

Checklist:

```txt
[ ] Admin can cancel pending payment.
[ ] Paid payment cannot be cancelled.
[ ] Already cancelled payment cannot be cancelled again.
```

---

# 19. Admin Package Tests

## List/Create Packages

Endpoint:

```txt
GET /admin-panel/packages/
POST /admin-panel/packages/
```

Checklist:

```txt
[ ] Admin can list packages.
[ ] Admin can create package.
[ ] Package type filter works.
[ ] Active status filter works.
```

---

## Update Package

Endpoint:

```txt
PATCH /admin-panel/packages/{id}/
```

Checklist:

```txt
[ ] Admin can update package name.
[ ] Admin can update price.
[ ] Admin can deactivate package.
[ ] Inactive package disappears from public packages.
```

---

# 20. Listing Report Moderation Tests

## Listing Reports

Endpoint:

```txt
GET /moderation/reports/
```

Checklist:

```txt
[ ] Admin can view listing reports.
[ ] Search reports works.
[ ] Filter by reason works.
[ ] Filter by resolved status works.
[ ] Filter by reporter works.
[ ] Filter by listing works.
[ ] Filter by date works.
```

---

## Resolve Listing Report

Endpoint:

```txt
POST /moderation/reports/{id}/resolve/
```

Checklist:

```txt
[ ] Admin can resolve listing report.
[ ] resolved_by is saved.
[ ] resolved_at is saved.
[ ] Already resolved report cannot be resolved again.
```

---

## Reject Reported Listing

Endpoint:

```txt
POST /moderation/reports/{id}/reject-listing/
```

Checklist:

```txt
[ ] Admin can reject reported listing.
[ ] Listing becomes rejected.
[ ] Rejection reason is saved.
```

---

## Delete Reported Listing

Endpoint:

```txt
POST /moderation/reports/{id}/delete-listing/
```

Checklist:

```txt
[ ] Admin can soft-delete reported listing.
[ ] Deleted listing disappears publicly.
```

---

# 21. Review Moderation Tests

## Admin Reviews

Endpoint:

```txt
GET /admin-panel/reviews/
```

Checklist:

```txt
[ ] Admin can view all reviews.
[ ] Search reviews works.
[ ] Filter by seller works.
[ ] Filter by reviewer works.
[ ] Filter by listing works.
[ ] Filter by rating works.
[ ] Filter by visible status works.
```

---

## Hide Review

Endpoint:

```txt
POST /admin-panel/reviews/{id}/hide/
```

Checklist:

```txt
[ ] Admin can hide review.
[ ] Hidden review disappears from public seller reviews.
[ ] Seller trust score recalculates.
```

---

## Show Review

Endpoint:

```txt
POST /admin-panel/reviews/{id}/show/
```

Checklist:

```txt
[ ] Admin can show hidden review again.
[ ] Review appears publicly again.
[ ] Seller trust score recalculates.
```

---

# 22. Chat Report Moderation Tests

## Admin Chat Reports

Endpoint:

```txt
GET /admin-panel/chat-reports/
```

Checklist:

```txt
[ ] Admin can view chat reports.
[ ] Search chat reports works.
[ ] Filter by reason works.
[ ] Filter by resolved status works.
[ ] Filter by reporter works.
[ ] Filter by reported user works.
[ ] Filter by thread works.
[ ] Filter by listing works.
[ ] Filter by date works.
```

---

## Chat Report Detail

Endpoint:

```txt
GET /admin-panel/chat-reports/{id}/
```

Checklist:

```txt
[ ] Admin can view chat report detail.
```

---

## Resolve Chat Report

Endpoint:

```txt
POST /admin-panel/chat-reports/{id}/resolve/
```

Checklist:

```txt
[ ] Admin can resolve chat report.
[ ] Admin note is saved.
[ ] resolved_by is saved.
[ ] resolved_at is saved.
```

---

# 23. Chat Block Admin Tests

## Admin Chat Blocks

Endpoint:

```txt
GET /admin-panel/chat-blocks/
```

Checklist:

```txt
[ ] Admin can view chat blocks.
[ ] Search blocks works.
[ ] Filter by blocker works.
[ ] Filter by blocked user works.
[ ] Filter by thread works.
[ ] Filter by listing works.
[ ] Filter by active status works.
[ ] Filter by date works.
```

---

# 24. Home Endpoint Tests

## Homepage

Endpoint:

```txt
GET /home/
```

Checklist:

```txt
[ ] Featured listings return.
[ ] Latest listings return.
[ ] Popular listings return.
[ ] Popular categories return.
[ ] Recent cars return.
[ ] Recent phones return.
[ ] Recent laptops return.
[ ] Expired listings do not show.
[ ] Sold listings do not show.
[ ] Unavailable listings do not show.
```

---

# 25. Me Counts Tests

## My Counts

Endpoint:

```txt
GET /me/counts/
```

Checklist:

```txt
[ ] User receives unread notification count.
[ ] User receives unread chat count.
[ ] User receives favorite count if implemented.
[ ] Counts update after reading messages.
[ ] Counts update after reading notifications.
```

---

# 26. WebSocket Tests

## Chat WebSocket

Endpoint:

```txt
ws://127.0.0.1:8000/ws/chats/threads/{thread_id}/?token=ACCESS_TOKEN
```

Checklist:

```txt
[ ] Authenticated user can connect.
[ ] User outside thread cannot connect.
[ ] Message broadcasts to other participant.
[ ] Invalid token is rejected.
```

---

## Notification WebSocket

Endpoint:

```txt
ws://127.0.0.1:8000/ws/notifications/?token=ACCESS_TOKEN
```

Checklist:

```txt
[ ] Authenticated user can connect.
[ ] Notification broadcasts to correct user.
[ ] Invalid token is rejected.
```

---

# 27. Management Command Tests

## Expire Listings

Command:

```bash
./venv/bin/python manage.py expire_listings
```

Checklist:

```txt
[ ] Expired active listings become expired.
[ ] Non-expired active listings remain active.
```

---

## Expire Featured Listings

Command:

```bash
./venv/bin/python manage.py expire_featured_listings
```

Checklist:

```txt
[ ] Expired featured listings become unfeatured.
[ ] Active featured listings remain featured.
```

---

## Sync Trust Scores

Command:

```bash
./venv/bin/python manage.py sync_trust_scores
```

Checklist:

```txt
[ ] Trust scores recalculate for all users.
```

---

## Seed Packages

Command:

```bash
./venv/bin/python manage.py seed_packages
```

Checklist:

```txt
[ ] Default promotion packages are created.
[ ] Running command again does not duplicate packages.
```

---

# 28. Final Full Flow Test

Use this order for a complete end-to-end test:

```txt
[ ] Register buyer.
[ ] Register seller.
[ ] Verify seller.
[ ] Seller creates listing.
[ ] Seller uploads images.
[ ] Admin approves listing.
[ ] Buyer searches listing.
[ ] Buyer favorites listing.
[ ] Buyer starts chat with seller.
[ ] Seller replies.
[ ] Buyer marks messages read.
[ ] Buyer creates saved search.
[ ] Seller creates another matching listing.
[ ] Admin approves matching listing.
[ ] Buyer receives saved-search notification.
[ ] Buyer reviews seller.
[ ] Seller trust score updates.
[ ] Seller creates payment for featured package.
[ ] Admin marks payment as paid.
[ ] Listing becomes featured.
[ ] Listing appears in homepage featured section.
[ ] Admin dashboard revenue updates.
[ ] Seller dashboard analytics updates.
```

---

# 29. Current Testing Status

Use this section to track progress:

```txt
Auth:                         Not Tested
Locations:                    Not Tested
Categories:                   Not Tested
Listings:                     Not Tested
Images:                       Not Tested
Favorites:                    Not Tested
Chats:                        Not Tested
Notifications:                Not Tested
Seller Dashboard:             Not Tested
Public Seller Profile:        Not Tested
Reviews:                      Not Tested
Searches:                     Not Tested
Payments:                     Not Tested
Admin Dashboard:              Not Tested
Admin Users:                  Not Tested
Admin Listings:               Not Tested
Admin Payments:               Not Tested
Admin Packages:               Not Tested
Listing Reports:              Not Tested
Review Moderation:            Not Tested
Chat Reports:                 Not Tested
Chat Blocks:                  Not Tested
Home:                         Not Tested
Me Counts:                    Not Tested
WebSockets:                   Not Tested
Management Commands:          Not Tested
Full Flow:                    Not Tested
```
