# Frontend Theme & Styling Guidelines

Version: **1.0**
Product Type: **Consumer Fintech / Digital Wallet**
Platforms: **Web, Mobile Web, Android, iOS**
Design Goals: **Trust, clarity, speed, mass accessibility**

GCash-inspired global theme for the React + Tailwind CSS frontend.
Primary brand color: **`#007DFE`** (GCash Blue).

## Architecture

| Layer | File | Purpose |
|-------|------|---------|
| Design tokens | `frontend/tailwind.config.js` | `primary`, `stat`, `surface` color scales; `shadow-card`; fonts |
| Shared color maps | `frontend/src/theme/colors.ts` | `statusStyles`, `priorityStyles`, `severityStyles`, `confidenceStyles` |
| Base defaults | `frontend/src/index.css` `@layer base` | Body bg, link colors, focus rings, input defaults |
| Component classes | `frontend/src/index.css` `@layer components` | `.btn-*`, `.card`, `.badge-*`, `.nav-link`, `.stat-card-*`, `.spinner` |

## 1. Design Principles

### 1.1 Trust by Default
Financial actions must feel safe, predictable, and reversible. Visual consistency, restrained motion, and conservative color usage reinforce user confidence.

### 1.2 Mobile-First Accessibility
Prioritize small screens, one-handed use, low bandwidth, and varying device performance.

### 1.3 Simplicity Over Density
Favor progressive disclosure, card-based grouping, and clear hierarchy over feature-heavy screens.

### 1.4 Inclusive Design
Support users with varying levels of financial literacy, language proficiency, and digital experience.

## 2. Color System

### 2.1 Core Palette
- **GCash Blue (`primary-*`)**: primary actions, navigation, highlights, trust anchor
- **White**: primary background
- **Light Gray**: containers, dividers, disabled states
- **Dark Gray / Near-Black**: primary text

### 2.2 Semantic Colors
- **Success**: green (transaction completed, positive status)
- **Warning**: yellow/amber (pending, attention needed)
- **Error**: red (failed transactions, validation errors)
- **Info**: light blue/teal (tips, system messages)

### 2.3 Usage Rules
- Primary blue should dominate CTAs and navigation.
- Avoid multiple accent colors on a single screen.
- Error and warning colors must never be used decoratively.

## 3. Typography System

### 3.1 Font Family
- Use a sans-serif, system-friendly, highly legible typeface.
- Optimize for mobile rendering and numeric clarity.
- Use platform system font fallbacks for Android, iOS, and web.

### 3.2 Type Scale
- **Display / Balance amounts**: large, bold
- **Section headers**: medium-large, semibold
- **Body text**: regular
- **Helper / Meta text**: small, regular

### 3.3 Typography Rules
- Numbers must be visually distinct.
- Keep line length optimized for mobile reading.
- Avoid long paragraphs; use short, scannable text blocks.

## 4. Layout & Grid

### 4.1 Grid System
- Single-column layout on mobile.
- Responsive multi-column layout on desktop.
- Consistent horizontal padding.

### 4.2 Card-Based Architecture
Cards are the primary organizational unit (wallet summary, recent transactions, services/features). Each card should include:
- Clear header
- Primary action (if applicable)
- Optional secondary actions

## 5. Navigation

### 5.1 Primary Navigation
- Bottom navigation bar on mobile.
- Icon + label pattern.
- Maximum 4-5 primary destinations.

### 5.2 Secondary Navigation
- Contextual tabs within sections.
- Back navigation always visible.

### 5.3 Navigation Rules
- Primary payment actions must be reachable in ≤ 2 taps.
- Navigation labels should use common financial language.

## 6. Buttons & CTAs

### 6.1 Button Types
- **Primary Button**: solid GCash Blue, white text, rounded corners
- **Secondary Button**: outline or lighter fill, lower visual priority
- **Tertiary/Text Button**: no container, for low-risk actions

