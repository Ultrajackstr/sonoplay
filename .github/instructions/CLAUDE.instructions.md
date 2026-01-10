---
applyTo: '**'
---

# CLAUDE.md - Superpowers-Enabled AI Assistant

**Starting the Docker stack** - always use ./start-dev.sh to start the full stack in DEV.  DO NOT run Prod stack (docker-compose.yml) in dev unless requested.  Ensure Dev and Prod parity.

<EXTREMELY_IMPORTANT>
You have superpowers. Superpowers are mandatory skills that govern your development workflow.

**The Iron Laws:**
1. **NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST** - Write code before test? Delete it. Start over.
2. **NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST** - Symptom fixes are failure.
3. **NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE** - Evidence before claims, always.
4. **NO BREAKING CHANGES WITHOUT MIGRATION PLAN** - The app has been released to the public.  We can no longer require users to reinstall, reset database, etc.  Any changes must include a migration path.

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

| Trigger | Skill | Path | Iron Law |
|---------|-------|------|----------|
| New feature, component, creative work | **Brainstorming** | `skills/brainstorming/SKILL.md` | Ask ONE question at a time, get design approval before ANY code |
| Have approved design | **Writing Plans** | `skills/writing-plans/SKILL.md` | Bite-sized tasks (2-5 min), exact file paths, complete code |
| Have implementation plan (same session) | **Subagent-Driven Development** | `skills/subagent-driven-development/SKILL.md` | Fresh subagent per task, two-stage review (spec then quality) |
| Have implementation plan (batched execution) | **Executing Plans** | `skills/executing-plans/SKILL.md` | Execute 3 tasks, stop, report, wait for feedback |
| Writing ANY code | **Test-Driven Development** | `skills/test-driven-development/SKILL.md` | RED → GREEN → REFACTOR → QUALITY GATE. No exceptions. |
| Bug, test failure, unexpected behavior | **Systematic Debugging** | `skills/systematic-debugging/SKILL.md` | Complete Phase 1 (root cause) before ANY fix attempt |
| Claiming work is done | **Verification Before Completion** | `skills/verification-before-completion/SKILL.md` | Run command, read output, THEN claim success |
| Need code review | **Requesting Code Review** | `skills/requesting-code-review/SKILL.md` | Review after each task or batch |
| Building UI/web components | **Frontend Design** | `.github/skills/frontend-design/` | Distinctive design, avoid generic AI aesthetics |
| Deep code analysis | **Rubber Duck** | `.github/skills/rubber-duck/` | Explain code like teaching, catch hidden bugs |

## Workflow

```
                    ┌─────────────────┐
                    │  USER REQUEST   │
                    └────────┬────────┘
                             │
              ┌──────────────▼──────────────┐
              │   What type of request?     │
              └──────────────┬──────────────┘
                    ┌────────┴────────┐
                    │                 │
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
    │ 2. WRITING PLANS  │           │                    │
    │    🦆💀🤖 Quality  │           │                    │
    │    analysis FIRST │           │                    │
    └─────────┬─────────┘           │                    │
              │                     │                    │
              ▼                     │                    │
    ┌───────────────────┐           │                    │
    │ 3. EXECUTION      │           │                    │
    │    (subagent or   │◀──────────┴────────────────────┘
    │     batched)      │
    └─────────┬─────────┘
              │
              ▼
    ╔═══════════════════════════════════════════════════════════════╗
    ║          TDD WITH BUILT-IN QUALITY (NO AFTERTHOUGHT)         ║
    ║  ┌─────────────────────────────────────────────────────────┐  ║
    ║  │  PHASE 0: PLANNING                                      │  ║
    ║  │  🦆 Edge cases? | 💀 Attack vectors? | 🤖 AI Slop?     │  ║
    ║  │  BLOCKS → RED phase                                     │  ║
    ║  │           ↓                                             │  ║
    ║  │  PHASE 1: RED - Write FAILING tests                     │  ║
    ║  │  Priority: Failures → Errors → Attacks → Happy path    │  ║
    ║  │  🦆 Missing tests? | 💀 Attack tests?                  │  ║
    ║  │  BLOCKS → GREEN phase                                   │  ║
    ║  │           ↓                                             │  ║
    ║  │  PHASE 2: GREEN - Write MINIMAL code                    │  ║
    ║  │  🦆 Logic bugs? | 💀 Security holes? | 🤖 AI Slop?     │  ║
    ║  │  BLOCKS test execution                                  │  ║
    ║  │  (Auto-fixes high confidence issues)                    │  ║
    ║  │           ↓                                             │  ║
    ║  │  PHASE 3: REFACTOR - Clean up                           │  ║
    ║  │  🦆 Edge cases? | 💀 Prod failures? | 🤖 AI Slop?      │  ║
    ║  │  BLOCKS → COMMIT                                        │  ║
    ║  │           ↓                                             │  ║
    ║  │  COMMIT (Quality built in, not checked after)           │  ║
    ║  └─────────────────────────────────────────────────────────┘  ║
    ╚═══════════════════════════════════════════════════════════════╝
              │
              ▼
    ┌───────────────────┐
    │ 4. VERIFICATION   │
    │    Run command    │
    │    Read output    │
    │    THEN claim     │
    └─────────┬─────────┘
              │
              ▼
    ┌───────────────────┐    Issues?    ┌─────────────────┐
    │ 5. CODE REVIEW    │──────YES─────▶│ Fix & re-review │
    └─────────┬─────────┘               └────────┬────────┘
              │NO                                │
              │◀─────────────────────────────────┘
              ▼
    ┌───────────────────┐    Issues?    ┌─────────────────┐
    │ 6. RUBBER DUCK    │──────YES─────▶│ Fix & re-review │
    │    Explain code   │               └────────┬────────┘
    │    like teaching  │                        │
    └─────────┬─────────┘                        │
              │NO                                │
              │◀─────────────────────────────────┘
              ▼
    ┌───────────────────┐
    │ 7. Next Task      │
    └───────────────────┘

## Skill Execution Patterns

### Brainstorming (Before Any Creative Work)
```
1. Read: .github/skills/superpowers/skills/brainstorming/SKILL.md
2. Announce: "I'm using the brainstorming skill to refine this design."
3. Check project context (files, docs, commits)
4. Ask ONE question, wait for answer
5. Repeat until you understand
6. Present design in 200-300 word sections
7. Save to: docs/plans/YYYY-MM-DD-<topic>-design.md
```

### Writing Plans (After Design Approval)
```
1. Read: .github/skills/writing-plans/SKILL.md
2. Announce: "I'm using the writing-plans skill to create the implementation plan."
3. BEFORE tasks: Run 🦆💀🤖 pre-analysis
   - Edge cases, attack vectors, AI slop risks
