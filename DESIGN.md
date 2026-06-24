# Design

## Visual Direction

Quiet local operations dashboard with a light neutral background, white data surfaces, dark readable text, and one teal accent for active actions and highlights.

## Typography

Use system UI fonts with Microsoft YaHei and Segoe UI fallbacks. Keep headings compact and table text readable at 13-14px.

## Color Tokens

- Background: `#f4f7f8`
- Surface: `#ffffff`
- Surface Muted: `#eef4f4`
- Ink: `#172326`
- Muted Ink: `#5f6f73`
- Border: `#d7e2e4`
- Accent: `#087f8c`
- Accent Dark: `#05616a`
- Warning: `#b7791f`
- Error: `#b42318`

## Components

- Drop zone: large dashed bordered panel with clear upload state.
- KPI cards: compact four-column row on desktop, two-column on mobile.
- Charts: horizontal ranked bars with labels and numeric values.
- Tables: dense but readable, sticky header, zebra rows, horizontal scroll on narrow screens.
- Buttons: 8px radius, clear focus ring, primary teal and secondary bordered variants.

## Layout

Single-page app. Top section contains title, date selector, file drop zone, and actions. Results appear below as KPI strip, chart grid, customer summary table, and shipment detail table.

## States

- Empty: explain that one or more Excel files can be dropped or selected.
- Loading: show file parsing status and disable actions.
- Error: show the exact workbook or parsing issue.
- Success: show summary metrics and charts immediately.
