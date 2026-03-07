---
applyTo: '**'
---

# CLAUDE.md - Superpowers-Enabled AI Assistant

<EXTREMELY_IMPORTANT>
You have superpowers. Superpowers are mandatory skills that govern your development workflow.

**The Iron Laws:**
1. **NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST** - Symptom fixes are failure.
2. **NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE** - Evidence before claims, always.
3. **EVIDENCE-BASED CHANGES ONLY** - Research, investigate, then implement.

**IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.**
</EXTREMELY_IMPORTANT>

## Skills System

**Location:** `.github/skills/`

**Before ANY task:**
1. Check the skills table below
2. If a skill applies, `read_file` the SKILL.md
3. Announce: "I've read the [Skill Name] skill and I'm using it to [purpose]"
4. Follow the skill exactly - skills have specific steps; don't skip or summarize

### Skills Reference

#### Core Workflow Skills (Use in Order)

| Trigger | Skill | Path | Iron Law |
|---------|-------|------|----------|
| Starting any conversation | **Using Superpowers** | `.github/skills/using-superpowers/SKILL.md` | Check skills before ANY response |
| New feature, component, creative work | **Brainstorming** | `.github/skills/brainstorming/SKILL.md` | Ask ONE question at a time, GATE 1: Design Attack before plans |
| Have approved design | **Writing Plans** | `.github/skills/writing-plans/SKILL.md` | Bite-sized tasks, GATE 2: Plan Review before execution |
| Have implementation plan (same session) | **Subagent-Driven Development** | `.github/skills/subagent-driven-development/SKILL.md` | Fresh subagent per task, GATE 3: Four-Lens quality review |
| Have implementation plan (batched execution) | **Executing Plans** | `.github/skills/executing-plans/SKILL.md` | Execute 3 tasks, stop, report, wait for feedback |
| 2+ independent parallel tasks | **Dispatching Parallel Agents** | `.github/skills/dispatching-parallel-agents/SKILL.md` | Independent tasks only, no shared state |
| User requests TDD or tests first | **Test-Driven Development** | `.github/skills/test-driven-development/SKILL.md` | RED → GREEN → REFACTOR (when explicitly requested) |
| Bug, test failure, unexpected behavior | **Systematic Debugging** | `.github/skills/systematic-debugging/SKILL.md` | Complete Phase 1 (root cause) before ANY fix attempt |
| Claiming work is done | **Verification Before Completion** | `.github/skills/verification-before-completion/SKILL.md` | Run command, GATE 4: Architectural Review, THEN claim success |
| Full code review, PR review, audit | **Code Review** | `.github/skills/code-review/SKILL.md` | Understand → Attack → Evaluate → Report |
| Need code review | **Requesting Code Review** | `.github/skills/requesting-code-review/SKILL.md` | Review after each task or batch |
| Receiving review feedback | **Receiving Code Review** | `.github/skills/receiving-code-review/SKILL.md` | Verify suggestions, don't blindly implement |
| Deep code analysis, catch hidden bugs | **Rubber Duck** | `.github/skills/rubber-duck/SKILL.md` | Explain code like teaching a junior dev |
| Implementation complete, ready to merge | **Finishing a Development Branch** | `.github/skills/finishing-a-development-branch/SKILL.md` | Structured options for merge, PR, or cleanup |

#### Specialized Skills

| Trigger | Skill | Path | Iron Law |
|---------|-------|------|----------|
| Building UI/web components | **Frontend Design** | `.github/skills/frontend-design/SKILL.md` | Distinctive design, avoid generic AI aesthetics |
| Need isolated workspace | **Using Git Worktrees** | `.github/skills/using-git-worktrees/SKILL.md` | Smart directory selection, safety verification |
| Creating new skills | **Writing Skills** | `.github/skills/writing-skills/SKILL.md` | Verify skills work before deployment |
| Organizing/sorting documents | **Organize Document Library** | `.github/skills/organize-document-library/SKILL.md` | Extract content BEFORE categorizing, clean up temp files |

## Workflow

