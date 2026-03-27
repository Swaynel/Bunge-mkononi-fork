# Bunge Mkononi (Parliament in Your Pocket)

Bunge Mkononi is a civic-tech platform for tracking Kenyan legislation across web, SMS, and USSD. Citizens can follow bills, review summaries, vote, and subscribe to updates even on basic phones, while admins can manage legislative data, trigger scrapes, and monitor messaging delivery.

## Key Features

- Citizen dashboard with live bill tracking, bill summaries, petition progress, county sentiment, and representative vote visibility.
- Admin command center for bill status changes, scrape jobs, manual SMS broadcasts, and operational monitoring.
- Offline participation through Africa's Talking SMS and USSD for subscriptions, voting, petition support, and bill lookups.
- Messaging audit trail with queued outbound messages, webhook receipts, delivery reports, and admin metrics.

## Installation and Setup

### Frontend

```bash
git clone https://github.com/ANNGLORIOUS/Bunge-mkononi.git
cd Bunge-mkononi
npm install
npm run dev
```

Access the admin UI at `/admin` and sign in with a Django admin or staff account for protected actions.

## Django Backend

The repo includes a Django REST API in `backend/` backed by SQL storage. PostgreSQL is the default database for local development, and you can override the `DJANGO_DB_*` variables in `backend/.env.example` if needed.

The backend also includes a Render Blueprint at `render.yaml` so you can provision the API and a matching Postgres database from the same repo.

### Backend Quick Start

1. `cd backend`
2. Make sure PostgreSQL is running and create the database once:

   ```bash
   createdb bunge_mkononi
   ```

3. `python3 -m venv .venv`
4. `source .venv/bin/activate`
5. `pip install -r requirements.txt`
6. `python manage.py migrate`
7. `python manage.py scrape_bills`
8. `python manage.py runserver 8000`

If the scraper returns no bills on your first run, the site will stay empty until Parliament data is available.

### Bill Document Processing

Bill detail pages prefer structured text over a raw PDF iframe.

The backend pipeline:

- downloads the bill PDF from the same Parliament source that the UI proxy serves
- extracts text with `pdftotext` when the PDF already contains a text layer
- falls back to local OCR for image-based PDFs when OCRmyPDF and its host dependencies are available
- stores the extracted text and page structure on the `Bill` record

Optional env vars:

- `PDF_TEXT_MIN_WORDS` to tune when a PDF should be considered text-readable

For image-only PDFs, install OCRmyPDF and its local OCR dependencies on the backend host.

Backfill existing bills with:

```bash
cd backend
python manage.py process_bill_documents
```

## Frontend to Backend Wiring

The frontend reads live data from the Django API.

### Frontend Env

Set this in a root `.env.local` for local development. In production, the frontend falls back to the Render backend URL if the variable is not set.

```bash
# Local development
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api

# Vercel production
NEXT_PUBLIC_API_BASE_URL=https://bunge-mkononi.onrender.com/api
```

### Live Endpoints Used by the UI

- `GET /api/dashboard/`
- `GET /api/bills/`
- `GET /api/bills/<id>/`
- `GET /api/representatives/?billId=<id>`
- `GET /api/counties/?billId=<id>`
- `GET /api/bills/<id>/votes/`
- `GET /api/bills/<id>/votes/summary/`
- `POST /api/votes/`
- `POST /api/bills/<id>/broadcast/`
- `POST /api/scrape/`
- `GET /api/scrape/history/`

### Render Deploy

1. Push the repo to GitHub, then create a new Render Blueprint from `render.yaml`.
2. Render will create the backend service plus a Postgres database.
3. The app bootstraps migrations and static file collection on Render startup, so even a manually created service with the default Gunicorn start command can come up cleanly.
4. The backend is already configured to trust `https://bunge-mkononi.vercel.app` for CORS and CSRF, but you can override `DJANGO_FRONTEND_ORIGIN` if the UI ever moves.

Render's free Postgres plan expires after 30 days, so upgrade the database if you want to keep data long term.

## Africa's Talking Messaging

Set these in `backend/.env` or your shell before using messaging features:

- `AFRICASTALKING_USERNAME`
- `AFRICASTALKING_API_KEY`
- `AFRICASTALKING_SHORT_CODE`
- `AFRICASTALKING_SMS_TIMEOUT`

### SMS Features

Inbound SMS supports bill lookups, subscriptions, watchlists, and self-service account controls.

Supported commands:

