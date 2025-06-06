from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import requests
from bs4 import BeautifulSoup
import asyncio

# 🔐 Токен твоего бота (не публикуй его нигде, кроме этого файла!)
API_TOKEN = '7910558919:AAFlI7JWP3s-MTPV6ILpzQzgnRZSBPnSyGo'

# 🟢 Укажи здесь свой канал. Обязательно начни с @ (если он публичный)
CHANNEL_ID = '@forex_alerts_100k'  # Заменишь, когда создашь канал

# Инициализация бота
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# 📥 Функция парсинга новостей с ForexFactory
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

# 🔁 Цикл проверки новостей каждые 5 минут
async def scheduled_news_check():
    while True:
        news = await fetch_forex_news()
        if news:
            for n in news:
                await bot.send_message(CHANNEL_ID, n)
        await asyncio.sleep(300)  # 300 секунд = 5 минут

# 💬 Команда /start — для ручного запуска
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    await message.answer("Привет! Я бот, который уведомляет о важных Forex-новостях 🧾")

# 🚀 Запуск
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(scheduled_news_check())
    executor.start_polling(dp, skip_updates=True)
