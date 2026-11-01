# Gmail Automation — Approval-First Prototype

A browser-only demonstration of an inbox triage workflow. It uses fictional sample messages and local page state only.

## What it demonstrates
- Classifies sample messages into categories and priority.
- Produces a suggested reply draft.
- Requires a human approval checkbox before the simulated send action.
- Shows a local activity log for the demo.

## Important limitations
- This is **not connected to Gmail**.
- It does not read, modify, send, or delete real email.
- The simulated send action only updates the page; no message leaves the browser.
- Sample messages are fictional. No personal inbox data is included.

## Production integration checklist
Before connecting a real mailbox: use Google's official OAuth flow and least-privilege scopes; request explicit mailbox-owner authorization; keep tokens in a secure backend secret store (never in browser code or Git); show the exact recipient and message before sending; require human approval for each outbound message; provide audit logs, revocation, retention controls, and error handling; comply with Google's API policies and applicable privacy rules.

## Run
Open `index.html` in a browser. No API key or installation is required.