- `HELP` returns the command menu.
- `TRACK <bill id or bill title>` subscribes the number to a bill and returns its latest status summary.
- `TRACK CATEGORY <category>` creates a category watchlist.
- `TRACK COUNTY <county>` creates a county watchlist.
- `TRACK SPONSOR <sponsor>` creates a sponsor watchlist.
- `TRACK ALL` subscribes the number to all-bills updates.
- `STATUS <bill id or bill title>` returns the latest bill status without creating a subscription.
- `SUMMARY <bill id or bill title>` returns a short bill brief.
- `DOCUMENT <bill id or bill title>` returns the structured bill summary.
- `SEARCH <term>` finds matching bills.
- `IMPACT <bill id or bill title>` returns county impact information.
- `TIMELINE <bill id or bill title>` returns the legislative timeline.
- `VOTES <bill id or bill title>` returns representative vote totals.
- `SIGN <bill id or bill title>` records support for the linked petition flow.
- `LIST` shows the caller's active and paused subscriptions.
- `LANG EN` or `LANG SW` switches between English and Kiswahili.
- `PAUSE [subscription reference]`, `RESUME [subscription reference]`, and `STOP [subscription reference]` manage one or more existing subscriptions.

Messaging behavior:

- Broadcast SMS uses the bill's current status by default when no custom message is supplied.
- Bill status changes automatically queue outbound alerts for matching instant and milestone subscribers, whether the change came from the admin UI or the scraper.
- Inbound SMS processing is idempotent, so duplicate webhook deliveries reuse the stored response instead of creating duplicate side effects.
- Inbound SMS replies are sent back out as audited `reply` outbound messages using the inbound `linkId` and your shortcode configuration.
- USSD-created subscriptions queue a confirmation SMS automatically.

### USSD Features

Configure your Africa's Talking USSD menu to post to `POST /api/ussd/`.

The current menu flow supports:

- `1` active bills via an SMS handoff that keeps the USSD session short
- `2` featured bill details delivered over SMS with follow-up command hints
- `3` watchlists
- `4` voting on the featured bill
- `5` help
- `6` language switching
- `7` my subscriptions
- `0` exit or return to the main menu

The watchlist flow supports:

- following a specific bill
- following a bill category
- following a county
- following a sponsor
- following all bills
- managing existing subscriptions from the same menu

Bill detail menus keep quick actions in USSD and move longer bill content into SMS follow-ups for:

- subscribe
- vote
- summary
- key points
- timeline
- county impact
- petition support

Long bill titles are shortened automatically so paginated bill lists fit on USSD screens.

### Webhooks and Delivery Tracking

Configure these callback URLs in Africa's Talking:

- Inbound SMS callback: `POST /api/sms/inbound/`
- Delivery report callback: `POST /api/sms/delivery/`
- USSD callback: `POST /api/ussd/`

Messaging is audited through:

- `OutboundMessage` records for queued, sent, failed, and skipped messages
- `WebhookReceipt` records for idempotent SMS inbound, delivery report, and USSD processing
- `SystemLog` entries for subscriptions, votes, broadcasts, delivery reports, consent changes, digests, and webhook activity
- `GET /api/admin/metrics/` for callback URLs, subscription counts, delivery buckets, outbound queue health, and recent webhook receipts
- `GET /api/outbound-messages/` and `GET /api/webhook-receipts/` for admin auditing

### Queueing and Digest Jobs

The messaging pipeline stores outbound work in the database before delivery, which makes retries and metrics easier to manage.

- `python manage.py dispatch_outbound_messages --limit 50` dispatches queued outbound SMS records.
- `python manage.py send_legislative_digests --limit 50` generates due daily and weekly digests, then attempts to dispatch queued messages.

Subscriptions support:

- channel tracking for `sms` and `ussd`
- scope targeting for bill, category, county, sponsor, and all-bills watchlists
- language preferences in English and Kiswahili
- cadence values including instant, daily, weekly, and milestone
- active, paused, and unsubscribed states

## API Surface

Public endpoints:

- `GET /api/health/`
- `GET /api/dashboard/`
- `GET /api/bills/`
- `GET /api/bills/<id>/`
- `GET /api/representatives/`
- `GET /api/counties/`
- `GET /api/bills/<bill_id>/votes/`
- `GET /api/bills/<bill_id>/votes/summary/`
- `POST /api/votes/`
- `POST /api/track/`
- `POST /api/subscriptions/`
- `POST /api/sms/inbound/`
- `POST /api/sms/delivery/`
- `POST /api/ussd/`

Admin and staff endpoints:

- `POST /api/bills/<id>/broadcast/`
- `POST /api/scrape/`
- `GET /api/scrape/history/`
- `POST /api/scrape/representatives/`
- `POST /api/scrape/votes/`
- `GET /api/admin/metrics/`
- `GET /api/logs/`
- `GET /api/subscriptions/`
- `GET /api/outbound-messages/`
- `GET /api/webhook-receipts/`

## Data Model

- `Bill`, `Petition`, `Representative`, `RepresentativeVote`
- `CountyStat`, `PollResponse`
- `Subscription` with channel, scope, language, cadence, status, and consent metadata
- `OutboundMessage`, `WebhookReceipt`, `SystemLog`
