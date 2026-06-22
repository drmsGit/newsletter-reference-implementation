---
type: principles
status: draft
topic:
  - architecture
  - design-principles
created: 2026-05-30
modified: 2026-05-30
source:
  - condor-reference-system
  - interview-2026-05-30
---

# Newsletter Architecture Design Principles

These principles were identified during the ADR interview but are not yet treated as standalone ADRs. They should be kept visible so they can later become ADRs, design rules or handbook chapters.

## Content Governance over Content Volume

Prefer a small number of high-quality reusable content records over a large uncontrolled content repository.

Reason:
- easier editorial governance
- easier automation
- better AI recommendations
- lower risk of duplicate or outdated content

## Business Driven Content Taxonomy

Content types are defined by the business case.
The architecture does not prescribe fixed types such as product, destination, partner or article.

Types should help users filter content and should support automation logic where useful.

## Builder as Composition Tool

The Builder does not create the source content.
It enables non-technical users to compose newsletters from approved content, modules, overrides and campaign-specific settings.

## Prefer Explicit Modules over Layout-changing Options

Prefer separate modules for major layout differences.

Example:
- Image Left
- Image Right
- Image Top

instead of one module with a layout-position option.

Reason:
- easier automation
- clearer AI decisions
- simpler testing
- fewer invalid combinations
- better control of visual rhythm

Options are acceptable when they do not fundamentally change the layout structure.

## Modules as Contracts

Every module should define:
- accepted inputs
- allowed configuration
- preview behavior
- rendering behavior
- optional business logic

Free implementation is possible as long as the module contract is respected by the automation and rendering pipeline.

## Raw HTML as Escape Hatch

Raw HTML should not be the default path.
If something is reusable, it should usually become a module.
If something is truly one-off and very specific, a custom one-off email may be better than weakening the core architecture.

## Campaign Groups as Metadata

Broader initiatives such as Black Friday, Reactivation or Product Launch should remain flexible metadata or grouping concepts.
They should not become a mandatory hard hierarchy in the core model unless a later use case requires it.

## Delivery separated from Composition

Composition defines what is communicated and how it is assembled.
Delivery defines who receives it, when and under which rules.

## AI as Assistant, not Source of Truth

AI may recommend, classify or select content.
Business-controlled content governance remains the source of truth.

## Dynamic Content Is Not Builder Complexity

The Builder may mark a slot as dynamic and provide constraints.
The actual decision logic should live outside the Builder.

## Reusable Modules before Custom Development

Before creating a new module, check whether an existing module or a combination of existing modules solves the use case.
New modules should be justified by recurring value, not one-off preference.

## Campaign Variants Share a Concept

Variants may differ substantially in modules or content, but they should still share the same campaign idea or newsletter concept.
Different languages, markets or audiences may be modeled as variants in some business cases, but they are not automatically variants.

## No Variant Sublevels

Variants should remain flat.
Nested variants introduce complexity and should be handled through personalization, delivery logic, metadata or separate campaigns.
