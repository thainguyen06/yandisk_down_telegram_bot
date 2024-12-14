import os
import shutil
import subprocess
from pyrogram import Client, filters

# Khai báo các thư mục
download_dir = "./downloads"
extract_dir = "./extracted"
os.makedirs(download_dir, exist_ok=True)
os.makedirs(extract_dir, exist_ok=True)

# Cấu hình Pyrogram
api_id = "6897064"  # Thay bằng API ID của bạn từ https://my.telegram.org/apps
api_hash = "206c2035a8dc342ab70421ea4094ac49"  # Thay bằng API Hash của bạn
bot_token = "7702702432:AAFQeis-uvQN0OhnPbwwA1X_JqEAjmbwXGg"  # Thay bằng token bot từ BotFather

app = Client("yandex_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Hàm kiểm tra và cài đặt Ruby
def check_install_ruby():
    try:
        subprocess.run(["ruby", "-v"], check=True)
    except FileNotFoundError:
        subprocess.run(["sudo", "apt", "install", "-y", "ruby"])

# Hàm kiểm tra và cài đặt yadisk
def check_install_yadisk():
    try:
        subprocess.run(["gem", "list", "|", "grep", "yadisk"], shell=True, check=True)
    except subprocess.CalledProcessError:
        subprocess.run(["sudo", "gem", "install", "yadisk"])

# Hàm tải file từ Yandex
def download_from_yandex(url, download_dir):
    os.makedirs(download_dir, exist_ok=True)
    subprocess.run(["yadisk", url, download_dir], check=True)

# Hàm giải nén file
def extract_zip_file(file_path, extract_to):
    os.makedirs(extract_to, exist_ok=True)
    shutil.unpack_archive(file_path, extract_to)

# Xử lý tin nhắn chứa link
@app.on_message(filters.text & ~filters.command)
async def handle_message(client, message):
    user_message = message.text
    chat_id = message.chat.id

    # Kiểm tra và cài đặt ruby, yadisk
    check_install_ruby()
    check_install_yadisk()

    if "http" in user_message:
        try:
            # Tải file từ Yandex
            download_from_yandex(user_message, download_dir)

            # Kiểm tra file tải về
            downloaded_files = os.listdir(download_dir)
            for file_name in downloaded_files:
                file_path = os.path.join(download_dir, file_name)
                if file_name.endswith(".zip"):
                    # Giải nén
                    extract_zip_file(file_path, extract_dir)

                    # Quét thư mục và gửi file lên Telegram
                    for root, dirs, files in os.walk(extract_dir):
                        for extracted_file in files:
                            extracted_file_path = os.path.join(root, extracted_file)
                            await client.send_document(chat_id, extracted_file_path)

                    # Dọn dẹp thư mục
                    shutil.rmtree(download_dir)
                    shutil.rmtree(extract_dir)

                    await message.reply_text("Đã tải và upload file lên Telegram!")
                else:
                    await message.reply_text("Không tìm thấy file .zip trong Yandex link.")
        except Exception as e:
            await message.reply_text(f"Đã xảy ra lỗi: {e}")
    else:
        await message.reply_text("Vui lòng gửi link Yandex.")

# Khởi động bot
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("Chào bạn! Gửi cho mình link Yandex để xử lý.")

app.run()
