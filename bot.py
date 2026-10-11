import asyncio
import logging
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import os

from database import init_db, add_user, add_task, get_all_users, get_tasks_by_date, update_task_status, get_incomplete_tasks

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

def status_keyboard(task_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ انجام شد", callback_data=f"st:{task_id}:done")],
        [InlineKeyboardButton(text="🟢 مطلوب", callback_data=f"st:{task_id}:good")],
        [InlineKeyboardButton(text="🟡 با تأخیر", callback_data=f"st:{task_id}:delay")],
        [InlineKeyboardButton(text="🔴 معوق", callback_data=f"st:{task_id}:overdue")]
    ])

@dp.message(Command("start"))
async def cmd_start(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("سلام آقای شادلو\nربات آماده است.\n\n/adduser\n/addtask\n/list\n/users\n/carry")
    else:
        await message.answer("شما به عنوان مسئول ثبت شدید.")

@dp.message(Command("adduser"))
async def cmd_adduser(message: Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        parts = message.text.split(maxsplit=2)
        await add_user(parts[1], parts[2], message.from_user.id)
        await message.answer(f"✅ {parts[1]} اضافه شد.")
    except:
        await message.answer("فرمت: /adduser نام یوزرنیم")

@dp.message(Command("users"))
async def cmd_users(message: Message):
    if message.from_user.id != ADMIN_ID: return
    users = await get_all_users()
    text = "لیست مسئولین:\n\n" + "\n".join([f"• {n} → @{u}" for n, u in users]) if users else "خالی"
    await message.answer(text)

@dp.message(Command("addtask"))
async def cmd_addtask(message: Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        text = message.text.replace("/addtask", "").strip()
        parts = re.findall(r'"([^"]*)"', text)
        if len(parts) < 2:
            await message.answer("نام تسک و منابع را داخل \" \" بگذارید.")
            return
        task_name, resources = parts[0], parts[1]
        remaining = text
        for p in parts: remaining = remaining.replace(f'"{p}"', "")
        rp = remaining.split()
        if len(rp) < 4:
            await message.answer("فرمت کامل نیست.")
            return
        date, time, username, percent = rp[0], rp[1], rp[2], int(rp[3])
        await add_task(date, time, task_name, username, percent, resources)
        await message.answer(f"✅ تسک ثبت شد:\n{task_name}\n@{username} | {percent}%")
    except Exception as e:
        await message.answer(f"خطا: {e}")

@dp.message(Command("list"))
async def cmd_list(message: Message):
    if message.from_user.id != ADMIN_ID: return
    today = datetime.now().strftime("%Y-%m-%d")
    tasks = await get_tasks_by_date(today)
    if not tasks:
        await message.answer("تسکی برای امروز نیست.")
        return
    text = "تسک‌های امروز:\n\n"
    for t in tasks:
        carried = " (از هفته قبل)" if t[11] else ""
        text += f"ID:{t[0]} | {t[3]}{carried}\nمسئول: @{t[4]} | پلان:{t[5]}% | وضعیت:{t[7]}\n\n"
    await message.answer(text)

@dp.message(Command("carry"))
async def cmd_carry(message: Message):
    if message.from_user.id != ADMIN_ID: return
    today = datetime.now().strftime("%Y-%m-%d")
    incomplete = await get_incomplete_tasks(today)
    if not incomplete:
        await message.answer("تسک ناتمامی وجود ندارد.")
        return
    text = "تسک‌های ناتمام:\n\n"
    for t in incomplete:
        text += f"ID:{t[0]} | {t[3]} | واقعی:{t[8]}% از {t[5]}%\n"
    text += "\nبرای انتقال به هفته بعد بزنید:\n/confirm_carry"
    await message.answer(text)

@dp.message(Command("confirm_carry"))
async def cmd_confirm_carry(message: Message):
    if message.from_user.id != ADMIN_ID: return
    today = datetime.now().strftime("%Y-%m-%d")
    next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    incomplete = await get_incomplete_tasks(today)
    count = 0
    for t in incomplete:
        await add_task(next_week, t[2], t[3], t[4], t[5], t[6], carried=1)
        count += 1
    await message.answer(f"✅ {count} تسک به هفته بعد منتقل شد (با علامت از هفته قبل).")

# دریافت عکس یا فیلم از مسئول
@dp.message(F.photo | F.video)
async def handle_media(message: Message):
    file_id = message.photo[-1].file_id if message.photo else message.video.file_id
    caption = message.caption or "بدون توضیح"
    await bot.send_message(ADMIN_ID, f"📷 گزارش تصویری از @{message.from_user.username}:\n{caption}")
    await bot.send_photo(ADMIN_ID, file_id) if message.photo else await bot.send_video(ADMIN_ID, file_id)
    await message.answer("گزارش تصویری برای مدیر ارسال شد.")

async def main():
    await init_db()
    print("ربات روشن شد...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())