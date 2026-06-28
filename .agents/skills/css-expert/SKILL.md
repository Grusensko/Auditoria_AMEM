---
name: css-expert
description: "CSS expert for flexbox, grid, animations, responsive design, and modern layout techniques"
---
# CSS Expert

A front-end layout specialist with deep command of modern CSS, from flexbox and grid to container queries and cascade layers. This skill provides precise, standards-compliant guidance for building responsive, accessible, and maintainable user interfaces using the latest CSS specifications and best practices.

## Key Principles

- Prefer CSS Grid for layout structure (both 2D and 1D) to enforce geometric alignment; use Flexbox only in specific scenarios like simple linear components, inline item alignments, or button groups
- Prefer `rem` units for typography, margins, paddings, and container dimensions to preserve accessibility and layout scaling consistency; reserve pixels (`px`) only for border thicknesses or specific shadow offsets
- Embrace custom properties (CSS variables) for theming, spacing scales, and any value that repeats or needs runtime adjustment
- Prefer OKLCH (`oklch(L C H)`) over Hex/HSL/RGB for colors to ensure perceptually uniform lightness, easy hover states via calc(), and excellent contrast accessibility
- Design responsive modules using Container Queries (`@container`) and fluid calculations (`clamp()`) based on container size instead of global viewport breakpoints
- Leverage the cascade intentionally with @layer declarations to control specificity without resorting to !important

## Techniques

- Define CSS Grid layouts with grid-template-areas for named regions, and auto-fit/auto-fill with minmax() for responsive grids
- Use `grid-template-rows: subgrid` (or columns) on nested components like card sections (headers, text bodies, buttons) to align them horizontally across all items in a row
- Use the `:has()` selector for parent-aware styling and conditional states without JavaScript (e.g., `.form-field:has(.input-error)`)
- Apply `:placeholder-shown` and `:focus-within` to build elegant floating labels for input fields using CSS only
- Apply `text-wrap: balance` for headline balancing and `text-wrap: pretty` for body paragraphs to prevent orphaned words
- Utilize `color-mix(in srgb, var(--color) X%, transparent)` for mixing dynamic alpha transparencias natively in CSS
- Declare `@view-transition { navigation: auto; }` for smooth, native cross-document transition animations between page navigations
- Animate hamburger buttons into a symmetrical "X" using absolute positioning with transform and translation transitions on class activation

## Common Patterns

- **Holy Grail Grid Layout**: CSS Grid with grid-template-rows (auto 1fr auto) and grid-template-columns (sidebar content sidebar) for header/footer/sidebar structures
- **Fluid Scaling**: clamp(1rem, 2.5vw, 2rem) for font sizes and paddings that scale smoothly between bounds without breakpoints
- **Floating Labels (Pure CSS)**: Input element preceding a label (`input:placeholder-shown ~ label` / `input:not(:placeholder-shown) ~ label`) to move and scale labels dynamically on focus/content presence
- **Hamburger to X Transition**: 3 absolute lines (`.hamburger-line`), translating the top and bottom lines to the center (Y-axis translation) and rotating them by 45deg and -45deg while fading out the middle line
- **Responsive Drawer (Mobile Navigation)**: Slide-out menu overlay (`transform: translateX(100% -> 0)`) with backdrop blur effects (`backdrop-filter: blur()`) on viewport container constraints
- **Logical Properties**: Use `margin-inline`, `padding-block`, and `inset: 0` for positioning, padding, and margins to build internationalization-ready stylesheets

## Pitfalls to Avoid

- Never use `<br />` tags in HTML for visual spacing, vertical margins, or element positioning; use CSS margins, paddings, or `gap` instead
- Do not use fixed pixel widths or heights for fluid layout containers; let CSS Grid and fluid units size them naturally
- Do not mix color models inconsistently; standardize on OKLCH for system theme coordinates
- Do not stack z-index values arbitrarily; establish a z-index scale in custom properties
- Do not nest selectors excessively, as the generated CSS becomes highly specific and difficult to maintain or override
