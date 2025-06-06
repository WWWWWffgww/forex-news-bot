from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import requests
from bs4 import BeautifulSoup
import asyncio

# 🔐 Токен твоего Telegram-бота
API_TOKEN = '7910558919:AAFlI7JWP3s-MTPV6ILpzQzgnRZSBPnSyGo'

# 📡 Канал, куда бот будет отправлять новости
CHANNEL_ID = '@forex_news_100k'

# 🤖 Инициализация бота
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# 📥 Получение важных новостей с ForexFactory
async def fetch_forex_news():
    url = 'https://www.forexfactory.com/calendar'
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    important_news = []
    table = soup.find('table', {'id': 'calendar__table'})
    if not table:
        return

    rows = table.find_all('tr', class_='calendar__row')
    for row in rows:
        impact = row.find('td', class_='calendar__impact')
        if impact and 'high' in impact.get('class', []):
            time = row.find('td', class_='calendar__time').text.strip()
            title = row.find('td', class_='calendar__event').text.strip()
            country = row.find('td', class_='calendar__country').text.strip()
            currency = row.find('td', class_='calendar__currency').text.strip()

            msg = f"🔥 Важная новость ({currency}): {title}\n⏰ Время: {time} ({country})"
            important_news.append(msg)

    return important_news

# 🔁 Фоновая проверка новостей каждые 5 минут
async def scheduled_news_check():
    while True:
        news = await fetch_forex_news()
        if news:
            for n in news:
                await bot.send_message(CHANNEL_ID, n)
        await asyncio.sleep(300)  # 5 минут

# 🟢 Команда /start — приветствие
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    await message.answer("Привет! Я слежу за важными новостями на рынке Forex 📊")

# 🧪 Команда /force — ручная проверка новостей
@dp.message_handler(commands=['force'])
async def force_news(message: types.Message):
    news = await fetch_forex_news()
    if news:
        for n in news:
            await bot.send_message(CHANNEL_ID, n)
        await message.answer("📨 Новости отправлены вручную.")
    else:
        await message.answer("❌ Важных новостей не найдено.")

# 🚀 Запуск бота
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(scheduled_news_check())
    executor.start_polling(dp, skip_updates=True)
