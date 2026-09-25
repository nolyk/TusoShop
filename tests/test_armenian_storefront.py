"""Dependency-free checks for the Armenian customer copy."""

import ast
import re
import string
from pathlib import Path

from tgbot.data.texts.hy import Language as Armenian
from tgbot.data.texts.ru import Language as Russian


ROOT = Path(__file__).resolve().parents[1]


def assigned_fields(path, role):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    language = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Language")
    cls = next(n for n in language.body if isinstance(n, ast.ClassDef) and n.name == role)
    return {
        n.targets[0].id
        for n in cls.body
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
    }


def run():
    source = ROOT / "tgbot" / "data" / "texts"
    for role in ("Buttons", "Texts"):
        russian_fields = assigned_fields(source / "ru.py", role)
        armenian_fields = assigned_fields(source / "hy.py", role)
        exempt = {"min_amount", "max_amount"} if role == "Texts" else {"position_button_name"}
        assert russian_fields - armenian_fields == exempt

    for role in ("Buttons", "Texts"):
        original = getattr(Russian, role)
        translated = getattr(Armenian, role)
        for field in assigned_fields(source / "ru.py", role):
            source_value = getattr(original, field)
            translated_value = getattr(translated, field)
            if isinstance(source_value, str):
                assert set(x[1] for x in string.Formatter().parse(source_value) if x[1]) == set(
                    x[1] for x in string.Formatter().parse(translated_value) if x[1]
                ), field

    assert Armenian.AdminTexts is Russian.AdminTexts
    assert Armenian.Buttons.admin_panel == Russian.Buttons.admin_panel
    assert not re.search(r"[А-Яа-я]", (source / "hy.py").read_text(encoding="utf-8"))
    print("ARMENIAN_STOREFRONT PASS translated_fields=PASS placeholders=PASS admin_russian=PASS")


if __name__ == "__main__":
    run()
