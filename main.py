from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
import requests
from bs4 import BeautifulSoup
import asyncio
from datetime import datetime, timedelta

# 🔐 Токен твоего Telegram-бота
API_TOKEN = '7910558919:AAFlI7JWP3s-MTPV6ILpzQzgnRZSBPnSyGo'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_filters = {}  # user_id: {'high', 'medium'} или {'ALL'}

def get_main_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📅 НОВОСТИ ДНЯ", callback_data='news_today'),
        InlineKeyboardButton("📆 ЗАВТРА", callback_data='news_tomorrow'),
        InlineKeyboardButton("🕘 ВАЖНЫЕ", callback_data='news_important'),
        InlineKeyboardButton("⚙️ ФИЛЬТР", callback_data='set_filter'),
        InlineKeyboardButton("✅ ВСЕ", callback_data='filter_all')
    )
    return kb

def get_filter_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🟥 Красные", callback_data='filter_high'),
        InlineKeyboardButton("🟨 Жёлтые", callback_data='filter_medium'),
        InlineKeyboardButton("🟩 Зелёные", callback_data='filter_low'),
        InlineKeyboardButton("🔙 Назад", callback_data='back')
    )
    return kb

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user_filters[message.from_user.id] = {'high'}
    await message.answer("Привет! Выбери действие 👇", reply_markup=get_main_menu())

@dp.callback_query_handler(lambda c: c.data.startswith('news_') or c.data.startswith('filter_') or c.data == 'back' or c.data == 'set_filter')
async def callback_handler(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in user_filters:
        user_filters[user_id] = {'high'}

    if callback_query.data == 'news_today':
        news = await fetch_forex_news(day_offset=0)
        await send_news(callback_query.from_user.id, news, user_id)

    elif callback_query.data == 'news_tomorrow':
        news = await fetch_forex_news(day_offset=1)
        await send_news(callback_query.from_user.id, news, user_id)

    elif callback_query.data == 'news_important':
        news = await fetch_forex_news(day_offset=0, last_minutes=10)
        await send_news(callback_query.from_user.id, news, user_id)

    elif callback_query.data == 'set_filter':
        await bot.send_message(callback_query.from_user.id, "Выбери уровни важности:", reply_markup=get_filter_menu())

    elif callback_query.data == 'filter_all':
        user_filters[user_id] = {'ALL'}
        await bot.send_message(callback_query.from_user.id, "Фильтрация отключена. Теперь будут отображаться все новости.")

    elif callback_query.data.startswith('filter_'):
        level = callback_query.data.replace('filter_', '')
        if user_filters.get(user_id) == {'ALL'}:
            user_filters[user_id] = set()
        if level in {'high', 'medium', 'low'}:
            if level in user_filters[user_id]:
                user_filters[user_id].remove(level)
            else:
                user_filters[user_id].add(level)
        current = ', '.join(user_filters[user_id]) or 'ничего не выбрано'
        await bot.send_message(callback_query.from_user.id, f"Текущие фильтры: {current}")

    elif callback_query.data == 'back':
        await bot.send_message(callback_query.from_user.id, "Главное меню 👇", reply_markup=get_main_menu())

    await bot.answer_callback_query(callback_query.id)

def filter_by_user(news_list, user_id):
    filters = user_filters.get(user_id, {'high'})
    if 'ALL' in filters:
        return news_list
    return [n for n in news_list if n['impact'] in filters]

async def send_news(chat_id, news, user_id):
    filtered = filter_by_user(news, user_id)
    if filtered:
        for item in filtered:
            await bot.send_message(chat_id, item['text'])
    else:
        await bot.send_message(chat_id, "Нет новостей по выбранным критериям.")

async def fetch_forex_news(day_offset=0, last_minutes=None):
    url = 'https://www.forexfactory.com/calendar'
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    table = soup.find('table', {'id': 'calendar__table'})
    if not table:
        return []

    rows = table.find_all('tr', class_='calendar__row')
    news_items = []
    now = datetime.utcnow()
    target_day = (now + timedelta(days=day_offset)).date()

    for row in rows:
        time_cell = row.find('td', class_='calendar__time')
        event_cell = row.find('td', class_='calendar__event')
        impact_cell = row.find('td', class_='calendar__impact')
        currency_cell = row.find('td', class_='calendar__currency')

        if not all([time_cell, event_cell, impact_cell, currency_cell]):
            continue

        time_str = time_cell.text.strip()
        if time_str.lower() in ['all day', 'tentative', '']:
            continue

        try:
            time_obj = datetime.strptime(time_str, '%I:%M%p')
            time_obj = time_obj.replace(year=now.year, month=now.month, day=now.day)
        except:
            continue

        if time_obj.date() != target_day:
            continue

        impact_class = impact_cell.find('span')['class']
        if 'high' in impact_class:
            impact = 'high'
        elif 'medium' in impact_class:
            impact = 'medium'
        elif 'low' in impact_class:
            impact = 'low'
        else:
            impact = 'unknown'

        if last_minutes:
            if abs((now - time_obj).total_seconds()) > last_minutes * 60:
                continue

        emoji = '🟥' if impact == 'high' else '🟨' if impact == 'medium' else '🟩'
        text = f"{emoji} {event_cell.text.strip()} — {time_str} ({currency_cell.text.strip()})"
        news_items.append({'impact': impact, 'text': text})

    return news_items

# 📢 Автоматическая рассылка важных новостей в канал
async def auto_broadcast():
    already_sent = set()
    while True:
        news = await fetch_forex_news(day_offset=0, last_minutes=5)
        for item in news:
            if item['impact'] == 'high' and item['text'] not in already_sent:
                await bot.send_message(CHANNEL_ID, f"🔥 Важная новость:\n{item['text']}")
                already_sent.add(item['text'])
        await asyncio.sleep(300)  # каждые 5 минут

if __name__ == '__main__':
    print("✅ Бот запущен и работает с авторассылкой")
    loop = asyncio.get_event_loop()
    loop.create_task(auto_broadcast())
    executor.start_polling(dp, skip_updates=True)
