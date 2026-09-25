import re


EMOJI_RE = re.compile(
    "["
    "\U0001F1E6-\U0001F1FF"
    "\U0001F300-\U0001FAFF"
    "\u2600-\u27BF"
    "]"
)

TG_EMOJI_RE = re.compile(r"<tg-emoji\s+emoji-id=[\"']\d+[\"']>(.*?)</tg-emoji>")

CUSTOM_EMOJI_IDS = [
    "5870995486453796729",
    "5920344347152224466",
    "5967390100357648692",
    "5258204546391351475",
    "5870982283724328568",
    "5327904946413121515",
    "4924862170224658711",
    "5796440171364749940",
]


def premiumize_text(value: str) -> str:
    if "<tg-emoji" in value:
        return value

    counter = 0

    def replace(match):
        nonlocal counter
        emoji = match.group(0)
        emoji_id = CUSTOM_EMOJI_IDS[counter % len(CUSTOM_EMOJI_IDS)]
        counter += 1
        return f'<tg-emoji emoji-id="{emoji_id}">{emoji}</tg-emoji>'

    return EMOJI_RE.sub(replace, value)


def strip_tg_emoji(value: str) -> str:
    return TG_EMOJI_RE.sub(r"\1", value)


def normalize_button_text(value: str) -> str:
    value = EMOJI_RE.sub("", value)
    value = value.replace("\ufe0f", "").replace("\u200d", "")
    value = re.sub(r"^[•·.\s|]+", "", value).strip()
    value = re.sub(r"\s{2,}", " ", value)
    return value


def _walk(value, transform):
    if isinstance(value, str):
        return transform(value)
    if isinstance(value, dict):
        return {key: _walk(val, normalize_button_text) for key, val in value.items()}
    if isinstance(value, tuple):
        return tuple(_walk(item, transform) for item in value)
    if isinstance(value, list):
        return [_walk(item, transform) for item in value]
    return value


def _transform_class(cls, transform):
    for name, value in list(vars(cls).items()):
        if name.startswith("__") or callable(value) or isinstance(value, (staticmethod, classmethod)):
            continue
        setattr(cls, name, _walk(value, transform))


def premiumize_language(language_cls):
    _transform_class(language_cls.Texts, premiumize_text)
    _transform_class(language_cls.Buttons, normalize_button_text)
    _transform_class(language_cls.AdminTexts, strip_tg_emoji)
    _transform_class(language_cls.AdminTexts, normalize_button_text)


def storefront_ad_label(value: str) -> str:
    label = normalize_button_text(value)
    return "Գովազդ" if label.casefold() == "реклама" else label
