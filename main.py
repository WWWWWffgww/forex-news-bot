import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

API_TOKEN = '7910558919:AAFlI7JWP3s-MTPV6ILpzQzgnRZSBPnSyGo'
CHANNEL_ID = '@forex_news_alert_100k_bot'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

def get_main_menu():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("📅 НОВОСТИ ДНЯ", callback_data="today"),
        InlineKeyboardButton("📆 ЗАВТРА", callback_data="tomorrow"),
        InlineKeyboardButton("🔴 ВАЖНЫЕ", callback_data="important"),
        InlineKeyboardButton("✅ ВСЕ", callback_data="all"),
        InlineKeyboardButton("🌐 ВСЕ НОВОСТИ С САЙТА", callback_data="raw")
    )
    return kb

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer("Привет! Выбери действие 👇", reply_markup=get_main_menu())

@dp.callback_query_handler(lambda c: c.data in ['today', 'tomorrow', 'important', 'all', 'raw'])
async def handle_buttons(callback: types.CallbackQuery):
    await bot.answer_callback_query(callback.id)
    await bot.send_message(callback.from_user.id, "⏳ Загружаю новости...")

    if callback.data == "raw":
        news = await fetch_forex_news()
    elif callback.data == "today":
        news = await fetch_forex_news(day="today")
    elif callback.data == "tomorrow":
        news = await fetch_forex_news(day="tomorrow")
    elif callback.data == "important":
        news = await fetch_forex_news(impact_filter=["high", "medium"])
    elif callback.data == "all":
        news = await fetch_forex_news(impact_filter=["high", "medium", "low", "unknown"])
    else:
        news = []

    if news:
        for n in news:
            await bot.send_message(callback.from_user.id, n)
    else:
        await bot.send_message(callback.from_user.id, "😔 Новости не найдены.")

async def fetch_forex_news(day=None, impact_filter=None):
    news_items = []
    target_date = datetime.utcnow().date()
    if day == "tomorrow":
        target_date += timedelta(days=1)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto("https://www.forexfactory.com/calendar", timeout=60000)
            await page.wait_for_selector("table.calendar__table")
            await asyncio.sleep(3)

            rows = await page.query_selector_all("tr.calendar__row")

            for row in rows:
                time = await row.query_selector_eval("td.calendar__time", "e => e.textContent?.trim()") or "-"
                event = await row.query_selector_eval("td.calendar__event", "e => e.textContent?.trim()") or "-"
                currency = await row.query_selector_eval("td.calendar__currency", "e => e.textContent?.trim()") or "-"

                impact_el = await row.query_selector("td.calendar__impact")
                impact_html = await impact_el.inner_html() if impact_el else ""
                if "high" in impact_html:
                    impact = "🔴 High"
                    impact_level = "high"
                elif "medium" in impact_html:
                    impact = "🟧 Medium"
                    impact_level = "medium"
                elif "low" in impact_html:
                    impact = "🟨 Low"
                    impact_level = "low"
                elif "holiday" in impact_html:
                    continue  # исключаем зелёные
                else:
                    impact = "⚪ Unknown"
                    impact_level = "unknown"

                if impact_filter and impact_level not in impact_filter:
                    continue

                date_attr = await row.get_attribute("data-event-datetime")
                if date_attr:
                    event_date = datetime.strptime(date_attr, "%Y-%m-%dT%H:%M:%S.%fZ").date()
                    if day in ["today", "tomorrow"] and event_date != target_date:
                        continue

                message = f"{impact} — {event} ({currency})\n🕒 {time}"
                news_items.append(message)

            await browser.close()
    except Exception as e:
        print(f"[❌ Ошибка парсинга]: {e}")

    return news_items

if __name__ == '__main__':
    print("✅ Бот запущен на Playwright с кнопками и фильтрацией")
    executor.start_polling(dp, skip_updates=True)
