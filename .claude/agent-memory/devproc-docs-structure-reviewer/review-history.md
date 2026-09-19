---
name: review-history
description: Log of docs-structure findings raised and whether they were fixed or knowingly deferred, for tracking improvement across reviews
metadata:
  type: project
---

2026-09-18: re-audit of client-secret five-year-limit docs (docs/m365.md "Credentials", docs/operations.md "Client secret rotation").
- Resolved: Expiry Invalid alarm now has cause/fix for >5yr; operations intro points to 5yr limit; m365 explains alarm with link to operations.md#when-to-rotate.
- Partial: m365 Credentials still says "a later date" right after talking about lifetime (length), so the length-vs-date mix remains.
- Knowingly deferred by user (pre-existing, out of feature scope, do not re-raise as new): blank lines between alarm bullets; no pointer from end of m365 Credentials back to operations "Update Parameter Store"; Verify-step parenthetical in operations.md; plan titles kept verbatim from GitHub issue titles.

**Why:** the user scopes fixes tightly to the feature and explicitly defers pre-existing issues.
**How to apply:** in re-audits, only report new issues introduced by fixes; list deferred items as deferred, not as findings.
