---
name: rubber-duck
description: Explain code like teaching a junior dev on day 1. Forces detailed analysis to catch hidden bugs, edge cases, security issues, and performance problems.
---


# Rubber Duck Debugging: The Junior Developer Explanation Method

This skill implements a proven debugging technique: by forcing yourself (or Claude) to explain code in exhaustive detail to someone who knows nothing, you catch bugs that skip past normal code review.

The premise is simple: **If you can't explain what your code does in every scenario, you don't fully understand it—and that's where bugs hide.**

## Core Principle

Treat every code explanation as if you're teaching someone on their first day who will ask uncomfortable questions like:
- "What happens if that's null?"
- "Could a user break this?"
- "What if this runs 10,000 times per second?"
- "Why did you assume that would always be true?"

## How to Use This Skill

### Mode 1: Phase Analysis (TDD Integration)

**Used during TDD cycle at specific phase boundaries.**

#### Phase 0: Planning Analysis

**Before writing ANY tests, explain the requirements:**

```
🦆 Rubber Duck Planning:

**What are we building?**
[Explain feature in simple terms]

**Edge Cases to Handle:**
  - Null/undefined inputs: userId could be null, what happens?
  - Boundary values: What if array is empty? 10k items?
  - Missing data: What if API returns incomplete response?
  - Invalid formats: What if date string is malformed?
  - State issues: What if user is deleted mid-operation?

**External Dependencies:**
  - Database: What if connection drops during transaction?
  - External API: What if it times out or returns 500?
  - Cache: What if Redis is unavailable?
  - File system: What if disk is full?

**Questions to Answer:**
  - How should errors propagate?
  - What cleanup is needed on failure?
  - Are state transitions atomic?
```

**BLOCKS RED phase until all edge cases documented in plan.**

#### Phase 1: Test Coverage Check

**After writing tests, before GREEN phase:**

```
🦆 Test Coverage Review:

**Tests Written:**
  ✅ test_valid_input
  ✅ test_null_userId
  ❌ Missing: empty array case
  ❌ Missing: database timeout scenario
  ❌ Missing: concurrent request race condition

**Assumptions in Tests:**
  - Assumes database always responds (add timeout test)
  - Assumes single-threaded execution (add concurrency test)

**BLOCK:** Add missing tests before writing implementation.
```

**BLOCKS GREEN phase until all identified edge cases have tests.**

#### Phase 2: Logic Review

**After writing code, before running tests:**

```
🦆 Logic Walkthrough:

**Line-by-Line Analysis:**
  Line 12: `const user = await db.findUser(userId)`
    → What if userId is null? ⚠️ Missing check
    → What if user not found? Returns undefined
    
  Line 15: `user.email.toLowerCase()`
    → Assumes user exists ⚠️ Will crash if null
    → Assumes email exists ⚠️ Could be undefined
    
  Line 23: `await externalAPI.call(data)`
    → No timeout ⚠️ Could hang forever
    → No retry on failure ⚠️ Transient errors not handled

**Auto-Fix (HIGH Confidence):**
  → Add null check for user before line 15
  → Add null check for user.email
  → Add timeout to API call (30 seconds)
  
**BLOCK for Human Review:**
  → Retry strategy unclear - exponential backoff vs fixed delay?
```

**AUTO-FIXES high-confidence issues. BLOCKS on unclear decisions.**

#### Phase 3: Edge Case Validation

**After REFACTOR, before COMMIT:**

```
🦆 Final Edge Case Check:

**From Planning (Revisited):**
  ✅ Null input handled
  ✅ Database timeout test passes
  ❌ Missing: What if user deleted between check and update?
  ❌ Missing: Memory usage with 10k array items?

**Production Scenarios:**
  - Graceful degradation if cache unavailable? ⚠️ No
  - Monitoring/logging for debugging? ✅ Yes
  - Transaction rollback on partial failure? ⚠️ No

**BLOCK:** Add transaction wrapper before committing.
```

**BLOCKS commit until critical edge cases addressed.**

### AI Slop Detection (All Modes)

**Integrated into every rubber duck analysis:**

#### Code Quality Issues

**Hard Block - Must Fix:**

1. **Useless Comments**
   ```typescript
   // BAD: Sets the user
   setUser(user);
   
   // GOOD: Clears session cache to prevent stale auth state after logout
   clearSessionCache();
   ```
   
2. **Missing "Why" Explanations**
   ```typescript
   // BAD: No explanation
   await sleep(1000 * attempt);
   
   // GOOD: Explains WHY
   // Exponential backoff prevents thundering herd on upstream service
   await sleep(1000 * Math.pow(2, attempt));
   ```

