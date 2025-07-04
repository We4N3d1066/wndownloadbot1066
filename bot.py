import telebot
import requests
from colorama import init, Fore, Style
import io
from datetime import datetime
from telebot import types
from yt_dlp import YoutubeDL
import tempfile
import os
import shutil
import subprocess

init(autoreset=True)
bot = telebot.TeleBot("7303743486:AAGJBwniF5dLEwF027NuoN8Vk-IPEAFDUAs")  

user_mode = {}

def download_tiktok_video(url):
    try:
        requests.head(url, allow_redirects=True)
        api = "https://tikwm.com/api/"
        data = requests.get(api, params={"url": url}).json()
        if "data" in data and "play" in data["data"]:
            return data["data"]["play"]
    except Exception as e:
        print(Fore.RED + f"❌ Ошибка при скачивании: {e}")
    return None

def download_youtube_video(url, format_id, bot=None, user_id=None, progress_message_id=None):
    try:
        temp_dir = tempfile.mkdtemp()
        outtmpl = os.path.join(temp_dir, '%(title)s.%(ext)s')
        progress = {'last_percent': -1}
        def progress_hook(d):
            if bot and user_id and progress_message_id and d['status'] == 'downloading':
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
                downloaded_bytes = d.get('downloaded_bytes', 0)
                speed = d.get('speed')
                eta = d.get('eta')
                if total_bytes:
                    percent = int(downloaded_bytes / total_bytes * 100)
                    if percent != progress['last_percent']:
                        bar = '█' * (percent // 10) + '░' * (10 - percent // 10)
                        text = f"⬇️ Скачивание: |{bar}| {percent}%"
                        try:
                            bot.edit_message_text(text, user_id, progress_message_id)
                        except Exception:
                            pass
                        progress['last_percent'] = percent
                    
                    speed_mb = speed / 1024 / 1024 if speed else 0
                    left_bytes = total_bytes - downloaded_bytes if total_bytes and downloaded_bytes else 0
                    left_mb = left_bytes / 1024 / 1024
                    print(f"[YT] {percent}% | {downloaded_bytes // (1024*1024)}MB/{total_bytes // (1024*1024)}MB | "
                          f"Скорость: {speed_mb:.2f} MB/s | Осталось: {left_mb:.2f} MB | ETA: {eta if eta else '?'} сек.", end='\r')
            if bot and user_id and progress_message_id and d['status'] == 'finished':
                try:
                    bot.edit_message_text('⬇️ Скачивание: |██████████| 100%\nГотово!', user_id, progress_message_id)
                except Exception:
                    pass
                print()  
        ydl_format = f"{format_id}+bestaudio/best"
        ydl_opts = {
            'format': ydl_format,
            'outtmpl': outtmpl,
            'quiet': True,
            'noplaylist': True,
            'merge_output_format': 'mp4',
            'progress_hooks': [progress_hook],
            'retries': 5,
            'fragment_retries': 10,
            'continuedl': True,
            'prefer_ffmpeg': True,
            'concurrent_fragment_downloads': 10,
            'http_chunk_size': 10485760,
            'noprogress': True,
            'no_warnings': True,
            'nocheckcertificate': True
        }
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        for filename in os.listdir(temp_dir):
            if filename.endswith('.mp4'):
                return os.path.join(temp_dir, filename)
        print(Fore.RED + "❌ Ошибка: файл .mp4 не найден в папке.")
    except Exception as e:
        print(Fore.RED + f"❌  Ошибка при скачивании YouTube-видео: {e}")
    return None

def get_youtube_info_ydl(url):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'noprogress': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'retries': 2
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    video_info = {
        "title": info.get("title", "Без названия"),
        "views": info.get("view_count", 0),
        "likes": info.get("like_count", 0),
        "publish_date": info.get("upload_date", "0000.00.00"),
        "channel": info.get("channel", "Неизвестно"),
        "duration": info.get("duration", 0),
        "thumbnail_url": info.get("thumbnail"),
        "formats": []
    }
    for fmt in info.get("formats", []):
        height = fmt.get("height")
        filesize = fmt.get("filesize") or fmt.get("filesize_approx")
        format_id = fmt.get("format_id")
        vcodec = fmt.get("vcodec")
        acodec = fmt.get("acodec")
        if height and filesize and format_id:
            size_mb = round(filesize / (1024 * 1024), 1)
            video_info["formats"].append({
                "format_id": format_id,
                "resolution": f"{height}p",
                "filesize_mb": size_mb
            })
        elif (vcodec == "none" and acodec != "none" and filesize and format_id):
            size_mb = round(filesize / (1024 * 1024), 1)
            video_info["formats"].append({
                "format_id": format_id,
                "resolution": "audio",
                "filesize_mb": size_mb
            })
    return video_info

def generate_video_card(info, user_id):
    TELEGRAM_FILE_LIMIT_MB = 49
    TELEGRAM_FILE_LIMIT = TELEGRAM_FILE_LIMIT_MB * 1024 * 1024
    title = info.get("title") or "Без названия"
    views = info.get("views") or 0
    likes = info.get("likes") or 0
    publish_date = info.get("publish_date") or "Неизвестно"
    if publish_date and publish_date.isdigit() and len(publish_date) == 8:
        publish_date = f"{publish_date[:4]}.{publish_date[4:6]}.{publish_date[6:]}"
    channel = info.get("channel") or "Неизвестный канал"
    duration = info.get("duration") or 0
    thumbnail_url = info.get("thumbnail_url")
    formats = info["formats"]
    try:
        minutes, seconds = divmod(int(duration), 60)
    except:
        minutes, seconds = 0, 0
    caption = (
        f"<b>{title}</b>\n"
        f"👁 {views:,}  ❤️ {likes:,} лайков\n"
        f"📅 {publish_date}\n"
        f"👤 {channel}\n"
        f"🕒 {minutes:02}:{seconds:02}\n\n"
        f"📥 Выбери качество (до {TELEGRAM_FILE_LIMIT_MB} МБ):"
    )
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    min_size_by_res = {}
    for fmt in formats:
        res = fmt.get("resolution") or "?"

        size = fmt.get("filesize_mb")
        format_id = fmt.get("format_id")
        size_bytes = size * 1024 * 1024 if size else None
        if not format_id or not size or size_bytes > TELEGRAM_FILE_LIMIT:
            continue
        if res == "?" and (not fmt.get("height")):
            res = "audio" if "audio" in (fmt.get("format_note") or "").lower() else "?"

        if res not in min_size_by_res or size < min_size_by_res[res]["filesize_mb"]:
            min_size_by_res[res] = fmt
    has_video = False
    for res, fmt in min_size_by_res.items():
        if res == "audio":
            continue
        size = fmt["filesize_mb"]
        format_id = fmt["format_id"]
        size_str = f"{size}mb"
        text = f"📹 🔸{res} - {size_str}"
        callback_data = f"yt_{format_id}"
        button = types.InlineKeyboardButton(text=text, callback_data=callback_data)
        keyboard.add(button)
        has_video = True
    best_audio = None
    for fmt in formats:
        is_audio = (
            (fmt.get("resolution") is None or fmt.get("resolution") == "audio") or
            ("audio" in (fmt.get("format_note") or "").lower())
        )
        if is_audio and fmt.get("filesize_mb"):
            size_bytes = fmt["filesize_mb"] * 1024 * 1024
            if size_bytes <= TELEGRAM_FILE_LIMIT:
                if not best_audio or fmt["filesize_mb"] < best_audio["filesize_mb"]:
                    best_audio = fmt
    if best_audio:
        audio_size = best_audio["filesize_mb"]
        audio_id = best_audio["format_id"]
        text = f"🎵🔸MP3 - {audio_size}mb"
        callback_data = f"ytmp3_{audio_id}"
        button = types.InlineKeyboardButton(text=text, callback_data=callback_data)
        keyboard.add(button)
    if not has_video and not best_audio:
        keyboard.add(types.InlineKeyboardButton(text="Нет подходящих форматов (до 49 МБ)", callback_data="yt_none"))

    if thumbnail_url and thumbnail_url.startswith("http"):
        if thumbnail_url.endswith('.webp'):
            thumbnail_url_jpg = thumbnail_url[:-5] + '.jpg'
        else:
            thumbnail_url_jpg = thumbnail_url
        try:
            bot.send_photo(user_id, photo=thumbnail_url_jpg, caption=caption, reply_markup=keyboard, parse_mode="HTML")
        except Exception as e:
            print(Fore.RED + f"❌ Ошибка отправки превью: {e}\nURL: {thumbnail_url_jpg}")
            bot.send_message(user_id, caption, reply_markup=keyboard, parse_mode="HTML")
    else:
        bot.send_message(user_id, caption, reply_markup=keyboard, parse_mode="HTML")

def download_instagram_video_ydl(url):
    try:
        temp_dir = tempfile.mkdtemp()
        outtmpl = os.path.join(temp_dir, '%(title)s.%(ext)s')
        ydl_opts = {
            'format': 'mp4',
            'outtmpl': outtmpl,
            'quiet': True,
            'noplaylist': True,
        }
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        for filename in os.listdir(temp_dir):
            if filename.endswith('.mp4'):
                return os.path.join(temp_dir, filename)
        print(Fore.RED + "❌ Ошибка: файл .mp4 не найден в папке.")
    except Exception as e:
        print(Fore.RED + f"❌ Ошибка при скачивании Instagram через yt_dlp: {e}")
    return None

def log_download(log_path, user, username, user_id, url):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = (
        f"👤 Пользователь: {user}\n"
        f"🔹 Юз: @{username}\n"
        f"🆔 ID: {user_id}\n"
        f"🔗 Ссылка: {url}\n"
        f"📅 Дата: {now}\n"
        f"----------------------------------------\n"
    )
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(log_entry)

@bot.message_handler(commands=['start'])
def start_message(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(
        types.KeyboardButton("📱 TikTok"),
        types.KeyboardButton("📺 YouTube"),
        types.KeyboardButton("📸 Instagram")
    )
    bot.send_message(
        message.chat.id,
        "Привет! 👋 Выбери приложение для скачивания видео.\nℹ️Или напиши команду /help для изучения бота",
        reply_markup=keyboard
    )

@bot.message_handler(func=lambda message: message.text in ["📱 TikTok", "📺 YouTube", "📸 Instagram"])
def select_platform(message):
    user_id = message.chat.id
    if message.text == "📱 TikTok":
        user_mode[user_id] = "tiktok"
        bot.send_message(user_id, "✅ Режим TikTok выбран. Отправь ссылку на видео 🎵")
    elif message.text == "📺 YouTube":
        user_mode[user_id] = {"mode": "youtube"}
        bot.send_message(user_id, "✅ Режим YouTube выбран. Отправь ссылку на видео 🎬.\n⚠️Примечание: Данный режим работает не полноценно в силу ограничений Telegram'a и нулевого бюджета разработки бота, потому он будет более комфортабельным для скачки музыки или небольших видео до 49MB.")
    elif message.text == "📸 Instagram":
        user_mode[user_id] = "instagram"
        bot.send_message(user_id, "✅ Режим Instagram выбран. Отправь ссылку на публикацию 📸")

@bot.message_handler(commands=['help'])
def help_command(message):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton(text="📄 О боте", callback_data="help_about"),
        types.InlineKeyboardButton(text="🆘 Помощь", callback_data="help_help"),
        types.InlineKeyboardButton(text="💰 Донат", callback_data="help_donate"),
        types.InlineKeyboardButton(text="🔗 Обратная связь", callback_data="help_feedback")
    )
    bot.send_message(
        message.chat.id,
        "ℹ️ Выберите раздел:",
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == "help_about")
def help_about_callback(call):
    about_text = (
        "<b>📄О боте</b>\n\n"
        "⚠️Бот — результат учебного эксперимента по освоению Telegram API и Python.\n"
        "Функционал не полный, потому что ни бюджета, ни полного доступа к BotAPI пока нет. "
        "Не полный фарш, но работает — и это главное.\n"
        "Если что-то сломается или пойдёт не так — напиши, исправим\n\n\n"
        "<b>ℹ️О функционале:</b>\n\n" 
        "📱 TikTok: Скачка видео (MP4) + скачка аудио (MP3);\n"
        "📺 YouTube: Получение информации о видео прямо в Telegram'e, скачка видео (MP4), скачка аудио (MP3);\n"
        "📸 Instagram: Скачка видео (MP4) + скачка аудио (MP3)."
    )
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="help_back"))
    try:
        bot.edit_message_text(
            about_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            about_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

@bot.callback_query_handler(func=lambda call: call.data == "help_help")
def help_help_callback(call):
    help_text = (
        "<b>🆘 Помощь</b>\n\n"
        "📱 TikTok: Видео скачиваются без водяных знаков. А также материалы с закрытых аккаунтов не могут быть скачаны в связи с политикой конфиденциальности TikTok;\n\n"
        "📺 YouTube: С помощью команды '@vid ...' можно находить видео или музыку прямо в Telegram'e;\n\n"
        "📸 Instagram: Материалы с закрытых аккаунтов не могут быть скачаны в связи с политикой конфиденциальности Instagram."
    )
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="help_back"))
    try:
        bot.edit_message_text(
            help_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            help_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

@bot.callback_query_handler(func=lambda call: call.data == "help_back")
def help_back_callback(call):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton(text="📄 О боте", callback_data="help_about"),
        types.InlineKeyboardButton(text="🆘 Помощь", callback_data="help_help"),
        types.InlineKeyboardButton(text="💰 Донат", callback_data="help_donate"),
        types.InlineKeyboardButton(text="🔗 Обратная связь", callback_data="help_feedback")
    )
    try:
        bot.edit_message_text(
            "ℹ️ Выберите раздел:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboard
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            "ℹ️ Выберите раздел:",
            reply_markup=keyboard
        )

