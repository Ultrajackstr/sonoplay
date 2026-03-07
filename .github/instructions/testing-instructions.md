---
applyTo: '**'
---

# Testing Skill — Optional TDD Methodology

## Philosophy

**Test-Driven Development (TDD)** is available when requested by the user. By default, focus on evidence-based implementation with verification.

**When user requests TDD:**
```
RED → GREEN → REFACTOR
 │       │         │
 │       │         └── Improve code quality, tests still pass
 │       └── Write minimal code to pass the test
 └── Write a failing test that defines expected behavior
```

**Default approach (when TDD not requested):**
```
RESEARCH → IMPLEMENT → VERIFY → COMMIT
 │            │           │         │
 │            │           │         └── Save working code
 │            │           └── Test that change works
 │            └── Write code using proven patterns
 └── Find existing patterns in codebase
```

## Test Types

| Type | Purpose | Scope | Speed |
|------|---------|-------|-------|
| **Unit** | Test isolated functions/classes | Single module, mocked dependencies | Fast (<100ms) |
| **Integration** | Test module interactions | Multiple modules, real DB/services | Medium (<5s) |
| **E2E** | Test complete user workflows | Full stack, browser/API | Slow (<30s) |
| **Security** | Test auth, validation, injection | Attack vectors, edge cases | Medium |

### When to Use Each Type

- **Unit**: Pure functions, utilities, business logic, data transformations
- **Integration**: API routes, database operations, service interactions
- **E2E**: Critical user journeys, checkout flows, authentication
- **Security**: Login/logout, password handling, input sanitization, RBAC

---

## TDD Workflow (When Explicitly Requested)

**Use this workflow ONLY when user explicitly asks for test-driven development.**

### Phase 1: BEFORE Implementation

1. **Understand the requirement** — What should the code do?
2. **Write failing tests first** — Define expected behavior in test form
3. **Run tests to confirm they fail** — RED state confirms test is valid
4. **Commit failing tests** — `test: add failing tests for [feature]`

```bash
# Example: Adding a new API endpoint
# BEFORE writing any route code:
1. Write test: "POST /api/items should create item and return 201"
2. Write test: "POST /api/items with invalid data should return 400"
3. Write test: "POST /api/items without auth should return 401"
4. Run tests → all fail → commit
```

### Phase 2: DURING Implementation

1. **Write minimal code to pass ONE test** — Don't over-engineer
2. **Run tests after each change** — Confirm progress
3. **Refactor if needed** — Tests protect against regressions
4. **Repeat until all tests pass** — GREEN state

```bash
# Implementation loop:
while tests_failing:
    write_minimal_code()
    run_tests()
    if tests_pass:
        refactor_if_needed()
        run_tests()  # Ensure refactor didn't break anything
```

---

## Evidence-Based Workflow (Default)

**Use this workflow by default unless user requests TDD.**

### Phase 1: Research

1. **Understand the requirement** — What needs to be built/fixed?
2. **Search for existing patterns** — `grep_search`, `semantic_search`, `read_file`
3. **Study proven approaches** — How does the codebase solve similar problems?
4. **Identify dependencies** — What files/functions will be affected?

### Phase 2: Implementation

1. **Write code using proven patterns** — Extract and adapt working code
2. **Make surgical changes** — Minimal, targeted modifications
3. **Follow existing conventions** — Match code style and structure
4. **Document complex logic** — Comments for non-obvious decisions

### Phase 3: Verification

1. **Run the code** — Execute and observe behavior
2. **Check outputs** — Confirm expected results
3. **Test edge cases** — Try invalid inputs, boundary conditions
4. **Verify integration** — Ensure it works with rest of system

### Phase 4: Commit

1. **Review changes** — Read the diff
2. **Commit with clear message** — Describe what and why
3. **Document if needed** — Update docs for significant changes

### Phase 3: AFTER Implementation

1. **Add edge case tests** — Empty inputs, large data, special characters
2. **Add error path tests** — Network failures, timeouts, invalid states
3. **Add regression tests** — If fixing a bug, add test that would have caught it
4. **Run full test suite** — Ensure no regressions
5. **Check coverage** — Meet thresholds before committing

---

## Project Setup

### First-Time Setup for Any Project

Before using this skill on a new project, create a project-specific test configuration file:

**Create `.github/instructions/testing-project.instructions.md`** with:

