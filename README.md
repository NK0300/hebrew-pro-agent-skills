# כישורי סוכן בעברית

<div dir="rtl" lang="he">

מאגר ציבורי של כישורי סוכן לפיתוח מוצרים בעברית, מימין לשמאל. נכתב עבור מפתחים שמדברים עברית ועובדים ב-Cursor, Claude Code, GitHub Copilot, Windsurf, ובכלים שקוראים `AGENTS.md` (Codex, Gemini CLI).

המקור האחד הוא `skills/`. מחולל בונה מתוכו את הקובץ שכל כלי באמת קורא. ההתקנה לא דורסת `CLAUDE.md` או `AGENTS.md` קיימים: היא ממזגת בלוק מסומן, ושומרת גיבוי עם חותמת זמן לפני החלפה של קובץ שכבר היה במקום.

החוזה הקצר, והיחיד שנשאר דלוק תמיד: מדברים עם האדם בעברית. קוד, הערות וקומיטים באנגלית. כל טקסט שהמשתמש רואה במוצר בעברית טבעית. שאר הכישורים נטענים לפי המשימה.

## התקנה

שכפול, ואז התקנה לתוך פרויקט:

```bash
git clone https://github.com/NK0300/hebrew-pro-agent-skills.git
cd hebrew-pro-agent-skills
./install.sh --mode project --target /path/to/your-app --profile kids-hebrew --tools cursor,claude
```

התקנה גלובלית, לכל הפרויקטים על המחשב:

```bash
./install.sh --mode global --profile full
```

אחרי שתג `v1.0.0` קיים, אפשר גם:

```bash
curl -fsSL https://raw.githubusercontent.com/NK0300/hebrew-pro-agent-skills/v1.0.0/install.sh | bash -s -- --profile full --target .
```

קראו את `install.sh` לפני הרצה מהרשת. שכפול המאגר בטוח יותר.

Windows:

```powershell
.\install.ps1 --mode project --target C:\src\app --profile web --tools cursor,copilot
```

## הסרה

```bash
./install.sh --uninstall --target /path/to/your-app
./install.sh --mode global --uninstall
```

ההסרה מוחקת את הבלוק המסומן ומשאירה את שאר הקובץ. קובץ שההתקנה יצרה נמחק. קובץ שהיה קיים לפני כן חוזר מהגיבוי, אלא אם ערכתם אותו אחרי ההתקנה. אז הוא נשאר כמו שהוא.

`--dry-run` מדפיס את הפעולות ולא כותב כלום.

## פרופילים

| פרופיל | מה נכנס |
| --- | --- |
| `full` | כל תשעת הכישורים |
| `web` | ליבה, API, RTL, אבטחה, תנועה, עברית וניקוד, בדיקות |
| `backend` | ליבה, API, אבטחה, בדיקות, פריסה |
| `kids-hebrew` | ליבה, RTL, אבטחה, תנועה, ניקוד, ילדים והנגשה, בדיקות |

## כלים

| כלי | בפרויקט | גלובלי |
| --- | --- | --- |
| Cursor | `.cursor/rules/*.mdc` | `~/.cursor/rules/*.mdc` |
| Claude Code | `.claude/skills/<name>/SKILL.md` ובלוק ב-`CLAUDE.md` | `~/.claude/skills/` ו-`~/.claude/CLAUDE.md` |
| GitHub Copilot | `.github/copilot-instructions.md` ו-`.github/instructions/*.instructions.md` | `~/.copilot/copilot-instructions.md` ו-`~/.copilot/instructions/` |
| Windsurf / Devin | `.windsurf/rules/*.md` ו-`.devin/rules/*.md` | `~/.devin/rules/*.md` |
| Codex, Gemini, כל `AGENTS.md` | `AGENTS.md`, ו-`GEMINI.md` שמצביע אליו | `~/.codex/AGENTS.md` ו-`~/.gemini/GEMINI.md` |

Claude הגלובלי נכתב אל `~/.claude/CLAUDE.md`, לא אל `~/CLAUDE.md`.

כשמתקינים כמה כלים יחד, החוזה המלא נכתב פעם אחת. Cursor קורא גם `AGENTS.md` וגם `CLAUDE.md`, אז לא שמים את אותו טקסט ארוך בשניהם. `--no-dedupe` מבטל את זה.

ניקוד: לטקסט מנוקד משתמשים ב-Noto Sans Hebrew או Noto Serif Hebrew, וב-Frank Ruhl Libre או David Libre לטקסט ארוך. Heebo, Assistant, Rubik ו-Suez One מיועדים לממשק בלי ניקוד.

</div>

## English

Public, Hebrew-first agent skills for Cursor, Claude Code, GitHub Copilot, Windsurf / Devin, and agents that read `AGENTS.md` (Codex, Gemini CLI).