@bot.message_handler(func=lambda m: m.chat.type in ["group", "supergroup"] and m.text)
def group_tiktok_instagram_handler(message):
    text = message.text or ""
    user_id = message.chat.id
    if "tiktok.com" in text:
        url = text.strip().split()[0]
        process_tiktok_instagram(bot, user_id, url, reply_to_message_id=message.message_id, is_tiktok=True, user_info=message)
        return
    if "instagram.com" in text:
        url = text.strip().split()[0]
        process_tiktok_instagram(bot, user_id, url, reply_to_message_id=message.message_id, is_tiktok=False, user_info=message)
        return

@bot.message_handler(func=lambda m: m.chat.type == "private")
def handle_message(message):
    user_id = message.chat.id
    if message.text and message.text.startswith("/"):
        return  # Не реагировать на команды, если они не обработаны явно
    if user_id not in user_mode:
        bot.send_message(user_id, "⚠️ Сначала выбери платформу с помощью меню ниже.")
        return
    mode_data = user_mode[user_id]
    mode = mode_data["mode"] if isinstance(mode_data, dict) else mode_data
    url = message.text.strip()
    if mode == "tiktok":
        if "tiktok.com" not in url:
            bot.send_message(user_id, "⚠️ Отправь ссылку на видео из TikTok 🎵")
            return
        process_tiktok_instagram(bot, user_id, url, is_tiktok=True, log_func=log_download, user_info=message)
        return
    elif mode == "instagram":
        if "instagram.com" not in url:
            bot.send_message(user_id, "⚠️ Отправь ссылку на публикацию из Instagram 📸")
            return
        process_tiktok_instagram(bot, user_id, url, is_tiktok=False, log_func=log_download, user_info=message)
        return
    elif mode == "youtube":
        if "youtube.com" not in url and "youtu.be" not in url:
            bot.send_message(user_id, "⚠️ Отправь ссылку на видео с YouTube 📺")
            return
        status_msg = bot.send_message(user_id, "🔍 Получаю информацию о видео...")
        try:
            info = get_youtube_info_ydl(url)
            user_mode[user_id] = {"mode": "youtube", "url": url, "info": info}
            generate_video_card(info, user_id)
        except Exception as e:
            bot.send_message(user_id,  "❌ Не удалось получить информацию о видео.")
            print(Fore.RED + f"Ошибка YouTube: {e}")
        finally:
            try:
                bot.delete_message(user_id, status_msg.message_id)
            except Exception:
                pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("yt_"))
