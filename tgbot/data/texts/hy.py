"""Armenian storefront copy. Administrative copy remains Russian."""

from tgbot.data.texts.ru import Language as Russian


class Language:
    language = "hy"

    class Buttons(Russian.Buttons):
        buy = "Գնել"
        profile = "Իմ էջը"
        support = "Աջակցություն"
        faq = "ՀՏՀ"
        topup_balance = "Լիցքավորել հաշվեկշիռը"
        back = "Հետ"
        contests = "Խաղարկություններ"
        faq_chat_inl = "💎 Զրույց"
        faq_news_inl = "📩 Նորություններ"
        send_payment_to_check = "✅ Ուղարկել վճարումը ստուգման"
        close = "❌ Փակել"
        activate_promo = "Պրոմոկոդ"
        ref_system = "Հրավիրումների համակարգ"
        purchases_history = "Պատմություն"
        support_text = 'Գրել աջակցությանը'
        refill_link_inl = "💵 Անցնել վճարմանը"
        refill_check_inl = "💎 Ստուգել վճարումը"
        cancel = "❌ Չեղարկել"
        admin_panel = Russian.Buttons.admin_panel
        choose_action = "Ընտրեք գործողությունը"
        nolimit = "Անսահմանափակ"
        pcs = "հատ"
        contest_enter = "🎉 Մասնակցել"
        you_not_completed_all_conditions = 'Դուք չեք կատարել բոլոր պայմանները. կատարված է {count}-ը {count_conditions}-ից'
        change_language = "🌐 Փոխել լեզուն"
        check_sub = "✅ Ստուգել"

    class Texts(Russian.Texts):
        is_buy_text = "❌ Գնումները ժամանակավորապես անհասանելի են։"
        is_ban_text = "❌ Դուք արգելափակված եք բոտում։"
        is_work_text = "❌ Բոտում տեխնիկական աշխատանքներ են ընթանում։"
        is_refill_text = "❌ Հաշվեկշռի լիցքավորումը ժամանակավորապես անհասանելի է։"
        is_ref_text = "❗ Հրավիրումների համակարգը ժամանակավորապես անհասանելի է։"
        is_contests_text = "❌ Խաղարկությունները ժամանակավորապես անհասանելի են։"
        channels_error = '<b><tg-emoji emoji-id="6181666851978748540">⚠</tg-emoji> Բոտից օգտվելուց առաջ անհրաժեշտ է բաժանորդագրվել մեր ալիքին։</b>'
        nobody = "<code>Ոչ ոք</code>"
        ref_s = ("հրավիրված օգտատեր",) * 3
        day_s = ("օր",) * 3
        member_s = ("մասնակից",) * 3
        winner_s = ("հաղթող",) * 3
        refill_s = ("լիցքավորում",) * 3
        purchase_s = ("գնում",) * 3
        channel_s = ("ալիք",) * 3
        person_s = ("մարդ",) * 3
        main_menu = '<b><tg-emoji emoji-id="6183704354399200886">👑</tg-emoji> {username}, բարի գալուստ <b>ԹույնShop</b>։\n\n<tg-emoji emoji-id="6181530044385468714">⬇</tg-emoji> Ընտրեք բաժինը ցանկից՝</b>'
        bot_will_not_respond = "❗ Բոտը չի պատասխանի, մինչև չդադարեցնեք սպամը։"
        please_dont_spam = "❗ Խնդրում ենք չուղարկել սպամ։"
        profile_text = """<b><tg-emoji emoji-id="6183468706723537731">👤</tg-emoji> Ձեր էջը՝

<tg-emoji emoji-id="6181478659396739452">👤</tg-emoji> Օգտատեր՝ {username}
<tg-emoji emoji-id="6181548602939155001">👤</tg-emoji> ID՝ <code>{user_id}</code>

<tg-emoji emoji-id="6181423645160646167">👛</tg-emoji> Հաշվեկշիռ՝ <code>{balance}{curr}</code>
<tg-emoji emoji-id="6183559145849890138">🪙</tg-emoji> Ընդամենը լիցքավորված՝ <code>{total_refill}{curr}</code>

<tg-emoji emoji-id="6181440610281464581">✍</tg-emoji> Գրանցման ամսաթիվ՝ <code>{reg_date}</code></b>"""
        support_is_not_provided = "<b>💻 Այս պահին աջակցությունը հասանելի չէ։</b>"
        support_text = '<b><tg-emoji emoji-id="6183774199157367778">🆘</tg-emoji> Աջակցությանը գրելու համար սեղմեք ներքևի կոճակը՝</b>'
        choose_language = "<b>❗ Ընտրեք լեզուն՝</b>"
        refill_check_no = "❌ Վճարումը չի գտնվել"
        payments_names = Russian.Texts.payments_names
        payments_names = {**Russian.Texts.payments_names, "stars": "⭐ Telegram Stars"}
        choose_refill_method = '<b><tg-emoji emoji-id="6181612022426247965">💸</tg-emoji> Ընտրեք լիցքավորման եղանակը՝</b>'
        payment_comment_api = "@{bot_name} բոտում {user_name} օգտատիրոջ հաշվի լիցքավորում՝ {pay_amount}{curr}"
        refill_was_rejected = "<b>❌ Ձեր {amount}{curr} լիցքավորումը մերժվել է։</b>"
        send_receipt_photo = '<b><tg-emoji emoji-id="6181523988481581415">📋</tg-emoji> Ուղարկեք փոխանցման անդորրագրի լուսանկարը՝</b>'
        confirm_send_receipt_photo = "<b>❓ Վստա՞հ եք, որ ցանկանում եք այս անդորրագիրն ուղարկել ստուգման։</b>"
        create_refill_text = "<b>⭐ Լիցքավորում՝ <code>{paymentMethod}</code>\n💰 Գումար՝ <code>{pay_amount}{curr}</code>\n🆔 Վճարման ID՝ <code>{pay_id}</code>\n⌛ Վճարեք մինչև <code>{under_date}</code>\n💎 Վճարելու համար սեղմեք ներքևի կոճակը՝</b>"
        cancel_create_refill_text = '<b><tg-emoji emoji-id="6181207762924478466">📝</tg-emoji> Դուք արդեն ունեք ակտիվ լիցքավորում՝\n\n<tg-emoji emoji-id="6181551167034631404">💳</tg-emoji> Եղանակ՝ <code>{paymentMethod}</code>\n<tg-emoji emoji-id="6183559145849890138">🪙</tg-emoji> Գումար՝ <code>{pay_amount}{curr}</code>\n<tg-emoji emoji-id="6181548602939155001">👤</tg-emoji> Վճարման ID՝ <code>{pay_id}</code>\n<tg-emoji emoji-id="6181377573046461008">⌛️</tg-emoji> Վճարեք մինչև <code>{under_date}</code>\n💎 Վճարելու համար սեղմեք ներքևի կոճակը՝</b>'
        custom_pay_transfer_details = """<b><tg-emoji emoji-id='6181248419084903585'>💰</tg-emoji> Փոխանցման տվյալներ</b>

<b>Բանկ՝</b> <code>{bank}</code>
<b>Ստացող՝</b> <code>{holder}</code>
<b>Քարտ՝</b> <code>{number}</code>{note}

Փոխանցումից հետո սեղմեք ստուգման կոճակը։"""
        custom_pay_no_cards = "<b>❌ Փոխանցման քարտերը դեռ կարգավորված չեն։ Դիմեք աջակցությանը։</b>"
        create_refill_text_custom_pay_method = "<b>⭐ Լիցքավորում՝ <code>{paymentMethod}</code>\n💰 Գումար՝ <code>{pay_amount}{curr}</code>\n🆔 Վճարման ID՝ <code>{pay_id}</code>\n⌛ Վճարեք մինչև <code>{under_date}</code></b>\n\n{custom_pay_method_text}"
        cancel_create_refill_text_custom_pay_method = '<b><tg-emoji emoji-id="6181207762924478466">📝</tg-emoji> Դուք արդեն ունեք ակտիվ լիցքավորում՝\n\n<tg-emoji emoji-id="6181551167034631404">💳</tg-emoji> Եղանակ՝ <code>{paymentMethod}</code>\n<tg-emoji emoji-id="6183559145849890138">🪙</tg-emoji> Գումար՝ <code>{pay_amount}{curr}</code>\n<tg-emoji emoji-id="6181548602939155001">👤</tg-emoji> Վճարման ID՝ <code>{pay_id}</code>\n<tg-emoji emoji-id="6181377573046461008">⌛️</tg-emoji> Վճարեք մինչև <code>{under_date}</code></b>\n\n{custom_pay_method_text}'
        enter_amount_of_refill = '<tg-emoji emoji-id="6181440610281464581">✍</tg-emoji><b> Մուտքագրեք լիցքավորման գումարը</b>'
        choose_crypto = "<b>⚙️ Ընտրեք կրիպտոարժույթը՝</b>"
        error_refill = "❌ Սխալ. հաշվեկշիռն արդեն լիցքավորված է։"
        success_refill_text = '<b><tg-emoji emoji-id="6181423645160646167">👛</tg-emoji> Ձեր հաշվեկշիռը հաջողությամբ լիցքավորվել է <code>{amount}{curr}</code>-ով։\n<tg-emoji emoji-id="6181612022426247965">💸</tg-emoji> Եղանակ՝ <code>{way}</code>\n<tg-emoji emoji-id="6181523988481581415">📋</tg-emoji> Անդորրագիր՝ <code>{receipt}</code></b>'
        yes_refill_ref = "<b>💎 Ձեր հրավիրած {name} օգտատերը լիցքավորել է հաշվեկշիռը <code>{amount}{cur}</code>-ով, և ձեզ փոխանցվել է <code>{ref_amount}{cur}</code>։</b>"
        yes_cancel_refill = "<b>❌ Լիցքավորումը չեղարկվել է։</b>"
        no_int_amount = "<b>❗ Լիցքավորման գումարը պետք է թիվ լինի։</b>"
        min_max_amount = "<b>❗ Գումարը պետք է լինի <code>{min_amount}{curr}</code>-ից մինչև <code>{max_amount}{curr}</code>։</b>"
        new_ref_lvl = "<b>💚 Ձեր հրավիրումների նոր մակարդակը {new_lvl} է։ {next_lvl}-րդ մակարդակին հասնելու համար պետք է ևս {remain_refs} {convert_ref}։</b>"
        max_ref_lvl = "<b>💚 Դուք հասել եք հրավիրումների 3-րդ՝ առավելագույն մակարդակին։</b>"
        cur_max_lvl = "💚 Դուք առավելագույն մակարդակում եք։</b>"
        next_lvl_remain = '<tg-emoji emoji-id="6183489966811653469">📝</tg-emoji> Հաջորդ մակարդակին հասնելու համար հրավիրեք ևս <code>{remain_refs} {person_s}</code>։</b>'
        ref_text = """<b><tg-emoji emoji-id="6181676644504185221">🤝</tg-emoji> Հրավիրումների համակարգ

<tg-emoji emoji-id="6181491892190978963">🔗</tg-emoji> Հղում՝
{ref_link}

<tg-emoji emoji-id="6181612022426247965">💸</tg-emoji> Ձեր հղումը ուղարկեք ընկերներին և նրանց յուրաքանչյուր լիցքավորումից ստացեք <code>{ref_percent}%</code>։

<tg-emoji emoji-id="6181512409249750964">👤</tg-emoji> Ձեզ հրավիրել է՝ {reffer}
<tg-emoji emoji-id="6181405799571531484">⚡</tg-emoji> Հրավիրվածներից վաստակած գումար՝ <code>{ref_earn}{curr}</code>
<tg-emoji emoji-id="6181405799571531484">⚡</tg-emoji> Հրավիրված օգտատերեր՝ <code>{ref_count}</code> {convert_ref}
<tg-emoji emoji-id="6181319861570905738">📊</tg-emoji> Հրավիրումների մակարդակ՝ <code>{ref_lvl}</code>
{mss}"""
        yes_reffer = "<b>❗ Ձեզ արդեն հրավիրել են։</b>"
        invite_yourself = "<b>❗ Չեք կարող ինքներդ ձեզ հրավիրել։</b>"
        new_refferal = "<b>💎 Դուք նոր հրավիրված օգտատեր ունեք՝ @{user_name}։\n⚙️ Այժմ ունեք <code>{user_ref_count}</code> {convert_ref}։</b>"
        promo_act = '<b><tg-emoji emoji-id="6183777454742577008">🎫</tg-emoji>Պրոմոկոդն ակտիվացնելու համար մուտքագրեք այն։\n<tg-emoji emoji-id="6181440610281464581">✍</tg-emoji> Օրինակ՝ Tuyn2027</b>'
        no_uses_promocode = "<b>❌ Պրոմոկոդի ակտիվացման ժամկետն ավարտվել է։</b>"
        no_promocode = "<b>❌ <code>{promocode}</code> պրոմոկոդը գոյություն չունի։</b>"
        yes_promocode = '<b><tg-emoji emoji-id="6181681557946770158">✅</tg-emoji> Պրոմոկոդն ակտիվացվել է. ստացել եք <code>{discount}{curr}</code>։</b>'
        yes_uses_promocode = "<b>❌ Դուք արդեն ակտիվացրել եք այս պրոմոկոդը։</b>"
        no_cats = "<b>❌ Այս պահին կատեգորիաներ չկան։</b>"
        available_cats = '<b><tg-emoji emoji-id="5472189467869619770">🛒</tg-emoji> Հասանելի կատեգորիաները</b>'
        current_cat = '<b><tg-emoji emoji-id="6181208703522317605">🛍</tg-emoji> Ընթացիկ կատեգորիա՝ <code>{name}</code></b>'
        no_products = "❌ Այս պահին ապրանքներ չկան։"
        open_position_text = '<b><tg-emoji emoji-id="5472189467869619770">🛒</tg-emoji> Կատեգորիա՝ <code>{cat_name}</code>\n\n<tg-emoji emoji-id="5472382354850881695">🛍</tg-emoji> Ապրանք՝ <code>{pos_name}</code>\n<tg-emoji emoji-id="5474129800949964546">🪙</tg-emoji> Գին՝ <code>{price}{cur}</code>\n<tg-emoji emoji-id="5471946243871645459">🔶</tg-emoji> Հասանելի քանակ՝ <code>{items}</code></b>\n\n{desc}'
        no_balance_for_buying = "❗ Գնելու համար բավարար միջոցներ չունեք։ Լիցքավորեք հաշվեկշիռը։"
        confirm_buy_products = '<b><tg-emoji emoji-id="6181742933029430549">❓</tg-emoji> Վստա՞հ եք, որ ցանկանում եք գնել ապրանքը։</b>\n\n- Ապրանք՝ <code>{position_name}</code>\n- Քանակ՝ <code>{count} հատ</code>\n- Ընդհանուր գումար՝ <code>{price}{curr}</code>'
        enter_count_items_for_buy = '<b><tg-emoji emoji-id="6181742933029430549">❓</tg-emoji> Մուտքագրեք գնվող ապրանքների քանակը՝</b>\n<tg-emoji emoji-id="6181666851978748540">⚠</tg-emoji> <code>1</code>-ից <code>{items}</code>\n\n- Ապրանք՝ <code>{pos_name}</code> — <code>{price}{curr}</code>\n- Ձեր հաշվեկշիռը՝ <code>{balance}{curr}</code>'
        incorrect_data = "<b>❌ Մուտքագրված տվյալները սխալ են։</b>"
        data_was_edit = "<b>❗ Ընտրված ապրանքը սպառվել է։</b>"
        incorrect_count_items = "<b>❌ Ապրանքների քանակը սխալ է։</b>"
        no_balance_on_account = "<b>❌ Հաշվեկշռում բավարար միջոցներ չկան։</b>"
        please_await_products = "<b>🔄 Սպասեք, ապրանքները պատրաստվում են։</b>"
        successful_buying = "<b>✅ Գնումը հաջողությամբ կատարվել է։</b>\n\n- Անդորրագիր՝ <code>{receipt}</code>\n- Ապրանք՝ <code>{position_name} | {purchase_count} հատ | {purchase_price}{curr}</code>\n- Գնման ամսաթիվ՝ <code>{date}</code>"
        receipt_purchase = '<b><tg-emoji emoji-id="6181523988481581415">📋</tg-emoji> Անդորրագիր <code>{receipt}</code>՝\n<tg-emoji emoji-id="6181208703522317605">🛍</tg-emoji> Ապրանք՝ <code>{pos_name}</code>\n<tg-emoji emoji-id="6183559145849890138">🪙</tg-emoji> Գումար՝ <code>{sum}{curr}</code>\n<tg-emoji emoji-id="6181535786756743376">📚</tg-emoji> Քանակ՝ <code>{count} հատ</code>\n<tg-emoji emoji-id="6181377573046461008">⌛️</tg-emoji> Ամսաթիվ՝ <code>{date}</code>\n<tg-emoji emoji-id="6181686548698767939">🧮</tg-emoji> Բովանդակություն՝</b>'
        last_10_purchases = "<b>🚀 Վերջին 10 գնումները</b>"
        no_have_purchases = "❗ Դուք դեռ գնումներ չունեք։"
        your_items = "<b>🛒 Ձեր ապրանքները</b>"
        no_contests = "❌ Այս պահին խաղարկություններ չկան։"
        choose_contest = "<b>🎉 Ընտրեք խաղարկությունը՝</b>"
        contest_text = '<b><tg-emoji emoji-id="6181273677787571937">🎁</tg-emoji> Խաղարկություն #{contest_id}\n\n<tg-emoji emoji-id="6183559145849890138">🪙</tg-emoji> Մրցանակ՝ <code>{prize}{cur}</code>\n<tg-emoji emoji-id="6181377573046461008">⌛️</tg-emoji> Ավարտին մնացել է՝ <code>{end_time}</code>\n<tg-emoji emoji-id="6183460812573646969">🎖</tg-emoji> {winners_num} {winners}\n<tg-emoji emoji-id="6181512409249750964">👤</tg-emoji> {members_num} {members}</b>'
        conditions = '\n\n<b><tg-emoji emoji-id="6181220201149768417">📋</tg-emoji> Պայմաններ՝</b>\n\n'
        conditions_refills = '<b><tg-emoji emoji-id="6181208703522317605">🛍</tg-emoji> {num} {refills} — {status}</b>\n'
        conditions_purchases = '<b><tg-emoji emoji-id="5472189467869619770">🛒</tg-emoji> {num} {purchases} — {status}</b>\n'
        conditions_channels = "<b>✨ Բաժանորդագրվել {num} {channels_text}՝\n\n{channels}</b>\n"
        u_win_the_contest = "<b>🎉 Շնորհավորում ենք, դուք հաղթել եք խաղարկությունում։\n💰 Ձեզ փոխանցվել է {prize}{cur} մրցանակը։</b>"
        u_didnt_have_time_to_enter_contest = "Չհասցրիք մասնակցել։ 💥"
        success = "✅ Կատարված է"
        u_already_enter_contest = "❌ Դուք արդեն մասնակցում եք։"
        contest_already_ended = "💥 Խաղարկությունն արդեն ավարտվել է։"

    AdminTexts = Russian.AdminTexts
