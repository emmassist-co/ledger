# Operator Skill Contract

The generated operator skill should stay thin.

It must:

- tell future agents to use the local archive first
- point to the generated recipe files by path
- include the editable expansion recipes and coverage ledger by path
- include the editable support hierarchy and confirmation threshold recipes by path
- include the editable currentness recipe and payload template when current-state safety matters
- explain that the coverage ledger carries multiple memory states, not only confirmed support gaps
- distinguish rule lookup from case application
- require a pre-answer judgment pass before treating retrieved local support as sufficient
- require a validated expansion plan before growth that adds durable knowledge
- require support labels for decisive claims and confirmation-boundary discipline for user-facing case conclusions
- require freshness, facts, and exception checks before case application
- require currentness checks before decisive current-state output when the pack says they apply
- require the answer contract before final legal or policy-facing output

The operator skill should make the shared decision surfaces obvious:

- `check_coverage_state` for known coverage weakness
- support-hierarchy checks for decisive support
- currentness checks for current-state support
- pre-answer weakness checks for likely below-target local support
- auto-expand checks for below-target answer decisions
- confirmation-boundary checks for user-facing case conclusions

It must not:

- duplicate the full recipe content inline
- hardcode source-specific crawl logic
- become a second framework beside Ledger