3. **Unclear Logic Without Context**
   ```typescript
   // BAD: Magic number
   if (status === 3) { }
   
   // GOOD: Named constant
   const STATUS_COMPLETED = 3;
   if (status === STATUS_COMPLETED) { }
   ```

**Output Format:**
```
🤖 AI Slop Detected:

Line 23: Comment "// processes data" is useless - REMOVE
Line 45: Magic number 3 - add explanatory constant
Line 67: Complex logic without explanation - add WHY comment

Auto-fixed:
  ✅ Removed useless comment line 23
  ✅ Added constant STATUS_COMPLETED = 3
```

#### Documentation Issues

**Hard Block - Must Fix:**

1. **Comments That Restate Code**
   - "Gets the user" for `getUser()`
   - "Returns true if valid" for function named `isValid()`

2. **Missing Context for Complex Logic**
   - Bitwise operations without explanation
   - Performance optimizations without reasoning
   - Workarounds without documenting the bug

3. **Over-Documentation of Obvious Code**
   ```typescript
   // BAD: Over-documented
   // Increment counter by one
   counter++;
   
   // GOOD: Document WHY when non-obvious
   // Skip first item (header row)
   for (let i = 1; i < items.length; i++) {  }
   ```

**Auto-Fix Criteria:**
- Remove useless "what" comments → HIGH confidence
- Add "why" explanations for complex logic → BLOCK for human (need context)
- Replace magic numbers with constants → HIGH confidence

### Mode 2: As a Quality Gate (Legacy - Post-Implementation)

**When called after code is written (not during TDD):**

1. **Analyze changes in git diff** - Focus on recent changes
2. **Rapid edge case review** - What edge cases exist? Are they tested?
3. **Assumption validation** - What assumptions could break?
4. **Security quick scan** - Any injection risks? Auth bypasses?

**Output Format for Quality Gate:**
```
🦆 Rubber Duck Review:

**Edge Cases:**
  - [ ] Tested: Empty array input
  - [x] Missing: Negative number handling
  
**Assumptions:**
  - Assumes user.email always exists (could be null)
  - Assumes API returns 200 (no retry logic)

**Security:**
  - No issues found

**Auto-fix Confidence: HIGH**
  → Adding null check for user.email (line 42)
  → Adding negative number validation (line 18)
```

**Auto-Fix Criteria:**
- **HIGH confidence**: Missing null checks, unhandled promise rejections, obvious validation gaps
- **BLOCK for human review**: Architectural questions, performance tradeoffs, security with subtle implications

### Mode 3: For Single Code Segments (Educational)

Paste your code snippet and Claude will:
1. Explain what each part does in plain language
2. Identify assumptions and where they could fail
3. Point out edge cases you haven't handled
4. Highlight security, performance, and reliability issues
5. Suggest specific test cases you should write

### For Entire Repositories
Provide the repo structure or key files and Claude will:
1. Map the code architecture and data flow
2. Identify brittleness points where failures cascade
3. Find coupling issues that make bugs hard to track
4. Spot patterns that indicate technical debt
5. Highlight areas most likely to have hidden bugs

## Explanation Framework by Code Type

### API Endpoints
**The Junior Dev Questions:**
- What happens if someone sends malformed JSON?
- What if they omit required fields?
- What if they send the request 1000 times in a second?
- Could they inject SQL, NoSQL queries, or shell commands?
- What happens when the database is slow or down?
- How does this handle concurrent requests to the same resource?
- What if the authentication token is expired but not detected?
- Could someone access data they shouldn't by manipulating IDs?

**What to Explain:**
```markdown
1. **Request Flow**: Trace from request arrival to response
2. **Validation**: What checks exist? What's missing?
3. **Authentication & Authorization**: Who can call this? How is it verified?
4. **Rate Limiting**: What stops abuse?
5. **Error Handling**: What happens when things fail?
6. **Side Effects**: What else does this change in the system?
7. **Rollback Strategy**: If this fails midway, what's left in a bad state?
8. **Load Behavior**: What breaks under 100, 1000, 10000 concurrent requests?
```

### Database Queries
**The Junior Dev Questions:**
- What happens with 0 rows? 1 row? 1 million rows?
- Is this query N+1 territory?
- What if someone deleted the foreign key record between queries?
- Could this lock tables under load?
- What's the explain plan say? (Are we doing a table scan?)
- What happens if the transaction times out?
- Could this deadlock with other queries?

**What to Explain:**
```markdown
1. **Query Plan**: Is this using indexes? Scanning entire tables?
2. **Result Set Size**: How many rows typically? At maximum?
3. **Locking Behavior**: What locks does this acquire? For how long?
4. **Transaction Boundaries**: Where does it commit? What if it rolls back?
5. **Race Conditions**: What happens if two run simultaneously?
6. **Missing Data**: What if the JOIN returns nothing?
7. **Performance Degradation**: When does this get slow?
8. **Connection Pooling**: Does this hold connections longer than needed?
```

