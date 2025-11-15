import asyncio
import logging
from datetime import datetime
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, ChannelPrivateError, InviteHashInvalidError
from telethon.tl.functions.channels import GetParticipantsRequest, JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
from telethon.tl.types import ChannelParticipantsSearch

# === ТВОИ ДАННЫЕ ===
API_ID = 29385016
API_HASH = '3c57df8805ab5de5a23a032ed39b9af9'
BOT_TOKEN = '8324933170:AAFatQ1T42ZJ70oeWS2UJkcXFeiwUFCIXAk'

# ⚠️ ЗАМЕНИ НА СВОЙ USER ID (узнай через @userinfobot)
OWNER_ID = 6893832048

# === КЛИЕНТЫ ===
user_client = TelegramClient('user_account', API_ID, API_HASH)
bot_client = TelegramClient('bot_controller', API_ID, API_HASH)

logging.basicConfig(level=logging.INFO)

def clean_username(text: str) -> str:
    return text.replace('https://t.me/', '').replace('@', '').strip()

# === БОТ: ОБРАБОТКА КОМАНД ===
@bot_client.on(events.NewMessage(pattern='/start'))
async def start(event):
    if event.sender_id == OWNER_ID:
        await event.reply(
            "🔐 Привет, хозяин!\n"
            "Команды:\n"
            "`/join @chat` — вступить\n"
            "`/leave @chat` — выйти\n"
            "`/parse @chat` — вступить → собрать @username → выйти → отправить TXT",
            parse_mode='monospace'
        )

@bot_client.on(events.NewMessage(pattern=r'/join\s+(.+)'))
async def join_chat(event):
    if event.sender_id != OWNER_ID:
        return
    target = clean_username(event.pattern_match.group(1))
    try:
        await user_client(JoinChannelRequest(target))
        await event.reply(f"✅ Вступил в @{target}")
    except Exception as e:
        await event.reply(f"❌ Ошибка при входе: {e}")

@bot_client.on(events.NewMessage(pattern=r'/leave\s+(.+)'))
async def leave_chat(event):
    if event.sender_id != OWNER_ID:
        return
    target = clean_username(event.pattern_match.group(1))
    try:
        await user_client(LeaveChannelRequest(target))
        await event.reply(f"✅ Вышел из @{target}")
    except Exception as e:
        await event.reply(f"❌ Ошибка при выходе: {e}")

@bot_client.on(events.NewMessage(pattern=r'/parse\s+(.+)'))
async def parse_and_leave(event):
    if event.sender_id != OWNER_ID:
        return

    target = clean_username(event.pattern_match.group(1))
    await event.reply(f"🔄 Запускаю: вступление → парсинг → выход из @{target}")

    # === 1. Вступить ===
    try:
        await user_client(JoinChannelRequest(target))
        await event.reply("✅ Вступил в чат")
    except InviteHashInvalidError:
        await event.reply("❌ Ссылка недействительна или чат не существует")
        return
    except FloodWaitError as e:
        await event.reply(f"⏳ Флуд-бан. Подожди {e.seconds} сек")
        return
    except Exception as e:
        await event.reply(f"❌ Не удалось вступить: {e}")
        return

    # === 2. Собрать участников ===
    try:
        chat = await user_client.get_entity(target)
        participants = []
        offset = 0
        limit = 200

        while True:
            result = await user_client(GetParticipantsRequest(
                channel=chat,
                filter=ChannelParticipantsSearch(''),
                offset=offset,
                limit=limit,
                hash=0
            ))
            if not result.users:
                break
            participants.extend(result.users)
            offset += len(result.users)
            if len(result.users) < limit:
                break

        # Фильтруем: только пользователи с username (и не боты)
        usernames = []
        for u in participants:
            if hasattr(u, 'username') and u.username and not getattr(u, 'bot', False):
                usernames.append(f"@{u.username}")

        # Уникальность и лимит
        usernames = list(dict.fromkeys(usernames))[:500]  # максимум 500

        if not usernames:
            await event.reply("⚠️ Никто из участников не имеет username")
            await user_client(LeaveChannelRequest(chat))
            return

        # === 3. Сохранить TXT ===
        filename = f"usernames_{target}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(usernames))

        # === 4. Выйти ===
        await user_client(LeaveChannelRequest(chat))

        # === 5. Отправить файл ===
        await bot_client.send_file(
            OWNER_ID,
            filename,
            caption=f"✅ Собрано {len(usernames)} username из @{target}\nФайл содержит только @username, по одному на строку."
        )
        await event.reply("📤 Готово! Файл отправлен.")

    except Exception as e:
        await event.reply(f"❌ Ошибка при парсинге: {e}")
        try:
            await user_client(LeaveChannelRequest(target))
        except:
            pass

# === ЗАПУСК ===
async def main():
    await user_client.start()
    print("✅ Аккаунт пользователя запущен")
    
    await bot_client.start(bot_token=BOT_TOKEN)
    print("✅ Бот запущен. Напиши ему /start")

    await asyncio.Event().wait()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Остановлено")
