"""The knowledge base: hand-authored troubleshooting articles.

Every article below was written from scratch for this project. Topic
selection for the ACCOUNT/CANCEL/CONTACT/DELIVERY/INVOICE/ORDER/PAYMENT/
REFUND/SHIPPING/SUBSCRIPTION-flavored articles was inspired by the
category/intent taxonomy in `bitext/Bitext-customer-support-llm-chatbot-
training-dataset` (used only as a topic checklist, per BUILD_PLAN.md — no
dataset text is copied into any article body). Articles for categories the
bitext taxonomy doesn't cover (technical/product/IT troubleshooting,
service outages, sales, HR) were invented directly to give every
`Category` in schemas.py reasonable knowledge-base coverage.

`source_note` on each document records that provenance distinction:
- "bitext taxonomy: <CATEGORY>/<intent>" — topic inspired by that taxonomy entry
- "original — no dataset source" — topic invented for KB completeness

Docstring assumption: every `Category` enum member has at least 3 articles,
so Phase 4's retrieval step never returns zero chunks for a validly
classified ticket category.
"""

from __future__ import annotations

from support_agent.schemas import Category, KBDocument

DOCUMENTS: list[KBDocument] = [
    # -- technical_support -------------------------------------------------
    KBDocument(
        id="ts-01-app-crashes-freezes",
        title="App crashes or freezes on startup",
        category=Category.TECHNICAL_SUPPORT,
        source_note="original — no dataset source",
        body=(
            "If the app crashes immediately after opening, or freezes on a splash "
            "screen, start with the basics: confirm you're on the latest version "
            "(check Settings > About), restart your device, and make sure at least "
            "1 GB of free storage is available — a nearly-full disk is one of the "
            "most common causes of startup crashes.\n\n"
            "If it still won't open, try a clean relaunch: fully quit the app "
            "(don't just background it), wait 10 seconds, then reopen. On desktop, "
            "check for a leftover lock file in the app's local data folder and "
            "delete it if present — a stale lock from a previous crash can block "
            "startup entirely.\n\n"
            "If crashes persist across multiple relaunches, collect the crash log "
            "(Settings > Diagnostics > Export Logs) before contacting support — it "
            "cuts investigation time dramatically and is the single most useful "
            "thing a reporter can attach to a technical support ticket."
        ),
    ),
    KBDocument(
        id="ts-02-error-codes",
        title="Understanding common error codes",
        category=Category.TECHNICAL_SUPPORT,
        source_note="original — no dataset source",
        body=(
            "E101 (Network Timeout): the app couldn't reach our servers within 15 "
            "seconds. Usually a local connectivity issue — check Wi-Fi/VPN and "
            "retry. If it persists on multiple networks, our service may be "
            "degraded; check the status page.\n\n"
            "E204 (Session Expired): your login session timed out for security "
            "reasons after a period of inactivity. Simply log in again — no data "
            "is lost.\n\n"
            "E409 (Conflicting Edit): two devices edited the same item while "
            "offline. The app keeps both versions and asks you to pick one or "
            "merge manually; nothing is silently overwritten.\n\n"
            "E500 (Server Error): something failed on our end, not yours. These "
            "are automatically logged and reviewed; if you see the same E500 "
            "repeatedly for the same action, report it with the timestamp so it "
            "can be matched to server-side logs."
        ),
    ),
    KBDocument(
        id="ts-03-sync-issues",
        title="Data not syncing across devices",
        category=Category.TECHNICAL_SUPPORT,
        source_note="original — no dataset source",
        body=(
            "Sync problems almost always trace back to one of three things: you're "
            "signed into different accounts on each device (check Settings > "
            "Account on both), one device is offline or in airplane mode, or "
            "background sync has been disabled in the OS's battery/data-saver "
            "settings.\n\n"
            "To force a manual sync, pull down to refresh on the main screen, or "
            "use Settings > Sync Now on desktop. If changes made on Device A still "
            "don't appear on Device B after a manual sync and both show 'Synced' "
            "status, there may be a sync conflict (see error code E409) that's "
            "silently waiting for resolution — check the Conflicts tab.\n\n"
            "As a last resort, signing out and back in on the lagging device "
            "forces a full re-sync from the server, which resolves the vast "
            "majority of persistent sync issues."
        ),
    ),
    KBDocument(
        id="ts-04-slow-performance",
        title="App running slowly or lagging",
        category=Category.TECHNICAL_SUPPORT,
        source_note="original — no dataset source",
        body=(
            "Performance issues are usually proportional to how much data you're "
            "working with. If a specific project or board has grown very large "
            "(thousands of items), try archiving completed items — archived data "
            "stays searchable but isn't loaded into the active view.\n\n"
            "Browser-based slowness is often caused by extensions intercepting "
            "network requests; try the app in a private/incognito window with "
            "extensions disabled as a quick test. On desktop, check Settings > "
            "Performance > Hardware Acceleration — toggling it can resolve "
            "rendering slowness on some GPU/driver combinations.\n\n"
            "If performance degraded suddenly rather than gradually, check the "
            "status page for an active incident before assuming it's local."
        ),
    ),
    KBDocument(
        id="ts-05-data-loss-recovery",
        title="Recovering lost or corrupted data",
        category=Category.TECHNICAL_SUPPORT,
        source_note="original — no dataset source",
        body=(
            "Losing work is stressful, so start here: don't create new items or "
            "make further edits in the affected project until you've tried "
            "recovery, since new activity can make version history harder to "
            "read.\n\n"
            "Step 1 — Check Trash. Deleted items (not corrupted ones) go to a "
            "per-project Trash folder for 30 days before permanent deletion. Open "
            "the project, go to Trash, and restore the item — this alone resolves "
            "most 'my data disappeared' reports.\n\n"
            "Step 2 — Check Version History. Every item keeps the last 90 days of "
            "edits. Open the item, click the clock icon, and browse prior "
            "versions. You can restore any version without losing the current "
            "one — restoring creates a new version rather than overwriting.\n\n"
            "Step 3 — Check for a sync conflict. If the item looks corrupted "
            "(garbled fields, merged content) rather than missing, it may be an "
            "unresolved E409 sync conflict. Open the Conflicts tab and look for "
            "an entry referencing the item; conflicts preserve both versions so "
            "nothing is actually lost, just waiting on you to pick one.\n\n"
            "Step 4 — Request a server-side restore. If none of the above "
            "surfaces the data, we keep nightly backups for 35 days. Contact "
            "support with the item's exact name, the project it lived in, and "
            "the approximate date it was last known-good. A server-side restore "
            "pulls from the nearest nightly backup and is a manual operation "
            "performed by our team — it typically takes 1–2 business days and "
            "restores to a new, separate copy so it can never clobber current "
            "work.\n\n"
            "Step 5 — Prevent recurrence. If corruption happened during an "
            "offline editing session, enable 'Conservative Sync' in Settings > "
            "Sync, which pauses automatic merging and asks for confirmation "
            "before applying any change that would overwrite existing content."
        ),
    ),
    # -- product_support -----------------------------------------------------
    KBDocument(
        id="ps-01-export-import-data",
        title="Exporting and importing your data",
        category=Category.PRODUCT_SUPPORT,
        source_note="original — no dataset source",
        body=(
            "To export, open any project and choose Export from the ⋯ menu. "
            "CSV is best for spreadsheet tools; JSON preserves full structure "
            "(nested items, custom fields, history) and is the recommended "
            "format if you plan to re-import later or migrate between "
            "workspaces.\n\n"
            "To import, use Import from the same menu and select a file. The "
            "importer maps CSV columns to fields automatically where names "
            "match, and lets you manually map anything it can't guess. Imports "
            "always create new items rather than overwriting existing ones, so "
            "re-importing the same file twice will produce duplicates — "
            "deduplicate in your source file first if you're re-running an "
            "import.\n\n"
            "Large imports (10,000+ rows) are processed as a background job; "
            "you'll get a notification when it completes rather than a blocking "
            "progress bar."
        ),
    ),
    KBDocument(
        id="ps-02-feature-parity",
        title="Feature differences between mobile and desktop apps",
        category=Category.PRODUCT_SUPPORT,
        source_note="original — no dataset source",
        body=(
            "The mobile app covers the core workflow — viewing, editing, "
            "commenting, and light project management — but a few advanced "
            "features are desktop/web-only for now: bulk editing (selecting 50+ "
            "items at once), custom automation rules, and the admin console for "
            "managing team members and billing.\n\n"
            "Offline mode works differently by platform too: desktop caches an "
            "entire workspace for offline editing, while mobile caches only "
            "recently-viewed items to conserve storage on the device.\n\n"
            "If a feature you rely on is mobile-only-missing, it's worth "
            "checking our public roadmap before assuming it'll never arrive — "
            "several previously desktop-only features (custom fields, saved "
            "filters) shipped to mobile within the last two release cycles."
        ),
    ),
    KBDocument(
        id="ps-03-usage-limits",
        title="Understanding plan usage limits and quotas",
        category=Category.PRODUCT_SUPPORT,
        source_note="original — no dataset source",
        body=(
            "Every plan has three quotas that matter day-to-day: seats (active "
            "user accounts), storage (attachments and files, not text content), "
            "and API calls per month for integrations. You can check current "
            "usage against your limit anytime under Settings > Plan & Usage.\n\n"
            "Hitting the seat limit doesn't lock you out — it blocks adding a "
            "*new* member until you either upgrade or deactivate an existing "
            "one. Hitting the storage limit blocks new attachment uploads but "
            "never deletes existing files. Hitting the API quota returns HTTP "
            "429 responses to integrations until the monthly window resets.\n\n"
            "Usage-based add-ons (extra storage blocks, extra API quota) can be "
            "purchased independently of a full plan upgrade if you only need "
            "more of one specific resource."
        ),
    ),
    KBDocument(
        id="ps-04-keyboard-shortcuts",
        title="Using keyboard shortcuts and productivity features",
        category=Category.PRODUCT_SUPPORT,
        source_note="original — no dataset source",
        body=(
            "Press `?` anywhere in the desktop or web app to open the full "
            "shortcut cheat sheet for your current view. A few that save the "
            "most time: `g` then `i` jumps to your inbox, `c` creates a new item "
            "from anywhere, `/` opens the command palette (search for any "
            "action by name instead of hunting through menus), and `e` archives "
            "the currently selected item.\n\n"
            "Shortcuts are keyboard-layout aware and can be remapped under "
            "Settings > Keyboard if the defaults conflict with your OS or "
            "browser shortcuts.\n\n"
            "Mobile doesn't support external keyboard shortcuts yet beyond "
            "basic text-editing keys (bold/italic/undo)."
        ),
    ),
    # -- customer_service ------------------------------------------------
    KBDocument(
        id="cs-01-update-profile",
        title="Updating your account profile information",
        category=Category.CUSTOMER_SERVICE,
        source_note="bitext taxonomy: ACCOUNT/edit_account",
        body=(
            "Go to Settings > Profile to update your display name, avatar, time "
            "zone, and notification preferences. Changes to your display name "
            "and avatar apply immediately across your team's workspace; time "
            "zone changes affect how due dates and timestamps are displayed to "
            "you specifically, not to teammates.\n\n"
            "Your username (used in @mentions) can be changed once every 30 "
            "days to prevent confusion from frequent changes; old @mentions in "
            "existing comments will still resolve to your account correctly "
            "even after a username change.\n\n"
            "Profile changes don't require re-verification unless you're "
            "changing the email address on the account — see the separate "
            "article on changing your account email for that flow."
        ),
    ),
    KBDocument(
        id="cs-02-change-email",
        title="Changing the email address on your account",
        category=Category.CUSTOMER_SERVICE,
        source_note="bitext taxonomy: ACCOUNT/edit_account",
        body=(
            "Go to Settings > Account > Email, enter the new address, and "
            "confirm your current password. We send a verification link to the "
            "*new* address — the change doesn't take effect until you click "
            "it, and your old email keeps working for login until then, so "
            "you're never locked out mid-change.\n\n"
            "If your account uses single sign-on (Google, Microsoft, SSO), the "
            "login email is managed by your identity provider and can't be "
            "changed from within the app directly — update it with your "
            "workspace admin instead.\n\n"
            "For security, changing your account email triggers a "
            "notification to both the old and new address, and any active "
            "sessions on other devices are required to re-authenticate."
        ),
    ),
    KBDocument(
        id="cs-03-delete-account",
        title="How to permanently delete your account",
        category=Category.CUSTOMER_SERVICE,
        source_note="bitext taxonomy: ACCOUNT/delete_account",
        body=(
            "Account deletion is under Settings > Account > Delete Account, and "
            "requires re-entering your password as a confirmation step. "
            "Deletion is not instant: your account enters a 14-day grace period "
            "during which logging back in cancels the deletion automatically.\n\n"
            "After the grace period, your profile data and personal settings "
            "are permanently removed. Content you created in *shared* team "
            "workspaces (comments, items you authored) is not deleted — it "
            "stays visible to your former teammates, attributed to "
            "'Former Member', since removing it would break shared project "
            "history for others.\n\n"
            "If you're the sole owner of a paid workspace, you'll need to "
            "either transfer ownership or cancel the subscription before "
            "account deletion can proceed — this is a safeguard so a workspace "
            "with active teammates and billing can't be orphaned by accident."
        ),
    ),
    KBDocument(
        id="cs-04-file-complaint",
        title="Filing a complaint and what happens next",
        category=Category.CUSTOMER_SERVICE,
        source_note="bitext taxonomy: FEEDBACK/complaint",
        body=(
            "You can file a complaint through Help > Contact Support — select "
            "'Complaint' as the category so it's routed correctly rather than "
            "queued as a general question. Include what happened, when, and "
            "what outcome you're looking for; complaints with a clear desired "
            "outcome are resolved faster than open-ended ones.\n\n"
            "Every complaint gets a written acknowledgment within one business "
            "day and is reviewed by a human, never auto-closed. If it involves "
            "a billing dispute, it's routed to the billing team in parallel so "
            "you're not bounced between teams.\n\n"
            "You'll receive a follow-up with either a resolution or a concrete "
            "next step and timeline — we don't consider a complaint closed "
            "just because a first reply was sent."
        ),
    ),
    # -- it_support -----------------------------------------------------------
    KBDocument(
        id="it-01-password-reset",
        title="Resetting a forgotten password",
        category=Category.IT_SUPPORT,
        source_note="bitext taxonomy: ACCOUNT/recover_password",
        body=(
            "On the login screen, click 'Forgot password?' and enter your "
            "account email. We send a reset link that's valid for 60 minutes; "
            "after that it expires and you'll need to request a new one.\n\n"
            "If the email doesn't arrive within a few minutes, check spam, and "
            "confirm you're using the email your account is actually "
            "registered under — if you're unsure, the 'Forgot password?' flow "
            "will say 'if an account exists, a reset link was sent' rather than "
            "confirming account existence, for privacy reasons.\n\n"
            "If your account uses SSO (Google, Microsoft), there's no separate "
            "password to reset — password recovery goes through your identity "
            "provider instead, not through us."
        ),
    ),
    KBDocument(
        id="it-02-two-factor-setup",
        title="Setting up two-factor authentication (2FA)",
        category=Category.IT_SUPPORT,
        source_note="original — no dataset source",
        body=(
            "Enable 2FA under Settings > Security > Two-Factor Authentication. "
            "We support authenticator apps (TOTP — Google Authenticator, Authy, "
            "1Password, etc.) and SMS, though authenticator apps are "
            "recommended since SMS can be intercepted via SIM-swap attacks.\n\n"
            "When you enable 2FA, you're shown 10 single-use backup codes — "
            "store them somewhere safe outside the app, since they're the only "
            "way back in if you lose access to your authenticator device.\n\n"
            "Lost your device and your backup codes? Account recovery in that "
            "case requires manual identity verification by support (a photo ID "
            "check) since we can't safely disable 2FA on request alone — this "
            "is intentional and can't be expedited, as it's the main thing "
            "protecting the account from takeover."
        ),
    ),
    KBDocument(
        id="it-03-login-issues",
        title="Troubleshooting login and single sign-on (SSO) issues",
        category=Category.IT_SUPPORT,
        source_note="original — no dataset source",
        body=(
            "Login failures split into a few distinct categories, each with a "
            "different fix — start by identifying which error you're actually "
            "seeing.\n\n"
            "'Invalid credentials' on a password-based account usually means "
            "either a typo or that the account was migrated to SSO at some "
            "point (common after a company adopts Google Workspace or "
            "Microsoft Entra) — try the 'Continue with Google/Microsoft' "
            "button instead of the password form.\n\n"
            "'SSO configuration error' means the problem is on the identity "
            "provider side, not ours: the SAML/OIDC connection between your "
            "company's IdP and our platform is misconfigured or its "
            "certificate expired. This has to be fixed by your workspace "
            "admin in the IdP's admin console — support can confirm what our "
            "side is expecting (entity ID, ACS URL, certificate fingerprint) "
            "but can't fix the IdP configuration directly.\n\n"
            "'Too many redirects' / login loop typically means stale cookies "
            "from a previous SSO session are conflicting with a new one. Clear "
            "cookies for both our domain and your identity provider's domain, "
            "then try again in a private browsing window to confirm it's a "
            "cookie issue before clearing your regular browser profile.\n\n"
            "'Account not provisioned' after a successful SSO login means "
            "authentication succeeded but your identity provider hasn't been "
            "configured to auto-provision an account on first login (SCIM), or "
            "you're not in the assigned user group for this app in your IdP. "
            "This is an admin-side access grant, not something you can "
            "self-resolve — ask your workspace admin to add you to the "
            "correct group.\n\n"
            "If none of the above matches what you're seeing, capture the "
            "exact error text and a screenshot before contacting support — SSO "
            "issues are diagnosed largely from the literal error message, "
            "which varies by identity provider."
        ),
    ),
    KBDocument(
        id="it-04-api-integration",
        title="Connecting third-party integrations via API keys",
        category=Category.IT_SUPPORT,
        source_note="original — no dataset source",
        body=(
            "Generate an API key under Settings > Developer > API Keys. Keys "
            "are scoped — when creating one, choose the minimum permissions "
            "the integration actually needs (read-only vs. read-write, which "
            "projects it can access) rather than granting full account access "
            "by default.\n\n"
            "API keys are shown in full only once, at creation time; if you "
            "lose it, you can't retrieve it again and must revoke it and "
            "generate a new one. Revoking a key takes effect within seconds "
            "and immediately breaks any integration still using it, so "
            "coordinate the swap with whatever tool depends on it.\n\n"
            "If an integration is returning 401/403 errors, the two most "
            "common causes are an expired/revoked key or a key that's scoped "
            "to fewer permissions than the action requires — check the key's "
            "scope before assuming it's a bug in the integration itself."
        ),
    ),
    KBDocument(
        id="it-05-browser-compatibility",
        title="Supported browsers and compatibility issues",
        category=Category.IT_SUPPORT,
        source_note="original — no dataset source",
        body=(
            "We officially support the current and previous major versions of "
            "Chrome, Firefox, Edge, and Safari. Older browser versions may "
            "still load the app but aren't tested against, and some newer "
            "features (real-time collaboration cursors, drag-and-drop file "
            "upload) may not work correctly.\n\n"
            "If the app looks visually broken (misaligned layout, missing "
            "icons) in a supported browser, it's usually a caching issue after "
            "a recent release — a hard refresh (Ctrl/Cmd+Shift+R) resolves "
            "this in most cases by forcing fresh CSS/JS instead of cached "
            "versions.\n\n"
            "Browser extensions that block third-party cookies or scripts "
            "(some ad blockers, privacy extensions) can interfere with "
            "real-time sync specifically, since it relies on a persistent "
            "WebSocket connection — if sync is broken but the rest of the app "
            "works fine, try disabling extensions one at a time to isolate "
            "the culprit."
        ),
    ),
    # -- billing_and_payments -----------------------------------------------
    KBDocument(
        id="bp-01-update-payment-method",
        title="Updating your payment method",
        category=Category.BILLING_AND_PAYMENTS,
        source_note="bitext taxonomy: PAYMENT/check_payment_methods",
        body=(
            "Go to Settings > Billing > Payment Method to add a new card or "
            "update an existing one. The new method becomes the default for "
            "your *next* charge immediately — it does not retroactively affect "
            "an invoice that's already been issued.\n\n"
            "If you're removing your only payment method on a paid plan, "
            "you'll be prompted to add a replacement first — we don't allow a "
            "paid subscription to have zero payment methods on file, since "
            "that would guarantee a failed charge at the next billing cycle.\n\n"
            "Payment method changes are logged in your billing history for "
            "audit purposes, but the actual card number is never stored on "
            "our servers — it's tokenized directly with our payment "
            "processor."
        ),
    ),
    KBDocument(
        id="bp-02-understand-invoice",
        title="Understanding charges on your invoice",
        category=Category.BILLING_AND_PAYMENTS,
        source_note="bitext taxonomy: INVOICE/check_invoice",
        body=(
            "Every invoice is available under Settings > Billing > Invoice "
            "History as a downloadable PDF. Line items break down into base "
            "plan cost, seat charges (prorated if you added members mid-cycle), "
            "and any usage-based add-ons (extra storage, extra API quota).\n\n"
            "Mid-cycle seat additions are prorated to the number of days "
            "remaining in the current billing period, then billed in full on "
            "the following cycle — this is why adding one member mid-month "
            "sometimes shows a small, oddly-specific charge rather than a full "
            "month's seat price.\n\n"
            "If a charge doesn't match anything you recognize, check the "
            "'Usage' tab first — most disputed charges turn out to be a "
            "usage-based add-on that was consumed automatically (e.g. storage "
            "overage) rather than a billing error."
        ),
    ),
    KBDocument(
        id="bp-03-failed-payment",
        title="Troubleshooting a failed or declined payment",
        category=Category.BILLING_AND_PAYMENTS,
        source_note="bitext taxonomy: PAYMENT/payment_issue",
        body=(
            "When a charge fails, we retry automatically on a schedule (day 1, "
            "day 3, day 7 after the original attempt) before taking any action "
            "on your account, and you'll get an email after each failed "
            "attempt.\n\n"
            "Step 1 — Check the decline reason. The billing email and the "
            "Billing tab both show the reason your bank gave, when available: "
            "insufficient funds, expired card, or 'declined by issuer' (a "
            "generic bank-side block, often triggered by fraud-prevention "
            "rules on unfamiliar recurring charges).\n\n"
            "Step 2 — Fix the underlying cause. Expired card: update it under "
            "Settings > Billing > Payment Method. Insufficient funds: nothing "
            "to do on our end — ensure funds are available before the next "
            "retry. Declined by issuer: call your bank and ask them to "
            "authorize charges from us specifically; banks can often whitelist "
            "a merchant on request.\n\n"
            "Step 3 — Force an early retry. Rather than waiting for the "
            "automatic schedule, you can trigger an immediate retry from "
            "Settings > Billing > Retry Payment once you believe the "
            "underlying issue is fixed, instead of waiting up to 6 more days "
            "for the next scheduled attempt.\n\n"
            "What happens if all retries fail: after the day-7 retry fails, "
            "the account moves to a 'Payment Required' state. Paid features "
            "are paused but no data is deleted — you keep read access to "
            "everything and can restore full functionality immediately upon "
            "adding a working payment method, even after this point. Accounts "
            "in this state for more than 30 days are downgraded to the free "
            "plan automatically rather than being deleted."
        ),
    ),
    KBDocument(
        id="bp-04-cancellation-fees",
        title="Cancellation fees and how they're calculated",
        category=Category.BILLING_AND_PAYMENTS,
        source_note="bitext taxonomy: CANCEL/check_cancellation_fee",
        body=(
            "Monthly plans have no cancellation fee — canceling stops future "
            "billing immediately and you retain access through the end of the "
            "period you already paid for.\n\n"
            "Annual plans are discounted in exchange for a commitment: "
            "canceling mid-term doesn't incur a separate 'fee' as such, but "
            "the discount is forfeited on any refund calculation — a mid-year "
            "cancellation refund is calculated as (unused months × the "
            "*monthly* list price), not the discounted annual rate, since the "
            "discount was priced in assuming a full year.\n\n"
            "If you cancel and resubscribe within 30 days, your previous plan "
            "and settings are restored automatically rather than starting "
            "fresh, and any remaining prorated credit from the cancellation is "
            "applied to the new subscription."
        ),
    ),
    KBDocument(
        id="bp-05-accepted-payment-methods",
        title="Payment methods we accept",
        category=Category.BILLING_AND_PAYMENTS,
        source_note="bitext taxonomy: PAYMENT/check_payment_methods",
        body=(
            "We accept major credit and debit cards (Visa, Mastercard, Amex, "
            "Discover) for all plans. Annual plans on Team tier and above can "
            "also pay by ACH bank transfer or wire, arranged through invoicing "
            "rather than the self-serve billing page — contact sales to set "
            "this up.\n\n"
            "We don't currently support PayPal, cryptocurrency, or purchase "
            "orders on self-serve plans. Purchase orders are available for "
            "Enterprise contracts negotiated directly with sales.\n\n"
            "All card payments are processed in USD; if your card is billed "
            "in a different currency, your bank handles the conversion and "
            "may apply its own foreign transaction fee — that fee is not "
            "something we control or receive."
        ),
    ),
    # -- returns_and_exchanges (mapped from order/shipping/refund/delivery) --
    KBDocument(
        id="re-01-cancel-order",
        title="Canceling an order",
        category=Category.RETURNS_AND_EXCHANGES,
        source_note="bitext taxonomy: ORDER/cancel_order",
        body=(
            "Orders can be canceled from Order History as long as they haven't "
            "entered the 'Preparing Shipment' stage — after that point, the "
            "order is already being packed and can no longer be canceled "
            "directly, but can still be returned once delivered.\n\n"
            "Canceling before shipment triggers a full refund to your original "
            "payment method within 3–5 business days; no restocking fee "
            "applies to a pre-shipment cancellation.\n\n"
            "If you need to cancel an order that's already shipped, use the "
            "return process instead (see our refund policy article) rather "
            "than trying to cancel — refusing delivery works too but adds "
            "delay compared to accepting it and returning through the normal "
            "flow."
        ),
    ),
    KBDocument(
        id="re-02-change-order",
        title="Changing an order after it's placed",
        category=Category.RETURNS_AND_EXCHANGES,
        source_note="bitext taxonomy: ORDER/change_order",
        body=(
            "You can edit quantity, size/variant, or shipping address on an "
            "order from Order History up until it reaches 'Preparing "
            "Shipment' status — the same cutoff as cancellation, since both "
            "require the order to still be unpacked in the warehouse.\n\n"
            "Adding items isn't supported as an 'edit' — place a separate "
            "order for additional items instead, since combining orders after "
            "the fact isn't possible on our end.\n\n"
            "Once an order has shipped, no changes are possible; wait for "
            "delivery and use a return/exchange if the item needs to be "
            "different."
        ),
    ),
    KBDocument(
        id="re-03-track-order-refund",
        title="Tracking your order or refund status",
        category=Category.RETURNS_AND_EXCHANGES,
        source_note="bitext taxonomy: ORDER/track_order, REFUND/track_refund",
        body=(
            "Order tracking is under Order History > select the order > "
            "Tracking. A tracking number appears once the order ships, "
            "typically within 1–2 business days of placement, and updates "
            "from the carrier can lag a few hours behind the actual scan "
            "event.\n\n"
            "Refund tracking works the same way, under Order History > "
            "Refunds. Refund status moves through Requested → Approved → "
            "Processed. 'Processed' means we've sent it to your bank; the "
            "funds typically post within 3–5 business days after that, "
            "depending on your bank's own processing time, which is outside "
            "our control.\n\n"
            "If a refund has shown 'Processed' for more than 10 business days "
            "without appearing on your statement, contact support with the "
            "order number — at that point it's worth investigating on our "
            "side rather than continuing to wait."
        ),
    ),
    KBDocument(
        id="re-04-refund-policy",
        title="Our refund policy explained",
        category=Category.RETURNS_AND_EXCHANGES,
        source_note="bitext taxonomy: REFUND/check_refund_policy",
        body=(
            "Standard items can be returned within 30 days of delivery for a "
            "full refund, provided they're unused and in original packaging. "
            "Final-sale and clearance items are marked as such at purchase and "
            "aren't eligible for return.\n\n"
            "Refunds are issued to the original payment method only — we "
            "don't offer store credit as a substitute unless you specifically "
            "request it, in which case store credit is issued instantly "
            "rather than waiting on the payment processor.\n\n"
            "Return shipping is free for defective or incorrect items; for "
            "other returns (changed your mind, wrong size), return shipping "
            "cost is deducted from the refund unless you're on an Elite "
            "membership plan, which includes free returns on everything."
        ),
    ),
    KBDocument(
        id="re-05-shipping-address",
        title="Updating or setting up a shipping address",
        category=Category.RETURNS_AND_EXCHANGES,
        source_note="bitext taxonomy: SHIPPING/set_up_shipping_address, SHIPPING/change_shipping_address",
        body=(
            "Manage saved addresses under Account > Addresses — you can store "
            "multiple and mark one as default for future orders. Changing your "
            "default address only affects new orders, never ones already "
            "placed.\n\n"
            "To change the address on an order you've already placed, open it "
            "in Order History and choose Edit Shipping Address — available "
            "only while the order is still in 'Processing' status, the same "
            "cutoff point used for order cancellation and changes.\n\n"
            "If an order has already shipped to the wrong address, we can't "
            "redirect it in transit; contact support as soon as possible so we "
            "can flag it and arrange a reship once it's returned to the "
            "carrier's facility as undeliverable, or coordinate with you on "
            "next steps if it does get delivered to the old address."
        ),
    ),
    # -- service_outages_and_maintenance -------------------------------------
    KBDocument(
        id="so-01-check-status",
        title="Checking current service status",
        category=Category.SERVICE_OUTAGES_AND_MAINTENANCE,
        source_note="original — no dataset source",
        body=(
            "Our live status page shows real-time health for every major "
            "subsystem (web app, API, sync, notifications) independently — a "
            "degraded API doesn't necessarily mean the web app is affected "
            "too, so check the specific component you're having trouble with.\n\n"
            "You can subscribe to status updates by email, SMS, or webhook "
            "directly from the status page, which is the fastest way to learn "
            "about an incident — often faster than it being reflected inside "
            "the app itself, since in-app banners require the affected "
            "systems to be healthy enough to display them.\n\n"
            "Historical incident reports (including root-cause writeups for "
            "major incidents) are archived on the same page going back 12 "
            "months."
        ),
    ),
    KBDocument(
        id="so-02-scheduled-maintenance",
        title="Understanding scheduled maintenance windows",
        category=Category.SERVICE_OUTAGES_AND_MAINTENANCE,
        source_note="original — no dataset source",
        body=(
            "Scheduled maintenance is announced on the status page and via "
            "email to workspace admins at least 72 hours in advance for any "
            "window expected to cause visible disruption. Most maintenance is "
            "'zero-downtime' — rolling updates behind a load balancer — and "
            "isn't announced at all because it's not user-visible.\n\n"
            "When a maintenance window *is* expected to cause disruption "
            "(e.g. a database migration), the app shows a banner starting 30 "
            "minutes before the window begins, and read access is typically "
            "preserved even when write access is briefly paused.\n\n"
            "Maintenance windows are scheduled during low-traffic hours based "
            "on aggregate usage patterns, not any single region's business "
            "hours, so the exact timing may not be convenient for every "
            "customer globally — this is a tradeoff of running one shared "
            "infrastructure."
        ),
    ),
    KBDocument(
        id="so-03-during-outage",
        title="What to do during an active outage",
        category=Category.SERVICE_OUTAGES_AND_MAINTENANCE,
        source_note="original — no dataset source",
        body=(
            "First, confirm it's a real outage rather than a local issue by "
            "checking the status page — if it shows all systems operational, "
            "the problem is more likely local (see the article on slow "
            "performance or connectivity troubleshooting) than a broader "
            "outage.\n\n"
            "If the status page confirms an incident, you don't need to open a "
            "support ticket just to report it — our team is already aware and "
            "working it, and a flood of duplicate reports slows down "
            "resolution rather than helping. Subscribe to the incident for "
            "updates instead.\n\n"
            "Desktop and mobile apps continue to work offline in read-only "
            "mode during most outages, queuing any edits locally to sync "
            "automatically once service is restored — so it's generally safe "
            "to keep working locally rather than waiting."
        ),
    ),
    # -- sales_and_pre_sales --------------------------------------------------
    KBDocument(
        id="sp-01-plan-comparison",
        title="Comparing plans and pricing tiers",
        category=Category.SALES_AND_PRE_SALES,
        source_note="original — no dataset source",
        body=(
            "Free covers individuals and very small teams: unlimited items, "
            "up to 3 seats, and core features with a reduced storage quota. "
            "Team adds unlimited seats, automation rules, and priority "
            "support, billed per seat monthly or annually (annual saves "
            "~20%). Business adds admin controls, SSO, and audit logs on top "
            "of everything in Team. Enterprise is custom-priced and adds "
            "dedicated support, custom contracts, and advanced compliance "
            "features (SCIM provisioning, data residency options).\n\n"
            "There's no feature-limited trial gate on Team or Business — "
            "every paid tier includes a 14-day full-featured trial, no credit "
            "card required to start.\n\n"
            "If you're unsure which tier fits, the honest signal is whether "
            "you need SSO/admin controls (go Business) or not (Team is "
            "usually sufficient) — seat count alone rarely determines the "
            "right tier."
        ),
    ),
    KBDocument(
        id="sp-02-place-new-order",
        title="Placing a new order or upgrading your plan",
        category=Category.SALES_AND_PRE_SALES,
        source_note="bitext taxonomy: ORDER/place_order",
        body=(
            "To start or upgrade a subscription, go to Settings > Billing > "
            "Change Plan, pick a tier and billing cycle, and confirm — the "
            "change and any prorated charge apply immediately, and premium "
            "features unlock right away without waiting for the next billing "
            "cycle.\n\n"
            "Downgrades are scheduled for the *end* of the current billing "
            "period rather than applying immediately, so you don't lose "
            "access to something you already paid for.\n\n"
            "For a merchandise/product order rather than a subscription "
            "change, use the storefront checkout directly — subscription "
            "billing and storefront orders are separate systems with "
            "separate order histories, which is why an order confirmation "
            "email and a subscription receipt look different."
        ),
    ),
    KBDocument(
        id="sp-03-request-demo-trial",
        title="Requesting a demo or extending your trial",
        category=Category.SALES_AND_PRE_SALES,
        source_note="original — no dataset source",
        body=(
            "Book a live demo with sales from the pricing page — demos are "
            "tailored to your use case if you share it in the request form, "
            "rather than being a fixed generic walkthrough.\n\n"
            "Standard trials run 14 days from signup. If you need more time "
            "(common for larger teams still gathering stakeholder feedback), "
            "a one-time 14-day extension can be requested from within the app "
            "banner shown during the last 3 days of your trial, or by asking "
            "sales directly — no reason needs to be given, this is granted "
            "automatically on request, once.\n\n"
            "Trial data isn't deleted when a trial ends without converting to "
            "paid — it's preserved for 30 days in a read-only state, so "
            "subscribing later restores full access to everything you set up "
            "during the trial."
        ),
    ),
    # -- human_resources --------------------------------------------------
    KBDocument(
        id="hr-01-application-status",
        title="Checking your job application status",
        category=Category.HUMAN_RESOURCES,
        source_note="original — no dataset source",
        body=(
            "You can check your application status anytime in the candidate "
            "portal using the link sent in your application confirmation "
            "email — status moves through Received → Under Review → "
            "Interview → Decision.\n\n"
            "We aim to move every application to at least 'Under Review' "
            "within 10 business days of submission. If your status hasn't "
            "changed after that window, it's fine to check in via the portal's "
            "message feature rather than assuming you weren't considered.\n\n"
            "We don't provide individualized feedback for candidates not "
            "moving forward before the final interview stage, due to volume — "
            "this isn't a reflection of application quality specifically."
        ),
    ),
    KBDocument(
        id="hr-02-referral-program",
        title="How the employee referral program works",
        category=Category.HUMAN_RESOURCES,
        source_note="original — no dataset source",
        body=(
            "Current employees can refer candidates through the internal "
            "referral portal, linked from the HR home page. A referral bonus "
            "is paid out only after the referred candidate is hired *and* "
            "completes 90 days of employment — not at the offer-acceptance "
            "stage — to align the incentive with successful, lasting hires "
            "rather than just placements.\n\n"
            "You can refer for any open role, not just ones on your own team, "
            "and there's no limit on the number of referrals per employee "
            "per year.\n\n"
            "If a referred candidate is already in our pipeline from another "
            "source (e.g. they applied directly before you referred them), "
            "the referral bonus isn't paid, since the referral wasn't what "
            "brought them in — first-touch is what counts, tracked "
            "automatically by the portal."
        ),
    ),
    KBDocument(
        id="hr-03-timesheet-pto",
        title="Submitting timesheets and requesting PTO",
        category=Category.HUMAN_RESOURCES,
        source_note="original — no dataset source",
        body=(
            "Timesheets are submitted weekly through the HR portal and are "
            "due by end of day Monday for the prior week — late submissions "
            "still process but can delay that pay cycle's payroll run for "
            "hourly employees specifically (salaried employees aren't "
            "affected by timesheet timing).\n\n"
            "PTO requests go through the same portal under Time Off > "
            "Request. Requests route to your manager for approval "
            "automatically; there's no fixed advance-notice requirement, but "
            "requests submitted less than 2 weeks ahead may take longer to "
            "approve simply because of typical manager response time, not any "
            "policy penalty.\n\n"
            "Unused PTO carryover rules vary by country/region due to local "
            "labor law — check the region-specific policy doc linked from "
            "your portal rather than assuming the general policy applies "
            "everywhere."
        ),
    ),
    # -- general_inquiry --------------------------------------------------
    KBDocument(
        id="gi-01-contact-support",
        title="How to contact support",
        category=Category.GENERAL_INQUIRY,
        source_note="bitext taxonomy: CONTACT/contact_customer_service, CONTACT/contact_human_agent",
        body=(
            "The fastest way to reach us is Help > Contact Support inside the "
            "app, which routes your message with account context already "
            "attached (plan, recent activity) so you don't have to re-explain "
            "your setup.\n\n"
            "For general questions, our self-serve help center often has a "
            "faster answer than waiting for a reply — search it first from "
            "the same Help menu.\n\n"
            "If you specifically need a human rather than starting with our "
            "help-center search or automated triage, say so directly in your "
            "message ('I'd like to speak with a person') and your ticket "
            "skips automated suggestions and routes straight to the queue for "
            "a support agent."
        ),
    ),
    KBDocument(
        id="gi-02-newsletter-preferences",
        title="Managing newsletter and email preferences",
        category=Category.GENERAL_INQUIRY,
        source_note="bitext taxonomy: SUBSCRIPTION/newsletter_subscription",
        body=(
            "Manage what you receive under Settings > Notifications > Email "
            "Preferences — product updates, the monthly newsletter, and "
            "transactional emails (receipts, security alerts) are controlled "
            "independently, so unsubscribing from the newsletter doesn't "
            "affect billing receipts or security notifications, which can't "
            "be disabled.\n\n"
            "Every marketing email also has an unsubscribe link at the "
            "bottom that takes effect immediately, without needing to log in "
            "— useful if you want to unsubscribe from an address you no "
            "longer have app access to.\n\n"
            "Re-subscribing after opting out takes effect on the next send "
            "cycle, not retroactively — you won't receive editions that went "
            "out while you were unsubscribed."
        ),
    ),
    KBDocument(
        id="gi-03-leave-feedback",
        title="Leaving feedback or a product review",
        category=Category.GENERAL_INQUIRY,
        source_note="bitext taxonomy: FEEDBACK/review",
        body=(
            "Product feedback and feature requests go through Help > Give "
            "Feedback, which feeds directly into our product team's backlog — "
            "distinct from a support ticket, so use this path rather than "
            "Contact Support if you're not reporting a problem.\n\n"
            "We can't reply individually to every piece of feedback given "
            "volume, but popular requests are aggregated and influence the "
            "public roadmap; you can see if your idea already exists and "
            "upvote it instead of submitting a duplicate.\n\n"
            "If you'd like to leave a public review (app store, review "
            "sites), that's entirely separate from in-app feedback and "
            "doesn't reach our product team directly — it's still valuable "
            "for prospective customers, just not the fastest path to a "
            "feature getting built."
        ),
    ),
]