### Async/Promise Code
**The Junior Dev Questions:**
- What happens if the promise rejects?
- Do you have an unhandled rejection floating around?
- What's the execution order really?
- Could these run in the wrong order?
- What if the API takes 5 minutes to respond?
- Are you leaking memory by not cleaning up event listeners?
- What happens if the user navigates away mid-operation?

**What to Explain:**
```markdown
1. **Execution Order**: Step through EXACTLY when each thing runs
2. **Error Propagation**: How do errors bubble up? Where are they caught?
3. **Cancellation**: Can this be stopped? Should it be?
4. **State Management**: What if state changes while waiting?
5. **Memory Leaks**: What's held in closures? Does it get released?
6. **Retry Logic**: What happens on timeout or failure?
7. **Race Conditions**: Can multiple calls interfere with each other?
8. **Zombie Callbacks**: Could this callback fire after component unmounts?
```

### UI/Component Code
**The Junior Dev Questions:**
- What happens if props change while rendering?
- What if the user clicks the button 10 times in 1 second?
- What if the API returns an error or empty data?
- Could the component re-render infinitely?
- What happens on slow networks or offline?
- What if props are undefined or null?
- Does this cause unnecessary re-renders of children?

**What to Explain:**
```markdown
1. **Render Cycle**: When does this re-render? Why?
2. **State Updates**: Are they batched? Could they race?
3. **Props Changes**: What happens when each prop changes?
4. **Event Handling**: What if events fire rapidly or unexpectedly?
5. **Loading States**: How does the user know something is happening?
6. **Error States**: What displays when things fail?
7. **Edge Cases**: Empty lists? Missing data? Very long strings?
8. **Performance**: Does this cause unnecessary expensive operations?
9. **Memory**: Are event listeners and subscriptions cleaned up?
10. **Accessibility**: Can keyboard and screen reader users use this?
```

### Authentication & Authorization Code
**The Junior Dev Questions:**
- Could someone bypass this by tampering with cookies/tokens?
- What if the session expires mid-request?
- Could someone escalate privileges?
- What happens if the auth service is down?
- Are passwords/secrets logged anywhere?
- Could timing attacks reveal valid usernames?
- What if someone's permissions change while they're logged in?

**What to Explain:**
```markdown
1. **Token/Session Validation**: How is identity verified? Where could it fail?
2. **Permission Checks**: Who can access what? Are checks server-side?
3. **Secrets Management**: Where are secrets stored? Are they exposed in logs/errors?
4. **Attack Vectors**: What could a malicious user try?
5. **Session Management**: How long do sessions last? How are they invalidated?
6. **Fallback Behavior**: What happens when auth services are unavailable?
7. **Audit Trail**: Is access logged? Could that logging be defeated?
```

### Batch/Background Jobs
**The Junior Dev Questions:**
- What happens if this runs twice simultaneously?
- What if it crashes halfway through?
- How do you know if it succeeded or failed?
- What if the data it's processing changes while running?
- Could this run indefinitely?
- What happens when it processes more data than expected?

**What to Explain:**
```markdown
1. **Idempotency**: Can this safely run multiple times?
2. **Partial Completion**: What's the state if it fails midway?
3. **Recovery**: How do you restart or resume?
4. **Resource Usage**: Memory, CPU, connections—what are the limits?
5. **Timing**: How long should this take? What's the timeout?
6. **Monitoring**: How do you know if it's stuck or failed?
7. **Data Consistency**: What if source data changes during processing?
8. **Concurrency**: What prevents two instances from conflicting?
```

### Configuration/Infrastructure Code
**The Junior Dev Questions:**
- What happens if this config value is wrong?
- Could someone inject commands through environment variables?
- What's the default if this isn't set?
- Will this work across dev/staging/prod?
- What happens if secrets aren't available?
- Could a typo bring down production?

**What to Explain:**
```markdown
1. **Required Values**: What MUST be set? What are sensible defaults?
2. **Validation**: How do you know if config is valid before using it?
3. **Security**: Could config be used to inject code or access secrets?
4. **Environment Differences**: Does this work in all environments?
5. **Change Impact**: What breaks if this config changes?
6. **Secrets**: How are secrets accessed? Could they leak?
7. **Failure Modes**: What happens with missing or malformed config?
```

## Red Flags to Always Look For

When explaining any code, actively hunt for these common bug patterns:

### Trust Issues
- **User Input**: Do we trust it? Is it validated, sanitized, rate-limited?
- **External APIs**: Do we handle errors, timeouts, schema changes?
- **Environment Variables**: Are defaults safe? Is validation present?
- **Database Data**: Could it be null, empty, malformed, huge?

