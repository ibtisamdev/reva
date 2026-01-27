# Reva Design System

> **"Trusted Intelligence"** - A design system that combines trust and approachability for AI-powered customer support.

## Table of Contents

1. [Overview](#overview)
2. [Design Principles](#design-principles)
3. [Color Palette](#color-palette)
4. [Typography](#typography)
5. [Spacing](#spacing)
6. [Border Radius](#border-radius)
7. [Shadows](#shadows)
8. [Components](#components)
9. [Animation](#animation)
10. [Widget Customization](#widget-customization)
11. [Accessibility](#accessibility)
12. [AI Agent Guidelines](#ai-agent-guidelines)

---

## Overview

Reva is an AI-powered customer support agent for Shopify stores. This design system ensures consistency across:

- **Web Dashboard** (`apps/web/`) - Next.js 15 + React 19 admin interface
- **Chat Widget** (`apps/widget/`) - Preact embeddable widget for Shopify stores

### Key Files

| File                           | Purpose                                      |
| ------------------------------ | -------------------------------------------- |
| `design-tokens.json`           | Single source of truth for all design values |
| `apps/web/src/app/globals.css` | CSS custom properties for the dashboard      |
| `apps/web/tailwind.config.ts`  | Tailwind configuration with extended palette |
| `apps/widget/src/styles.css`   | Standalone widget styles                     |
| `apps/web/components.json`     | shadcn/ui CLI configuration                  |

---

## Design Principles

### 1. Trust Through Clarity

Use clear visual hierarchy and predictable patterns. Users trust interfaces they can understand quickly.

### 2. Warmth in AI

Balance technical capability with human approachability. The teal-coral palette was chosen to make AI feel helpful, not cold.

### 3. Accessibility First

Maintain WCAG 2.1 AA compliance. All color combinations meet 4.5:1 contrast ratio for normal text.

### 4. Progressive Enhancement

Core functionality works everywhere. Enhanced experiences for modern browsers.

### 5. Shopify Ecosystem Fit

Design language complements Shopify without copying it. Differentiated but not jarring.

---

## Color Palette

### Brand Colors

#### Primary - Deep Teal

The primary brand color conveys trust, intelligence, and calm.

| Token          | Hex           | HSL             | Usage                 |
| -------------- | ------------- | --------------- | --------------------- |
| `teal-50`      | `#f0fdfa`     | 166 76% 97%     | Subtle backgrounds    |
| `teal-100`     | `#ccfbf1`     | 167 85% 89%     | Hover states (light)  |
| `teal-200`     | `#99f6e4`     | 168 84% 78%     | Borders (light)       |
| `teal-300`     | `#5eead4`     | 171 77% 64%     | -                     |
| `teal-400`     | `#2dd4bf`     | 172 66% 50%     | -                     |
| `teal-500`     | `#14b8a6`     | 173 80% 40%     | Light variant         |
| **`teal-600`** | **`#0d9488`** | **175 84% 32%** | **Primary (DEFAULT)** |
| `teal-700`     | `#0f766e`     | 175 77% 26%     | Hover state           |
| `teal-800`     | `#115e59`     | 176 69% 22%     | Active state          |
| `teal-900`     | `#134e4a`     | 176 61% 19%     | -                     |
| `teal-950`     | `#042f2e`     | 179 81% 10%     | -                     |

```tsx
// Usage in components
<Button className="bg-primary">Primary Action</Button>
<Button className="bg-teal-600 hover:bg-teal-700">Direct Teal</Button>
```

#### Accent - Warm Coral

The accent color adds energy and warmth. Use sparingly for emphasis.

| Token           | Hex           | HSL            | Usage                |
| --------------- | ------------- | -------------- | -------------------- |
| `coral-50`      | `#fff7ed`     | 33 100% 96%    | Subtle backgrounds   |
| `coral-100`     | `#ffedd5`     | 34 100% 91%    | Badges (light)       |
| `coral-200`     | `#fed7aa`     | 32 98% 83%     | -                    |
| `coral-300`     | `#fdba74`     | 31 97% 72%     | -                    |
| `coral-400`     | `#fb923c`     | 27 96% 61%     | -                    |
| **`coral-500`** | **`#f97316`** | **25 95% 53%** | **Accent (DEFAULT)** |
| `coral-600`     | `#ea580c`     | 21 90% 48%     | Hover state          |
| `coral-700`     | `#c2410c`     | 17 88% 40%     | Active state         |
| `coral-800`     | `#9a3412`     | 15 79% 34%     | -                    |
| `coral-900`     | `#7c2d12`     | 13 73% 28%     | -                    |
| `coral-950`     | `#431407`     | 14 80% 15%     | -                    |

```tsx
// Usage - Important CTAs, AI activity indicators
<Button className="bg-accent">Upgrade Now</Button>
<Badge variant="warning">AI Processing</Badge>
```

### Semantic Colors

| Token                   | Hex       | Usage                         |
| ----------------------- | --------- | ----------------------------- |
| `success`               | `#22c55e` | Success states, confirmations |
| `warning`               | `#f59e0b` | Warnings, pending states      |
| `error` / `destructive` | `#ef4444` | Errors, destructive actions   |
| `info`                  | `#3b82f6` | Informational messages        |

```tsx
// Usage
<Badge variant="success">Active</Badge>
<Badge variant="warning">Pending</Badge>
<Badge variant="destructive">Failed</Badge>
```

### Neutral Colors (Slate)

| Token       | Hex       | Usage                      |
| ----------- | --------- | -------------------------- |
| `slate-50`  | `#f8fafc` | Page background            |
| `slate-100` | `#f1f5f9` | Card backgrounds, surfaces |
| `slate-200` | `#e2e8f0` | Borders, dividers          |
| `slate-300` | `#cbd5e1` | Disabled states            |
| `slate-400` | `#94a3b8` | Placeholder text           |
| `slate-500` | `#64748b` | Muted text                 |
| `slate-600` | `#475569` | Secondary text             |
| `slate-700` | `#334155` | Body text                  |
| `slate-800` | `#1e293b` | Headings                   |
| `slate-900` | `#0f172a` | Primary text (foreground)  |
| `slate-950` | `#020617` | Darkest                    |

### CSS Custom Properties

These are defined in `globals.css` and consumed via Tailwind:

```css
:root {
  --background: 210 40% 98%; /* slate-50 */
  --foreground: 222 47% 11%; /* slate-900 */
  --primary: 175 84% 32%; /* teal-600 */
  --primary-foreground: 0 0% 100%;
  --accent: 25 95% 53%; /* coral-500 */
  --accent-foreground: 0 0% 100%;
  --muted: 210 40% 96%; /* slate-100 */
  --muted-foreground: 215 16% 47%; /* slate-500 */
  --border: 214 32% 91%; /* slate-200 */
  --ring: 175 84% 32%; /* teal-600 */
}
```

---

## Typography

### Font Family

```css
font-family:
  system-ui,
  -apple-system,
  BlinkMacSystemFont,
  'Segoe UI',
  Roboto,
  'Helvetica Neue',
  Arial,
  sans-serif;
```

We use the system font stack for:

- Fastest loading (no font files)
- Native feel on each platform
- Excellent readability

### Font Sizes

| Class       | Size            | Line Height | Usage                           |
| ----------- | --------------- | ----------- | ------------------------------- |
| `text-xs`   | 0.75rem (12px)  | 1rem        | Labels, captions, badges        |
| `text-sm`   | 0.875rem (14px) | 1.25rem     | Buttons, inputs, secondary text |
| `text-base` | 1rem (16px)     | 1.5rem      | Body text                       |
| `text-lg`   | 1.125rem (18px) | 1.75rem     | Lead paragraphs                 |
| `text-xl`   | 1.25rem (20px)  | 1.75rem     | Card titles                     |
| `text-2xl`  | 1.5rem (24px)   | 2rem        | Section headings                |
| `text-3xl`  | 1.875rem (30px) | 2.25rem     | Page titles                     |
| `text-4xl`  | 2.25rem (36px)  | 2.5rem      | Hero headings                   |

### Font Weights

| Class           | Weight | Usage                 |
| --------------- | ------ | --------------------- |
| `font-normal`   | 400    | Body text             |
| `font-medium`   | 500    | Buttons, labels       |
| `font-semibold` | 600    | Card titles, emphasis |
| `font-bold`     | 700    | Page headings         |

### Typography Examples

```tsx
// Page title
<h1 className="text-3xl font-bold text-foreground">Dashboard</h1>

// Section heading
<h2 className="text-2xl font-semibold text-foreground">Analytics</h2>

// Card title
<h3 className="text-xl font-semibold">Conversations Today</h3>

// Body text
<p className="text-base text-foreground">Your AI agent handled 127 inquiries.</p>

// Muted text
<p className="text-sm text-muted-foreground">Last updated 5 minutes ago</p>

// Label
<label className="text-sm font-medium">Email address</label>
```

---

## Spacing

We use Tailwind's default spacing scale. Common values:

| Class         | Value   | Pixels | Usage                    |
| ------------- | ------- | ------ | ------------------------ |
| `p-1` / `m-1` | 0.25rem | 4px    | Tight spacing            |
| `p-2` / `m-2` | 0.5rem  | 8px    | Between related elements |
| `p-3` / `m-3` | 0.75rem | 12px   | -                        |
| `p-4` / `m-4` | 1rem    | 16px   | Standard padding         |
| `p-6` / `m-6` | 1.5rem  | 24px   | Card padding             |
| `p-8` / `m-8` | 2rem    | 32px   | Section spacing          |
| `gap-2`       | 0.5rem  | 8px    | Between buttons          |
| `gap-4`       | 1rem    | 16px   | Between form fields      |
| `gap-6`       | 1.5rem  | 24px   | Between cards            |

### Spacing Guidelines

1. **Cards**: Use `p-6` (24px) for card padding
2. **Form fields**: Use `gap-4` (16px) between fields
3. **Buttons in a row**: Use `gap-2` (8px)
4. **Sections**: Use `py-8` or `py-12` for vertical spacing
5. **Page margins**: Use `px-4` on mobile, `px-8` on desktop

---

## Border Radius

| Token          | Value          | Usage                    |
| -------------- | -------------- | ------------------------ |
| `rounded-sm`   | 0.125rem (2px) | Subtle rounding          |
| `rounded`      | 0.25rem (4px)  | Default                  |
| `rounded-md`   | 0.375rem (6px) | Inputs, small buttons    |
| `rounded-lg`   | 0.5rem (8px)   | Cards, buttons (default) |
| `rounded-xl`   | 0.75rem (12px) | Larger cards             |
| `rounded-2xl`  | 1rem (16px)    | Modals, widget           |
| `rounded-full` | 9999px         | Avatars, badges, pills   |

### Component-Specific

| Component | Border Radius        |
| --------- | -------------------- |
| Button    | `rounded-md` (6px)   |
| Input     | `rounded-md` (6px)   |
| Card      | `rounded-lg` (8px)   |
| Badge     | `rounded-full`       |
| Avatar    | `rounded-full`       |
| Dialog    | `rounded-lg` (8px)   |
| Widget    | `rounded-2xl` (16px) |

---

## Shadows

| Token           | Value                         | Usage            |
| --------------- | ----------------------------- | ---------------- |
| `shadow-sm`     | `0 1px 2px rgba(0,0,0,0.05)`  | Subtle elevation |
| `shadow`        | `0 1px 3px rgba(0,0,0,0.1)`   | Cards, buttons   |
| `shadow-md`     | `0 4px 6px rgba(0,0,0,0.1)`   | Dropdowns        |
| `shadow-lg`     | `0 10px 15px rgba(0,0,0,0.1)` | Modals           |
| `shadow-xl`     | `0 20px 25px rgba(0,0,0,0.1)` | Large overlays   |
| `shadow-widget` | `0 8px 30px rgba(0,0,0,0.12)` | Chat widget      |

---

## Components

### Component Inventory

| Component    | File                | Radix Primitive                 | Status |
| ------------ | ------------------- | ------------------------------- | ------ |
| Button       | `button.tsx`        | `@radix-ui/react-slot`          | Ready  |
| Input        | `input.tsx`         | Native                          | Ready  |
| Label        | `label.tsx`         | `@radix-ui/react-label`         | Ready  |
| Card         | `card.tsx`          | Native                          | Ready  |
| Avatar       | `avatar.tsx`        | `@radix-ui/react-avatar`        | Ready  |
| Separator    | `separator.tsx`     | `@radix-ui/react-separator`     | Ready  |
| DropdownMenu | `dropdown-menu.tsx` | `@radix-ui/react-dropdown-menu` | Ready  |
| Badge        | `badge.tsx`         | Native                          | Ready  |
| Skeleton     | `skeleton.tsx`      | Native                          | Ready  |
| Tooltip      | `tooltip.tsx`       | `@radix-ui/react-tooltip`       | Ready  |
| Dialog       | `dialog.tsx`        | `@radix-ui/react-dialog`        | Ready  |
| Toaster      | `sonner.tsx`        | `sonner`                        | Ready  |

### Button Variants

```tsx
import { Button } from '@/components/ui/button';

// Variants
<Button variant="default">Primary</Button>      // Teal background
<Button variant="secondary">Secondary</Button>  // Gray background
<Button variant="outline">Outline</Button>      // Border only
<Button variant="ghost">Ghost</Button>          // No background
<Button variant="link">Link</Button>            // Underline on hover
<Button variant="destructive">Delete</Button>   // Red background

// Sizes
<Button size="sm">Small</Button>     // h-9, px-3
<Button size="default">Default</Button>  // h-10, px-4
<Button size="lg">Large</Button>     // h-11, px-8
<Button size="icon">Icon</Button>    // h-10, w-10
```

### Badge Variants

```tsx
import { Badge } from '@/components/ui/badge';

<Badge variant="default">Default</Badge>      // Teal
<Badge variant="secondary">Secondary</Badge>  // Gray
<Badge variant="success">Active</Badge>       // Green
<Badge variant="warning">Pending</Badge>      // Amber
<Badge variant="destructive">Failed</Badge>   // Red
<Badge variant="outline">Outline</Badge>      // Border only
```

### Using Tooltips

```tsx
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

<TooltipProvider>
  <Tooltip>
    <TooltipTrigger asChild>
      <Button variant="outline">Hover me</Button>
    </TooltipTrigger>
    <TooltipContent>
      <p>Helpful information</p>
    </TooltipContent>
  </Tooltip>
</TooltipProvider>;
```

### Using Dialogs

```tsx
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';

<Dialog>
  <DialogTrigger asChild>
    <Button variant="outline">Open Dialog</Button>
  </DialogTrigger>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Confirm Action</DialogTitle>
      <DialogDescription>This action cannot be undone.</DialogDescription>
    </DialogHeader>
    <DialogFooter>
      <Button variant="outline">Cancel</Button>
      <Button>Continue</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>;
```

### Using Toast Notifications

```tsx
// In layout.tsx, add the Toaster component

// In any component, use toast()
import { toast } from 'sonner';

import { Toaster } from '@/components/ui/sonner';

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        {children}
        <Toaster />
      </body>
    </html>
  );
}

// Success
toast.success('Changes saved successfully');

// Error
toast.error('Failed to save changes');

// Warning
toast.warning('Your session will expire soon');

// Info
toast.info('New features available');

// Custom
toast('Event scheduled', {
  description: 'Friday, February 10, 2024',
  action: {
    label: 'Undo',
    onClick: () => console.log('Undo'),
  },
});
```

### Adding New Components

Use the shadcn/ui CLI to add components:

```bash
cd apps/web
npx shadcn@latest add accordion
npx shadcn@latest add tabs
npx shadcn@latest add select
```

---

## Animation

### Duration

| Token          | Value | Usage               |
| -------------- | ----- | ------------------- |
| `duration-150` | 150ms | Hover states        |
| `duration-200` | 200ms | Default transitions |
| `duration-300` | 300ms | Larger animations   |
| `duration-500` | 500ms | Page transitions    |

### Easing

| Token         | Value                          | Usage            |
| ------------- | ------------------------------ | ---------------- |
| `ease-in`     | `cubic-bezier(0.4, 0, 1, 1)`   | Exit animations  |
| `ease-out`    | `cubic-bezier(0, 0, 0.2, 1)`   | Enter animations |
| `ease-in-out` | `cubic-bezier(0.4, 0, 0.2, 1)` | Default          |

### Common Animations

```tsx
// Hover transition
<button className="transition-colors duration-200 hover:bg-primary/90">
  Click me
</button>

// Fade in
<div className="animate-fade-in">Content</div>

// Scale in (modals, dropdowns)
<div className="animate-scale-in">Modal content</div>

// Pulse (loading states)
<div className="animate-pulse bg-muted h-4 w-full rounded" />

// Spin (loading indicator)
<Loader2 className="animate-spin h-4 w-4" />
```

---

## Widget Customization

The chat widget can be customized per-store through CSS custom properties.

### Default Theme

```css
.reva-widget {
  --reva-primary: #0d9488;
  --reva-primary-hover: #0f766e;
  --reva-primary-foreground: #ffffff;
}
```

### Store Customization

Stores can override the primary color via the widget configuration:

```typescript
// Widget initialization
Reva.init({
  storeId: 'store-123',
  primaryColor: '#8b5cf6', // Custom purple
});
```

This sets `--reva-primary` on the widget root element:

```css
/* Applied dynamically */
.reva-widget {
  --reva-primary: #8b5cf6;
}
```

### What Can Be Customized

| Property        | Default          | Customizable  |
| --------------- | ---------------- | ------------- |
| Primary color   | `#0d9488` (teal) | Yes           |
| Widget position | Bottom-right     | Future        |
| Agent name      | "Reva Support"   | Yes (via API) |
| Welcome message | Dynamic          | Yes (via API) |

### What Stays Consistent

- Typography (system fonts)
- Spacing scale
- Border radius
- Animation timing
- Message bubble shapes

---

## Accessibility

### Color Contrast

All color combinations meet WCAG 2.1 AA requirements (4.5:1 for normal text):

| Combination                    | Ratio | Status |
| ------------------------------ | ----- | ------ |
| Primary on white               | 4.6:1 | Pass   |
| White on primary               | 4.6:1 | Pass   |
| Foreground on background       | 16:1  | Pass   |
| Muted foreground on background | 4.9:1 | Pass   |

### Focus States

All interactive elements have visible focus indicators:

```css
:focus-visible {
  outline: none;
  ring: 2px;
  ring-color: var(--ring); /* teal-600 */
  ring-offset: 2px;
}
```

### Screen Reader Support

- All icons have `aria-label` or accompanying text
- Form inputs have associated labels
- Dialogs trap focus and have proper ARIA attributes
- Toast notifications are announced via `aria-live`

### Reduced Motion

The widget respects `prefers-reduced-motion`:

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## AI Agent Guidelines

When working with this codebase as an AI coding agent, follow these guidelines:

### Design Token Usage

1. **Always use semantic tokens** over hardcoded colors:

   ```tsx
   // Good
   <div className="bg-primary text-primary-foreground">

   // Avoid
   <div className="bg-[#0d9488] text-white">
   ```

2. **Reference `design-tokens.json`** for exact values when needed

3. **Use the extended palette** (teal-_, coral-_) for one-off variations:
   ```tsx
   <div className="bg-teal-50 border border-teal-200">
   ```

### Component Creation

1. **Follow existing patterns** - Look at `button.tsx` for CVA variant patterns
2. **Use `cn()` utility** for class merging:
   ```tsx
   import { cn } from '@/lib/utils';

   <div className={cn('base-classes', className)} />;
   ```
3. **Add `'use client'`** directive for components using hooks or event handlers

### CSS Custom Properties

When adding new tokens:

1. Add HSL values to `globals.css` `:root`
2. Add Tailwind mapping to `tailwind.config.ts`
3. Update `design-tokens.json` with hex values

### Widget Modifications

1. Keep styles scoped to `.reva-widget`
2. Use CSS custom properties for all colors
3. Test with custom `primaryColor` configurations
4. Ensure `prefers-reduced-motion` is respected

### Testing Changes

After design system changes:

```bash
# Build to check for errors
pnpm build

# Type check
pnpm type-check

# Lint
pnpm lint
```

---

## Quick Reference

### Primary Color Usage

| Use Case       | Class                                |
| -------------- | ------------------------------------ |
| Primary button | `bg-primary text-primary-foreground` |
| Primary text   | `text-primary`                       |
| Primary border | `border-primary`                     |
| Primary hover  | `hover:bg-primary/90`                |
| Focus ring     | `focus:ring-primary`                 |

### Common Patterns

```tsx
// Card with header
<Card>
  <CardHeader>
    <CardTitle>Title</CardTitle>
    <CardDescription>Description</CardDescription>
  </CardHeader>
  <CardContent>Content</CardContent>
  <CardFooter>Footer</CardFooter>
</Card>

// Form field
<div className="space-y-2">
  <Label htmlFor="email">Email</Label>
  <Input id="email" type="email" placeholder="you@example.com" />
</div>

// Button group
<div className="flex gap-2">
  <Button variant="outline">Cancel</Button>
  <Button>Save</Button>
</div>

// Loading state
<Button disabled>
  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
  Please wait
</Button>
```

---

## Changelog

### v1.0.0 (2026-01-27)

- Initial design system implementation
- "Trusted Intelligence" palette (Teal + Coral)
- Core components: Button, Input, Card, Badge, Dialog, Tooltip, Toast
- Widget CSS aligned with design tokens
- Comprehensive documentation
