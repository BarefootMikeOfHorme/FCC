# Game Plan: Naming Convention Audit and Fix

## Objective
To identify and document all instances of "free-claude-code" and related naming conventions throughout the codebase that may cause confusion with actual Claude Code, particularly focusing on:
1. File and directory names
2. File contents (documentation, code comments, strings, etc.)

## Phase 1: Discovery - COMPLETED
1. ✅ Recursively scanned all directories for folder/file names containing "free-claude-code"
2. ✅ Recursively scanned all files for content containing:
   - "free-claude-code"
   - "claude" (in contexts that might cause confusion)
   - "agents" (in contexts that might cause confusion)
   - Related variations

## Phase 2: Documentation - COMPLETED
1. ✅ Created list of all problematic file/directory names in NAMING_ISSUES_PATHS.txt
2. ✅ Created list of all problematic content matches in NAMING_ISSUES_CONTENT.txt
3. ✅ Included file paths, line numbers, and context for content matches

## Phase 3: Analysis - COMPLETED
1. ✅ Reviewed findings to distinguish between:
   - Actual problematic naming that should be changed (documentation files like CLAUDE.md, AGENTS.md)
   - Internal package/import references that are correct (src/free_claude_code/...)
   - Console command references that are correctly prefixed (fcc-*)
   - Legitimate references to actual Claude Code (where interaction is intended)

## Phase 4: Recommendations - READY FOR EXECUTION

### PRIMARY ISSUE IDENTIFIED:
The main naming confusion stems from two files in the project root:
- `CLAUDE.md`
- `AGENTS.md`

These files could be mistaken for actual Claude Code documentation, which was the specific concern raised by the user.

### RECOMMENDED ACTIONS:

#### HIGH PRIORITY (Addressing User's Specific Concern):
1. **Rename CLAUDE.md → fcc-claude.md**
2. **Rename AGENTS.md → fcc-agents.md**
3. **Update internal references to these files:**
   - In the renamed files: Update the "Keep ... identical" directive to reference the new file names
   - In ARCHITECTURE.md: Update `[fcc-agents.md](fcc-agents.md)` and `[fcc-claude.md](fcc-claude.md)` links to point to the new file names
   - Check any other files that might reference these documentation files

#### MEDIUM PRIORITY (Consistency Improvements):
- Consider adding a brief disclaimer in the renamed documentation files clarifying that this is Free Claude Code (fcc-), not actual Claude Code
- Ensure all user-facing documentation consistently uses appropriate terminology

#### LOW PRIORITY (Internal Package Name - NOT RECOMMENDED AT THIS TIME):
- Renaming `src/free_claude_code/` to `src/fcc/` would be a MAJOR breaking change requiring:
  - Version bump to 6.0.0+ (per CLAUDE.md versioning rules)
  - Updates to ~1000+ import statements throughout codebase
  - pyproject.toml modifications
  - Significant disruption for existing users
  - The console commands already appropriately use the fcc- prefix, addressing the core branding concern
  - **Not recommended unless a major version update is already planned**

### FILES TO MODIFY:
1. Rename: CLAUDE.md → fcc-claude.md
2. Rename: AGENTS.md → fcc-agents.md
3. Update: fcc-claude.md (formerly CLAUDE.md) - update "Keep ... identical" directive
4. Update: fcc-agents.md (formerly AGENTS.md) - update "Keep ... identical" directive
5. Update: ARCHITECTURE.md - fix links to the documentation files

### VERIFICATION STEPS:
After implementing changes:
1. Verify all internal links and references work correctly
2. Ensure documentation displays properly
3. Check for any broken references in code or documentation
4. Confirm console commands (fcc-server, fcc-claude, etc.) still work correctly

## EXECUTION READY:
The game plan has been completed through all phases. The specific files to rename and update have been identified and documented. Ready for implementation of the naming convention fixes.