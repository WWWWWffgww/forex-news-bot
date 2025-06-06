from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
import requests
from bs4 import BeautifulSoup
import asyncio
from datetime import datetime

# 🔐 Токен твоего Telegram-бота
API_TOKEN = '7910558919:AAFlI7JWP3s-MTPV6ILpzQzgnRZSBPnSyGo'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Сохраняем выбранные фильтры по пользователю
user_filters = {}

# Главное меню
def get_main_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📅 НОВОСТИ ДНЯ", callback_data='news_today'),
        InlineKeyboardButton("🔴 ВАЖНЫЕ", callback_data='news_important'),
        InlineKeyboardButton("⚙️ ФИЛЬТР", callback_data='set_filter')
    )
    return kb

# Меню фильтра по цвету
def get_filter_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🟥 Красные", callback_data='filter_high'),
        InlineKeyboardButton("🟨 Жёлтые", callback_data='filter_medium'),
        InlineKeyboardButton("🟩 Зелёные", callback_data='filter_low'),
        InlineKeyboardButton("✅ Назад", callback_data='back')
    )
    return kb

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user_filters[message.from_user.id] = {'high'}
    await message.answer("Привет! Выбери действие 👇", reply_markup=get_main_menu())

@dp.callback_query_handler(lambda c: c.data in ['news_today', 'news_important', 'set_filter', 'filter_high', 'filter_medium', 'filter_low', 'back'])
async def callback_handler(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in user_filters:
        user_filters[user_id] = {'high'}

    if callback_query.data == 'news_today':
        news = await fetch_forex_news(include_all_today=True)
        if news:
            for item in news:
                await bot.send_message(callback_query.from_user.id, item['text'])
        else:
            await bot.send_message(callback_query.from_user.id, "Сегодня пока нет новостей.")
    elif callback_query.data == 'news_important':
        news = await fetch_forex_news(last_minutes=10)
        filtered = filter_by_user(news, user_id)
        if filtered:
            for item in filtered:
                await bot.send_message(callback_query.from_user.id, item['text'])
        else:
            await bot.send_message(callback_query.from_user.id, "Нет важных новостей за последние 10 минут.")
    elif callback_query.data == 'set_filter':
        await bot.send_message(callback_query.from_user.id, "Выбери уровень важности:", reply_markup=get_filter_menu())
    elif callback_query.data.startswith('filter_'):
        level = callback_query.data.replace('filter_', '')
        if level in {'high', 'medium', 'low'}:
            if level in user_filters[user_id]:
                user_filters[user_id].remove(level)
            else:
                user_filters[user_id].add(level)
        selected = ', '.join(user_filters[user_id]) or 'ничего не выбрано'
        await bot.send_message(callback_query.from_user.id, f"Выбрано: {selected}")
    elif callback_query.data == 'back':
        await bot.send_message(callback_query.from_user.id, "Главное меню 👇", reply_markup=get_main_menu())

    await bot.answer_callback_query(callback_query.id)

# Фильтрация новостей по фильтрам пользователя
def filter_by_user(news_list, user_id):
    filters = user_filters.get(user_id, {'high'})
    return [n for n in news_list if n['impact'] in filters]

# Парсер новостей с сайта
async def fetch_forex_news(include_all_today=False, last_minutes=None):
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

    for row in rows:
        time_cell = row.find('td', class_='calendar__time')
        event_cell = row.find('td', class_='calendar__event')
        impact_cell = row.find('td', class_='calendar__impact')
        country_cell = row.find('td', class_='calendar__country')
        currency_cell = row.find('td', class_='calendar__currency')

        if not all([time_cell, event_cell, impact_cell, country_cell, currency_cell]):
            continue

        time_str = time_cell.text.strip()
        if time_str.lower() in ['all day', '']:
            continue

        try:
            time_obj = datetime.strptime(time_str, '%I:%M%p')
            time_obj = time_obj.replace(year=now.year, month=now.month, day=now.day)
        except:
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

        news_items.append({
            'impact': impact,
            'text': f"{'🟥' if impact=='high' else '🟨' if impact=='medium' else '🟩'} {event_cell.text.strip()} — {time_str} ({currency_cell.text.strip()})"
        })

    return news_items

# Старт бота
if __name__ == '__main__':
    print("✅ Бот запущен и готов к работе.")
    executor.start_polling(dp, skip_updates=True)
