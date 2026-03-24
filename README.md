# 🇰🇪 Bunge Mkononi (Parliament in Your Pocket)
Bunge Mkononi is a civic-tech platform designed to bridge the gap between the Kenyan Parliament and its citizens. It provides real-time tracking of bills, member accountability, and regional impact data, with a heavy focus on digital inclusion through Africa's Talking SMS and USSD integration.

## 🚀 Key Features
1. Citizen DashboardLive Bill Tracking: A visual timeline showing the progress of bills from First Reading to Presidential Assent.Member Tracker: A transparency tool showing how specific MPs voted on key legislation.Participation Hub: A "Live Opinion Poll" allowing citizens to vote "Support" or "Oppose" on active bills.Regional Impact Map: Data visualization showing sentiment across different counties.
2. Admin Command Center (Protected)Secure Access: Guarded by a dedicated authentication layer (AdminGuard).Legislative Management: Admins can transition bills through different stages.AT SMS Broadcaster: A one-click button to trigger mass SMS alerts to thousands of subscribers via Africa's Talking API.System Logs: Real-time monitoring of USSD hits and SMS dispatch status.
3. Inclusive Offline Access (Africa's Talking)USSD (*384*16250#): Allows users without smartphones to vote and check bill status.SMS (22334): Users can send keywords like TRACK [BillID] to receive automated status updates.🛠️ Frontend Technical StackFramework: Next.js 14+ (App Router)Styling: Tailwind CSS (Mobile-first, dark/light theme separation)Icons: Lucide ReactState Management: React Hooks (useState, useEffect)Animations: Framer Motion / CSS Transitions


### 🔌 Integration Points
The frontend now reads live data from the Django API and uses the scraper for bill population.

### 🛠️ Installation & SetupClone the repo
Git clone https://[github.com/your-username/bunge-mkononi.git](https://github.com/ANNGLORIOUS/Bunge-mkononi)

### Install dependencies:Bashnpm install
Run the development server:npm run dev
Access Admin Panel:Navigate to /admin and sign in with a Django admin account for protected actions.

## 🐍 Django Backend
The repo now includes a Django REST API in `backend/` backed by SQL storage. PostgreSQL is the default database for local development, and you can override the `DJANGO_DB_*` variables in `backend/.env.example` if needed.

The backend also includes a Render Blueprint at `render.yaml` so you can provision the API and a matching Postgres database from the same repo.

## 🌐 Frontend to Backend Wiring
The Next.js frontend now reads live data from the Django API.

### Frontend env
Set this in a root `.env.local` for local development. In production, the frontend falls back to the Render backend URL if the variable is not set.
```bash
# Local development
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api

# Vercel production
NEXT_PUBLIC_API_BASE_URL=https://bunge-mkononi.onrender.com/api
```

### Live endpoints used by the UI
- `GET /api/dashboard/`
- `GET /api/bills/`
- `GET /api/bills/<id>/`
- `GET /api/representatives/?bill=<id>`
- `GET /api/counties/?bill=<id>`
- `POST /api/votes/`
- `POST /api/bills/<id>/broadcast/`
- `POST /api/scrape/`
- `GET /api/scrape/history/`

### Quick start
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

If the scraper returns no bills on your first run, the site will simply stay empty until parliament data is available.

### Render deploy
1. Push the repo to GitHub, then create a new Render Blueprint from `render.yaml`.
2. Render will create the backend service plus a Postgres database.
3. The app bootstraps migrations and static file collection on Render startup, so even a manually created service with the default Gunicorn start command can come up cleanly.
4. The backend is already configured to trust `https://bunge-mkononi.vercel.app` for CORS and CSRF, but you can override `DJANGO_FRONTEND_ORIGIN` if the UI ever moves.

Render's free Postgres plan expires after 30 days, so upgrade the database if you want to keep data long term.

### Africa's Talking SMS
Set these in `backend/.env` or your shell before using the admin broadcast button:
- `AFRICASTALKING_USERNAME`
- `AFRICASTALKING_API_KEY`
- `AFRICASTALKING_SENDER_ID`
- `AFRICASTALKING_SMS_TIMEOUT`

### Africa's Talking webhooks
Configure these callback URLs in Africa's Talking:
- Inbound SMS callback: `POST /api/sms/inbound/`
- Delivery report callback: `POST /api/sms/delivery/`
- USSD callback: `POST /api/ussd/`

The admin metrics page for these webhooks lives at `/admin/metrics`.
Inbound SMS subscribers can text `TRACK <bill id or bill title>` to the shortcode you configure on the Africa's Talking side.

### API surface
- `GET /api/health/`
- `GET /api/dashboard/`
- `GET /api/bills/`
- `GET /api/representatives/?billId=1`
- `POST /api/votes/`
- `POST /api/track/`
- `POST /api/sms/inbound/`
- `POST /api/sms/delivery/`
- `POST /api/ussd/`
- `POST /api/bills/<id>/broadcast/`

### Data model
- `Bill`, `Petition`, `Representative`, `RepresentativeVote`
- `CountyStat`, `PollResponse`, `Subscription`, `SystemLog`
