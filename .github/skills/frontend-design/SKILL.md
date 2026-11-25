---
name: frontend-design
description: Design and refine professional financial software interfaces in React and CSS, with strong visual hierarchy, typography, spacing, data visualisation, accessibility, and usability while preserving existing functionality and project conventions.
---

# Frontend design for financial software

Use this skill when designing, redesigning, or implementing React interfaces for finance products such as dashboards, transaction views, budgets, forecasts, reports, and account management screens.

## Design objective

Create interfaces that feel trustworthy, calm, precise, and easy to scan. The interface should help users understand financial state and make decisions quickly without turning every screen into a dashboard.

Before editing code:

- Inspect the existing React structure, routes, components, CSS strategy, design tokens, icon system, charting library, and package scripts.
- Identify the current user flows and data contracts. Preserve existing behavior, routes, loading states, validation, permissions, responsive behavior, and integrations unless the request explicitly changes them.
- Reuse the project's established technologies and components. Do not introduce a new framework, styling system, chart library, or dependency when the existing stack can support the work.
- Identify the primary task and the most important piece of information on the screen. Design around that task rather than adding more panels.

## Visual direction

- Establish hierarchy with type scale, weight, contrast, grouping, and whitespace before using color or decoration.
- Prefer a restrained palette: a clear surface/background relationship, one primary action color, semantic positive/negative/warning colors, and neutral text tones. Do not encode meaning by color alone.
- Use typography that is highly legible at financial-data sizes. Keep labels, values, units, dates, and supporting context visually distinct. Use tabular numerals for aligned amounts when the font supports them.
- Use a consistent spacing rhythm and align content to a small number of intentional columns. Keep dense tables readable through row height, padding, grouping, and sticky context - not tiny type.
- Use borders, subtle fills, and elevation sparingly to separate regions. Avoid excessive gradients, glassmorphism, ornamental blobs, decorative illustrations, and gratuitous shadows.
- Avoid generic AI-generated dashboard aesthetics: do not fill the page with equal-sized cards, oversized hero metrics, arbitrary charts, neon accents, or decoration that does not improve comprehension.
- Make the most important action obvious, but avoid competing primary buttons. Destructive financial actions should be explicit and require an appropriate confirmation or undo path.

## Financial information design

- Show period, currency, account scope, and data freshness wherever they affect interpretation.
- Format money, percentages, dates, and quantities consistently with locale-aware utilities already present in the project. Do not concatenate currency symbols or round values inconsistently in components.
- Distinguish actuals, forecasts, budgets, pending transactions, and unavailable data in both labels and visual treatment.
- Use positive/negative styling carefully: gains and losses need text or icons in addition to color, and red/green should not imply universal good/bad semantics without context.
- For tables, prioritize the fields required for comparison; align numeric columns, keep headers meaningful, support sorting/filtering only when it serves the task, and provide an understandable empty state.
- For charts, choose the simplest chart that answers the question. Label axes and units, provide useful tooltips or an accessible data summary, include a legend only when needed, and avoid misleading axes or decorative 3D effects.
- Always provide a non-visual equivalent for chart insights where practical, such as a summary, table, or accessible data description.

## React and CSS implementation

- Keep presentational styling separate from business logic where the existing architecture supports it. Preserve component boundaries that make state and behavior understandable.
- Prefer semantic HTML and existing primitives. Use real buttons, links, headings, labels, tables, lists, dialogs, and form controls instead of clickable generic containers.
- Use the project's tokens and responsive conventions. If tokens are missing, define a small, coherent set close to the existing styling approach rather than scattering one-off values.
- Design mobile and narrow-width behavior intentionally: allow tables to scroll or reflow without hiding critical fields, keep actions reachable, and preserve readable chart labels.
- Make states part of the design: loading, empty, error, partial data, disabled, success, validation, and long-content states should retain the same hierarchy and explain what the user can do next.
- Keep transitions subtle and functional. Respect `prefers-reduced-motion`; never make essential information depend on animation.

## Accessibility and usability

- Meet WCAG-oriented contrast expectations for text, controls, focus indicators, and semantic status colors.
- Ensure complete keyboard operation, visible focus, sensible tab order, and usable touch targets. Do not remove outlines without providing a stronger replacement.
- Give every form control a visible or programmatic label, associate validation messages with their fields, and make errors specific and actionable.
- Use a logical heading structure and landmarks. Provide accessible names for icon buttons and meaningful alternative text for informative imagery.
- Announce asynchronous updates and important status changes appropriately without making routine screen updates noisy.
- Check zoom/reflow, reduced motion, keyboard navigation, screen-reader semantics, and color-blind interpretation when reviewing the result.

## Review checklist

Before finishing, verify:

- The primary user task and key financial insight are immediately clear.
- Existing functionality and data behavior still work, including edge states.
- Typography, spacing, alignment, and number formatting are consistent.
- Charts and color use are understandable without relying on decoration or color alone.
- Responsive layouts work at narrow and wide sizes without losing essential context.
- Keyboard, focus, labels, contrast, and reduced-motion behavior are covered.
- The result looks deliberate and product-specific rather than like a collection of generic dashboard cards.
