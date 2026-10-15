---
name: 3d-animation-web-builder
description: Build polished, mobile-first 3D animated websites using semantic HTML, CSS, JavaScript, and Three.js. Use when asked to create a 3D website, animated landing page, interactive 3D hero, product showcase, or to convert an existing HTML landing page into a modern 3D experience.
---

# 3D Animation Website Builder

## Mission
Deliver a complete, usable website—not a mockup—with intentional 3D motion, responsive layout, accessible controls, and honest claims about functionality.

## Workflow
1. Inspect the existing repository and any supplied HTML before changing files. Preserve the user's existing copy, branding, links, and working features unless the request authorizes changes.
2. Identify the page's main goal and build one coherent visual direction. Default to premium dark surfaces, high-contrast typography, soft gradients, and restrained accent colors unless the brief says otherwise.
3. Use Three.js for real-time 3D when a dependency/CDN is acceptable. If unavailable, use CSS 3D transforms and explain the difference. Do not label a flat image as interactive 3D.
4. Create a focused hero scene: layered geometric objects, particles, lighting, depth, subtle pointer parallax, and a clear fallback for reduced-motion or WebGL failure.
5. Add purposeful scroll reveals, animated counters only when the underlying values are real, responsive navigation, clear calls to action, and working buttons/links.
6. Optimize for phones: compressed assets, capped pixel ratio, resize handling, no excessive particles, and touch-friendly controls. Respect prefers-reduced-motion.
7. Keep code organized, semantic, keyboard accessible, and maintainable. Use CSS variables and meaningful names. Avoid huge frameworks for a single landing page.
8. Never invent customer testimonials, visitor counts, urgency timers, discounts, guarantees, or results. Mark placeholders clearly or remove unsupported social proof.
9. Never expose API keys or secrets in client-side code. Forms and payment buttons must not claim to work unless connected to a real backend/provider.
10. Validate file paths, internal anchors, JavaScript syntax, mobile layout, WebGL fallback, and console errors when tools are available.

## Deliverables
- A runnable website entry point with complete HTML/CSS/JS or a clearly documented framework setup.
- Short README with local preview and deployment instructions.
- A concise list of implemented interactions and any remaining integrations.
- Do not claim a deployment or browser test succeeded unless it was actually verified.

## Default design checklist
- [ ] Clear hero headline and one primary CTA
- [ ] Real 3D motion with pause/reduced-motion behavior
- [ ] Responsive mobile-first layout
- [ ] Readable contrast and focus states
- [ ] Functional navigation and buttons
- [ ] Graceful fallback if Three.js/WebGL is unavailable
- [ ] No fabricated testimonials, metrics, countdowns, or payment success
- [ ] Lightweight dependencies and honest setup notes
