from tgbot.data.config import BotConfig, BotTexts, DB
from tgbot.data.loader import bot
from tgbot.utils.models import Contest
from rates import get_def_exchanges, get_exchanges

import time
import random
import asyncio
import aiohttp
from bs4 import BeautifulSoup as bs
from datetime import datetime, timedelta

# Обновление курсов валют
async def check_rates() -> None:
    rate_usd_to_rub, rate_usd_to_eur, rate_eur_to_rub, rate_eur_to_usd, rate_rub_to_usd, rate_rub_to_eur = await get_def_exchanges()

    await DB.update_rates(usd_rub=rate_usd_to_rub, usd_eur=rate_usd_to_eur, eur_rub=rate_eur_to_rub,
                          eur_usd=rate_eur_to_usd, rub_usd=rate_rub_to_usd, rub_eur=rate_rub_to_eur)


# Перевести из одной валюты в другую
async def get_exchange(amount: float, cur1: str, cur2: str) -> float | int:
    try:
        if cur1.upper() == cur2.upper():
            return round(float(amount), 2)
        if "AMD" in {cur1.upper(), cur2.upper()}:
            rate = await get_exchanges(1, cur1.upper(), cur2.upper())
            return round(float(rate * amount), 2)
        rate_usd_to_rub, rate_usd_to_eur, rate_eur_to_rub, rate_eur_to_usd, rate_rub_to_usd, rate_rub_to_eur = await DB.get_rates()

        if amount == 0:
            return 0
        if cur1.upper() == 'RUB' and cur2.upper() == 'USD':
            return round(float(rate_rub_to_usd * amount), 2)
        elif cur1.upper() == 'RUB' and cur2.upper() == 'EUR':
            return round(float(rate_rub_to_eur * amount), 2)
        elif cur1.upper() == 'USD' and cur2.upper() == 'RUB':
            return round(float(rate_usd_to_rub * amount), 2)
        elif cur1.upper() == 'EUR' and cur2.upper() == 'RUB':
            return round(float(rate_eur_to_rub * amount), 2)
        elif cur1.upper() == 'USD' and cur2.upper() == 'EUR':
            return round(float(rate_usd_to_eur * amount), 2)
        elif cur1.upper() == 'EUR' and cur2.upper() == 'USD':
            return round(float(rate_eur_to_usd * amount), 2)
    except Exception as e:
        print(e)


async def get_currency_amounts(amount: float, currency: str) -> dict[str, float]:
    """Return one monetary value represented in every supported shop currency."""
    currency = currency.upper()
    result = {}
    for target in ("RUB", "USD", "EUR", "AMD"):
        result[target.lower()] = (round(float(amount), 2) if target == currency
                                  else await get_exchange(amount, currency, target))
    return result


# Рассылка сообщения админам
async def send_admins(phrase, is_phrase=True, is_channel=True, photo=None, file_id=None, **kwargs) -> None:
        if not BotConfig.LOGS_CHANNEL:
            is_channel = False
        
        if is_channel:
            texts = await get_language(BotConfig.ADMINS[0])
            if is_phrase:
                message = texts.ADMIN_TEXTS.__getattribute__(phrase).format(**kwargs)
            else:
                message = phrase
            
            if not photo and not file_id:
                await bot.send_message(BotConfig.LOGS_CHANNEL, text=message)
            if photo:
                await bot.send_photo(BotConfig.LOGS_CHANNEL, photo=photo, caption=message)
            if file_id:
                await bot.send_document(BotConfig.LOGS_CHANNEL, document=file_id, caption=message)
        else:
            for admin in BotConfig.ADMINS:
                texts = await get_language(admin)
                if is_phrase:
                    message = texts.ADMIN_TEXTS.__getattribute__(phrase).format(**kwargs)
                else:
                    message = phrase
                
                if not photo and not file_id:
                    await bot.send_message(admin, text=message)
                if photo:
                    await bot.send_photo(admin, photo=photo, caption=message)
                if file_id:
                    await bot.send_document(admin, document=file_id, caption=message)


# Получение текущего unix-времени
def get_unix(full: bool = False) -> float | int:
    if full:
        return time.time_ns()
    else:
        return int(time.time())


# Получение текущей даты
def get_date() -> str:
    this_date = datetime.today().replace(microsecond=0)
    this_date = this_date.strftime("%d.%m.%Y %H:%M:%S")

    return this_date


# Склонение слов в зависимости от числа
def numeral_noun_declension(number: int, words: tuple) -> str:
    nominative_singular, genetive_singular, nominative_plural = words
    return (
        (number in range(5, 20)) and nominative_plural or
        (1 in (number, (diglast := number % 10))) and nominative_singular or
        ({number, diglast} & {2, 3, 4}) and genetive_singular or nominative_plural
    )
    
    
# Разбив списка на несколько частей
def split_messages(get_list: list, count: int) -> list[list]:
    return [get_list[i:i + count] for i in range(0, len(get_list), count)]


