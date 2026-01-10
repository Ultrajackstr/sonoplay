---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---

# Writing Plans

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, how to test it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume they are a skilled developer, but know almost nothing about our toolset or problem domain. Assume they don't know good test design very well.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Context:** This should be run in a dedicated worktree (created by brainstorming skill).

**Save plans to:** `docs/plans/YYYY-MM-DD-<feature-name>.md`

## Bite-Sized Task Granularity

**Each step is one action (2-5 minutes):**
- "Write the failing test" - step
- "Run it to make sure it fails" - step
- "Implement the minimal code to make the test pass" - step
- "Run the tests and make sure they pass" - step
- "Commit" - step

## Plan Document Header

**Every plan MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

## Task Structure with Built-In Quality

For EACH task, include quality checkpoints:

```markdown
### Task N: [Component Name]

**Quality Requirements:**
- Edge Cases: [null userId, empty array, timeout]
- Attack Vectors: [SQL injection in search, XSS in name]
- AI Slop Watch: [No TODOs, no generic names, specific error messages]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

**Step 1: Planning Phase - Quality Gate**
Run 🦆 and 💀 analysis:
- Edge cases: userId null/undefined, empty search string
- Security: sanitize search input, check permissions
- AI Slop: ensure descriptive names, no placeholders

**Step 2: Write failing tests (RED)**
Priority order: failure cases → error paths → attacks → happy path

```python
# Failure test first
def test_rejects_null_user_id():
    with pytest.raises(ValueError, match="userId required"):
        function(None)

# Attack vector test
def test_prevents_sql_injection():
    malicious = "1' OR '1'='1"
    result = function(malicious)
    assert result == []  # Should find nothing

# Happy path last
def test_valid_input():
    result = function(123)
    assert result.id == 123
```

**Step 3: Test Coverage Quality Gate**
Verify tests cover:
- ✅ Null case tested
- ✅ SQL injection tested
- ✅ Happy path tested
- ❌ Missing: empty array case - ADD TEST

**Step 4: Run tests to verify they fail**
Run: `pytest tests/path/test.py -v`
Expected: 3 FAIL (function not defined)

**Step 5: Write minimal implementation**

```python
def function(user_id):
    if not user_id:
        raise ValueError("userId required")
    
    # Parameterized query prevents injection
    return db.query("SELECT * FROM users WHERE id = ?", [user_id])
```

**Step 6: Code Quality Gate**
Check implementation:
- 🦆 Logic: Validates input before query ✅
- 💀 Security: Parameterized query prevents injection ✅
- 🤖 AI Slop: No TODOs, descriptive names ✅

**Step 7: Run tests to verify they pass**
Run: `pytest tests/path/test.py -v`
Expected: 3 PASS

**Step 8: Refactor + Final Quality Gate**
- 🦆 Edge cases: Handles null ✅, What about DB timeout? ⚠️
- 💀 Production: Add retry logic for transient failures? ⚠️
- 🤖 AI Slop: Remove any useless comments ✅

**Step 9: Commit**
```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add user lookup with injection protection

- Validates userId before query
- Uses parameterized queries
- Tests cover null input and SQL injection"
```
```

## Plan Quality Review (Before Saving)

**MANDATORY before saving plan to docs/plans/.**

After writing all tasks, review the complete plan:

### 🦆 Plan Completeness

**Check:**
- Are all edge cases from requirements covered in tasks?
- Do tasks follow RED-GREEN-REFACTOR cycle?
- Are quality gates defined for each phase?
- Is the task order logical?

### 💀 Plan Feasibility

**Check:**
- Are file paths exact and verifiable?
- Are tasks small enough (2-5 min each)?
- Are verification steps specific with expected output?
- Are security tasks prioritized appropriately?

### 🤖 Plan Quality

**Hard Block (Must Fix):**
- Vague task titles ("Update API", "Fix bug")
- Missing verification steps
- No quality gates defined
- TODOs or "implement later"
- Generic code examples without specifics

**Auto-Fix:**
- Add missing verification commands
- Split tasks > 10 minutes into smaller steps
- Add quality gate checkpoints
- Make task titles more specific

**After Review:**
1. Fix all auto-fixable issues
2. Add 🦆💀🤖 annotations to tasks needing extra attention
3. Ensure requirements section is complete
4. Verify every task has quality gates

## Execution Handoff

## Remember
- Exact file paths always
- Complete code in plan (not "add validation")
- Exact commands with expected output
- Reference relevant skills with @ syntax
- DRY, YAGNI, TDD, frequent commits

## Pre-Planning Quality Analysis

**MANDATORY before defining ANY tasks.**

Before writing the task list, run quality analysis on requirements:

### 🦆 Rubber Duck Requirements

For each major component, identify:

**Edge Cases:**
- Null/undefined/empty inputs
- Boundary values (0, -1, MAX_INT, empty arrays, huge strings)
- Missing required data
- Invalid formats
- State transition issues

**External Dependencies:**
- API timeouts/errors
- Database failures
- Cache unavailable
- File system errors

**Error Propagation:**
- How should errors bubble up?
- What gets logged vs returned?
- Cleanup on partial failure?

**Output:** Document edge cases in plan before tasks

### 💀 Be-a-Shithead Requirements  

For each feature, identify:

**Security Risks:**
- User input going into queries/file paths/commands?
- Auth/authorization checks needed?
- Rate limiting required?
- Sensitive data logged?

**Data Integrity:**
- Need transactions?
- Need unique constraints?
- Orphaned record risks?
- Race conditions?

**Performance:**
- N+1 query potential?
- Pagination needed?
- Caching strategy?

**Output:** Document security/integrity concerns before tasks

### 🤖 AI Slop in Requirements

Check requirements for slop:

**Hard Block (Must Fix Before Planning):**
- Vague acceptance criteria ("make it work", "handle errors")
- No mention of edge cases or error paths
- "TODO: figure out X" in requirements
- Generic feature names without specifics
- No security considerations mentioned

**Output:** Clear, specific requirements with edge cases identified

### Requirements Quality Gate

**BLOCKS task definition until:**
- ✅ All edge cases identified and documented
- ✅ Security risks identified and mitigation planned
- ✅ Data integrity strategy defined
- ✅ No vague or TODO requirements

Add a Requirements section to plan header:

```markdown
# Feature Implementation Plan

**Requirements:**
- Edge Cases: null userId, empty search, 10k+ results
- Security: Sanitize search input, check user permissions, rate limit
- Data Integrity: Wrap in transaction, enforce unique constraint
- Error Handling: Return 400 for invalid input, 500 for server errors
```

## Task Structure with Built-In Quality

**"Plan complete and saved to `docs/plans/<filename>.md`. Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?"**

**If Subagent-Driven chosen:**
- **REQUIRED SUB-SKILL:** Use superpowers:subagent-driven-development
- Stay in this session
- Fresh subagent per task + code review

**If Parallel Session chosen:**
- Guide them to open new session in worktree
- **REQUIRED SUB-SKILL:** New session uses superpowers:executing-plans
