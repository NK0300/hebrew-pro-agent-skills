<!-- hebrew-pro-agent-skills:begin -->
<!-- version: 1.0.0 profile: full -->
<!-- Managed by hebrew-pro-agent-skills. Re-run install.sh to update. -->

# Core orchestrator

## When to use

This is the only always-on skill. Keep it in context. Open another skill only when its description matches the task. Do not paste every skill into the prompt.

## Rules

1. Talk to the user in Hebrew. Write natural Hebrew, not English syntax with Hebrew words.
2. Write code, identifiers, comments, commit messages, and pull-request text in English.
3. Write every string a person sees in the product in Hebrew, including loading, empty, and error states.
4. Route by task. Do not load every skill.
   - APIs, validation, data, server state: `fullstack-architect`
   - CSS, layout, components, RTL: `ui-rtl-system`
   - Auth, secrets, XSS, headers, the release gate: `qa-security-gate`
   - GSAP, scroll, canvas, motion: `interactive-motion`
   - Hebrew copy, nikud, dates, numbers: `hebrew-content-nikud`
   - Children, audio, WCAG, privacy: `kids-edtech-a11y`
   - Tests, Playwright, visual RTL: `testing-strategy`
   - Env, CI, Docker, preview, rollback: `devops-deploy`
5. Work in three beats.
   - Plan: a short plan, the risks, and the skill names you will open.
   - Build: the smallest change that matches this repository.
   - Verify: run real commands. Report each command, its exit status, and the result. Then list what you did not verify. Never invent a green check.
6. A rule may bend when a one-line comment states why and the blast radius is small. Auth, privacy, secrets, and the verification report do not bend.
7. Prefer libraries and patterns already in the repository once you have seen them.
8. Nikud stays in stored text. Do not strip combining marks. Fold a copy when search must ignore vowels.

Installed copies live in the tool's own folder (`.cursor/rules`, `.claude/skills/<name>/SKILL.md`, `.github/instructions`, `.windsurf/rules`, `.devin/rules`). Read the file that matches the task.

## Examples

### Good

User-facing reply: "שמרתי את השינוי. לא הרצתי בדיקת דפדפן, אז אני לא יודע אם היישור תקין במובייל."

```text
Verified:
- `bash script/test-install.sh` — exit 0 — install cases passed
Not verified:
- Windows `install.ps1`. PowerShell is not installed in this environment.
```

### Bad

```text
All tests passed.
```

No command was run. Also bad: answering the user in English by default, or naming a function in Hebrew.

## Checklist

- [ ] The reply to the user is Hebrew.
- [ ] Code, comments, and commits are English.
- [ ] UI copy is Hebrew.
- [ ] Only the skills that match the task were opened.
- [ ] The verification note names real commands and names the gaps.
<!-- hebrew-pro-agent-skills:end -->
