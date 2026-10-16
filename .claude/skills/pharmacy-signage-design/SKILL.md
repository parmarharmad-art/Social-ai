---
name: pharmacy-signage-design
description: Design generic pharmacy outdoor signage boards and deliver editable SVG/HTML, print-ready PDF, and PNG preview. Use when a user asks for pharmacy signboards, storefront signage, pharmacy banners, or large-format print artwork.
---

# Pharmacy Signage Design

Create clear, high-contrast, production-aware outdoor signage for a generic-medicine pharmacy. Follow this skill exactly.

## 1. Required intake — ask before designing

At the start of a new signage job, ask the user for:
1. Store name (exact spelling/capitalization).
2. Tagline (suggestion: “Generic Medicines, Savings Up To 80%”; never promise a discount unless the user confirms it is accurate).
3. Phone number.
4. Full address.
5. Board size: 8 × 2 ft, 10 × 3 ft, or 6 × 2 ft.
6. Official logo file upload (SVG, PDF, PNG, or high-resolution JPG).
7. Exact brand orange HEX, if they have an official brand guide. Until supplied, use placeholder orange #F26522 and label it provisional.
8. Optional: language(s), installation environment, illumination, printer/fabricator requirements.

Do not invent missing contact details. If the user has not supplied a logo, keep a clearly marked rectangular placeholder reading “LOGO HERE”. Never redraw, recreate, trace, approximate, or generate a replacement logo. Preserve the supplied logo artwork and proportions; do not recolour it unless explicitly authorized.

## 2. Brand and content rules

- Primary: orange. Use the official HEX if supplied; otherwise provisional #F26522.
- Secondary: white and dark grey (default #292929).
- High contrast; restrained palette; avoid tiny decorative details.
- Typeface: bold, legible sans-serif such as Poppins, Montserrat, or Roboto. Confirm font licensing/embedding for production; use a metrically similar available font only if needed and disclose substitution.
- Required content: store name, tagline, “Open 8AM-10PM”, phone number, and address. Ask if opening hours differ; never silently change user-provided hours.
- Suggested tagline: “Generic Medicines, Savings Up To 80%” only if user approves the claim.
- Default hierarchy: logo left; large store name; tagline below; opening hours and phone/address grouped in a clear contact strip.
- Avoid medical claims, government emblems, certification marks, or brand claims unless supplied and authorized by the user.
- Keep all critical text inside the safe area. No clipping, overlap, or text over a busy background.

## 3. Size and print geometry

Supported finished board sizes (aspect ratio locked):
- 8 × 2 ft = 4:1
- 10 × 3 ft = 3.333:1
- 6 × 2 ft = 3:1

Do not stretch artwork to fit a different size. If the user changes size, reflow the layout and regenerate exports.

Print setup:
- Finished trim size is the selected board size.
- Add 0.5 inch bleed on every edge in the print PDF/artwork; document whether the printer wants bleed included in the page size or as PDF bleed boxes.
- Keep text, logo, phone, and address at least 2 inches inside the finished trim edge (safe margin). Background colour may extend through bleed.
- Deliver a vector SVG with a viewBox matching the full artwork/bleed geometry and a PDF at the correct physical dimensions. Include crop/trim marks only if requested or required by the fabricator.
- For raster preview, target 300 pixels per inch at final physical dimensions including bleed. This can create very large PNGs; if resource limits prevent a full-resolution PNG, clearly label it as a preview and give its actual pixel dimensions. Do not call a low-resolution image “300 DPI print-ready”.
- For PDF, prefer vector text/shapes and embed fonts where licensing permits. Convert text to outlines only if the printer requests it, and preserve an editable SVG source.
- Before delivery, verify page dimensions, aspect ratio, bleed, safe area, missing fonts, text overflow, contrast, and the actual exported files.

### Letter-height rule for viewing from 10 ft

For outdoor readability, target uppercase letter height of at least 1 inch for essential text viewed from 10 ft; make the store name substantially larger (typically 3–6 inches depending on board height and layout). Use 1 inch as a conservative starting target, not a universal guarantee: readability also depends on font weight, contrast, viewing angle, lighting, and visual acuity. Avoid setting the phone/address at a size that becomes unreadable from the intended viewing distance. Confirm final sizes with the sign fabricator and a full-size proof.

## 4. Concepts and approval

After intake, create 2–3 genuinely distinct concepts and show a preview of each before making final production exports:
- Concept A — Horizontal: logo left, dominant store name, tagline, contact band.
- Concept B — With icon: use only a simple generic pharmacy/medical symbol (e.g., cross) if suitable; do not incorporate it into or imitate the official logo. Keep the logo placeholder/file separate.
- Concept C — Minimal: large type, orange/white blocks, minimal ornament, maximum distance readability.

Use the same approved content and board aspect ratio across concepts. Briefly explain each concept's hierarchy and trade-offs. Ask the user to choose A/B/C or request changes. Do not claim approval without an explicit choice.

## 5. Output files

Once a concept is chosen, create these files in a dedicated output folder:
- `signage.svg` — editable vector source, exact aspect ratio and documented bleed.
- `signage.pdf` — print-ready PDF with correct physical dimensions and bleed setup.
- `preview.png` — raster preview at 300 DPI when feasible, otherwise explicitly labelled lower-resolution preview with pixel dimensions.

Also provide a simple HTML preview if useful. Keep output filenames exactly as above. If tools/libraries needed for export are unavailable, provide the SVG/HTML source and precise export commands, and clearly state which files were not generated; never claim nonexistent files are ready.

Suggested implementation approach:
- Build artwork in SVG using physical units (inches or points) and a matching viewBox.
- Render PDF with a vector-capable renderer such as Inkscape CLI or CairoSVG plus a PDF workflow that preserves physical dimensions.
- Render PNG with Inkscape or another SVG renderer at the target dimensions.
- If available, use ImageMagick/Pillow only for raster preview checks, not as a substitute for vector print artwork.
- After export, inspect the PDF page size and PNG pixel dimensions and visually inspect the preview. Fix and re-export if any issue is found.

## 6. Quality checklist

Before delivering:
- [ ] User approved the chosen concept.
- [ ] Store name, tagline, hours, phone, and address match supplied text exactly.
- [ ] Correct official logo file used, or “LOGO HERE” placeholder shown.
- [ ] Orange is official HEX or clearly provisional #F26522.
- [ ] Selected size and aspect ratio are locked.
- [ ] 0.5-inch bleed and 2-inch safe margin are documented and respected.
- [ ] Essential lettering follows the 10-ft readability guidance.
- [ ] No clipped text, overlaps, unintended font substitutions, or low contrast.
- [ ] SVG, PDF, and PNG exist and were checked; state actual DPI/pixel dimensions and any limitations.

## 7. Interaction style

Be practical and step-by-step. Ask only for the required intake details first. Do not make the user choose technical export settings unless the print vendor requires them. Use simple language and clearly separate design preview from production-ready files.
