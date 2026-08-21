# Memory Index

- [Seams — never flag as dead](project_seams_do_not_flag.md) — dynamically discovered surfaces and deliberate seam examples with zero static refs, verified live
- [Already in the backlog](project_backlog_already_logged.md) — delivery/provider issues docs/backlog.md already holds; don't re-report them
- [Cluster 1 sweep — frontend + templates](project_cluster1_frontend_templates.md) — no dead routes, no orphaned templates; the tricky-but-live ones and the method that proved it
- [Cluster 2 sweep — overrides + campaigns](project_cluster2_overrides_campaigns.md) — no dead code, but orphaned columns and router payload drift; what is deliberate there
- [Cluster 3 sweep — content + rendering](project_cluster3_content_rendering.md) — no dead code, no orphaned schema; missing DB constraints and an ADR-062 audit gap instead
- [Cluster 4 sweep — insight + recipients](project_cluster4_insight_recipients.md) — the dropped preference tables are truly gone; residue is in scripts/, and the settings weight editor is inert
- [Cluster 5 sweep — audience + decision](project_cluster5_audience_decision.md) — pins and rule blocks coexist (premise was wrong); ADR-084 settles the max_results question
- [Cluster 6 sweep — auth + settings](project_cluster6_auth_settings.md) — constraint-gap streak ends; 3 loc residue; two sign-in defects and a double session resolution instead
- [Cluster 7 sweep — ai + snapshots + email_modules](project_cluster7_ai_snapshots_email_modules.md) — AI-optional boot is settled NO; residue is one template dropdown; run_task is untested
- [Review only, never edit](feedback_review_only.md) — report findings; write access is limited to this memory directory
