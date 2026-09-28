"""Storefront button appearance; actions and visibility remain unchanged."""
from tgbot.utils.premium_emoji import normalize_button_text

STOREFRONT_EMOJI_IDS = {'Mini app': '6181221171812377434', 'Գնել': '6181477413856224769', 'Աջակցություն': '6183774199157367778', 'Լիցքավորել հաշվեկշիռը': '6181704819489644554', 'Իմ էջը': '6181512409249750964', 'Խաղարկություններ': '6184004370749726738', 'Գովազդ': '6183558664813550912', 'Stars & Premium': '6181597355112932310'}

def style_storefront_keyboard(keyboard):
    rows = getattr(keyboard, 'keyboard', None)
    if rows is None:
        rows = keyboard.inline_keyboard
    for row in rows:
        for button in row:
            label = normalize_button_text(button.text).removeprefix("⭐").strip()
            if label.casefold() == 'mini app':
                label = 'Mini app'
            emoji_id = STOREFRONT_EMOJI_IDS.get(label)
            if emoji_id:
                button.text = label
                button.icon_custom_emoji_id = emoji_id
    return keyboard