4. Break into bite-sized tasks (2-5 minutes each)
5. Each task: exact file paths, complete code, verification steps, quality gates
6. Save to: docs/plans/YYYY-MM-DD-<feature-name>.md
```

### TDD (During All Implementation)
```
1. Read: .github/skills/test-driven-development/SKILL.md
2. For EACH piece of functionality:
   
   PHASE 0 - PLANNING:
   - 🦆 Identify edge cases (null, empty, boundaries)
   - 💀 Identify attack vectors (injection, XSS, bypass)
   - 🤖 Check for vague requirements
   - BLOCKS → RED until documented
   
   PHASE 1 - RED:
   - Write failure tests FIRST (null, errors, attacks)
   - Write happy path tests LAST
   - 🦆 Check test coverage
   - 💀 Check attack test coverage
   - 🤖 Check for generic test names
   - BLOCKS → GREEN until all tests written
   - RUN TESTS, watch them FAIL
   
   PHASE 2 - GREEN:
   - Write minimal code
   - 🦆 Review logic for bugs
   - 💀 Review for security holes
   - 🤖 Check for TODOs, generic names, slop
   - BLOCKS test run until critical issues fixed
   - Auto-fixes high confidence issues
   - RUN TESTS, watch them PASS
   
   PHASE 3 - REFACTOR:
   - Clean up code
   - 🦆 Validate edge case handling
   - 💀 Check production failure risks
   - 🤖 Remove useless comments, dead code
   - BLOCKS → COMMIT until critical issues fixed
   - RUN TESTS, confirm still passes
   
   COMMIT with descriptive message
```

### Systematic Debugging (For Any Bug/Error)
```
1. Read: .github/skills/superpowers/skills/systematic-debugging/SKILL.md
2. Announce: "I'm using systematic debugging to find the root cause."
3. Phase 1: Root Cause Investigation (MANDATORY)
   - Read error messages carefully
   - Reproduce consistently
   - Check recent changes
   - Gather evidence
4. ONLY after Phase 1: propose fix
5. Random fixes waste time. Quick patches mask issues.
```

### Verification Before Completion
```
BEFORE claiming ANY status:
1. IDENTIFY: What command proves this claim?
2. RUN: Execute the FULL command
3. READ: Full output, check exit code
4. VERIFY: Does output confirm the claim?
5. ONLY THEN: Make the claim

❌ "Should work now" / "Looks correct" / "I'm confident"
✅ [Run test] [See: 34/34 pass] "All tests pass"
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

- Thinking "skip TDD just this once"? Stop. That's rationalization.
- Thinking "I know what the bug is"? Stop. Run Phase 1.
- Thinking "it should work"? Stop. Run verification.
- Thinking "I'll just quickly..."? Stop. Read the skill.
