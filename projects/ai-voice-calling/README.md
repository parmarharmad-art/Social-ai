# AI Voice Calling Automation — Consent-Based Demo

**Status: Interactive prototype / simulated calls only.** This project demonstrates an enquiry-to-follow-up workflow. It does not place telephone calls, connect to a telephony provider, or contact real customers.

## Demo
Open `index.html` in a browser or serve this folder as a static site.

## Workflow
1. Capture a customer enquiry and preferred callback window.
2. Require explicit consent before any real call workflow could proceed.
3. Prepare a short call script from the enquiry type.
4. In this prototype, simulate the call outcome locally (no network request).
5. Record the outcome and next action in the on-screen log.

## Safety and privacy
- Sample records are fictional.
- No phone number is required or stored.
- No real call is made.
- A production integration must use a compliant telephony provider, disclose that the caller is automated, honor consent and opt-outs, and restrict access to call recordings/transcripts.
- Human review is required before any appointment, delivery, or other commitment is confirmed.

## Production integration checklist
- Select a provider and verify India calling, consent, pricing, and data-processing terms.
- Store credentials only in server-side secrets.
- Add authenticated webhook verification and idempotency.
- Add consent timestamp/source, opt-out suppression, retention limits, and audit logs.
- Test with consenting internal participants before customer rollout.

## Run
No dependencies. Open `index.html` in a browser.
