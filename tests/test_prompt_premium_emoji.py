from tgbot.data.config import BotTexts

def test_exact_armenian_prompts():
    assert BotTexts.Hy.TEXTS.promo_act == '<b><tg-emoji emoji-id="6183777454742577008">🎫</tg-emoji>Պրոմոկոդն ակտիվացնելու համար մուտքագրեք այն։\n<tg-emoji emoji-id="6181440610281464581">✍</tg-emoji> Օրինակ՝ Tuyn2027</b>'
    assert BotTexts.Hy.TEXTS.enter_amount_of_refill == '<tg-emoji emoji-id="6181440610281464581">✍</tg-emoji><b> Մուտքագրեք լիցքավորման գումարը</b>'