# Получение списка каналов из строки
def get_channels(channels):
    try:
        if channels is None or channels == "-":
            return []
        
        channels = str(channels)
        if "," in channels:
            channels = channels.split(",")
        else:
            if len(channels) >= 1:
                channels = [channels]
            else:
                channels = []
        while "" in channels:
            channels.remove("")
        while " " in channels:
            channels.remove(" ")

        channels = list(map(int, channels))

        return channels
    except Exception as err:
        print(err)
        return []
    

# Получение читаемого формата времени для конца розыгрыша
def get_time_for_end_contest(contest: Contest, day_s: str) -> str:
    contest_time = contest.end_time - time.time()
    today = datetime.today()
    new_time = today + timedelta(seconds=contest_time)
    end_time = str(new_time - today).split(".")[0]
    if "days" in end_time or "day" in end_time:
        if "days" in end_time:
            end_time = end_time.replace(
                "days",
                numeral_noun_declension(int(end_time.split(" days")[0]), day_s)    
            )
        else:
            end_time = end_time.replace(
                "day",
                numeral_noun_declension(int(end_time.split(" day")[0]), day_s)    
            )
    return end_time


# Закончить розыгрыш
async def end_contest(contest: Contest):
    currency = contest.currency.value
    cur = BotConfig.CURRENCIES[currency]['sign']
    all_members = await DB.get_contest_members_id(contest.contest_id)
        
    winners_num = contest.winners_num
    
    if winners_num > len(all_members):
        winners_num = len(all_members)
        
    winners_ids = []
    if len(all_members) == 0:
        await DB.delete_contest(contest.contest_id)
        return await send_admins("contest_is_finished_and_members_are_zero_alert",
            prize=contest.prize,
            cur=cur
        )

    if winners_num == 1:
        random.shuffle(all_members)
        winners_ids.append(random.choice(all_members))
    else:
        while len(winners_ids) <= (winners_num - 1):
            random.shuffle(all_members)
            winner_id = random.choice(all_members)
            if winner_id in winners_ids:
                continue
            else:
                winners_ids.append(winner_id)
    
    await DB.delete_contest(contest.contest_id)
    for winner in winners_ids:
        user = await DB.get_user(user_id=winner)
        if user is None:
            continue
        amounts = await get_currency_amounts(contest.prize, currency)
        await DB.update_user(user_id=winner, **{
            f"balance_{code}": getattr(user, f"balance_{code}") + amount
            for code, amount in amounts.items()
        })
        try:
            member = await bot.get_chat(winner)
            await send_admins("contest_is_finished_alert", prize=contest.prize, cur=cur)
            await send_admins(f"<b><a href='tg://user?id={member.id}'>{member.full_name}</a> [<code>{member.id}</code>]</b>", False)
            await send_admins("prize_given")
        except Exception:
            pass
        try:
            texts = await get_language(winner)
            await bot.send_message(winner, texts.TEXTS.u_win_the_contest.format(
                prize=contest.prize, cur=cur
            ))
        except:
            pass


# Проверка розыгрышей на конец
async def check_contests() -> None:
    while True:
        await asyncio.sleep(3)
        contests = await DB.get_all_contests()
        if not contests:
            continue
        for contest in contests:
            contest_id = contest.contest_id
            now_time = time.time()
            members = await DB.get_contest_members_id(contest_id)
            if len(members) >= contest.members_num or contest.end_time < now_time:
                try:
                    await end_contest(contest)
                except Exception:
                    from traceback import print_exc
                    print_exc()
            

# Получение класса языка для пользователя
async def get_language(user_id: int) -> BotTexts.Hy:
    # Storefront is Armenian for both existing and new customers. Keep persisted
    # language settings untouched so the administrative panel is unaffected.
    return BotTexts.Hy
        
        
# Проверка обновлений 
async def check_updates() -> None:
    async with aiohttp.ClientSession() as session:
        ress = await session.get(f'https://sites.google.com/view/tosa-projects/главная-страница')
        res = await ress.text()
        soup = bs(res, "html.parser")
        res2 = soup.findAll('p', class_='zfr3Q CDt4Ke')
        ress = str(res2[1])
        res3 = ress.split("Актуальная версия: ")[1]
        current_version = res3.split('</span></p>')[0]
        if BotConfig.BOT_VERSION != current_version:
            msg = f"""
<b>❗❗❗ Обновление AutoShop'а ❗❗❗

🧩 Ваша текущая версия: <code>{BotConfig.BOT_VERSION}</code>
⭐ Новая версия: <code>{current_version}</code>

https://lolz.live/threads/4980786/
https://lolz.live/threads/4980786/
https://lolz.live/threads/4980786/

<u>Данное оповещение видят только администраторы бота!</u></b>
                """
            await send_admins(msg, False)
            
            
# Автоматическая очистка ежедневной статистики после 00:00
async def clear_stats_day() -> None:
    await DB.update_settings(profit_day=get_unix())
    

# Автоматическая очистка еженедельной статистики в понедельник 00:00
async def clear_stats_week() -> None:
    await DB.update_settings(profit_week=get_unix())
