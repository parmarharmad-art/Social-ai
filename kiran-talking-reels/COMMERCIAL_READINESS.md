# Kiran Kumar AI Reels Studio — Commercial Readiness

## Product status
The current application renders a vertical MP4 from a still photo and voiceover, adds a brand watermark and subtitles, and now offers an optional real mouth lip-sync path through the public free MuseTalk ZeroGPU Space. This is not a guaranteed always-on service: public queue/quota availability can vary, and each generation must be tested. It does not provide blinking/head motion beyond what the model produces, generated B-roll, account login, subscription billing, Instagram auto-publishing, analytics, or a customer admin panel.

## Safe initial offer
Until the missing integrations are built and tested, sell only as a **limited early-access / assisted service**, not as a finished self-service SaaS:
- Be explicit that the output is a photo animation/narration effect, not a talking avatar.
- Provide a sample video made with permission from the person pictured.
- State supported input types and practical file-size limits.
- Give a clear refund/support policy and response window.
- Never promise virality, follower growth, perfect Hindi pronunciation, or 100% uptime.
- Do not accept sensitive/private photos without informed consent and a documented retention process.

## Suggested product packages (validate willingness to pay before advertising)
- **Trial demo:** one short sample reel, with the limitation notice shown before checkout.
- **Creator starter:** a limited number of narrated-photo reels per month.
- **Assisted setup:** custom branding and help preparing scripts/voiceovers.
These are packaging ideas only; prices and quotas should be set after testing actual hosting costs and demand.

## Required before public self-service sales
- [ ] Choose and configure a licensed photo-to-video/lip-sync provider or deploy a suitable GPU model; document per-generation cost and consent rules.
- [ ] Add user accounts, secure password reset, rate limits, and tenant-isolated storage.
- [ ] Add a payment provider (for example Razorpay for India) with verified webhooks, plan entitlements, failed-payment handling, invoices, and refunds. Do not store card data.
- [ ] Add durable private object storage, expiry/deletion controls, and a privacy policy covering processors and retention.
- [ ] Add job queue/status, retry handling, timeouts, concurrency limits, monitoring, and backups.
- [ ] Add terms of service, acceptable-use rules, consent/rights confirmation for uploaded faces/voices, support contact, pricing, refund/cancellation terms, and tax/invoice handling.
- [ ] Complete live-host end-to-end tests with real customer-like accounts, payment sandbox, upload, generation, downloads, concurrent jobs, restart behavior, and deletion verification.
- [ ] Confirm commercial rights/terms for every TTS, video, music, font, and model used.
- [ ] Complete Meta/Instagram Graph API app setup and review before advertising automated publishing; this is a separate feature.

## Release gate
Do not call this production-ready until the items above that apply to the advertised package are completed and verified. CI passing proves only the tests it ran; it does not prove live hosting, third-party services, billing, security, or lip-sync quality.
