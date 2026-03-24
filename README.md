# 🇰🇪 Bunge Mkononi (Parliament in Your Pocket)
Bunge Mkononi is a civic-tech platform designed to bridge the gap between the Kenyan Parliament and its citizens. It provides real-time tracking of bills, member accountability, and regional impact data, with a heavy focus on digital inclusion through Africa's Talking SMS and USSD integration.
## 🚀 Key Features
1. Citizen DashboardLive Bill Tracking: A visual timeline showing the progress of bills from First Reading to Presidential Assent.Member Tracker: A transparency tool showing how specific MPs voted on key legislation.Participation Hub: A "Live Opinion Poll" allowing citizens to vote "Support" or "Oppose" on active bills.Regional Impact Map: Data visualization showing sentiment across different counties.
2. Admin Command Center (Protected)Secure Access: Guarded by a dedicated authentication layer (AdminGuard).Legislative Management: Admins can transition bills through different stages.AT SMS Broadcaster: A one-click button to trigger mass SMS alerts to thousands of subscribers via Africa's Talking API.System Logs: Real-time monitoring of USSD hits and SMS dispatch status.
3. Inclusive Offline Access (Africa's Talking)USSD (384100#): Allows users without smartphones to vote and check bill status.SMS (22334): Users can send keywords like TRACK [BillID] to receive automated status updates.🛠️ Frontend Technical StackFramework: Next.js 14+ (App Router)Styling: Tailwind CSS (Mobile-first, dark/light theme separation)Icons: Lucide ReactState Management: React Hooks (useState, useEffect)Animations: Framer Motion / CSS Transitions
### 📂 Project Structure (Frontend)
├── app/
│   ├── (public)/          # Public-facing citizen pages
│   │   ├── layout.tsx     # Citizen navigation & footer
│   │   └── page.tsx       # Main dashboard feed
│   └── (admin)/           # Management protected routes
│       ├── layout.tsx     # AdminGuard wrapper & admin sidebar
│       └── admin/
│           └── page.tsx   # SMS Broadcaster & Bill Management
├── components/            # Reusable UI Blocks
│   ├── BillCard.tsx       # Individual bill preview
│   ├── BillTimeline.tsx   # Progress tracking visualizer
│   ├── MemberTracker.tsx  # Table of MP votes
│   └── AdminGuard.tsx     # Password-protected route wrapper
└── types/
    └── index.ts           # Shared TypeScript interfaces (Bill, MP, Petition)
### 🔌 Integration Points
 (For Backend Devs)The frontend is currently built with Mock Data and is ready for API integration.FeatureBackend ExpectationAT IntegrationVotingPOST /api/votesUpdates signatureCountStatus ChangePATCH /api/bills/:idTriggers AT SMS to subscribersTrackingPOST /api/trackSubscribes phone number to updatesUSSD MenuCallback URLHandles *384*100# session logic
 ### 🛠️ Installation & SetupClone the repo
 :Bashgit clone https://github.com/your-username/bunge-mkononi.git
### Install dependencies:Bashnpm install
Run the development server:npm run dev
Access Admin Panel:Navigate to /admin and enter the key: bunge2026