Scan the existing ADRs and codebase for decisions that read as technical but actually encode business or strategic assumptions.

For each flagged decision, answer:
1. What business/strategic assumption is baked into this ADR/implementation, even if not stated?
2. Is this assumption universal (should stay hardcoded) or context-specific (should become a config/extension point for someone tailoring this)?
3. If someone forks this for a different use case, would this decision block them or would they naturally override it?
4. Is this documented anywhere as a decision, or only discoverable by reading code?
5. If you were teaching someone this decision, what would you need to explain that isn't in the ADR?

Reference specific ADR IDs, files, and functions. Do not suggest fixes — only surface and classify.

**Delegate the ADR sweep.** Never read the 75 records in `docs/architecture/ADR/` into the main session — fan out with the Explore agent, or use `assumption-scanner` when the input is business prose rather than code.

Skip what is already decided: `docs/playbook-strategy.md` §5 (Decision Log) and the resolved findings in `docs/business-interview-baseline.md`. Two full passes have run, so the value here is in what they did not reach — surface a settled decision only if you can say what changed.

Save output to `docs/business-interview-baseline.md`, grouped by ADR/feature area.
