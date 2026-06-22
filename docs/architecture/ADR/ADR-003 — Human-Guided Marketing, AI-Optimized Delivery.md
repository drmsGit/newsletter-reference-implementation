---
type: adr
status: proposed
topic:
  - ai
  - marketing
  - automation
  - governance
created: 2026-06-06
modified: 2026-06-06
---

## Status
Proposed

## Context

Marketing teams spend a significant portion of their time on repetitive operational activities such as:

- Selecting content
- Building newsletter variants
- Ordering modules
- Optimizing send times
- Managing audience splits
- Executing product-focused campaigns

These activities are often driven by commercial goals and performance targets rather than customer understanding.

At the same time, marketers create the greatest value when they:

- Discover customer interests
- Develop content strategies
- Create narratives and campaigns
- Identify emerging trends
- Build customer relationships
- Define business and communication goals

As AI capabilities improve, there is a risk of focusing automation on replacing marketers instead of reducing operational workload.

## Decision

The architecture shall prioritize automation of delivery and optimization tasks while preserving human ownership of strategy, creativity, and customer understanding.

The system should:

- Automate repetitive campaign execution activities
- Optimize content selection and ordering
- Optimize frequency and send timing
- Generate recommendations and suggestions
- Surface customer insights

The system should not assume fully autonomous marketing decision-making.

Human marketers remain responsible for:

- Strategic direction
- Campaign objectives
- Brand voice
- Customer research
- Content creation
- Approval and governance

### Preferred AI Features

- Content recommendations
- Newsletter scoring
- Audience insights
- Dynamic content selection
- Frequency optimization
- Send-time optimization
- Variant suggestions

### Secondary AI Features

- Subject line generation
- Copy suggestions

### Not a Primary Goal

- Fully autonomous marketing strategy
- Fully autonomous campaign planning
- Removal of human campaign ownership

## Consequences

### Positive

- Increased marketing productivity
- More time for strategic work
- Better customer understanding
- Improved scalability
- Reduced operational effort
- Easier adoption by marketing teams

### Negative

- Lower level of full automation
- Continued need for human review and governance
- Some optimization opportunities may remain intentionally constrained

## Notes

The objective of AI is not to replace marketing teams.

The objective is to free marketing teams from repetitive optimization work so they can spend more time understanding customers and developing better communication strategies.

Commercial product promotion is often highly rule-based and performance-driven, making it a suitable candidate for automation.

Customer understanding, storytelling, creativity, and strategic planning remain primarily human responsibilities.

The system maximizes relevance and efficiency. Marketers maximize insight and creativity.

## Related ADRs

### Referenced By

- [[ADR-001 — Newsletter Architecture Boundaries]]
