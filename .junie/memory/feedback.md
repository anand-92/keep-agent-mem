[2026-06-06 01:24] - Updated by Junie
{
    "TYPE": "negative",
    "CATEGORY": "insufficient follow-through",
    "EXPECTATION": "User expected more than just editing code; they wanted validation and full follow-through after changes.",
    "NEW INSTRUCTION": "WHEN modifying source code THEN run validations/tests and report verification steps and results."
}

[2026-06-06 01:25] - Updated by Junie
{
    "TYPE": "negative",
    "CATEGORY": "insufficient follow-through",
    "EXPECTATION": "User wants thorough, end-to-end completion with validation and proactive cleanup, not minimal edits.",
    "NEW INSTRUCTION": "WHEN finishing a code change THEN run tests, update impacted tests/docs, and report verification results."
}

[2026-06-06 01:26] - Updated by Junie
{
    "TYPE": "negative",
    "CATEGORY": "insufficient thoroughness; PowerShell errors",
    "EXPECTATION": "User wants complete, validated follow-through and PowerShell-compatible commands without Unix-only tools.",
    "NEW INSTRUCTION": "WHEN giving shell commands on Windows THEN use PowerShell syntax, avoid Unix tools, and show executed commands and outputs"
}

