from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import requests

# Hàm khởi tạo bot
def start(update, context):
    update.message.reply_text('Chào mừng! Gửi link Yandex Disk để tải file.')

# Hàm tải file từ Yandex Disk
def download_file_from_yandex(link):
    response = requests.get(link)
    response.raise_for_status()
    return response.content

# Hàm xử lý tin nhắn chứa link Yandex Disk
def handle_message(update, context):
    url = update.message.text
    try:
        file_content = download_file_from_yandex(url)
        update.message.reply_document(file_content, filename="downloaded_file")
    except Exception as e:
        update.message.reply_text(f'Có lỗi xảy ra: {e}')

# Khởi tạo bot
def main():
    updater = Updater("TELEGRAM_BOT_API_TOKEN", use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
