# scene-audit

<div dir="rtl" lang="he">

כלי לביקורת סצנות מאוירות בספר, ברמת האובייקט. הסקריפטים עושים את מה שמדיד: מלאי, חתימות, אריחים, חיתוכים מוגדלים, תיבות, מדד כיסוי ודוחות. Claude Code עושה את ההסתכלות לפי המיומנות (skill) שמגיעה עם החבילה. הכלי לא מייצר ולא מתקן תמונות, ולא כותב לעולם לתיקיית `scenes/`.

## התקנה ב־Windows

מעתיקים את התיקייה `tools/scene-audit` מהמאגר אל `C:\Users\nachm\Documents\Codex\scene-audit`, ואז:

```powershell
pip install -e C:\Users\nachm\Documents\Codex\scene-audit
```

בתיקיית הספר (או בתיקיית הפרויקט שבה פותחים את Claude Code):

```powershell
scene-audit skill
scene-audit init --scenes renders --spec spec\production.docx --layout spread
scene-audit inventory
```

`scene-audit skill` מתקין את המיומנות ב־`.claude\skills\scene-audit\SKILL.md` של התיקייה הנוכחית. עם `--user` היא מותקנת לכל הפרויקטים ב־`~\.claude\skills`.

לקריאת מסמך הפקה בפורמט PDF:

```powershell
pip install -e "C:\Users\nachm\Documents\Codex\scene-audit[pdf]"
```

## עבודה ב־Claude Code

פותחים את Claude Code בתיקיית הספר ואומרים «תסרוק את כל הסצנות», או מפעילים `/scene-audit`. המיומנות מריצה את השלבים לפי הסדר ועוצרת בשתי נקודות שבהן ההחלטה שלך: אישור קובץ הכללים שחולץ ממסמך ההפקה, ותור ההחלטות בסוף.

| שלב | פקודה |
| --- | --- |
| מלאי, חתימות, גיליון מגע, בדיקת גיליונות מעקב | `scene-audit inventory` |
| חילוץ מסמך ההפקה ואישור הכללים | `scene-audit rules`, `scene-audit rules --approve` |
| חיפוש מונח בכל כתיב (ניקוד, כתיב מלא וחסר, אותיות סופיות) | `scene-audit spec-search כובע` |
| פריים מלא ו־9 אריחים חופפים לכל סצנה שהשתנתה | `scene-audit scan --all` |
| איחוד האובייקטים מכל המבטים | `scene-audit map --scene 07` |
| חיתוך מוגדל לכל אובייקט, חיתוך הקשר, ומבטים לאזורים שלא כוסו | `scene-audit crops --scene 07` |
| בדיקת תקינות: ארבעה תיוגים לכל ממצא, סעיף קיים, תיבות | `scene-audit validate --scene 07` |
| אימות צולב עצמאי | `scene-audit verify-pack`, `scene-audit verify-apply` |
| דוחות | `scene-audit report` |
| תור החלטות | `scene-audit decide`, `scene-audit decide --set 07-F02=ok` |
| בדיקה חוזרת אחרי רינדור | `scene-audit recheck --scene 07` |
| מצב כל הסצנות והצעד הבא | `scene-audit status` |

## פלטים

`out/report.html` (עברית, מימין לשמאל), `out/scenes.md`, `out/defects.csv`, `out/decisions.csv`, `out/marked/scene-NN.png`, `out/prompt-block.md`. מקור האמת הוא `work/scene-NN.json`, והפלטים נבנים ממנו.

## מגבלות

הכלי מסדר את העבודה של העין שלך, הוא לא מחליף אותה. מספר אצבעות ביד קטנה, ספירה בסצנה צפופה וסחף סגנון עדין הם המקומות החלשים, ולכן כל פריט שלא ניתן לקבוע מסומן «לוודא», והדוח אומר מה לא נבדק. ניקוד שמודל ייצר דורש הגהה אנושית לפני דפוס.

</div>

## English

`scene-audit` audits illustrated book scenes at the object level. The scripts handle the measurable parts: inventory, hashes, tiles, zoomed crops, boxes, coverage, and reports. Claude Code does the looking, following the bundled skill (`scene_audit/data/SKILL.md`). The tool never generates or edits images and never writes to `scenes/`.

Install with `pip install -e <path>/scene-audit` (add `[pdf]` for PDF specs). Requires Python 3.11+, Pillow, PyYAML and Jinja2.

Pipeline: `init` → `inventory` → `rules` (owner approves) → `scan` → per scene `map` → `crops` → findings in `work/scene-NN.json` → `validate` → `verify-pack` / `verify-apply` (independent second pass) → `done` → `report` → `decide` → after a re-render, `scan` + `recheck`.

Every image Claude looks at is a view recorded in `work/scene-NN/views.json` with its offset and scale, so a box drawn on any view converts exactly to source pixels. Coverage counts only objects with all seven object checks filled and gap views marked seen.

Tests: `python -m unittest discover -s tests -v` from this folder.