### 6.2 Button States
- Default
- Pressed
- Disabled
- Loading (with spinner)

## 7. Iconography

### 7.1 Icon Style
- Flat, line-based icons
- Rounded corners
- Consistent stroke weight

### 7.2 Usage Guidelines
- Always pair icons with text labels.
- Icons should reinforce meaning, not replace it.
- Avoid decorative icons in transactional flows.

## 8. Imagery & Illustrations

### 8.1 Photography
- Keep usage minimal.
- Keep imagery functional, not aspirational.
- Avoid luxury/lifestyle-heavy imagery.

### 8.2 Illustrations
- Use for onboarding, promotions, and education.
- Keep style friendly, simple, and culturally neutral.

## 9. Motion & Feedback

### 9.1 Animation Principles
- Fast and subtle.
- Purpose-driven (feedback, progress, confirmation).

### 9.2 Feedback Patterns
- Show immediate visual confirmation for actions.
- Provide clear success and failure states.
- Avoid long blocking animations.

## 10. Accessibility

### 10.1 Readability
- Maintain high color contrast.
- Enforce minimum font sizes.

### 10.2 Interaction
- Ensure large tap targets.
- Preserve clear focus states.

### 10.3 Language
- Use plain language.
- Avoid technical or banking jargon when possible.

## 11. Tone & Microcopy

### 11.1 Voice
- Clear
- Reassuring
- Neutral and respectful

### 11.2 Copy Guidelines
- Use short sentences.
- Prefer action-oriented CTAs.
- Require explicit confirmation for money-related actions.

## 12. Design System Summary

The GCash design system prioritizes clarity, trust, and speed. It balances fintech reliability with consumer-friendly simplicity, ensuring digital financial services are accessible to a broad and diverse user base.

## Implementation in This Codebase

### How New Pages/Components Inherit Theme

Unstyled elements auto-inherit GCash styling from `@layer base`:
- **Body**: `bg-surface` (`#F7F8FA`), `text-gray-800`
- **Links**: `text-primary-600` with `hover:text-primary-700`
- **Focus rings**: `ring-2 ring-primary-500 ring-offset-2` on `:focus-visible`
- **Inputs/selects/textareas**: `rounded-lg border-gray-300` with primary focus ring

New components should use component classes:
```jsx
<div className="page-container">
  <h1 className="page-title">New Page</h1>
  <div className="card">Content auto-themed</div>
  <button className="btn-primary">Save</button>
</div>
```

### Available Component Classes

#### Buttons
| Class | Usage |
|-------|-------|
| `.btn-primary` | Primary actions — GCash blue bg, white text |
| `.btn-secondary` | Secondary/cancel — white bg, gray border |
| `.btn-danger` | Destructive actions — red bg |
| `.btn-warning` | Caution actions — amber bg |

#### Cards & Layout
| Class | Usage |
|-------|-------|
| `.card` | Standard card — white bg, rounded-xl, shadow-card |
| `.card-hover` | Interactive card — adds hover lift + shadow |
| `.page-container` | Page wrapper — max-w-7xl, responsive padding |
| `.page-title` | H1 heading — 2xl bold gray-900 |
| `.page-subtitle` | Subheading — sm gray-500 |

#### Badges
| Class | Usage |
|-------|-------|
| `.badge` | Base badge — rounded-full, xs font |
| `.badge-primary` | Primary — GCash blue tint |
| `.badge-success` | Success — green |
| `.badge-warning` | Warning — yellow |
| `.badge-danger` | Danger — red |
| `.badge-neutral` | Neutral — gray |

#### Navigation, Feedback, Tables, Modals
| Class | Usage |
|-------|-------|
| `.nav-link` | Nav item — gray, hover primary |
| `.nav-link-active` | Active nav — primary bg tint |
| `.spinner` | Loading spinner — primary-600 border |
| `.spinner-sm` | Small spinner (in buttons) |
| `.stat-card-blue/teal/violet/emerald` | Dashboard stat cards |
| `.table-header` | Table column header |
| `.table-row-hover` | Hoverable table row |
| `.modal-backdrop` | Modal overlay |
| `.modal-panel` | Modal content panel |

