import os
import subprocess
import shutil
from pyrogram import Client, filters
import zipfile
import glob
import ffmpeg  # Add this import

# Configure your Telegram bot
api_id = id
api_hash = "hash"
bot_token = "token"

def get_video_info(file_path):
    """
    Extract video metadata using ffmpeg probe
    
    Args:
        file_path (str): Path to the video file
    
    Returns:
        tuple: Duration, width, height of the video (or None if not found)
    """
    try:
        probe = ffmpeg.probe(file_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        if video_stream:
            duration = float(probe['format']['duration'])
            width = int(video_stream['width'])
            height = int(video_stream['height'])
            return duration, width, height
    except Exception as e:
        print(f"Error probing video: {e}")
    return None, None, None

def extract_thumbnail(video_path, thumbnail_path):
    """
    Extract a thumbnail from a video file
    
    Args:
        video_path (str): Path to the source video
        thumbnail_path (str): Path to save the thumbnail
    """
    try:
        (
            ffmpeg
            .input(video_path, ss="00:00:01")
            .filter('scale', 320, -1)
            .output(thumbnail_path, vframes=1)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
    except Exception as e:
        print(f"Thumbnail extraction error: {e}")

def convert_media_file(input_file):
    """
    Convert media files by renaming them
    
    Args:
        input_file (str): Path to the input file
    
    Returns:
        str: Path to the converted/renamed file
    """
    # List of extensions to convert
    extensions_to_convert = {
        '.mov': '.mp4',
        '.m4v': '.mp4',
    }
    
    # Get file extension
    file_ext = os.path.splitext(input_file)[1].lower()
    
    # Check if the file needs conversion
    if file_ext in extensions_to_convert:
        # Create new file path with new extension
        output_file = os.path.splitext(input_file)[0] + extensions_to_convert[file_ext]
        
        try:
            # Rename the file
            os.rename(input_file, output_file)
            return output_file
        except Exception as e:
            print(f"File conversion error: {e}")
            return input_file
    
    return input_file

def check_requirements():
    """Check and install required dependencies"""
    # Check Ruby installation
    try:
        subprocess.run(['ruby', '--version'], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        subprocess.run(['sudo', 'apt', 'install', 'ruby'], check=True)
    
    # Check yadisk gem installation
    try:
        subprocess.run(['gem', 'list', 'yadisk'], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        subprocess.run(['sudo', 'gem', 'install', 'yadisk'], check=True)
    
    # Check wget installation
    try:
        subprocess.run(['wget', '--version'], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        subprocess.run(['sudo', 'apt', 'install', 'wget'], check=True)

# Run check_requirements before starting the bot
print("Checking system requirements...")
check_requirements()
print("System requirements check completed.")

# Initialize bot
app = Client("yandex_downloader_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

def setup_directories():
    """Create necessary directories if they don't exist"""
    for directory in ['downloads', 'extracts', 'thumbnails']:  # Added thumbnails directory
        if not os.path.exists(directory):
            os.makedirs(directory)

def download_from_yandisk(url):
    """Download file from Yandex Disk"""
    setup_directories()
    subprocess.run(['yadisk', url, './downloads'], check=True)
    
def get_downloaded_file():
    """Get the downloaded zip file from downloads directory"""
    zip_files = glob.glob('./downloads/*.zip')
    return zip_files[0] if zip_files else None

def extract_zip(zip_path):
    """Extract the zip file"""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall('./extracts')
    return './extracts'

def cleanup():
    """Remove downloaded and extracted files"""
    shutil.rmtree('./downloads', ignore_errors=True)
    shutil.rmtree('./extracts', ignore_errors=True)
    shutil.rmtree('./thumbnails', ignore_errors=True)  # Added thumbnails cleanup

@app.on_message(filters.command('start'))
async def start_command(client, message):
    await message.reply_text("Welcome! Send me a Yandex Disk link and I'll download and send you the files.")

@app.on_message(filters.text & filters.regex(r'https?://disk\.yandex\.[a-z]+/[^\s]+'))
async def process_yandex_link(client, message):
    try:
        # Send initial status
        status_message = await message.reply_text("Processing your request...")
        
        # Download file
        await status_message.edit_text("Downloading from Yandex Disk...")
        download_from_yandisk(message.text)
        
        # Get downloaded file
        zip_file = get_downloaded_file()
        if not zip_file:
            await status_message.edit_text("No zip file found in downloads!")
            return
        
        # Extract files
        await status_message.edit_text("Extracting files...")
        extract_path = extract_zip(zip_file)
        
        # Upload files to Telegram
        await status_message.edit_text("Uploading files to Telegram...")
        for filepath in glob.glob(f'{extract_path}/**/*', recursive=True):
            if os.path.isfile(filepath):
                try:
                    # Convert media file if needed
                    converted_file = convert_media_file(filepath)
                    
                    # Check if it's a video file
                    if converted_file.lower().endswith(('.mp4', '.mov', '.m4v')):
                        # Get video info
                        duration, width, height = get_video_info(converted_file)
                        
                        # Generate thumbnail
                        if duration:
                            thumbnail_path = os.path.join('thumbnails', f"{os.path.basename(converted_file)}.jpg")
                            extract_thumbnail(converted_file, thumbnail_path)
                            
                            # Send video with thumbnail
                            if os.path.exists(thumbnail_path):
                                await client.send_video(
                                    chat_id=message.chat.id,
                                    video=converted_file,
                                    thumb=thumbnail_path,
                                    duration=int(duration) if duration else None,
                                    width=width,
                                    height=height
                                )
                                continue
                    
                    # If not a video or thumbnail generation failed, send as document
                    await client.send_document(
                        chat_id=message.chat.id,
                        document=converted_file
                    )
                except Exception as e:
                    await message.reply_text(f"Error uploading {os.path.basename(filepath)}: {str(e)}")
        
        # Cleanup
        cleanup()
        await status_message.edit_text("All files have been processed and uploaded!")
        
    except Exception as e:
        await message.reply_text(f"An error occurred: {str(e)}")

# Run the bot
if __name__ == "__main__":
    print("Bot is starting...")
    app.run()
