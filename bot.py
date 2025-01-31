import os
import subprocess
import shutil
from pyrogram import Client, filters
import zipfile
import glob
import ffmpeg
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configure your Telegram bot
api_id = id
api_hash = "hash"
bot_token = "token"

# Configure directories
DOWNLOADS_DIR = 'downloads'
EXTRACTS_DIR = 'extracts'
THUMBNAILS_DIR = 'thumbnails'

class YandexDownloaderBot:
    def __init__(self):
        self.app = Client(
            "yandex_downloader_bot",
            api_id=api_id,
            api_hash=api_hash,
            bot_token=bot_token
        )
        self.setup_handlers()
        self.setup_directories()

    def setup_directories(self):
        """Create necessary directories if they don't exist"""
        for directory in [DOWNLOADS_DIR, EXTRACTS_DIR, THUMBNAILS_DIR]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info(f"Created directory: {directory}")

    def setup_handlers(self):
        """Setup message handlers"""
        @self.app.on_message(filters.command('start'))
        async def start_command(client, message):
            welcome_text = (
                "👋 Welcome to Yandex Disk Downloader Bot!\n\n"
                "Send me a Yandex Disk link and I'll:\n"
                "1. Download the file\n"
                "2. Process it (ZIP or MP4)\n"
                "3. Send it back to you on Telegram\n\n"
                "Just send me a Yandex Disk link to get started! 🚀"
            )
            await message.reply_text(welcome_text)

        @self.app.on_message(filters.text & filters.regex(r'https?://disk\.yandex\.[a-z]+/[^\s]+'))
        async def process_yandex_link(client, message):
            try:
                await self._handle_yandex_link(client, message)
            except Exception as e:
                logger.error(f"Error processing link: {str(e)}")
                await message.reply_text(f"❌ An error occurred: {str(e)}")

    async def _handle_yandex_link(self, client, message):
        """Handle incoming Yandex Disk links"""
        status_message = await message.reply_text("🔄 Processing your request...")
        
        try:
            # Download file
            await status_message.edit_text("⬇️ Downloading from Yandex Disk...")
            self.download_from_yandisk(message.text)
            
            # Get downloaded file
            downloaded_file, file_type = self.get_downloaded_file()
            if not downloaded_file:
                await status_message.edit_text("❌ No zip or mp4 files found in downloads!")
                return
            
            if file_type == 'zip':
                await self._process_zip_file(client, message, status_message, downloaded_file)
            elif file_type == 'mp4':
                await self._process_mp4_file(client, message, status_message, downloaded_file)
            
            # Cleanup
            self.cleanup()
            await status_message.edit_text("✅ All files have been processed and uploaded!")
            
        except Exception as e:
            logger.error(f"Error in _handle_yandex_link: {str(e)}")
            await status_message.edit_text(f"❌ An error occurred: {str(e)}")
            self.cleanup()

    def download_from_yandisk(self, url):
        """Download file from Yandex Disk"""
        try:
            subprocess.run(['yadisk', url, f'./{DOWNLOADS_DIR}'], check=True)
            logger.info(f"Successfully downloaded from Yandex Disk: {url}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error downloading from Yandex Disk: {str(e)}")
            raise Exception("Failed to download from Yandex Disk")

    def get_downloaded_file(self):
        """Get the downloaded zip or mp4 file from downloads directory"""
        # First check for zip files
        zip_files = glob.glob(f'./{DOWNLOADS_DIR}/*.zip')
        if zip_files:
            return zip_files[0], 'zip'
        
        # If no zip files found, check for mp4 files
        mp4_files = glob.glob(f'./{DOWNLOADS_DIR}/*.mp4')
        if mp4_files:
            return mp4_files[0], 'mp4'
        
        return None, None

    def extract_zip(self, zip_path):
        """Extract the zip file"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(f'./{EXTRACTS_DIR}')
            logger.info(f"Successfully extracted zip file: {zip_path}")
            return f'./{EXTRACTS_DIR}'
        except Exception as e:
            logger.error(f"Error extracting zip file: {str(e)}")
            raise

    def get_video_info(self, file_path):
        """Extract video metadata using ffmpeg probe"""
        try:
            probe = ffmpeg.probe(file_path)
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
            if video_stream:
                duration = float(probe['format']['duration'])
                width = int(video_stream['width'])
                height = int(video_stream['height'])
                return duration, width, height
        except Exception as e:
            logger.error(f"Error probing video: {str(e)}")
        return None, None, None

    def extract_thumbnail(self, video_path, thumbnail_path):
        """Extract a thumbnail from a video file"""
        try:
            (
                ffmpeg
                .input(video_path, ss="00:00:01")
                .filter('scale', 320, -1)
                .output(thumbnail_path, vframes=1)
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            logger.info(f"Successfully extracted thumbnail: {thumbnail_path}")
            return True
        except Exception as e:
            logger.error(f"Thumbnail extraction error: {str(e)}")
            return False

    def convert_media_file(self, input_file):
        """Convert media files by renaming them"""
        extensions_to_convert = {
            '.mov': '.mp4',
            '.m4v': '.mp4',
        }
        
        file_ext = os.path.splitext(input_file)[1].lower()
        
        if file_ext in extensions_to_convert:
            output_file = os.path.splitext(input_file)[0] + extensions_to_convert[file_ext]
            try:
                os.rename(input_file, output_file)
                logger.info(f"Successfully converted {input_file} to {output_file}")
                return output_file
            except Exception as e:
                logger.error(f"File conversion error: {str(e)}")
                return input_file
        
        return input_file

    async def _process_zip_file(self, client, message, status_message, zip_file):
        """Process downloaded zip file"""
        await status_message.edit_text("📂 Extracting files...")
        extract_path = self.extract_zip(zip_file)
        
        await status_message.edit_text("⬆️ Uploading files to Telegram...")
        for filepath in glob.glob(f'{extract_path}/**/*', recursive=True):
            if os.path.isfile(filepath):
                await self._process_single_file(client, message, filepath)

    async def _process_mp4_file(self, client, message, status_message, mp4_file):
        """Process downloaded MP4 file"""
        await status_message.edit_text("⬆️ Uploading MP4 file to Telegram...")
        await self._process_single_file(client, message, mp4_file)

    async def _process_single_file(self, client, message, filepath):
        """Process and upload a single file"""
        try:
            converted_file = self.convert_media_file(filepath)
            
            if converted_file.lower().endswith(('.mp4', '.mov', '.m4v')):
                duration, width, height = self.get_video_info(converted_file)
                
                thumbnail_path = os.path.join(THUMBNAILS_DIR, f"{os.path.basename(converted_file)}.jpg")
                if duration and self.extract_thumbnail(converted_file, thumbnail_path):
                    await client.send_video(
                        chat_id=message.chat.id,
                        video=converted_file,
                        thumb=thumbnail_path,
                        duration=int(duration) if duration else None,
                        width=width,
                        height=height
                    )
                else:
                    await client.send_video(
                        chat_id=message.chat.id,
                        video=converted_file,
                        duration=int(duration) if duration else None,
                        width=width,
                        height=height
                    )
            else:
                await client.send_document(
                    chat_id=message.chat.id,
                    document=converted_file
                )
            
            logger.info(f"Successfully uploaded file: {os.path.basename(converted_file)}")
        except Exception as e:
            logger.error(f"Error uploading {os.path.basename(filepath)}: {str(e)}")
            await message.reply_text(f"❌ Error uploading {os.path.basename(filepath)}: {str(e)}")

    def cleanup(self):
        """Remove downloaded and extracted files"""
        for directory in [DOWNLOADS_DIR, EXTRACTS_DIR, THUMBNAILS_DIR]:
            shutil.rmtree(f'./{directory}', ignore_errors=True)
            os.makedirs(f'./{directory}')
        logger.info("Cleanup completed")

    def run(self):
        """Run the bot"""
        logger.info("Bot is starting...")
        self.app.run()

if __name__ == "__main__":
    # Create and run the bot
    bot = YandexDownloaderBot()
    bot.run()