### Shared Color Maps (`theme/colors.ts`)

Import these instead of defining inline maps in components:
```tsx
import { statusStyles, priorityStyles } from '../theme/colors';

<span className={`badge ${statusStyles[ticket.status]}`}>
  {ticket.status}
</span>
```

Available exports: `statusStyles`, `priorityStyles`, `severityStyles`, `confidenceStyles`, `mergeStatusLabels`.

### Enforced Rules

1. **Never hardcode `blue-*` or `indigo-*`** for interactive elements — use `primary-*` tokens so the theme can be changed in one place.
2. **Use component classes** (`.btn-primary`, `.card`, etc.) for standard UI patterns — do not reinvent button/card styles inline.
3. **Import from `theme/colors.ts`** for status/priority/severity badges — do not duplicate maps in components.
4. **Semantic colors stay semantic** — red for danger, amber for warning, green for success.
5. **Dashboard stat cards** use blue-shifted complementary hues (`stat.blue`, `stat.teal`, `stat.violet`, `stat.emerald`).
6. **CSS custom properties** in `:root` and `:root.dark` (`--color-primary`, `--color-surface`, etc.) are available for edge cases outside Tailwind.
7. **Every element must include `dark:` variants** — light-only styling is incomplete. See the Dark Mode section below.

## Dark Mode

The app supports **light and dark mode** via Tailwind's `darkMode: "class"` strategy. Every frontend change **must** include `dark:` variants for full compatibility.

### How It Works

| Layer | Mechanism |
|-------|-----------|
| Toggle | `useTheme()` hook (`frontend/src/hooks/useTheme.ts`) adds/removes `.dark` on `<html>` |
| Persistence | `localStorage` key `deduptickets-theme`; falls back to OS `prefers-color-scheme` |
| FOUC prevention | Inline `<script>` in `index.html <head>` applies theme before React hydrates |
| CSS variables | `:root` and `:root.dark` in `index.css` define `--color-surface`, `--color-text`, `--color-border`, etc. |
| Component classes | `.btn-*`, `.card`, `.badge-*`, `.stat-card-*` already include `dark:` variants |
| UI control | `<ThemeToggle />` in the app header (sun/moon icon) |

### Dark Mode Rules

1. **Every visible element must have a `dark:` variant.** When you add `bg-white`, also add `dark:bg-[var(--color-surface-card)]`. When you add `text-navy-900`, also add `dark:text-[var(--color-text)]`.
2. **Use CSS custom properties for dark values** — prefer `dark:bg-[var(--color-surface)]` over hardcoded colors like `dark:bg-gray-900`.
3. **Borders must adapt** — pair `border-navy-200` with `dark:border-[var(--color-border)]`.
4. **Badge maps in `theme/colors.ts` must include `dark:` variants** — e.g., `'bg-primary-50 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300'`.
5. **Test both modes** — visually verify new components in light and dark before marking work done.

### Common Dark Variant Patterns

```
Light                          → Dark
bg-white                       → dark:bg-[var(--color-surface-card)]
bg-navy-50                     → dark:bg-[var(--color-surface-alt)]
text-navy-900                  → dark:text-[var(--color-text)]
text-navy-600                  → dark:text-[var(--color-text-muted)]
border-navy-200                → dark:border-[var(--color-border)]
divide-navy-200                → dark:divide-[var(--color-border)]
hover:bg-navy-50               → dark:hover:bg-white/5
ring-navy-200                  → dark:ring-[var(--color-border)]
```

## Changing the Theme

To rebrand, update these files only:
1. `frontend/tailwind.config.js` — change the `primary` color scale
2. `frontend/src/index.css` — update `:root` and `:root.dark` CSS custom properties
3. No component files need to change (they should reference tokens and shared classes)