`skills/` is the only source. A generator emits the file each tool actually loads. The installer never replaces an existing `CLAUDE.md` or `AGENTS.md`. It merges a delimited block, and it takes a timestamped backup before overwriting a file.

The only always-on text is short: talk to the person in Hebrew; write code, comments, and commits in English; write product copy in natural Hebrew. Every other skill loads when the task matches.

### Install

```bash
git clone https://github.com/NK0300/hebrew-pro-agent-skills.git
cd hebrew-pro-agent-skills
./install.sh --mode project --target /path/to/your-app --profile kids-hebrew --tools cursor,claude
```

```bash
./install.sh --mode global --profile full
```

After the `v1.0.0` tag exists:

```bash
curl -fsSL https://raw.githubusercontent.com/NK0300/hebrew-pro-agent-skills/v1.0.0/install.sh | bash -s -- --profile full --target .
```

Read `install.sh` before piping it from the network.

```powershell
.\install.ps1 --mode project --target C:\src\app --profile web --tools cursor,copilot
```

### Uninstall

```bash
./install.sh --uninstall --target /path/to/your-app
./install.sh --mode global --uninstall
```

Uninstall removes the managed block and leaves the rest of the file. A file this installer created is deleted. A file that existed before install is restored from the backup, unless you edited it afterwards, in which case your edit is kept.

`--dry-run` prints the plan and writes nothing.

### Profiles

| Profile | Skills |
| --- | --- |
| `full` | all nine |
| `web` | core, fullstack, RTL, security, motion, Hebrew and nikud, testing |
| `backend` | core, fullstack, security, testing, deploy |
| `kids-hebrew` | core, RTL, security, motion, nikud, kids and accessibility, testing |

### Tool support

Checked against the vendor docs in November 2026. See `CONTRIBUTING.md` for the links.

| Tool | Project | Global |
| --- | --- | --- |
| Cursor | `.cursor/rules/*.mdc` with `description`, `globs` (comma-separated string), `alwaysApply` | `~/.cursor/rules/*.mdc` |
| Claude Code | `.claude/skills/<name>/SKILL.md` (`name` matches the folder) and a block in `CLAUDE.md` | `~/.claude/skills/` and `~/.claude/CLAUDE.md` |
| GitHub Copilot | `.github/copilot-instructions.md` and `.github/instructions/*.instructions.md` (`applyTo`) | `~/.copilot/copilot-instructions.md` and `~/.copilot/instructions/` |
| Windsurf / Devin | `.windsurf/rules/*.md` and `.devin/rules/*.md` with `trigger` | `~/.devin/rules/*.md` |
| Codex, Gemini, other `AGENTS.md` agents | `AGENTS.md`, plus `GEMINI.md` pointing at it | `~/.codex/AGENTS.md` and `~/.gemini/GEMINI.md` |

Global Claude instructions are `~/.claude/CLAUDE.md`, never `~/CLAUDE.md`.

When several tools are selected, the full router is written once. Cursor also loads root `AGENTS.md` and root `CLAUDE.md`, so those two files do not both carry the long text. `--no-dedupe` turns that off. Global installs give each product its own copy, because those files are not in the same context. Devin is the exception: if Claude is installed too, Devin reads `~/.claude/CLAUDE.md`, so the Windsurf core rule is not also `always_on`.

### Skills

| Skill | Loads when |
| --- | --- |
| `core-orchestrator` | Always. Routes the rest. Plan, then build, then verify. |
| `fullstack-architect` | APIs, validation, data, server state |
| `ui-rtl-system` | CSS and components. Logical properties, BiDi, tokens |
| `qa-security-gate` | Auth, secrets, XSS, headers, supply chain, the release report |
| `interactive-motion` | GSAP, scroll, canvas, reduced motion, RTL direction |
| `hebrew-content-nikud` | Copy, nikud, `he-IL` numbers and dates |
| `kids-edtech-a11y` | Children's products, large targets, audio, privacy |
| `testing-strategy` | Unit, integration, Playwright, RTL checks |
| `devops-deploy` | Env, CI, Docker, preview, rollback |

### Nikud

Pointed text wants a face that positions Hebrew marks. Use Noto Sans Hebrew or Noto Serif Hebrew, and test Frank Ruhl Libre or David Libre for long reading. Alef is an acceptable UI fallback after a screenshot. Heebo, Assistant, Rubik, and Suez One are for unpointed interface and display type. They place nikud poorly. Raise line-height to about 1.9. Do not strip combining marks from stored text. The token template is `skills/ui-rtl-system/tokens.template.css` (light, dark, and `data-theme`).

### Develop

```bash
shellcheck install.sh script/test-install.sh
python3 script/validate_skills.py
python3 -m unittest discover -s tests -v
bash script/test-install.sh
```

`dist/project-full/` is generated. License: MIT. Version 1.0.0.
