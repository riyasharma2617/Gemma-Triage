# Project Reorganization Design

**Date:** 2026-05-04  
**Status:** Approved  
**Scope:** Flatten double-nested directory structure; consolidate duplicate AI config files; relocate stray PDF

---

## Problem

The workspace root (`s:/Gemma-Triage/`) has two structural issues:

1. **Double nesting with typo** — all project files live at `Gemma-traige/gemma-triage/` (note: "traige" is a typo). This adds two meaningless path segments to every file reference.

2. **Five duplicate AI config files** — `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.cursorrules`, `.windsurfrules` at the root all contain identical copies of the code-review-graph MCP instructions. The real project config (with build rules, architecture, TDD rules, etc.) is the inner `Gemma-traige/gemma-triage/CLAUDE.md`.

3. **Stray PDF** — `DeepSeek - Into the Unknown.pdf` sits loose in the project directory with no home.

---

## Target Structure

```
s:/Gemma-Triage/
  android/                          # moved from Gemma-traige/gemma-triage/android/
  model/                            # moved from Gemma-traige/gemma-triage/model/
  scripts/                          # moved from Gemma-traige/gemma-triage/scripts/
  docs/                             # moved from Gemma-traige/gemma-triage/docs/
    references/
      DeepSeek - Into the Unknown.pdf   # relocated stray PDF
    API_REFERENCE.md
    DEPLOYMENT.md
    USER_MANUAL.md
    riya-pipeline-walkthrough.md
    superpowers/
      specs/
      plans/
  CLAUDE.md                         # real inner CLAUDE.md + MCP section appended
  .claude/                          # unchanged (settings.json, skills/)
  .code-review-graph/               # unchanged
  .mcp.json                         # unchanged
```

**Removed:**
- `Gemma-traige/` (entire shell, now empty)
- `AGENTS.md` (duplicate)
- `GEMINI.md` (duplicate)
- `.cursorrules` (duplicate)
- `.windsurfrules` (duplicate)
- Root `CLAUDE.md` (replaced by real inner one)
- `Gemma-traige/gemma-triage/README.md` (empty file)

---

## Approach

Use `git mv` for all file moves to preserve git history and `git blame` across the reorganization commit.

### Execution Order

1. **Remove duplicates from root** — `git rm CLAUDE.md AGENTS.md GEMINI.md .cursorrules .windsurfrules`
2. **Merge MCP instructions into inner CLAUDE.md** — append the code-review-graph MCP section to `Gemma-traige/gemma-triage/CLAUDE.md` so nothing is lost
3. **Move project directories to root** — `git mv` for `android/`, `model/`, `scripts/`, `docs/`
4. **Create `docs/references/` and move PDF** — `git mv` the PDF into the new subfolder
5. **Move inner CLAUDE.md to root** — `git mv Gemma-traige/gemma-triage/CLAUDE.md CLAUDE.md`
6. **Remove empty README** — `git rm Gemma-traige/gemma-triage/README.md`
7. **Commit** — single commit: `chore: flatten project structure and consolidate AI configs`

### Why `git mv`

- Preserves `git log --follow` and `git blame` for all source files
- Critical during active hackathon development (debugging, attribution)
- No history loss vs. delete+re-add approach

---

## What Does NOT Change

- All source code is identical — this is purely a structural move
- `.claude/` settings, hooks, and skills are unchanged
- `.mcp.json` is unchanged
- `.code-review-graph/` graph database is unchanged
- All internal file references within source code are unaffected (package names, imports, asset paths are relative to the Android project root, not the workspace root)
- Inner `CLAUDE.md` content is fully preserved; only the MCP section is appended

---

## Risk

**Low.** This is a pure rename/move operation with no code changes. The only non-trivial step is merging the MCP instructions block into `CLAUDE.md` — risk is that content is accidentally omitted, mitigated by appending verbatim rather than rewriting.
