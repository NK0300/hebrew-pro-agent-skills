"""Defect taxonomy, enums, and the Hebrew labels used in reports."""

from __future__ import annotations

OBJECT_CODES = ["ID", "ST", "FB", "AN", "OB", "AC", "GZ"]
SCENE_CODES = ["DU", "SF", "SY", "AU", "TG", "WD", "SP"]
ALL_CODES = OBJECT_CODES + SCENE_CODES

CODE_NAMES_HE = {
    "ID": "זהות דמות",
    "ST": "סגנון",
    "FB": "אלמנטים אסורים",
    "AN": "אנטומיה",
    "OB": "שלמות חפצים",
    "AC": "פעולה והיגיון",
    "GZ": "מבט וקשר",
    "DU": "כפילות",
    "SF": "בטיחות",
    "SY": "סמלים לא מכוונים",
    "AU": "התאמה לקהל",
    "TG": "תגי «מצאו»",
    "WD": "מילים ופריטים",
    "SP": "חוטים לאורך כפולה",
}

# Neutral questions for the independent second pass. They name what to look
# for, never the first pass's conclusion.
CODE_QUESTIONS = {
    "ID": "Do the character's locked identity marks (signature item, color family, proportions) look complete and consistent?",
    "ST": "Do the faces, materials and lighting look consistent with a single illustration style?",
    "FB": "Is there any lettering, text-like marks or other element that a children's book spec would usually forbid?",
    "AN": "Count fingers on every visible hand and check faces, eyes and limbs. Is any anatomy malformed, missing or extra?",
    "OB": "Is any object broken, floating, duplicated, or merged into another object or surface?",
    "AC": "Is the action physically possible: is the grip real, is balance plausible, does anything pass through a body?",
    "GZ": "Where are the eyes pointed? Do they meet what the pose implies?",
    "DU": "Does the same character appear more than once?",
    "SF": "Is there anything a parent would not want a small child to imitate?",
    "SY": "Does any shape read as an unintended symbol, sign or word?",
    "AU": "Is there a cultural or religious detail that could be questioned?",
    "TG": "Count every instance of the requested item, including edges and background.",
    "WD": "Is the requested item clearly visible, and what color is it?",
    "SP": "Does the element continue correctly across the two halves of the spread?",
}

# Generic prevention lines for prompt-block.md, keyed by code.
PREVENTION_HE = {
    "ID": "כל דמות שומרת על סימני הזיהוי הנעולים שלה: הפריט המזהה, משפחת הצבע והפרופורציות.",
    "ST": "אותו סגנון בכל הסצנות: אותן פנים, אותם חומרים, אותה תאורה.",
    "FB": "אין כיתוב, אותיות או סימנים דמויי טקסט בשום מקום בתמונה.",
    "AN": "חמש אצבעות בכל יד, שתי עיניים מכוונות, גפיים שלמות ומחוברות נכון.",
    "OB": "כל חפץ שלם, מונח על משטח, לא מרחף ולא מתמזג בחפץ אחר.",
    "AC": "כל אחיזה אמיתית: היד נוגעת בחפץ ואוחזת בו, ושום חפץ לא עובר דרך גוף.",
    "GZ": "כיוון המבט תואם את הפעולה: דמויות שמשוחחות מביטות זו בזו.",
    "DU": "כל דמות מופיעה פעם אחת בלבד בסצנה.",
    "SF": "אין מצבים מסוכנים לילדים בלי מבוגר לצדם.",
    "SY": "בלי צורות שנקראות כסמלים, אותיות או שלטים.",
    "AU": "פרטים תרבותיים ודתיים לפי מסמך ההפקה בלבד.",
    "TG": "מספר הפריטים בתמונה שווה בדיוק למספר שבתג.",
    "WD": "כל פריט מהרשימה נראה בבירור ובאותו צבע כמו בפס הפריטים.",
    "SP": "אלמנטים שחוצים את הכפולה נמשכים ברציפות בין שני העמודים.",
}

TYPES = ["spec_violation", "spec_conflict", "suggestion"]
SEVERITIES = ["critical", "medium", "minor"]
CONFIDENCES = ["certain", "likely", "verify"]
FIX_KINDS = ["local_edit", "rerender"]
STATUSES = ["pending", "dismissed", "local_edit", "rerender", "fixed_verified"]
CHECK_VALUES = ["pass", "fail", "verify", "na"]
OBJECT_KINDS = ["character", "animal", "object", "furniture", "find_item", "text", "background", "other"]
TAG_RESULTS = ["correct", "wrong", "ambiguous", "unconfirmed"]

TYPE_HE = {"spec_violation": "הפרת מפרט", "spec_conflict": "סתירה במפרט", "suggestion": "הצעה"}
SEVERITY_HE = {"critical": "קריטי", "medium": "בינוני", "minor": "קל"}
CONFIDENCE_HE = {"certain": "ודאי", "likely": "סביר", "verify": "לוודא"}
FIX_HE = {"local_edit": "עריכה מקומית", "rerender": "רינדור מחדש"}
STATUS_HE = {
    "pending": "ממתין להחלטה",
    "dismissed": "תקין (נדחה)",
    "local_edit": "לתיקון מקומי",
    "rerender": "לרינדור מחדש",
    "fixed_verified": "תוקן ונבדק",
}
TAG_RESULT_HE = {"correct": "נכון", "wrong": "שגוי", "ambiguous": "דו־משמעי", "unconfirmed": "לא ניתן לאשר"}

# Decisions the owner can type in decisions.csv or `decide --set`.
DECISION_ALIASES = {
    "ok": "dismissed",
    "dismiss": "dismissed",
    "dismissed": "dismissed",
    "תקין": "dismissed",
    "נדחה": "dismissed",
    "local": "local_edit",
    "local_edit": "local_edit",
    "מקומי": "local_edit",
    "rerender": "rerender",
    "רינדור": "rerender",
    "fixed": "fixed_verified",
    "fixed_verified": "fixed_verified",
    "pending": "pending",
}
