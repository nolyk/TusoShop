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
        contests = "🎁 Խաղարկություններ"
        faq_chat_inl = "💎 Զրույց"
        faq_news_inl = "📩 Նորություններ"
        send_payment_to_check = "✅ Ուղարկել վճարումը ստուգման"
        close = "❌ Փակել"
        activate_promo = "Պրոմոկոդ"
        ref_system = "Հրավիրումների համակարգ"
        purchases_history = "Պատմություն"
        support_text = "Գրել աջակցությանը"
        refill_link_inl = "💵 Անցնել վճարմանը"
        refill_check_inl = "💎 Ստուգել վճարումը"
        cancel = "❌ Չեղարկել"
        admin_panel = Russian.Buttons.admin_panel
        choose_action = "Ընտրեք գործողությունը"
        nolimit = "Անսահմանափակ"
        pcs = "հատ"
        contest_enter = "🎉 Մասնակցել"
        you_not_completed_all_conditions = "❗ Դուք չեք կատարել բոլոր պայմանները. կատարված է {count}-ը {count_conditions}-ից"
        change_language = "🌐 Փոխել լեզուն"
        check_sub = "✅ Ստուգել"

    class Texts(Russian.Texts):
        is_buy_text = "❌ Գնումները ժամանակավորապես անհասանելի են։"
        is_ban_text = "❌ Դուք արգելափակված եք բոտում։"
        is_work_text = "❌ Բոտում տեխնիկական աշխատանքներ են ընթանում։"
        is_refill_text = "❌ Հաշվեկշռի լիցքավորումը ժամանակավորապես անհասանելի է։"
        is_ref_text = "❗ Հրավիրումների համակարգը ժամանակավորապես անհասանելի է։"
        is_contests_text = "❌ Խաղարկությունները ժամանակավորապես անհասանելի են։"
        channels_error = "<b>📰 Բոտից օգտվելուց առաջ անհրաժեշտ է բաժանորդագրվել մեր ալիքին։</b>"
        nobody = "<code>Ոչ ոք</code>"
        ref_s = ("հրավիրված օգտատեր",) * 3
        day_s = ("օր",) * 3
        member_s = ("մասնակից",) * 3
        winner_s = ("հաղթող",) * 3
        refill_s = ("լիցքավորում",) * 3
        purchase_s = ("գնում",) * 3
        channel_s = ("ալիք",) * 3
        person_s = ("մարդ",) * 3
        main_menu = "<b><tg-emoji emoji-id='5260399854500191689'>👤</tg-emoji> {username}, բարի գալուստ <b>GS AutoShop</b>։\n\n<tg-emoji emoji-id='5231102735817918643'>👇</tg-emoji> Ընտրեք բաժինը ցանկից՝</b>"
        bot_will_not_respond = "❗ Բոտը չի պատասխանի, մինչև չդադարեցնեք սպամը։"
        please_dont_spam = "❗ Խնդրում ենք չուղարկել սպամ։"
        profile_text = """<b><tg-emoji emoji-id="5327904946413121515">©️</tg-emoji> Ձեր էջը՝

<tg-emoji emoji-id="5258011929993026890">👤</tg-emoji> Օգտատեր՝ {username}
<tg-emoji emoji-id="5936017305585586269">🪪</tg-emoji> ID՝ <code>{user_id}</code>

<tg-emoji emoji-id="5258204546391351475">💰</tg-emoji> Հաշվեկշիռ՝ <code>{balance}{curr}</code>
<tg-emoji emoji-id="5967390100357648692">💵</tg-emoji> Ընդամենը լիցքավորված՝ <code>{total_refill}{curr}</code>

<tg-emoji emoji-id="5796440171364749940">📌</tg-emoji> Գրանցման ամսաթիվ՝ <code>{reg_date}</code></b>"""
        support_is_not_provided = "<b>💻 Այս պահին աջակցությունը հասանելի չէ։</b>"
        support_text = "<b>💻 Աջակցությանը գրելու համար սեղմեք ներքևի կոճակը՝</b>"
        choose_language = "<b>❗ Ընտրեք լեզուն՝</b>"
        refill_check_no = "❌ Վճարումը չի գտնվել"
        payments_names = Russian.Texts.payments_names
        payments_names = {**Russian.Texts.payments_names, "stars": "⭐ Telegram Stars"}
        choose_refill_method = "<b>💰 Ընտրեք լիցքավորման եղանակը՝</b>"
        payment_comment_api = "@{bot_name} բոտում {user_name} օգտատիրոջ հաշվի լիցքավորում՝ {pay_amount}{curr}"
        refill_was_rejected = "<b>❌ Ձեր {amount}{curr} լիցքավորումը մերժվել է։</b>"
        send_receipt_photo = "<b>🧾 Ուղարկեք փոխանցման անդորրագրի լուսանկարը՝</b>"
        confirm_send_receipt_photo = "<b>❓ Վստա՞հ եք, որ ցանկանում եք այս անդորրագիրն ուղարկել ստուգման։</b>"
        create_refill_text = "<b>⭐ Լիցքավորում՝ <code>{paymentMethod}</code>\n💰 Գումար՝ <code>{pay_amount}{curr}</code>\n🆔 Վճարման ID՝ <code>{pay_id}</code>\n⌛ Վճարեք մինչև <code>{under_date}</code>\n💎 Վճարելու համար սեղմեք ներքևի կոճակը՝</b>"
        cancel_create_refill_text = "<b>❗ Դուք արդեն ունեք ակտիվ լիցքավորում՝\n\n⭐ Եղանակ՝ <code>{paymentMethod}</code>\n💰 Գումար՝ <code>{pay_amount}{curr}</code>\n🆔 Վճարման ID՝ <code>{pay_id}</code>\n⌛ Վճարեք մինչև <code>{under_date}</code>\n💎 Վճարելու համար սեղմեք ներքևի կոճակը՝</b>"
        custom_pay_transfer_details = """<b>🏦 Փոխանցման տվյալներ</b>

<b>Բանկ՝</b> <code>{bank}</code>
<b>Ստացող՝</b> <code>{holder}</code>
<b>Քարտ՝</b> <code>{number}</code>{note}

Փոխանցումից հետո սեղմեք ստուգման կոճակը։"""
        custom_pay_no_cards = "<b>❌ Փոխանցման քարտերը դեռ կարգավորված չեն։ Դիմեք աջակցությանը։</b>"
        create_refill_text_custom_pay_method = "<b>⭐ Լիցքավորում՝ <code>{paymentMethod}</code>\n💰 Գումար՝ <code>{pay_amount}{curr}</code>\n🆔 Վճարման ID՝ <code>{pay_id}</code>\n⌛ Վճարեք մինչև <code>{under_date}</code></b>\n\n{custom_pay_method_text}"
        cancel_create_refill_text_custom_pay_method = "<b>❗ Դուք արդեն ունեք ակտիվ լիցքավորում՝\n\n⭐ Եղանակ՝ <code>{paymentMethod}</code>\n💰 Գումար՝ <code>{pay_amount}{curr}</code>\n🆔 Վճարման ID՝ <code>{pay_id}</code>\n⌛ Վճարեք մինչև <code>{under_date}</code></b>\n\n{custom_pay_method_text}"
        enter_amount_of_refill = "<b>❗ Մուտքագրեք լիցքավորման գումարը՝</b>"
        choose_crypto = "<b>⚙️ Ընտրեք կրիպտոարժույթը՝</b>"
        error_refill = "❌ Սխալ. հաշվեկշիռն արդեն լիցքավորված է։"
        success_refill_text = "<b>⭐ Ձեր հաշվեկշիռը հաջողությամբ լիցքավորվել է <code>{amount}{curr}</code>-ով։\n💎 Եղանակ՝ <code>{way}</code>\n🧾 Անդորրագիր՝ <code>{receipt}</code></b>"
        yes_refill_ref = "<b>💎 Ձեր հրավիրած {name} օգտատերը լիցքավորել է հաշվեկշիռը <code>{amount}{cur}</code>-ով, և ձեզ փոխանցվել է <code>{ref_amount}{cur}</code>։</b>"
        yes_cancel_refill = "<b>❌ Լիցքավորումը չեղարկվել է։</b>"
        no_int_amount = "<b>❗ Լիցքավորման գումարը պետք է թիվ լինի։</b>"
        min_max_amount = "<b>❗ Գումարը պետք է լինի <code>{min_amount}{curr}</code>-ից մինչև <code>{max_amount}{curr}</code>։</b>"
        new_ref_lvl = "<b>💚 Ձեր հրավիրումների նոր մակարդակը {new_lvl} է։ {next_lvl}-րդ մակարդակին հասնելու համար պետք է ևս {remain_refs} {convert_ref}։</b>"
        max_ref_lvl = "<b>💚 Դուք հասել եք հրավիրումների 3-րդ՝ առավելագույն մակարդակին։</b>"
        cur_max_lvl = "💚 Դուք առավելագույն մակարդակում եք։</b>"
        next_lvl_remain = "💚 Հաջորդ մակարդակին հասնելու համար հրավիրեք ևս <code>{remain_refs} {person_s}</code>։</b>"
        ref_text = """<b>💎 Հրավիրումների համակարգ

🔗 Հղում՝
{ref_link}

📔 Ձեր հղումը ուղարկեք ընկերներին և նրանց յուրաքանչյուր լիցքավորումից ստացեք <code>{ref_percent}%</code>։

⚙️ Ձեզ հրավիրել է՝ {reffer}
💵 Հրավիրվածներից վաստակած գումար՝ <code>{ref_earn}{curr}</code>
📌 Հրավիրված օգտատերեր՝ <code>{ref_count}</code> {convert_ref}
🎲 Հրավիրումների մակարդակ՝ <code>{ref_lvl}</code>
{mss}"""
        yes_reffer = "<b>❗ Ձեզ արդեն հրավիրել են։</b>"
        invite_yourself = "<b>❗ Չեք կարող ինքներդ ձեզ հրավիրել։</b>"
        new_refferal = "<b>💎 Դուք նոր հրավիրված օգտատեր ունեք՝ @{user_name}։\n⚙️ Այժմ ունեք <code>{user_ref_count}</code> {convert_ref}։</b>"
        promo_act = "<b>📩 Պրոմոկոդն ակտիվացնելու համար մուտքագրեք այն։\n⚙️ Օրինակ՝ promo2025</b>"
        no_uses_promocode = "<b>❌ Պրոմոկոդի ակտիվացման ժամկետն ավարտվել է։</b>"
        no_promocode = "<b>❌ <code>{promocode}</code> պրոմոկոդը գոյություն չունի։</b>"
        yes_promocode = "<b>✅ Պրոմոկոդն ակտիվացվել է. ստացել եք <code>{discount}{curr}</code>։</b>"
        yes_uses_promocode = "<b>❌ Դուք արդեն ակտիվացրել եք այս պրոմոկոդը։</b>"
        no_cats = "<b>❌ Այս պահին կատեգորիաներ չկան։</b>"
        available_cats = "<b>🛒 Հասանելի կատեգորիաները՝</b>"
        current_cat = "<b>🚀 Ընթացիկ կատեգորիա՝ <code>{name}</code></b>"
        no_products = "❌ Այս պահին ապրանքներ չկան։"
        open_position_text = "<b>💎 Կատեգորիա՝ <code>{cat_name}</code>\n\n🛍️ Ապրանք՝ <code>{pos_name}</code>\n💰 Գին՝ <code>{price}{cur}</code>\n⚙️ Հասանելի քանակ՝ <code>{items}</code></b>\n\n{desc}"
        no_balance_for_buying = "❗ Գնելու համար բավարար միջոցներ չունեք։ Լիցքավորեք հաշվեկշիռը։"
        confirm_buy_products = "<b>❓ Վստա՞հ եք, որ ցանկանում եք գնել ապրանքը։</b>\n\n- Ապրանք՝ <code>{position_name}</code>\n- Քանակ՝ <code>{count} հատ</code>\n- Ընդհանուր գումար՝ <code>{price}{curr}</code>"
        enter_count_items_for_buy = "<b>❗ Մուտքագրեք գնվող ապրանքների քանակը՝</b>\n⚠️ <code>1</code>-ից <code>{items}</code>\n\n- Ապրանք՝ <code>{pos_name}</code> — <code>{price}{curr}</code>\n- Ձեր հաշվեկշիռը՝ <code>{balance}{curr}</code>"
        incorrect_data = "<b>❌ Մուտքագրված տվյալները սխալ են։</b>"
        data_was_edit = "<b>❗ Ընտրված ապրանքը սպառվել է։</b>"
        incorrect_count_items = "<b>❌ Ապրանքների քանակը սխալ է։</b>"
        no_balance_on_account = "<b>❌ Հաշվեկշռում բավարար միջոցներ չկան։</b>"
        please_await_products = "<b>🔄 Սպասեք, ապրանքները պատրաստվում են։</b>"
        successful_buying = "<b>✅ Գնումը հաջողությամբ կատարվել է։</b>\n\n- Անդորրագիր՝ <code>{receipt}</code>\n- Ապրանք՝ <code>{position_name} | {purchase_count} հատ | {purchase_price}{curr}</code>\n- Գնման ամսաթիվ՝ <code>{date}</code>"
        receipt_purchase = "<b>⭐ Անդորրագիր <code>{receipt}</code>՝\n📌 Ապրանք՝ <code>{pos_name}</code>\n💰 Գումար՝ <code>{sum}{curr}</code>\n🛒 Քանակ՝ <code>{count} հատ</code>\n🎲 Ամսաթիվ՝ <code>{date}</code>\n🔗 Բովանդակություն՝</b>"
        last_10_purchases = "<b>🚀 Վերջին 10 գնումները</b>"
        no_have_purchases = "❗ Դուք դեռ գնումներ չունեք։"
        your_items = "<b>🛒 Ձեր ապրանքները</b>"
        no_contests = "❌ Այս պահին խաղարկություններ չկան։"
        choose_contest = "<b>🎉 Ընտրեք խաղարկությունը՝</b>"
        contest_text = "<b>🎉 Խաղարկություն #{contest_id}\n\n💰 Մրցանակ՝ <code>{prize}{cur}</code>\n🕒 Ավարտին մնացել է՝ <code>{end_time}</code>\n🎉 {winners_num} {winners}\n👥 {members_num} {members}</b>"
        conditions = "\n\n<b>❗ Պայմաններ՝</b>\n\n"
        conditions_refills = "<b>💳 {num} {refills} — {status}</b>\n"
        conditions_purchases = "<b>🛒 {num} {purchases} — {status}</b>\n"
        conditions_channels = "<b>✨ Բաժանորդագրվել {num} {channels_text}՝\n\n{channels}</b>\n"
        u_win_the_contest = "<b>🎉 Շնորհավորում ենք, դուք հաղթել եք խաղարկությունում։\n💰 Ձեզ փոխանցվել է {prize}{cur} մրցանակը։</b>"
        u_didnt_have_time_to_enter_contest = "Չհասցրիք մասնակցել։ 💥"
        success = "✅ Կատարված է"
        u_already_enter_contest = "❌ Դուք արդեն մասնակցում եք։"
        contest_already_ended = "💥 Խաղարկությունն արդեն ավարտվել է։"

    AdminTexts = Russian.AdminTexts
