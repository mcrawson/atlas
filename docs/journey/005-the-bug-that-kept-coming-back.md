# Journey Post #5: The Bug That Kept Coming Back

**Date:** 2026-03-22
**Topic:** QC Loop Debugging, React vs Static HTML, Defense in Depth

---

## LinkedIn Post

**Journey Post #6: The bug that kept coming back**

Spent the morning chasing a QC loop that wouldn't stop finding "new" issues.

Fixed the code. Ran QC. Failed.
Fixed again. Ran QC. Different failures.
Fixed THOSE. Ran QC. Original failures came back.

5 attempts. Still failing.

**Then I asked the right question:**

"What is QC actually *looking at*?"

Turns out: QC evaluates the HTML preview. My React app's preview? An empty `<div id="root"></div>`. All the features existed — in .tsx files QC never checked.

**The fix wasn't in the code. It was in understanding what QC could see.**

Rebuilt as static HTML. Same features. QC passed first try.

**Lessons:**
1. When something "should work" but doesn't — you're checking the wrong layer
2. Match your validation tools to what they can actually evaluate
3. Fix the code, then write the test, then move on. Defense in depth.

Building ATLAS taught me this today. Shipping the fix to prevent it from happening on the next project.

---

**Hashtags:** #BuildingInPublic #SoftwareEngineering #Debugging #AI #ATLAS

---

## X/Twitter Thread

**Tweet 1 (Hook):**
QC kept finding bugs.

Fixed them. New bugs appeared.
Fixed those. Old bugs came back.

5 attempts. Still failing.

Then I checked what QC was actually *looking at*.

---

**Tweet 2:**
My React app rendered features dynamically.

QC evaluated the HTML preview.

The preview showed: `<div id="root"></div>`

QC saw: empty page, missing features.

The code was fine. QC was blind to it.

---

**Tweet 3:**
Rebuilt as static HTML. Same features, visible in markup.

QC passed immediately.

The bug wasn't in my code.
It was in assuming my tools could see what I could see.

---

**Tweet 4:**
Lesson: When you're sure something works but validation fails —

Stop fixing.
Start asking: "What is this tool actually checking?"

Different layer = different reality.

---

**Tweet 5:**
Patched the fix. Added tests. Updated the docs.

Because fixing a bug once isn't enough.
You have to make sure it *stays* fixed.

Building @ATLAS_ai in public. Day by day.

---

## Session Context

**What happened:**
- QC kept finding issues on project 100 after multiple fix attempts
- Auto-fix loop ran 5 times, still failing
- Root cause: QC evaluates HTML preview, React SPA shows empty `<div id="root">`
- Solution: Rebuilt as static HTML, simplified Business Brief to match MVP scope
- Added defensive code for `tech_stack` context (handles both dict and string)
- Created 6 tests in `test_mason.py` to prevent regression

**Files changed:**
- `atlas/agents/mason.py` — tech_stack validation fix
- `tests/test_agents/test_mason.py` — new test file (6 tests)

**Key insight:**
When user says "doesn't work" and you think it does — you're checking the wrong layer.
