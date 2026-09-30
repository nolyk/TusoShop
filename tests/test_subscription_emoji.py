from tgbot.data.config import BotTexts

def test_subscription_warning_exact():
    assert BotTexts.Hy.TEXTS.channels_error == '<b><tg-emoji emoji-id="6181666851978748540">⚠</tg-emoji> Բոտից օգտվելուց առաջ անհրաժեշտ է բաժանորդագրվել մեր ալիքին։</b>'
