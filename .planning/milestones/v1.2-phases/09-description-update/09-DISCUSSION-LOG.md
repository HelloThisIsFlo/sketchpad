# Phase 9: Description Update - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-20
**Phase:** 09-description-update
**Areas discussed:** Description tone, Naming in descriptions, Newline separator, Read-first guidance

---

## Description Tone

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit guardrails | Keep the "Do / Do NOT" list — agents need firm boundaries | :heavy_check_mark: |
| Soft guidance | Positive guidance only, no prohibitions | |
| Minimal | Just describe what the tool does | |

**User's choice:** Explicit guardrails
**Notes:** Draft style with "Do NOT" list stays.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, mention storage limit | Agents should know about the 20KB cap | |
| No, let the error speak | Error message is sufficient | :heavy_check_mark: |

**User's choice:** No storage limit mention
**Notes:** "In the normal use case, they should never reach that size anyway, and if they do, then maybe our description of the tool is not correct."

---

## Naming in Descriptions

| Option | Description | Selected |
|--------|-------------|----------|
| Sketchpad | Matches project name, server name, tool names | :heavy_check_mark: |
| Scratchpad | Draft's choice, more generic | |
| Generic (no name) | Just "shared persistence layer" | |

**User's choice:** Sketchpad

---

| Option | Description | Selected |
|--------|-------------|----------|
| Lowercase "sketchpad" | More natural, like "your clipboard" | |
| Capitalized "Sketchpad" | Treats it as a named product/tool | :heavy_check_mark: |

**User's choice:** Capitalized "Sketchpad"

---

## Newline Separator

| Option | Description | Selected |
|--------|-------------|----------|
| Smart newline | Only add \n if existing doesn't end with one | |
| Always double newline | Insert \n\n between entries | |
| Always single newline | Always prepend \n regardless | :heavy_check_mark: |

**User's choice:** Always single newline
**Notes:** Simple and predictable.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, briefly mention | One line in mode parameter description | :heavy_check_mark: |
| No, implicit | Standard behavior, don't document | |

**User's choice:** Yes, briefly mention newline behavior in description.

---

## Read-first Guidance

| Option | Description | Selected |
|--------|-------------|----------|
| Contextual nudge | "Check for context left by a previous session" | |
| Always read first | "Always read at the start of every task" | |
| No guidance | Just describe what the tool returns | |

**User's initial choice:** Contextual nudge, but with notes: "I think it should be more user-led. I don't want my agents to check the Sketchpad without me telling them to."

**Follow-up:**

| Option | Description | Selected |
|--------|-------------|----------|
| What not when | Describe what it contains, not when to read | |
| Mention user-directed reading | Explicitly say "read when the user asks" | :heavy_check_mark: |

**User's choice:** Mention user-directed reading

---

| Option | Description | Selected |
|--------|-------------|----------|
| Both triggers (user + cross-session) | Write when user asks OR agent needs handoff | |
| User-directed only | Only write when user explicitly asks | :heavy_check_mark: |

**User's choice:** User-directed only
**Notes:** Full user control. No proactive agent writes. Significant departure from draft todo which encouraged autonomous cross-session persistence.

---

## Claude's Discretion

- Exact wording of Field(description=...) for `content` and `mode` parameters
- Final sentence-level polish of docstrings
- Whether to use bullet lists or prose in the docstring body

## Deferred Ideas

None — discussion stayed within phase scope