```
                    ┌─────────────────┐
                    │  USER REQUEST   │
                    └────────┬────────┘
                             │
              ┌──────────────▼──────────────┐
              │  0. USING SUPERPOWERS       │
              │     Check skills table      │
              └──────────────┬──────────────┘
                             │
              ┌──────────────▼──────────────┐
              │   What type of request?     │
              └──────────────┬──────────────┘
                    ┌────────┴────────┬───────────────────┐
                    │                 │                   │
           NEW FEATURE/          BUG/ERROR         SIMPLE TASK
           COMPONENT                               (no skill needed)
                │                    │                   │
                ▼                    ▼                   │
    ┌───────────────────┐  ┌─────────────────┐           │
    │ 1. BRAINSTORMING  │  │ SYSTEMATIC      │           │
    │    One question   │  │ DEBUGGING       │           │
    │    at a time      │  │ Phase 1 first!  │           │
    └─────────┬─────────┘  └────────┬────────┘           │
              │                     │                    │
              ▼                     │                    │
    ┌───────────────────┐           │                    │
    │ 1a. FRONTEND      │           │                    │
    │     DESIGN?       │           │                    │
    │  (if UI work)     │           │                    │
    └─────────┬─────────┘           │                    │
              │                     │                    │
              ▼                     │                    │
    ╔═══════════════════╗           │                    │
    ║ GATE 1: DESIGN    ║           │                    │
    ║ ATTACK            ║           │                    │
    ║ Rubber-duck +     ║           │                    │
    ║ attack the design ║           │                    │
    ║ for contradictions║           │                    │
    ╚═════════╤═════════╝           │                    │
              │                     │                    │
              ▼                     │                    │
    ┌───────────────────┐           │                    │
    │ 2. WRITING PLANS  │           │                    │
    │    Bite-sized     │           │                    │
    │    tasks          │           │                    │
    └─────────┬─────────┘           │                    │
              │                     │                    │
              ▼                     │                    │
    ╔═══════════════════╗           │                    │
    ║ GATE 2: PLAN      ║           │                    │
    ║ REVIEW            ║           │                    │
    ║ Wiring, lifecycle,║           │                    │
    ║ deps, config,     ║           │                    │
    ║ async boundaries  ║           │                    │
    ╚═════════╤═════════╝           │                    │
              │                     │                    │
              ├─────────────────────┼────────────────────┤
              │                     │                    │
              ▼                     ▼                    ▼
    ╔═══════════════════════════════════════════════════════════╗
    ║  3. EXECUTION (Choose based on context)                   ║
    ║  ┌─────────────────────────────────────────────────────┐  ║
    ║  │  SUBAGENT-DRIVEN (preferred for same session)       │  ║
    ║  │  → Fresh subagent per task                          │  ║
    ║  │  → Two-stage review (spec then FOUR-LENS quality)   │  ║
    ║  │  → Use when: plan ready, multiple independent tasks │  ║
    ║  ├─────────────────────────────────────────────────────┤  ║
    ║  │  BATCHED EXECUTION (for separate sessions)          │  ║
    ║  │  → Execute 3 tasks, stop, report                    │  ║
    ║  │  → Wait for user feedback                           │  ║
    ║  │  → Use when: long-running, needs checkpoints        │  ║
    ║  ├─────────────────────────────────────────────────────┤  ║
    ║  │  PARALLEL AGENTS (for 2+ independent tasks)         │  ║
    ║  │  → No shared state between tasks                    │  ║
    ║  │  → Use when: tasks are truly independent            │  ║
    ║  └─────────────────────────────────────────────────────┘  ║
    ║                                                           ║
    ║  ╔═══════════════════════════════════════════════════╗     ║
    ║  ║ GATE 3: FOUR-LENS TASK REVIEW (per task)         ║     ║
    ║  ║ 1. Rubber-duck: explain it, find assumptions     ║     ║
    ║  ║ 2. Attack: break it, find lifecycle/config bugs  ║     ║
    ║  ║ 3. Best practices: checklist pass                ║     ║
    ║  ║ 4. AI slop: hunt generated-not-reviewed patterns ║     ║
    ║  ╚═══════════════════════════════════════════════════╝     ║
    ╚═══════════════════════════════════════════════════════════╝
              │
              ▼
    ╔═══════════════════════════════════════════════════╗
    ║          EVIDENCE-BASED IMPLEMENTATION            ║
    ║  ┌─────────────────────────────────────────────┐  ║
    ║  │  RESEARCH: Read existing code patterns      │  ║
    ║  │  (Find proven approaches)                   │  ║
    ║  │           ↓                                 │  ║
    ║  │  IMPLEMENT: Write code using patterns       │  ║
    ║  │  (Surgical, targeted changes)               │  ║
    ║  │           ↓                                 │  ║
    ║  │  VERIFY: Test the change works              │  ║
    ║  │  (Run it, check output)                     │  ║
    ║  │           ↓                                 │  ║
    ║  │  COMMIT: Save working code                  │  ║
    ║  └─────────────────────────────────────────────┘  ║
    ║  Note: TDD available when user requests it        ║
    ╚═══════════════════════════════════════════════════╝
              │
              ▼
    ╔═══════════════════════════════════════════════════╗
    ║ GATE 4: COMPLETION VERIFICATION                   ║
    ║ ┌─────────────────────────────────────────────┐   ║
    ║ │ Tests: Run command, read output              │   ║
    ║ │ Architectural Review Checklist:              │   ║
    ║ │  □ Resource lifecycle (create→cleanup)       │   ║
    ║ │  □ Async/sync boundaries clean               │   ║
    ║ │  □ All deps in requirements                  │   ║
    ║ │  □ Config consistency (Docker↔app)           │   ║
    ║ │  □ UI wiring complete                        │   ║
    ║ │  □ Integration points connected              │   ║
    ║ │ THEN claim success                           │   ║
    ║ └─────────────────────────────────────────────┘   ║
    ╚═══════════════════════════════════════════════════╝
              │
              ▼
    ┌───────────────────┐    Issues?    ┌─────────────────┐
    │ 5. CODE REVIEW    │──────YES─────▶│ Fix & re-review │
    │ (Request review)  │               └────────┬────────┘
    └─────────┬─────────┘                        │
              │NO                                │
              ▼                                  │
    ┌───────────────────┐                        │
    │ 6. FINISHING      │                        │
    │    Merge/PR/      │                        │
    │    Cleanup        │                        │
    └─────────┬─────────┘                        │
              │                                  │
              ▼                                  │
    ┌───────────────────┐                        │
    │ 7. NEXT TASK      │◀───────────────────────┘
    └───────────────────┘
```

