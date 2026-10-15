---
id: TASK-380
title: 'How-to: connecting a product catalogue so shops pick products by article id'
status: To Do
assignee: []
created_date: '2026-10-15 20:37'
labels:
  - docs
dependencies: []
type: docs
ordinal: 210500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Docs]** Raised by the user on 2026-10-15, while building the email blocks (task-371): an e-commerce shop wants to pick products by article id instead of typing their contents in. Not built; a how-to chapter for the playbook.

**What it would cover.**
- Where product data comes from: the shop's PIM or product feed, a CRM, or a DWH (task-120 holds sales and transaction data).
- How it reaches the platform. One way is products as content records, imported or synced through the content API with an integration key (ADR-166; the content CSV import exists). The other is fetched when needed, the related-data question of task-294.
- Article ids as identifiers. A record's external id, or a declared field, found by the picker and by decision slots.
- Product images. Either as library images (ADR-197, copied per brand) or as web addresses from the shop's CDN, with alt text (the ADR-197 addendum of 2026-10-15). The image library is not a DAM, and a shop with tens of thousands of product images connects its media centre instead (task-112's note on scale).
- Prices and stock change after a send is frozen. Say what an email can promise (ADR-183) and when a dynamic link or a live block would be needed (task-366).
- Which blocks suit products (the ADR-198 set: Column pairs, Image left or right).

**Related.** task-112, task-120, task-294, task-366, task-364, task-379; ADR-166, ADR-183, ADR-197.
<!-- SECTION:DESCRIPTION:END -->
