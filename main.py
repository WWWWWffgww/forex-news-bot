import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
from playwright.async_api import async_playwright

API_TOKEN = '7910558919:AAFlI7JWP3s-MTPV6ILpzQzgnRZSBPnSyGo'
CHANNEL_ID = '@forex_news_alert_100k_bot'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

def get_main_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🌐 ВСЕ НОВОСТИ С САЙТА", callback_data='news_all_raw')
    )
    return kb

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    await message.answer("Привет! Выбери действие 👇", reply_markup=get_main_menu())

@dp.callback_query_handler(lambda c: c.data == 'news_all_raw')
async def handle_all_news(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id, text="Загружаю сайт...")
    news_list = await fetch_all_forex_news_playwright()
    if news_list:
        for news in news_list:
            await bot.send_message(callback_query.from_user.id, news)
    else:
        await bot.send_message(callback_query.from_user.id, "😔 Новости не найдены.")

async def fetch_all_forex_news_playwright():
    news_items = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto("https://www.forexfactory.com/calendar", timeout=60000)
            await page.wait_for_selector("table.calendar__table")

            rows = await page.query_selector_all("tr.calendar__row")

            for row in rows:
                time = await row.query_selector_eval("td.calendar__time", "e => e.textContent?.trim()") or "—"
                currency = await row.query_selector_eval("td.calendar__currency", "e => e.textContent?.trim()") or "—"
                event = await row.query_selector_eval("td.calendar__event", "e => e.textContent?.trim()") or "—"

                impact_el = await row.query_selector("td.calendar__impact")
                impact_html = await impact_el.inner_html() if impact_el else ""

                if "high" in impact_html:
                    impact = "🔴 High"
                elif "medium" in impact_html:
                    impact = "🟠 Medium"
                elif "low" in impact_html:
                    impact = "🟡 Low"
                else:
                    impact = "⚪ Unknown"

                message = f"{impact} — {event} ({currency})\n🕒 {time}"
                news_items.append(message)

            await browser.close()
    except Exception as e:
        print(f"❌ Ошибка Playwright: {e}")

    print(f"✅ Получено новостей: {len(news_items)}")
    return news_items

if __name__ == '__main__':
    print("✅ Бот запущен. Таблица теперь видна и новости читаются.")
    executor.start_polling(dp, skip_updates=True)
