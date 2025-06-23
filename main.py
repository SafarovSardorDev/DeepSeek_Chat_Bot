import os
import requests
import json
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
MANDATORY_CHANNEL = os.getenv("MANDATORY_CHANNEL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
YOUR_SITE_URL = os.getenv("YOUR_SITE_URL", "https://t.me/your_bot")
YOUR_SITE_NAME = os.getenv("YOUR_SITE_NAME", "DeepSeek Chat Bot")

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

async def check_subscription(user_id: int) -> bool:
    """
    Improved subscription check with better error handling
    """
    try:
        member = await bot.get_chat_member(chat_id=MANDATORY_CHANNEL, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"Subscription check error: {e}")
        try:
            await bot.send_chat_action(chat_id=MANDATORY_CHANNEL, user_id=user_id, action="typing")
            return True
        except:
            return False

async def get_deepseek_response(user_message: str) -> str:
    """
    More robust API response handling
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": YOUR_SITE_URL,
        "X-Title": YOUR_SITE_NAME
    }
    
    payload = {
        "model": "deepseek/deepseek-r1-0528:free",
        "messages": [{"role": "user", "content": user_message}]
    }
    
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            data=json.dumps(payload),
            timeout=30
        )
        
        response.raise_for_status()
        response_data = response.json()
        
        if "choices" in response_data and len(response_data["choices"]) > 0:
            return response_data["choices"][0]["message"]["content"]
        elif "error" in response_data:
            return f"⚠️ API xatosi: {response_data['error'].get('message', 'Nomalum xato')}"
        else:
            return "⚠️ Kutilmagan API javobi formati"
            
    except requests.exceptions.RequestException as e:
        print(f"API connection error: {e}")
        return "⚠️ API serveriga ulanib bo'lmadi. Iltimos, keyinroq urunib ko'ring."
    except Exception as e:
        print(f"API processing error: {e}")
        return "⚠️ Javobni qayta ishlashda xatolik yuz berdi."

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    
    if await check_subscription(user_id):
        await message.reply("""
✅ Siz kanalga obuna bo'lgansiz!
Menga istalgan savolingizni yuborishingiz mumkin.
Menga savolingizni yuboring
Men DeepSeek AI yordamida javob beraman
Iltimos faqat ozroq kuting, DeepSeek o'zi sekin javob qaytaradi.
""")
    else:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("✅ Obunani tekshirish", callback_data="check_subscription"))
        keyboard.add(types.InlineKeyboardButton("📢 Kanalga o'tish", url=f"https://t.me/{MANDATORY_CHANNEL[1:]}"))
        
        await message.reply(
            f"""👋 Assalomu alaykum! Botdan foydalanish uchun quyidagi kanalga obuna bo'lishingiz kerak: {MANDATORY_CHANNEL}

Obuna bo'lish uchun:
1. Yuqoridagi kanalga kiring
2. "Join" tugmasini bosing
3. "✅ Obunani tekshirish" tugmasini bosing

Agar obuna bo'lsangiz, lekin bot ishlamasa, /start ni qayta yuboring.""",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )

@dp.callback_query_handler(lambda c: c.data == "check_subscription")
async def process_callback_check_subscription(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    
    if await check_subscription(user_id):
        # Obuna bo'lgan - xabarni o'zgartiramiz
        await callback_query.message.edit_text(
            "✅ Siz kanalga obuna bo'ldingiz! Endi bemalol savollar yuborishingiz mumkin."
        )
    else:
        # Obuna bo'lmagan - faqat alert chiqaramiz
        await bot.answer_callback_query(
            callback_query.id,
            "❌ Siz hali kanalga obuna bo'lmagansiz! Iltimos, obuna bo'ling.",
            show_alert=True
        )
    
    # Callback queryga javob qaytarish
    await bot.answer_callback_query(callback_query.id)

@dp.message_handler()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    
    if not await check_subscription(user_id):
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("📢 Kanalga o'tish", url=f"https://t.me/{MANDATORY_CHANNEL[1:]}"))
        
        await message.reply(
            f"❌ Siz kanalga obuna bo'lmagansiz! Botdan foydalanish uchun quyidagi kanalga obuna bo'ling: {MANDATORY_CHANNEL}",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        return
    
    await bot.send_chat_action(user_id, "typing")
    
    try:
        # DeepSeek API dan response olish
        response_text = await get_deepseek_response(message.text)
        
        # response yuborish (uzun xabarlarni split qilib)
        if len(response_text) > 4096:
            parts = [response_text[i:i+4096] for i in range(0, len(response_text), 4096)]
            for part in parts:
                await message.reply(part)
                await asyncio.sleep(1) 
        else:
            await message.reply(response_text)
            
    except Exception as e:
        print(f"Error processing message: {e}")
        await message.reply("⚠️ Kechirasiz, xabaringizni qayta ishlashda xatolik yuz berdi. Iltimos, keyinroq qayta urunib ko'ring.")

if __name__ == '__main__':
    import asyncio
    executor.start_polling(dp, skip_updates=True)