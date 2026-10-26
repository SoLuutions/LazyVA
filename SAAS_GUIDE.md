# LazyVA — SaaS Business, Monetization & Windows Deployment Guide

This guide details how to turn **LazyVA** into a profitable, compliant, and scalable software product, especially targeting Virtual Assistants and remote workers in the Philippines and worldwide.

---

## 1. Product Positioning: Avoiding Bans & Antivirus Flags

### ⚠️ The Golden Rule of Keep-Awake Software
**Do not market LazyVA as an "employer monitoring evasion tool" or "activity tracker bypass."**

| ❌ Dangerous Positioning (High Risk) | ✅ Commercial Positioning (Approved) |
|---|---|
| "Cheat Time Doctor / Hubstaff" | "Intelligent Workspace Keep-Awake Assistant" |
| "Stealth Activity Simulator" | "Continuous Display & Session Active Utility" |
| "Fake Work Generator" | "Smart Pomodoro & Presentation Companion" |

### Why this matters:
1. **Payment Gateways (PayMongo, Stripe, Lemon Squeezy)**: Explicitly prohibit deceptive software or tools designed to breach employment contracts. If flagged, accounts are banned and funds frozen.
2. **Antivirus & Windows Defender**: Tools that label themselves as stealth process hooks or keyloggers get flagged as PUP (Potentially Unwanted Programs). LazyVA uses clean Windows API calls (`SetThreadExecutionState`, `SetCursorPos`), safe hotkeys, and genuine UI dialogs, keeping false-positive rates low.

---

## 2. Solving Payments in the Philippines (Without GCash Business)

If you don't have a GCash Business merchant account, here are your best three options:

### Option A: Manual GCash / Maya (Zero Setup Cost — Best for Early Sales)
1. **How it works**:
   - Customer pays directly to your Personal GCash or Maya QR / mobile number.
   - They submit their email and proof of payment on your landing page or via chat.
   - You generate a license key in 5 seconds using LazyVA's built-in Admin API:
     ```bash
     curl -X POST https://your-api.lazyva.app/api/v1/admin/generate-license \
       -H "x-admin-secret: YOUR_ADMIN_SECRET" \
       -H "Content-Type: application/json" \
       -d '{"email": "buyer@example.com", "plan": "lifetime", "max_activations": 2}'
     ```
   - Send the generated key (e.g. `LVA-LIFE-98X21-A89BC-44F21`) to their email.
2. **Pros**: Zero fees, starts immediately, no business registration required.
3. **Cons**: Manual labor per sale; personal GCash accounts have monthly transaction limits.

---

### Option B: PayMongo (Automated GCash, Maya & Card Checkout)
PayMongo is the standard Philippine payment gateway. It allows automated checkouts where buyers pay via GCash, Maya, GrabPay, or credit cards.
1. **Requirements**: A DTI Business Registration certificate (Sole Proprietorship). You can register online at [bnrs.dti.gov.ph](https://bnrs.dti.gov.ph) for ~₱230 within 30 minutes.
2. **Integration Flow**:
   - Customer clicks "Buy LazyVA" on your website.
   - PayMongo Checkout handles GCash / Maya payment.
   - PayMongo sends a webhook to `https://your-api.lazyva.app/api/v1/webhooks/paymongo`.
   - Your LazyVA server automatically generates a license key and emails it to the buyer.

---

### Option C: Merchant of Record (Lemon Squeezy, Polar, or Gumroad)
If you want to sell internationally (US, UK, Australia, global freelancers):
- Platforms like **Lemon Squeezy** or **Polar** act as the Merchant of Record.
- They handle global sales tax, VAT, card payments, Apple Pay, PayPal, and invoice delivery.
- Payouts are sent to your Philippine bank account, Wise, or PayPal.
- Built-in webhook in `server/main.py` (`POST /api/v1/webhooks/lemonsqueezy`) handles instant license provisioning.

---

## 3. Recommended Pricing Strategy

For Philippine Virtual Assistants:
- **Price Sensitivity**: Philippine freelancers prefer a low one-time price over recurring monthly commitments.
- **Recommended Model**:
  - **Free Tier**: 7-day trial with standard keep-awake and micro-jitter.
  - **Pro Lifetime License**: **₱499 PHP** (or **$14.99 USD** internationally).
    - Unlocks Cubic Bezier natural curves.
    - Unlocks Smart Pomodoro breaks with automated rest reminders.
    - Allows activation on up to **2 PCs** (laptop + desktop).
    - Lifetime software updates included.

---

## 4. Deploying the Backend Licensing Server

You can deploy `server/main.py` for free or low cost on:
- **Railway.app** or **Render.com** (Python FastAPI service)
- **Supabase** (run `server/schema.sql` to setup customer and activation tables)

### Environment Variables:
```env
LAZYVA_SECRET_KEY=your_secure_custom_secret_key_here
PAYMONGO_WEBHOOK_SECRET=whsec_your_paymongo_secret
LEMONSQUEEZY_WEBHOOK_SECRET=your_lemonsqueezy_secret
DATABASE_PATH=lazyva_saas.db
```

---

## 5. Compiling & Distributing the Windows Installer

### Step 1: Build the Executable
On your Windows machine, run:
```cmd
python packaging\build_exe.py
```
This generates a standalone, console-less folder at `dist\LazyVA\`.

### Step 2: Build the Inno Setup Installer
Open `packaging\LazyVA_Setup.iss` in **Inno Setup 6** and press **Compile**.  
This creates `dist\LazyVA_Setup_v1.0.0.exe`.

### Step 3: Code Signing (Eliminating Windows SmartScreen Warnings)
When users download an unsigned `.exe` from the web, Windows SmartScreen shows a blue warning ("Windows protected your PC").

**Options to sign your app:**
1. **Azure Trusted Signing** (~$10/month, Microsoft's official cloud signing service).
2. **Sectigo / DigiCert Standard Code Signing Certificate** (~$200/year).
3. **Bootstrap Phase (Unsigned)**:
   - Provide clear instructions on your website: *"Click 'More Info' -> 'Run Anyway' on first install."*
   - As your app builds reputation with Microsoft Defender SmartScreen, the warning disappears automatically after several hundred installs.

---

## 6. Launch Checklist

- [x] Test LazyVA desktop client locally (`python run.py`).
- [x] Verify Bezier curve trajectories and keep-awake power state.
- [x] Build standalone executable using `packaging\build_exe.py`.
- [x] Compile Inno Setup installer (`LazyVA_Setup_v1.0.0.exe`).
- [x] Deploy FastAPI server to Railway or Render.
- [x] Test license activation endpoint with sample HWID.
- [x] Configure payment gateway webhook (PayMongo or Lemon Squeezy).
- [x] Prepare marketing landing page showcasing features, screenshots, and ₱499 checkout.