### State Problems
- **Race Conditions**: Can two operations interfere?
- **Stale Data**: Could cached data be out of date?
- **Orphaned State**: What if a cleanup operation doesn't run?
- **Implicit State**: Are we depending on order of operations?

### Resource Management
- **Memory Leaks**: Are listeners, timers, subscriptions cleaned up?
- **Connection Pools**: Do connections get released?
- **File Handles**: Are files/streams closed on all paths?
- **Locks**: Could we deadlock? Is there a timeout?

### Error Handling Gaps
- **Unhandled Exceptions**: What throws that we don't catch?
- **Ignored Errors**: Do we log errors but then continue?
- **Error Swallowing**: Do we catch errors and do nothing?
- **Cascading Failures**: Does one failure cause a chain reaction?

### Performance Traps
- **N+1 Queries**: Do we query in a loop?
- **Unbounded Growth**: Can lists, logs, queues grow without limit?
- **Blocking Operations**: Do we wait synchronously for slow operations?
- **Missing Indexes**: Are we scanning large tables?

### Security Blindspots
- **Injection**: SQL, NoSQL, Command, XSS—where's user input used?
- **Authorization**: Are checks only client-side?
- **Secrets Exposure**: Could secrets leak through logs, errors, URLs?
- **IDOR**: Could users access resources by changing IDs?

## Output Format

For each code segment, provide:

1. **Plain English Summary**: What this code is supposed to do
2. **Line-by-Line Walkthrough**: Explain each significant part
3. **Assumptions & Dependencies**: What MUST be true for this to work
4. **Edge Cases Identified**: Scenarios that aren't handled
5. **Potential Bugs**: Specific things that could go wrong
6. **Attack Vectors**: How a malicious user could exploit this
7. **Performance Issues**: Where this could get slow or resource-intensive
8. **Test Cases Needed**: Specific tests that would catch these issues

## Example Response Pattern

```markdown
### What This Code Does
[Plain English explanation]

### Step-by-Step Breakdown
1. Line X-Y: [What it does, why it matters]
2. Line Z: [What it does, what could go wrong]

### Critical Assumptions
- Assumes that [X] is always [Y]
- Depends on [Z] being available
- Expects data in format [A]

### Edge Cases Not Handled
- ❌ What if the input is null/empty?
- ❌ What happens with concurrent access?
- ❌ How does this behave under load?

### Bugs & Security Issues Found
🐛 **Bug**: [Specific issue]
   - Impact: [What breaks]
   - Reproduction: [How to trigger]
   - Fix: [What to change]

🔒 **Security**: [Vulnerability]
   - Risk: [What an attacker could do]
   - Mitigation: [How to fix]

⚡ **Performance**: [Issue]
   - When: [Conditions that trigger slowdown]
   - Why: [Root cause]
   - Solution: [Optimization approach]

### Recommended Tests
```typescript
describe('Component', () => {
  it('should handle null input gracefully', () => {
    // Test case that catches the bug
  });
});
```

### Questions for the Developer
- [ ] Have you tested this with [edge case]?
- [ ] What happens if [assumption] isn't true?
- [ ] How does this behave when [unusual condition]?


## Special Instructions

1. **Be Skeptical**: Question every assumption. If the code assumes something "will always be true," explain what happens when it isn't.

2. **Think Like an Attacker**: For any code that touches user input, network requests, or sensitive data, explicitly describe how a malicious user could abuse it.

3. **Consider Scale**: Everything works fine with 10 users. What breaks at 10,000? At 100,000?

4. **Trace Data Flow**: Follow data from entry point to storage/output. Where could it be corrupted, lost, or leaked?

5. **Surface Hidden Complexity**: If the code looks simple but depends on complex behavior elsewhere, call that out.

6. **Don't Assume Best Practices**: If error handling is missing, say so. If there's no validation, point it out. If it's not thread-safe, mention it.

## When NOT to Use This Skill

This skill is for debugging and catching bugs. Don't use it when:
- You just want the code to be written for you
- You want general programming advice
- You're looking for style or formatting improvements only
- You need help with an algorithm design (use this AFTER you have code)

## The Goal


By the end of the explanation, you should have:
- A clear mental model of what the code does
- A list of specific bugs and edge cases to fix
- Concrete test cases to write
- Awareness of security and performance implications
- Confidence that you understand every line

## Capture Bugs

When bugs are identified, document them clearly with:
- **Description**: What the bug is
- **Impact**: What breaks or could be exploited
- **Reproduction Steps**: How to trigger the bug
- **Suggested Fix**: What changes are needed to resolve it
- **Test Case**: A specific test that would catch this bug in the future

Remember: **If explaining the code reveals questions you can't answer, those questions are where bugs hide.**
