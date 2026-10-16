# NumeroMaster AI

Mobile-first numerology reflection studio operated under the business name **Kiran Software Solutions** (product creator: Kiran Kumar).

## Included
- Pythagorean and Chaldean name-number calculations and alternate spelling comparison.
- Moolank, Bhagyank, traditional Navagraha associations and Lo Shu grid.
- Mobile digit analysis and up to 10 candidate comparisons.
- Vehicle registration digit reflection.
- Personal focus/remedy planner and gemstone/stone-bracelet ideas with budget and authenticity cautions.
- Premium report with number themes, strengths, reflection prompts, practical 30-day plan, spelling/mobile comparisons, vehicle analysis and stone-bracelet guide.
- Print / Save PDF.
- Server-side Razorpay order creation, signature verification, captured-payment check, amount/currency check and report-input hash binding.

## Deploy
- Node.js 20+
- Build command: `npm test`
- Start command: `npm start`
- Set `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` in the Render service environment to enable checkout. UPI is intended to be available through Razorpay Checkout when enabled for the merchant account; test with Razorpay test credentials before any live launch.
- Set `OPENAI_API_KEY` only if optional AI reflection is desired. Never commit secrets.
- Checkout is intentionally unavailable when Razorpay credentials are absent.

## Commercial launch checklist
- Verify Razorpay account, test-mode payment flow, live-mode flow, settlement and refund/cancellation process.
- Publish the no-refund/no-cancellation policy in Terms, with a clear statement that mandatory consumer rights and payment-provider/statutory requirements still apply. Add verified support contact, applicable business address/jurisdiction and refund-failure support process before accepting live payments.
- Test report generation and PDF output on Android and desktop.
- This version has no customer accounts, report history, or durable user dashboard. A paid report is generated for the current purchase and unlocked in the current browser session.
- Render Free may spin down after inactivity.

## Important
Numerology and gemstone meanings are traditional cultural/spiritual interpretations, not scientifically validated predictors. They do not guarantee wealth, health, luck or relationship outcomes and must not replace professional medical, legal or financial advice. Never enter PINs, passwords or OTPs.