def handle_youtube_button(call):
    user_id = call.message.chat.id
    format_id = call.data.split("_", 1)[1]
    user_data = user_mode.get(user_id)
    if not user_data or not isinstance(user_data, dict) or "url" not in user_data:
        bot.send_message(user_id, "⚠️ Сначала отправь ссылку на видео YouTube.")
        return
    url = user_data["url"]
    try:
        bot.delete_message(user_id, call.message.message_id)
    except Exception:
        pass
    user_msg = bot.send_message(user_id, "⬇️ Скачивание: |░░░░░░░░░░| 0%")
    video_path = download_youtube_video(url, format_id, bot=bot, user_id=user_id, progress_message_id=user_msg.message_id)
    if not video_path:
        bot.send_message(user_id, "❌ Не удалось скачать видео. Попробуй другое качество.")
        return
    try:
        filesize_mb = round(os.path.getsize(video_path) / (1024 * 1024), 1)
        info = user_data.get("info", {})
        chosen_format = None
        for fmt in info.get("formats", []):
            if fmt.get("format_id") == format_id:
                chosen_format = fmt
                break
        res = chosen_format.get("resolution") if chosen_format else "?"

        size = f"{filesize_mb} MB"
        caption = f"📹 Качество: <b>{res}</b>\n💾 Размер: <b>{size}</b>\n🤖 Бот: @wndownloadbot"
        with open(video_path, "rb") as video:
            bot.send_video(user_id, video, timeout=120, caption=caption, parse_mode="HTML")
        print(Fore.GREEN + f"✅ Видео отправлено пользователю: {video_path}")
        bot.delete_message(user_id, user_msg.message_id)
        log_download(
            os.path.join("logs", "download_youtube_log.txt"),
            call.from_user.first_name or "-",
            call.from_user.username or "-",
            user_id,
            url
        )
    except Exception as e:
        bot.send_message(user_id, "❌ Ошибка при отправке видео.")
        print(Fore.RED + f"❌ Ошибка отправки: {e}")
    finally:
        if video_path and os.path.exists(video_path):
            os.remove(video_path)
            print(Fore.YELLOW + f"🧹 Временный видеофайл удалён: {video_path}")
            shutil.rmtree(os.path.dirname(video_path), ignore_errors=True)
            print(Fore.YELLOW + f"🧹 Временная папка удалена: {os.path.dirname(video_path)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("ytmp3_"))
def handle_youtube_mp3_button(call):
    user_id = call.message.chat.id
    format_id = call.data.split("_", 1)[1]
    user_data = user_mode.get(user_id)
    if not user_data or not isinstance(user_data, dict) or "url" not in user_data:
        bot.send_message(user_id, "⚠️ Сначала отправь ссылку на видео YouTube.")
        return
    url = user_data["url"]
    try:
        bot.delete_message(user_id, call.message.message_id)
    except Exception:
        pass
    user_msg = bot.send_message(user_id, "⬇️ Скачивание аудио: |░░░░░░░░░░| 0%")
    audio_path = None
    try:
        temp_dir = tempfile.mkdtemp()
        outtmpl = os.path.join(temp_dir, '%(title)s.%(ext)s')
        def progress_hook(d):
            if bot and user_id and user_msg.message_id and d['status'] == 'downloading':
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
                downloaded_bytes = d.get('downloaded_bytes', 0)
                percent = int(downloaded_bytes / total_bytes * 100) if total_bytes else 0
                bar = '█' * (percent // 10) + '░' * (10 - percent // 10)
                text = f"⬇️ Скачивание аудио: |{bar}| {percent}%"
                try:
                    bot.edit_message_text(text, user_id, user_msg.message_id)
                except Exception:
                    pass
            if bot and user_id and user_msg.message_id and d['status'] == 'finished':
                try:
                    bot.edit_message_text('⬇️ Скачивание аудио: |██████████| 100%\nГотово!', user_id, user_msg.message_id)
                except Exception:
                    pass
        ydl_opts = {
            'format': format_id,
            'outtmpl': outtmpl,
            'quiet': True,
            'noplaylist': True,
            'progress_hooks': [progress_hook],
            'retries': 5,
            'fragment_retries': 10,
            'continuedl': True,
            'prefer_ffmpeg': True,
            'concurrent_fragment_downloads': 5,
            'http_chunk_size': 10485760,
            'noprogress': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'merge_output_format': 'mp3',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        }
        from yt_dlp import YoutubeDL
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        for filename in os.listdir(temp_dir):
            if filename.endswith('.mp3'):
                audio_path = os.path.join(temp_dir, filename)
                break
        if not audio_path:
            bot.send_message(user_id, "❌ Не удалось скачать аудио в mp3-формате.")
            return
        filesize_mb = round(os.path.getsize(audio_path) / (1024 * 1024), 1)
        caption = f"🎵 MP3\n💾 Размер: <b>{filesize_mb} MB</b>\n🤖 Бот: @wndownloadbot"
        with open(audio_path, "rb") as audio:
            bot.send_audio(user_id, audio, timeout=120, caption=caption, parse_mode="HTML")
        print(Fore.GREEN + f"✅ Аудио отправлено пользователю: {audio_path}")
        bot.delete_message(user_id, user_msg.message_id)
        log_download(
            os.path.join("logs", "download_youtube_log.txt"),
            call.from_user.first_name or "-",
            call.from_user.username or "-",
            user_id,
            url
        )
    except Exception as e:
        bot.send_message(user_id, "❌ Ошибка при отправке аудио.")
        print(Fore.RED + f"❌ Ошибка отправки аудио: {e}")
    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
            print(Fore.YELLOW + f"🧹 Временный аудиофайл удалён: {audio_path}")
            shutil.rmtree(os.path.dirname(audio_path), ignore_errors=True)
            print(Fore.YELLOW + f"🧹 Временная папка удалена: {os.path.dirname(audio_path)}")

def extract_mp3_from_video(video_path, mp3_path):
    ffmpeg_path = os.path.abspath(os.path.join("lib", "ffmpeg-2025-06-16-git-e6fb8f373e-essentials_build", "bin", "ffmpeg.exe"))
    ffmpeg_args = [
        ffmpeg_path, '-y', '-i', video_path, '-vn', '-acodec', 'libmp3lame',
        '-ar', '44100', '-ac', '2', '-ab', '192k', '-f', 'mp3', mp3_path
    ]
    subprocess.run(ffmpeg_args, capture_output=True)
    return os.path.exists(mp3_path)

def cleanup_temp_files(video_path, mp3_path=None):
    if video_path and os.path.exists(video_path):
        os.remove(video_path)
    if mp3_path and os.path.exists(mp3_path):
        os.remove(mp3_path)
    temp_dir = os.path.dirname(video_path)
    shutil.rmtree(temp_dir, ignore_errors=True)

def process_tiktok_instagram(bot, user_id, url, reply_to_message_id=None, is_tiktok=True, log_func=None, user_info=None):
    import time
    status_msg = None
    temp_dir = tempfile.mkdtemp()
    video_path = os.path.join(temp_dir, "video.mp4")
    mp3_path = os.path.join(temp_dir, "audio.mp3")
    try:
        if is_tiktok:
            if bot:
                status_msg = bot.send_message(user_id, "⏳ Скачиваю видео TikTok...") if not reply_to_message_id else (bot.reply_to(user_info, "⏳ Скачиваю видео TikTok...") if user_info else bot.send_message(user_id, "⏳ Скачиваю видео TikTok..."))
            video_url = download_tiktok_video(url)
        else:
            if bot:
                status_msg = bot.send_message(user_id, "⏳ Скачиваю видео Instagram...") if not reply_to_message_id else (bot.reply_to(user_info, "⏳ Скачиваю видео Instagram...") if user_info else bot.send_message(user_id, "⏳ Скачиваю видео Instagram..."))
            video_url = url
        if not video_url:
            if bot:
                msg = "❌ Не удалось получить видео. Возможно оно удалено или приватное." if is_tiktok else "❌ Не удалось получить видео. Возможно оно удалено, приватное или не поддерживается."
                if not reply_to_message_id:
                    bot.send_message(user_id, msg)
                else:
                    if user_info:
                        bot.reply_to(user_info, msg)
                    else:
                        bot.send_message(user_id, msg)
            return
        if is_tiktok:
            response = requests.get(video_url, stream=True, timeout=15)
            with open(video_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=10 * 1024 * 1024):
                    f.write(chunk)
        else:
            video_path = download_instagram_video_ydl(url)
            if not video_path:
                if bot:
                    msg = "❌ Не удалось получить видео. Возможно оно удалено, приватное или не поддерживается."
                    if not reply_to_message_id:
                        bot.send_message(user_id, msg)
                    else:
                        if user_info:
                            bot.reply_to(user_info, msg)
                        else:
                            bot.send_message(user_id, msg)
                return
        with open(video_path, "rb") as video_bytes:
            if not reply_to_message_id:
                bot.send_video(user_id, video_bytes, timeout=60, caption="🤖 Бот: @wndownloadbot")
            else:
                bot.send_video(user_id, video_bytes, timeout=60, caption="🤖 Бот: @wndownloadbot", reply_to_message_id=reply_to_message_id)
        if log_func and user_info:
            log_func(
                os.path.join("logs", "download_tiktok_log.txt") if is_tiktok else os.path.join("logs", "download_insta_log.txt"),
                user_info.from_user.first_name or "-",
                user_info.from_user.username or "-",
                user_id,
                url
            )
        # Извлечение mp3
        if extract_mp3_from_video(video_path, mp3_path):
            with open(mp3_path, "rb") as audio_bytes:
                if not reply_to_message_id:
                    bot.send_audio(user_id, audio_bytes, timeout=60, caption="🎵 MP3 из TikTok-видео" if is_tiktok else "🎵 MP3 из Instagram-видео")
                else:
                    bot.send_audio(user_id, audio_bytes, timeout=60, caption="🎵 MP3 из TikTok-видео" if is_tiktok else "🎵 MP3 из Instagram-видео", reply_to_message_id=reply_to_message_id)
            if log_func and user_info and is_tiktok:
                log_func(
                    os.path.join("logs", "download_tiktok_log.txt"),
                    user_info.from_user.first_name or "-",
                    user_info.from_user.username or "-",
                    user_id,
                    url
                )
        else:
            if bot:
                msg = "❌ Не удалось извлечь аудио из видео (TikTok). Проверьте ffmpeg." if is_tiktok else "❌ Не удалось извлечь аудио из видео (Instagram). Проверьте ffmpeg."
                if not reply_to_message_id:
                    bot.send_message(user_id, msg)
                else:
                    if user_info:
                        bot.reply_to(user_info, msg)
                    else:
                        bot.send_message(user_id, msg)
        if status_msg:
            try:
                if not reply_to_message_id:
                    bot.delete_message(user_id, status_msg.message_id)
                else:
                    bot.delete_message(user_id, status_msg.message_id)
            except Exception:
                pass
    except Exception as e:
        if bot:
            msg = "❌ Ошибка при отправке видео или аудио." if is_tiktok else "❌ Ошибка при отправке видео."
            if not reply_to_message_id:
                bot.send_message(user_id, msg)
            else:
                if user_info:
                    bot.reply_to(user_info, msg)
                else:
                    bot.send_message(user_id, msg)
    finally:
        cleanup_temp_files(video_path, mp3_path)

@bot.callback_query_handler(func=lambda call: call.data == "help_donate")
def help_donate_callback(call):
    donate_caption = "💵Хотите сказать спасибо? Поддержите по QR-коду!"
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="help_back"))

    import os
    img_path = os.path.join(os.path.dirname(__file__), "visual", "binance_donate.png")
    if os.path.exists(img_path):
        with open(img_path, "rb") as photo:
            try:
                bot.edit_message_media(
                    media=types.InputMediaPhoto(photo, caption=donate_caption, parse_mode="HTML"),
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=keyboard
                )
            except Exception:
                bot.send_photo(
                    call.message.chat.id,
                    photo,
                    caption=donate_caption,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
    else:
        bot.edit_message_text(
            "❌ Картинка для доната не найдена!",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboard
        )

@bot.callback_query_handler(func=lambda call: call.data == "help_feedback")
def help_feedback_callback(call):
    feedback_text = (
        "<b>🔗 Обратная связь</b>\n\n"
        "✈️ Telegram — <a href=\"https://t.me/zxcd17b1073\">@zxcd17b1073</a>\n"
        "🛩 Spare telegram — <a href=\"https://t.me/stuppidnigger\">@stuppidnigger</a>\n"
        "📷 Instagram — <a href=\"https://www.instagram.com/we4n3d1066?igsh=aWxhaXhteHRjNXNo\">we4n3d1066</a>\n"
        "👾 Discord — <a href=\"https://discord.com/users/916274823477485619\">we4n3d1066</a>"
    )
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="help_back"))
    try:
        bot.edit_message_text(
            feedback_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            feedback_text,
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

@bot.message_handler(content_types=['text'])
def group_tiktok_instagram_handler(message):
    # Только для групповых чатов
    if message.chat.type not in ["group", "supergroup"]:
        return
    text = message.text or ""
    user_id = message.chat.id
    # TikTok
    if "tiktok.com" in text:
        url = text.strip().split()[0]
        status_msg = bot.reply_to(message, "⏳ Скачиваю видео TikTok...")
        video_url = download_tiktok_video(url)
        if not video_url:
            bot.reply_to(message, "❌ Не удалось получить видео. Возможно оно удалено или приватное.")
            return
        temp_dir = tempfile.mkdtemp()
        video_path = os.path.join(temp_dir, "video.mp4")
        mp3_path = os.path.join(temp_dir, "audio.mp3")
        try:
            response = requests.get(video_url, stream=True, timeout=15)
            with open(video_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=10 * 1024 * 1024):
                    f.write(chunk)
            with open(video_path, "rb") as video_bytes:
                bot.send_video(user_id, video_bytes, timeout=60, caption="🤖 Бот: @wndownloadbot", reply_to_message_id=message.message_id)
            # Извлечение mp3 через ffmpeg
            ffmpeg_path = os.path.abspath(os.path.join("lib", "ffmpeg-2025-06-16-git-e6fb8f373e-essentials_build", "bin", "ffmpeg.exe"))
            ffmpeg_args = [
                ffmpeg_path, '-y', '-i', video_path, '-vn', '-acodec', 'libmp3lame',
                '-ar', '44100', '-ac', '2', '-ab', '192k', '-f', 'mp3', mp3_path
            ]
            subprocess.run(ffmpeg_args, capture_output=True)
            if os.path.exists(mp3_path):
                with open(mp3_path, "rb") as audio_bytes:
                    bot.send_audio(user_id, audio_bytes, timeout=60, caption="🎵 MP3 из TikTok-видео", reply_to_message_id=message.message_id)
            try:
                bot.delete_message(user_id, status_msg.message_id)
            except Exception:
                pass
        except Exception as e:
            bot.reply_to(message, "❌ Ошибка при отправке видео или аудио.")
        finally:
            if os.path.exists(video_path):
                os.remove(video_path)
            if os.path.exists(mp3_path):
                os.remove(mp3_path)
            shutil.rmtree(temp_dir, ignore_errors=True)
        return
    # Instagram
    if "instagram.com" in text:
        url = text.strip().split()[0]
        status_msg = bot.reply_to(message, "⏳ Скачиваю видео Instagram...")
        video_path = download_instagram_video_ydl(url)
        if not video_path:
            bot.reply_to(message, "❌ Не удалось получить видео. Возможно оно удалено, приватное или не поддерживается.")
            return
        try:
            with open(video_path, "rb") as video:
                bot.send_video(user_id, video, timeout=60, caption="🤖 Бот: @wndownloadbot", reply_to_message_id=message.message_id)
            # Извлечение mp3 через ffmpeg
            ffmpeg_path = os.path.abspath(os.path.join("lib", "ffmpeg-2025-06-16-git-e6fb8f373e-essentials_build", "bin", "ffmpeg.exe"))
            mp3_path = video_path + ".mp3"
            ffmpeg_args = [
                ffmpeg_path, '-y', '-i', video_path, '-vn', '-acodec', 'libmp3lame',
                '-ar', '44100', '-ac', '2', '-ab', '192k', '-f', 'mp3', mp3_path
            ]
            subprocess.run(ffmpeg_args, capture_output=True)
            if os.path.exists(mp3_path):
                with open(mp3_path, "rb") as audio_bytes:
                    bot.send_audio(user_id, audio_bytes, timeout=60, caption="🎵 MP3 из Instagram-видео", reply_to_message_id=message.message_id)
                os.remove(mp3_path)
            try:
                bot.delete_message(user_id, status_msg.message_id)
            except Exception:
                pass
        except Exception as e:
            bot.reply_to(message, "❌ Ошибка при отправке видео.")
        finally:
            if video_path and os.path.exists(video_path):
                os.remove(video_path)
                shutil.rmtree(os.path.dirname(video_path), ignore_errors=True)
        return

if __name__ == "__main__":
    try:
        print(Fore.GREEN + "✅ Бот запущен и ждёт сообщений... 🧐")
        bot.polling(none_stop=True, timeout=90, long_polling_timeout=60)
    except KeyboardInterrupt:
        print(Fore.RED + "\n⛔ Бот остановлен вручную (Ctrl + C)")
    finally:
        print(Fore.YELLOW + "👋 Бот завершил работу. До встречи!" + Style.RESET_ALL)
        import time
        time.sleep(0.2)
        import logging
        logging.getLogger('telebot').setLevel(logging.CRITICAL)