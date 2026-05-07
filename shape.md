# Shape Brief — Black Pearl Frontend Redesign

**Register:** product
**Target register:** Product (utility app)
**Design reference:** Warp terminal + Arc browser minimalism + Things 3 card discipline
**Aesthetic goal:** Technical, confident, efficient. Dark-first, electric amber accent, dense but legible.

---

## Current State

- Single-page Jinja2 template (`templates/index.html`)
- Custom CSS with maritime dark theme (preto/ouro)
- Vanilla JS handling search, results, settings modal
- Components: header (logo + controls), search bar, loading spinner, empty state, results list, footer, cookie settings modal
- Responsive via media queries (basic)

---

## Proposed Layout & Components

### 1. Global Shell

- Background: `--color-bg` (oklch(0.09 0.005 285))
- Text: `--color-text` on all surfaces
- Font: Outfit (sans) for UI, JetBrains Mono for data/code
- Container: max-width 1024px, centered. Padding: `var(--space-4)` desktop, `env(safe-area-inset)` mobile.
- Skip link first element, visibly focused only.

### 2. Header

**Desktop:**
- Left: Logo "BP" in 2×2 grid? Actually use text "Black Pearl" but styled: weight 700, tracking -0.04em, size 1.5rem. Color --color-text.
- Right: Controls stack vertically (reduces width). Items:
  - Enrich toggle: small toggle switch (checkbox + label). Label "Auto-tag". Use `--color-text-muted` for label, toggle accent color.
  - Settings button: icon-only (`settings` svg), width/height 40px, border 1px solid --color-border, rounded 4px. Hover: border --color-accent-light.
  - Cookie indicator: small dot (--color-success or --color-error) above settings button? Or badge on button.

**Mobile:**
- Logo centered.
- Controls right-aligned horizontally if space allows, else hide toggle behind menu? Keep toggle visible as it's key feature. Use smaller spacing.

### 3. Search Area

Full-width container. Background `--color-surface`, border 1px --color-border, border-radius 4px. Padding 1rem.

Inside: grid of input + button.

- Input: no border (inherit), font-family --font-mono, size 1rem. Placeholder: --color-text-muted.
- Button: primary accent, text --color-bg, weight 600. Padding 0.75rem 1.25rem. Icon + text "Buscar".

Search hint below: small text (--color-text-muted), 0.75rem.

### 4. Empty State

Centered icon (48×48, stroke --color-text-muted), h3 "Pronto para baixar", p description.

No decorative graphics.

### 5. Results Section

Header: "Resultados" + count badge (background --color-surface, border --color-border, padding 0.25rem 0.75rem, rounded 3px).

List: vertical stack, gap 0.6rem. Each item: `.card-result` as defined in DESIGN.md.

Card structure:

```
<div class="card-result" data-id="...">
  <img class="card-thumb" src="..." alt="Thumbnail">
  <div class="card-info">
    <h3 class="card-title">Video title</h3>
    <p class="card-meta">Channel • duration</p>
    <p class="card-format">MP3 • 320kbps</p>
  </div>
  <button class="btn-primary card-download">
    <svg download icon...>
    <span>Baixar</span>
  </button>
</div>
```

Hover: border highlight, shadow-glow.

Download progress: each card can show inline mini progress bar (3px height, full width of card, gradient accent). Starts at 0%, updates via JS. On complete: change button text to "Pronto" briefly, then hide progress.

### 6. Loading State

Full-width overlay bar or inline below search. Styling: same as current spinner but accent top. Text "Buscando resultados..." beside spinner.

### 7. Settings Modal

Overlay: `oklch(0 0 0 / 0.6)`.
Content: max-width 640px, margin 5vh auto, padding 1.5rem, background --color-surface, border --color-border, radius 6px.

Header: h2 with settings icon + "Configurações", close button (×) top-right.
Body: cookie section as before but restyled:
- Section title: weight 600, margin-bottom 0.75rem.
- Description: --color-text-muted.
- Status row: dot (circle, size 8px, bg --success or --error) + text.
- Actions: upload button (secondary style) + delete button (hidden by default).
- Help details: styled details element (no default triangle; custom SVG? Keep native but style summary).

All inputs, buttons inside modal: full width where appropriate.

### 8. Footer

Small text --color-text-muted, centered. Links: underline on hover (--color-accent-light). Margin: 2rem 0.

---

## Motion & Interactions

- Button hover: 120ms ease-out, translateY(-1px) + shadow-glow.
- Card hover: border-color transition 120ms ease-out, shadow 200ms.
- Results appear: fade-in 200ms ease-out, staggered 50ms each.
- Modal: fade-in overlay 150ms, content scale 0.98→1 ease-out.
- Focus rings: `:focus-visible` with outline offset 2px, color --color-accent.

No layout property transitions.

---

## Responsive Breakpoints

- Desktop: ≥768px. Container 1024px max.
- Mobile: <768px. Container full-bleed with 1rem padding. Results card grid-template change to: thumbnail 80px | info 1fr | action auto? Actually keep 120px might overflow; reduce to 100px or stack? Let's keep single row but shrink thumb: 100px width, height 56px (16:9). If title too long, truncate 2 lines.

Also consider very small screens: hide header subtitle, reduce header padding.

---

## Accessibility

- Skip link to #main.
- All interactive elements: `:focus-visible` styling.
- Images: alt text from video title or "Thumbnail of {title}".
- Buttons: include visible text (no icon-only on mobile if no aria-label). Settings button: aria-label "Configurações".
- Modal: trap focus not implemented now but at least ensure focus moves to modal on open and returns to trigger on close.
- Reduced motion: media query reduces transitions to 50ms or removes.

---

## Technical Implementation Notes

- CSS: new file `static/css/style.css` replacing old one. Use CSS custom properties from DESIGN.md.
- JS: no framework. Keep `app.js`. Add functions for:
  - Rendering results using template literals, creating DOM nodes.
  - Progress bar element attached to card.
  - Staggered fade-in using CSS class `.fade-in` with animation or JS timeout.
  - Modal open/close with ESC key and overlay click.
- Icons: inline SVG, stroke width 2px, currentColor.
- No external dependencies besides fonts.
- Keep existing API endpoints (FastAPI routes) unchanged.

---

## What Changes Files

1. `static/css/style.css` — full rewrite
2. `templates/index.html` — markup refresh, classes semantic, ARIA as needed
3. `static/js/app.js` — adapt to new DOM structure and progress handling

Nothing else.

---

## Questions / Decisions Needed

- Keep "Auto-tag" toggle in header? Yes. Placement: next to settings or below logo?
- Should results show video length, channel name, and upload date in meta line? Current shows format only. Better: "Channel • 3:45 • 2 days ago" but could be crowded.
- Thumbnail aspect: 16:9 is fine. Square might be cleaner? Warp uses square avatars. But YouTube thumbnails are 16:9 usually. Keep 16:9.
- Should we add keyboard shortcuts? Possibly: Ctrl+K focus search, Ctrl+, open settings. Not required for v1.
- Footer keep? Minimal, fine.

---

**Implementation approach:**
1. Build CSS baseline (variables, reset, base styles).
2. Implement header, search, empty state.
3. Results list + card component.
4. Modal styling.
5. Update JS to render new card structure, wire events.
6. Test desktop + mobile responsive.
7. Add motion and polish.

Ready to proceed?