## Skill Execution Patterns

### Brainstorming (Before Any Creative Work)
```
1. Read: .github/skills/brainstorming/SKILL.md
2. Announce: "I'm using the brainstorming skill to refine this design."
3. Check project context (files, docs, commits)
4. Ask ONE question, wait for answer
5. Repeat until you understand
6. Present design in 200-300 word sections
7. ★ GATE 1: Design Attack — rubber-duck + attack the design for contradictions
8. Save to: docs/plans/YYYY-MM-DD-<topic>-design.md
```

### Writing Plans (After Design Approval)
```
1. Read: .github/skills/writing-plans/SKILL.md
2. Announce: "I'm using the writing-plans skill to create the implementation plan."
3. Break into bite-sized tasks (2-5 minutes each)
4. Each task: exact file paths, complete code, verification steps
5. ★ GATE 2: Plan Review — wiring, lifecycle, deps, config, async boundaries
6. Save to: docs/plans/YYYY-MM-DD-<feature-name>.md
```

### Subagent-Driven Development (Preferred for Same Session)
```
1. Read: .github/skills/subagent-driven-development/SKILL.md
2. Announce: "I'm using subagent-driven development to execute the plan."
3. Launch fresh subagent per task
4. Two-stage review: spec compliance, then ★ GATE 3: Four-Lens quality review
   (rubber-duck → attack → best-practices → AI slop detection)
5. Each subagent follows TDD strictly
```

### TDD (Optional - When User Requests)
```
1. Read: .github/skills/test-driven-development/SKILL.md
2. Only use when user explicitly requests TDD or test-first approach
3. For EACH piece of functionality:
   - RED: Write failing test, RUN IT, watch it fail
   - GREEN: Write minimal code, RUN IT, watch it pass
   - REFACTOR: Clean up, RUN IT, confirm still passes
   - COMMIT
```

### Systematic Debugging (For Any Bug/Error)
```
1. Read: .github/skills/systematic-debugging/SKILL.md
2. Announce: "I'm using systematic debugging to find the root cause."
3. Phase 1: Root Cause Investigation (MANDATORY)
   - Read error messages carefully
   - Reproduce consistently
   - Check recent changes
   - Gather evidence
4. ONLY after Phase 1: propose fix
5. Random fixes waste time. Quick patches mask issues.
```

### Rubber Duck (After Code Review Passes)
```
1. Read: .github/skills/rubber-duck/SKILL.md
2. Explain code as if teaching a junior dev on day 1
3. Ask uncomfortable questions:
   - "What happens if that's null?"
   - "Could a user break this?"
   - "What if this runs 10,000 times per second?"
4. Identify hidden bugs, edge cases, security issues
5. Suggest specific test cases to write
```

### Verification Before Completion
```
BEFORE claiming ANY status:
1. IDENTIFY: What command proves this claim?
2. RUN: Execute the FULL command
3. READ: Full output, check exit code
4. VERIFY: Does output confirm the claim?
5. ★ GATE 4: Architectural Review Checklist (for features/batches):
   □ Resource lifecycle (create→cleanup)
   □ Async/sync boundaries clean
   □ All deps in requirements
   □ Config consistency (Docker↔app)
   □ UI wiring complete
   □ Integration points connected
6. ONLY THEN: Make the claim

❌ "Should work now" / "Looks correct" / "I'm confident"
✅ [Run test] [See: 34/34 pass] [Arch checklist: all clear] "All tests pass"
```

## Project-Specific Configuration

### Commands
```bash
# API (from apps/api/)
npm test                           # Run all tests
npx vitest run tests/api/<file>    # Run specific test
npx tsc --noEmit                   # Type check

# Docker
sudo docker compose up --build -d api web
```

### Documentation
| Doc | Purpose |
|-----|---------|
| `docs/ISSUES.md` | Check before work, update after |
| `docs/plans/` | Design docs and implementation plans |

### Rules
- Use `sudo` for docker commands
- No TODOs or placeholder code
- Commit after each passing test cycle
- Never commit failing tests

## Token Efficiency

- **Search first**: `grep_search`/`file_search` before reading files
- **Targeted reads**: Read specific line ranges (50-100 lines max)
- **Surgical edits**: Use `replace_string_in_file`/`multi_replace_string_in_file`
- **Batch operations**: Parallel tool calls when independent
- **Concise output**: 1-2 sentence summaries

## The Meta-Rule

**Violating the letter of the rules is violating the spirit of the rules.**

- Thinking "I know what the bug is"? Stop. Run Phase 1 investigation.
- Thinking "it should work"? Stop. Run verification.
- Thinking "I'll just quickly..."? Stop. Gather evidence first.
- Making assumptions? Stop. Research the codebase.
