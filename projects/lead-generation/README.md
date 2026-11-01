# Lead Generation Automation — Consent-First Demo

A browser-only lead workflow using fictional sample records. It demonstrates qualification, source tracking, CSV export, and approval-gated outreach drafts.

## Features
- Filter fictional leads by fit score.
- Show a transparent qualification score based on stated business fit.
- Keep a source field with every sample record.
- Generate a personalized first-contact draft for review.
- Require explicit human approval before the demo marks a draft approved.
- Export the sample lead list as CSV.

## Safety and limitations
- All records are fictional examples; no real people are listed.
- This demo does not scrape websites, collect personal data, send email, or contact anyone.
- Approval changes only local page state. No outreach is sent.
- Do not use this pattern for unsolicited bulk messaging. For a real workflow, use appropriate lawful sources, document the basis for contact, honor opt-outs, minimize stored data, and require review before each message.

## Production checklist
Add an approved lead source and source URL; validate business contact details; implement deduplication and retention limits; store credentials server-side; comply with applicable privacy, anti-spam, and platform rules; provide suppression lists and audit logs; require per-recipient human approval before any outbound action.

## Run
Open `index.html` in a browser. No setup or API key required.
