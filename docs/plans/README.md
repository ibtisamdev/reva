# Implementation Plans

This folder contains detailed implementation plans for each milestone of Reva.

## Structure

```
docs/plans/
├── README.md                    # This file
├── m0-foundation.md             # Phase 0: Project foundation (completed)
├── m1-product-qa.md             # Milestone 1: Product Q&A Bot
└── m1-phases/                   # Detailed M1 implementation phases
    ├── phase-1-rag-pipeline.md  # Core AI/RAG pipeline
    ├── phase-2-widget-api.md    # Widget API integration
    ├── phase-3-dashboard.md     # Dashboard features
    └── phase-4-shopify.md       # Shopify integration
```

## Milestones Overview

| Milestone | Name                                | Status      | Timeline    |
| --------- | ----------------------------------- | ----------- | ----------- |
| M0        | [Foundation](m0-foundation.md)      | Completed   | Week 1      |
| M1        | [Product Q&A Bot](m1-product-qa.md) | In Progress | Weeks 2-5   |
| M2        | Order Status Agent                  | Not Started | Weeks 6-7   |
| M3        | Sales Agent                         | Not Started | Weeks 8-9   |
| M4        | Cart Recovery                       | Not Started | Weeks 10-11 |
| M5        | Action Agent                        | Not Started | Weeks 12-13 |
| M6        | Omnichannel                         | Not Started | Weeks 14-15 |
| M7        | Analytics                           | Not Started | Week 16     |
| M8        | Developer Platform                  | Not Started | Week 17+    |

## Quick Links

### Current Focus: Milestone 1

- [M1 Overview](m1-product-qa.md) - Goals, architecture, success criteria
- [Phase 1: RAG Pipeline](m1-phases/phase-1-rag-pipeline.md) - Knowledge ingestion and AI responses
- [Phase 2: Widget API](m1-phases/phase-2-widget-api.md) - Connect widget to backend
- [Phase 3: Dashboard](m1-phases/phase-3-dashboard.md) - Merchant management UI
- [Phase 4: Shopify](m1-phases/phase-4-shopify.md) - Store connection and product sync

### Reference

- [Product Roadmap](../../ROADMAP.md) - High-level product vision and features
- [M0 Foundation](m0-foundation.md) - Technical architecture and infrastructure

## How to Use These Docs

1. **Before starting work:** Read the relevant phase document
2. **During development:** Check off tasks as you complete them
3. **When blocked:** Reference the dependencies and prerequisites
4. **After completing a phase:** Update status and move to next phase

## Naming Convention

- `m{N}-{name}.md` - Milestone overview document
- `m{N}-phases/phase-{N}-{name}.md` - Detailed phase documents

## Contributing

When adding new milestone plans:

1. Create `m{N}-{milestone-name}.md` for the overview
2. Create `m{N}-phases/` folder if multiple phases needed
3. Update this README with the new milestone
4. Link from the main ROADMAP.md