```markdown
---
applyTo: '**'
---

# Project Test Configuration

## Stack
- **Language**: [e.g., TypeScript, Python, Go]
- **Framework**: [e.g., Express, FastAPI, Gin]
- **Test Runner**: [e.g., Vitest, Jest, Pytest, go test]
- **E2E Framework**: [e.g., Playwright, Cypress, none]

## Commands
- **Run all tests**: `[command]`
- **Run unit tests**: `[command]`
- **Run integration tests**: `[command]`
- **Run E2E tests**: `[command]`
- **Run with coverage**: `[command]`
- **Run single file**: `[command] [file]`

## File Conventions
- **Test location**: `[e.g., __tests__/, tests/, *.test.ts adjacent]`
- **Unit test pattern**: `[e.g., *.test.ts, *_test.py]`
- **Integration test pattern**: `[e.g., *.integration.test.ts]`
- **E2E test pattern**: `[e.g., *.e2e.test.ts, e2e/*.spec.ts]`

## Mocking Strategy
- **External APIs**: [e.g., MSW, nock, responses, httpretty]
- **Database**: [e.g., in-memory SQLite, test containers, prisma mock]
- **Time/Date**: [e.g., vi.useFakeTimers(), freezegun]
- **Environment**: [e.g., dotenv-flow, test.env file]

## Fixtures & Factories
- **Location**: `[e.g., tests/fixtures/, tests/factories/]`
- **Factory library**: `[e.g., Fishery, Factory Boy, custom]`

## Coverage Thresholds
- **Critical paths**: 90%+ [list critical modules]
- **Business logic**: 80%+
- **API routes**: 70%+
- **Overall minimum**: 75%

## CI/CD Integration
- **Pre-commit hook**: [yes/no, command]
- **CI test command**: [command]
- **Coverage reporting**: [tool, e.g., Codecov, Coveralls]
```

### AI Agent Instructions

When starting work on a new project:

1. **Check for existing test config** — Look for `.github/instructions/testing-project.instructions.md`
2. **If missing, create it** — Analyze the project structure, package.json/pyproject.toml/go.mod, and create the config
3. **Verify test setup works** — Run the test command to confirm it executes
4. **Then proceed with TDD workflow**

---

## Pre-Commit Requirements

**Tests MUST pass before committing.** No exceptions.

### Commit Checklist

```markdown
Before `git commit`:
- [ ] All new code has corresponding tests
- [ ] All tests pass locally
- [ ] No skipped tests (`.skip`, `@pytest.mark.skip`) without documented reason
- [ ] Coverage thresholds met for changed files
- [ ] No console.log/print debugging left in tests
```

### Commit Message Conventions

```
test: add unit tests for UserService.create
test: add integration tests for POST /api/users
test: add e2e tests for user registration flow
test: add security tests for authentication bypass
fix: resolve flaky test in subscription runner
```

---

## Test Categories by Change Type

| Change Type | Required Tests |
|-------------|---------------|
| **New Feature** | Unit + Integration + (E2E for user-facing) |
| **Bug Fix** | Regression test that reproduces the bug |
| **Refactor** | Existing tests must pass (no new tests needed) |
| **Security Fix** | Security test + regression test |
| **API Change** | Integration tests for all affected endpoints |
| **Database Change** | Integration tests with real DB operations |
| **UI Component** | Unit tests for logic, E2E for critical flows |

---

## Coverage Guidelines

### Tiered Thresholds

| Code Category | Minimum Coverage | Examples |
|---------------|------------------|----------|
| **Critical** | 90%+ | Auth, payments, encryption, core business rules |
| **Business Logic** | 80%+ | Services, validators, data processing |
| **API/Routes** | 70%+ | Controllers, route handlers, middleware |
| **UI Components** | 60%+ | React components, templates |
| **Overall Project** | 75%+ | Aggregate across all files |

### What NOT to Test (Use Judgment)

- Generated code (Prisma client, GraphQL types)
- Simple getters/setters with no logic
- Framework boilerplate
- Third-party library internals

### Coverage Commands

After implementing tests, verify coverage:

```bash
# Check coverage meets thresholds
[coverage command from project config]

# Focus on changed files
git diff --name-only | xargs [coverage command]
```

---

## Test Quality Principles

### Good Tests Are:

1. **Isolated** — No test depends on another test's state
2. **Deterministic** — Same input = same output, every time
3. **Fast** — Unit tests < 100ms, integration < 5s
4. **Readable** — Test name describes the behavior being tested
5. **Maintainable** — DRY setup, clear arrange/act/assert structure

### Test Naming Convention

```
[Unit Under Test] [Scenario] [Expected Result]

Examples:
- "UserService.create with valid data returns new user"
- "POST /api/login with invalid password returns 401"
- "CartTotal with discount code applies percentage off"
```

### Arrange-Act-Assert Pattern

```typescript
test('UserService.create with valid data returns new user', async () => {
  // Arrange — Set up test data and dependencies
  const userData = { email: 'test@example.com', name: 'Test User' };
  
  // Act — Execute the code under test
  const result = await userService.create(userData);
  
  // Assert — Verify the expected outcome
  expect(result.id).toBeDefined();
  expect(result.email).toBe(userData.email);
});
```

---

## Handling Flaky Tests

Flaky tests (pass sometimes, fail sometimes) are **bugs**. Fix them immediately.

Common causes and fixes:

| Cause | Fix |
|-------|-----|
| Race conditions | Add proper async/await, use waitFor() |
| Time-dependent | Mock Date/time, avoid real delays |
| Order-dependent | Isolate test data, reset state between tests |
| External services | Mock all external calls |
| Random data | Use seeded random or fixed test data |

---

## Summary

1. **Tests first** — Write failing tests before implementation
2. **All types** — Unit, integration, E2E, security as appropriate
3. **Three phases** — Before (RED), During (GREEN), After (REFACTOR + edge cases)
4. **Project config** — Create stack-specific config for each project
5. **No commit without green** — All tests must pass
6. **Coverage matters** — Meet tiered thresholds, focus on critical paths
