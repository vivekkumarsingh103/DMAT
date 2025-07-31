import os
import re
import logging
from typing import Dict, List, Union, Optional
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    Message, 
    CallbackQuery,
    InputMediaPhoto
)
from pymongo import MongoClient
from pymongo.collection import Collection
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Environment variables
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MONGO_URI = os.getenv("MONGO_URI", "")
DATABASE_NAME = os.getenv("DATABASE_NAME", "AutoFilterBot")
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", 0))
REQ_CHANNEL = int(os.getenv("REQ_CHANNEL", 0))
PICS = os.getenv("PICS", "").split()
FILE_STORE_CHANNEL = [int(ch) for ch in os.getenv("FILE_STORE_CHANNEL", "").split()] if os.getenv("FILE_STORE_CHANNEL") else []
LAZY_MODE = os.getenv("LAZY_MODE", "False").lower() == "true"
ADMINS = [int(admin) for admin in os.getenv("ADMINS", "").split()] if os.getenv("ADMINS") else []
LAZY_RENAMERS = [int(user) for user in os.getenv("LAZY_RENAMERS", "").split()] if os.getenv("LAZY_RENAMERS") else []
URL_MODE = os.getenv("URL_MODE", "False").lower() == "true"
URL_SHORTNER_WEBSITE = os.getenv("URL_SHORTNER_WEBSITE", "")
URL_SHORTNER_WEBSITE_API = os.getenv("URL_SHORTNER_WEBSITE_API", "")
LZURL_PRIME_USERS = [int(user) for user in os.getenv("LZURL_PRIME_USERS", "").split()] if os.getenv("LZURL_PRIME_USERS") else []
LAZY_GROUPS = [int(group) for group in os.getenv("LAZY_GROUPS", "").split()] if os.getenv("LAZY_GROUPS") else []
MY_USERS = [int(user) for user in os.getenv("MY_USERS", "").split()] if os.getenv("MY_USERS") else []
FQDN = os.getenv("FQDN", "")
PRIME_DOWNLOADERS = [int(user) for user in os.getenv("PRIME_DOWNLOADERS", "").split()] if os.getenv("PRIME_DOWNLOADERS") else []

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Connect to MongoDB
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DATABASE_NAME]
col_files = db["files"]          # Collection for indexed files
col_filters = db["filters"]      # Collection for manual filters
col_users = db["users"]          # Collection for user data
col_thumb = db["thumbnails"]     # Collection for thumbnails
col_settings = db["settings"]    # Collection for bot settings

# Initialize the bot
app = Client("autofilter_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Helper functions
async def save_file(chat_id: int, file_id: str, file_name: str, file_type: str, caption: str = ""):
    """Save file to database with quality extraction"""
    # Extract quality from filename
    quality = "Unknown"
    for q in ["480p", "540p", "720p", "1080p", "2160p"]:
        if q in file_name:
            quality = q
            break
    
    # Save to database
    col_files.insert_one({
        "chat_id": chat_id,
        "file_id": file_id,
        "file_name": file_name,
        "file_type": file_type,
        "quality": quality,
        "caption": caption,
        "timestamp": datetime.now()
    })

async def search_files(query: str, max_results: int = 50) -> list:
    """Search files by query"""
    regex_query = {"$regex": query, "$options": "i"}
    return list(col_files.find({"file_name": regex_query}).limit(max_results))

async def add_filter(chat_id: int, keyword: str, file_id: str, caption: str = ""):
    """Add manual filter"""
    col_filters.update_one(
        {"chat_id": chat_id, "keyword": keyword.lower()},
        {"$set": {"file_id": file_id, "caption": caption}},
        upsert=True
    )

async def get_filter(chat_id: int, keyword: str) -> Optional[dict]:
    """Get manual filter"""
    return col_filters.find_one({"chat_id": chat_id, "keyword": keyword.lower()})

async def get_all_filters(chat_id: int) -> list:
    """Get all manual filters for a chat"""
    return list(col_filters.find({"chat_id": chat_id}))

async def delete_filter(chat_id: int, keyword: str) -> bool:
    """Delete manual filter"""
    result = col_filters.delete_one({"chat_id": chat_id, "keyword": keyword.lower()})
    return result.deleted_count > 0

async def delete_all_filters(chat_id: int) -> int:
    """Delete all manual filters for a chat"""
    result = col_filters.delete_many({"chat_id": chat_id})
    return result.deleted_count

async def save_thumbnail(user_id: int, thumb_id: str, is_lazy: bool = False):
    """Save thumbnail for renaming feature"""
    col_thumb.update_one(
        {"user_id": user_id, "is_lazy": is_lazy},
        {"$set": {"thumb_id": thumb_id}},
        upsert=True
    )

async def get_thumbnail(user_id: int, is_lazy: bool = False) -> Optional[str]:
    """Get thumbnail for renaming feature"""
    doc = col_thumb.find_one({"user_id": user_id, "is_lazy": is_lazy})
    return doc.get("thumb_id") if doc else None

async def delete_thumbnail(user_id: int, is_lazy: bool = False) -> bool:
    """Delete thumbnail"""
    result = col_thumb.delete_one({"user_id": user_id, "is_lazy": is_lazy})
    return result.deleted_count > 0

async def save_caption(user_id: int, caption: str):
    """Save custom caption"""
    col_settings.update_one(
        {"user_id": user_id},
        {"$set": {"caption": caption}},
        upsert=True
    )

async def get_caption(user_id: int) -> Optional[str]:
    """Get custom caption"""
    doc = col_settings.find_one({"user_id": user_id})
    return doc.get("caption") if doc else None

async def delete_caption(user_id: int) -> bool:
    """Delete custom caption"""
    result = col_settings.delete_one({"user_id": user_id})
    return result.deleted_count > 0

async def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMINS

async def is_lazy_renamer(user_id: int) -> bool:
    """Check if user is lazy renamer"""
    return user_id in LAZY_RENAMERS

async def is_my_user(user_id: int) -> bool:
    """Check if user is allowed"""
    return user_id in MY_USERS

async def log_message(text: str):
    """Log message to log channel"""
    if LOG_CHANNEL:
        await app.send_message(LOG_CHANNEL, text)

async def log_error(error: str):
    """Log error to log channel"""
    if LOG_CHANNEL:
        await app.send_message(LOG_CHANNEL, f"🚨 **ERROR**:\n```{error}```")

# Bot commands and handlers
@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """Handler for /start command"""
    user_id = message.from_user.id
    username = message.from_user.username or ""
    
    # Add user to database
    col_users.update_one(
        {"user_id": user_id},
        {"$set": {"username": username, "first_seen": datetime.now()}},
        upsert=True
    )
    
    # Send welcome message with images if available
    if PICS:
        media = [InputMediaPhoto(pic) for pic in PICS]
        await client.send_media_group(message.chat.id, media)
    
    text = (
        "👋 **Welcome to AutoFilter Bot!**\n\n"
        "I can automatically filter and send files when you search for them.\n"
        "Use /help to see available commands."
    )
    await message.reply_text(text)

@app.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    """Handler for /help command"""
    help_text = (
        "📚 **Available Commands:**\n\n"
        "• /logs - Get recent errors\n"
        "• /stats - Get database status\n"
        "• /filter - Add manual filter\n"
        "• /filters - View filters\n"
        "• /connect - Connect to PM\n"
        "• /disconnect - Disconnect from PM\n"
        "• /del - Delete a filter\n"
        "• /delall - Delete all filters\n"
        "• /deleteall - Delete all indexed files\n"
        "• /delete - Delete specific file\n"
        "• /info - Get user info\n"
        "• /id - Get Telegram IDs\n"
        "• /imdb - Fetch info from IMDb\n"
        "• /users - List bot users\n"
        "• /chats - List connected chats\n"
        "• /index - Add files from channel\n"
        "• /leave - Leave a chat\n"
        "• /disable - Disable a chat\n"
        "• /enable - Re-enable chat\n"
        "• /ban - Ban a user\n"
        "• /unban - Unban a user\n"
        "• /channel - List connected channels\n"
        "• /broadcast - Broadcast message\n"
        "• /batch - Create link for multiple posts\n"
        "• /link - Create link for one post\n"
        "• /set_caption - Set custom caption\n"
        "• /del_caption - Delete custom caption\n"
        "• /set_thumb - Set custom thumbnail\n"
        "• /view_thumb - View custom thumbnail\n"
        "• /del_thumb - Delete custom thumbnail\n"
        "• /set_lazy_thumb - Set lazy thumbnail\n"
        "• /view_lazy_thumb - View lazy thumbnail\n"
        "• /del_lazy_thumb - Delete lazy thumbnail"
    )
    await message.reply_text(help_text)

@app.on_message(filters.command("filter"))
async def add_filter_command(client: Client, message: Message):
    """Add manual filter"""
    if not message.reply_to_message or not message.reply_to_message.media:
        await message.reply_text("Reply to a media file with /filter <keyword>")
        return
    
    if len(message.command) < 2:
        await message.reply_text("Please provide a keyword. Usage: /filter <keyword>")
        return
    
    keyword = message.command[1]
    file_id = None
    caption = ""
    
    # Get file ID based on media type
    if message.reply_to_message.video:
        file_id = message.reply_to_message.video.file_id
        caption = message.reply_to_message.caption or ""
    elif message.reply_to_message.document:
        file_id = message.reply_to_message.document.file_id
        caption = message.reply_to_message.caption or ""
    elif message.reply_to_message.audio:
        file_id = message.reply_to_message.audio.file_id
        caption = message.reply_to_message.caption or ""
    else:
        await message.reply_text("Unsupported media type")
        return
    
    await add_filter(message.chat.id, keyword, file_id, caption)
    await message.reply_text(f"✅ Filter added for keyword: `{keyword}`")

@app.on_message(filters.command("filters"))
async def list_filters_command(client: Client, message: Message):
    """List all manual filters"""
    filters = await get_all_filters(message.chat.id)
    if not filters:
        await message.reply_text("No filters in this chat")
        return
    
    text = "📝 **Filters in this chat:**\n\n"
    for idx, fltr in enumerate(filters, 1):
        text += f"{idx}. `{fltr['keyword']}`\n"
    
    await message.reply_text(text)

@app.on_message(filters.command("del"))
async def delete_filter_command(client: Client, message: Message):
    """Delete a manual filter"""
    if len(message.command) < 2:
        await message.reply_text("Please provide a keyword. Usage: /del <keyword>")
        return
    
    keyword = message.command[1]
    deleted = await delete_filter(message.chat.id, keyword)
    
    if deleted:
        await message.reply_text(f"✅ Filter `{keyword}` deleted")
    else:
        await message.reply_text(f"❌ Filter `{keyword}` not found")

@app.on_message(filters.command("delall"))
async def delete_all_filters_command(client: Client, message: Message):
    """Delete all manual filters"""
    count = await delete_all_filters(message.chat.id)
    await message.reply_text(f"✅ Deleted {count} filters")

@app.on_message(filters.command("stats"))
async def stats_command(client: Client, message: Message):
    """Get bot statistics"""
    file_count = col_files.count_documents({})
    filter_count = col_filters.count_documents({})
    user_count = col_users.count_documents({})
    
    stats_text = (
        "📊 **Bot Statistics:**\n\n"
        f"• Total files: `{file_count}`\n"
        f"• Total filters: `{filter_count}`\n"
        f"• Total users: `{user_count}`"
    )
    await message.reply_text(stats_text)

@app.on_message(filters.command("logs") & filters.user(ADMINS))
async def logs_command(client: Client, message: Message):
    """Get recent logs (admin only)"""
    # In a real implementation, you would read from a log file
    await message.reply_text("📜 **Recent logs:**\n\nLogs would appear here")

@app.on_message(filters.command("broadcast") & filters.user(ADMINS))
async def broadcast_command(client: Client, message: Message):
    """Broadcast message to all users (admin only)"""
    if not message.reply_to_message:
        await message.reply_text("Reply to a message to broadcast it")
        return
    
    users = col_users.find()
    success = 0
    failed = 0
    
    for user in users:
        try:
            await message.reply_to_message.copy(user["user_id"])
            success += 1
        except Exception as e:
            failed += 1
            await log_error(f"Broadcast failed for {user['user_id']}: {str(e)}")
    
    await message.reply_text(
        f"📣 Broadcast completed!\n\n"
        f"• Success: `{success}`\n"
        f"• Failed: `{failed}`"
    )

@app.on_message(filters.command("index") & filters.user(ADMINS))
async def index_command(client: Client, message: Message):
    """Index files from a channel (admin only)"""
    # Implementation would include iterating through channel messages
    await message.reply_text("🔍 Indexing started... This might take a while")

@app.on_message(filters.command("imdb"))
async def imdb_command(client: Client, message: Message):
    """Fetch IMDb information"""
    if len(message.command) < 2:
        await message.reply_text("Please provide a title. Usage: /imdb <title>")
        return
    
    title = " ".join(message.command[1:])
    # In a real implementation, you would call IMDb API here
    await message.reply_text(f"🎬 IMDb info for `{title}` would appear here")

@app.on_message(filters.command("set_thumb"))
async def set_thumb_command(client: Client, message: Message):
    """Set custom thumbnail"""
    if not message.reply_to_message or not message.reply_to_message.photo:
        await message.reply_text("Reply to a photo to set it as thumbnail")
        return
    
    user_id = message.from_user.id
    thumb_id = message.reply_to_message.photo.file_id
    await save_thumbnail(user_id, thumb_id)
    await message.reply_text("✅ Custom thumbnail saved!")

@app.on_message(filters.command("view_thumb"))
async def view_thumb_command(client: Client, message: Message):
    """View custom thumbnail"""
    user_id = message.from_user.id
    thumb_id = await get_thumbnail(user_id)
    
    if thumb_id:
        await client.send_photo(message.chat.id, thumb_id, caption="Your custom thumbnail")
    else:
        await message.reply_text("❌ No thumbnail set. Use /set_thumb to set one")

# Auto-filter functionality
@app.on_message(
    filters.group & 
    filters.text & 
    filters.create(lambda _, __, m: not m.command)
)
async def auto_filter(client: Client, message: Message):
    """Handle auto-filter requests"""
    query = message.text.strip()
    # Rest of your function...    
    # 1. First check manual filters
    manual_filter = await get_filter(message.chat.id, query)
    if manual_filter:
        await client.send_cached_media(
            chat_id=message.chat.id,
            file_id=manual_filter["file_id"],
            caption=manual_filter.get("caption", "")
        )
        return
    
    # 2. Then search indexed files
    results = await search_files(query)
    if not results:
        # Stay silent if no results
        return
    
    # Create buttons for different qualities
    buttons = []
    qualities = {}
    
    # Group files by quality
    for file in results:
        quality = file.get("quality", "Unknown")
        if quality not in qualities:
            qualities[quality] = []
        qualities[quality].append(file)
    
    # Create quality buttons row
    quality_row = []
    for quality in sorted(qualities.keys()):
        quality_row.append(InlineKeyboardButton(quality, callback_data=f"quality:{quality}:{query}"))
    if quality_row:
        buttons.append(quality_row)
    
    # Add "All" button
    buttons.append([InlineKeyboardButton("All", callback_data=f"all:{query}")])
    
    # Add pagination buttons
    buttons.append([
        InlineKeyboardButton("« Back", callback_data="page:back"),
        InlineKeyboardButton("1/5", callback_data="page:current"),
        InlineKeyboardButton("Next »", callback_data="page:next")
    ])
    
    # Send the search results
    await message.reply_text(
        f"🔍 Found {len(results)} results for '{query}'",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# Callback query handlers
@app.on_callback_query(filters.regex(r"^quality:"))
async def quality_callback(client: Client, callback_query: CallbackQuery):
    """Handle quality selection"""
    data = callback_query.data.split(":")
    quality = data[1]
    query = data[2]
    
    results = await search_files(query)
    quality_files = [file for file in results if file.get("quality") == quality]
    
    if not quality_files:
        await callback_query.answer("No files found for this quality", show_alert=True)
        return
    
    # For simplicity, send the first file in this quality
    file = quality_files[0]
    await client.send_cached_media(
        chat_id=callback_query.message.chat.id,
        file_id=file["file_id"],
        caption=file.get("caption", "")
    )
    await callback_query.answer()

@app.on_callback_query(filters.regex(r"^all:"))
async def all_callback(client: Client, callback_query: CallbackQuery):
    """Handle 'All' selection"""
    query = callback_query.data.split(":")[1]
    results = await search_files(query)
    
    if not results:
        await callback_query.answer("No files found", show_alert=True)
        return
    
    # Send all files (in a real implementation, you might send a list or batch)
    for file in results[:5]:  # Limit to 5 files to avoid flooding
        await client.send_cached_media(
            chat_id=callback_query.message.chat.id,
            file_id=file["file_id"],
            caption=file.get("caption", "")
        )
    
    await callback_query.answer()

@app.on_callback_query(filters.regex(r"^page:"))
async def page_callback(client: Client, callback_query: CallbackQuery):
    """Handle pagination"""
    action = callback_query.data.split(":")[1]
    # In a full implementation, you would track pagination state
    await callback_query.answer(f"Page {action} clicked")

# Index files when added to a connected channel
@app.on_message(filters.channel & (filters.document | filters.video | filters.audio))
async def index_new_file(client: Client, message: Message):
    """Automatically index new files in channels"""
    if message.chat.id not in FILE_STORE_CHANNEL:
        return
    
    file_name = ""
    file_id = ""
    file_type = ""
    
    if message.document:
        file_name = message.document.file_name or ""
        file_id = message.document.file_id
        file_type = "document"
    elif message.video:
        file_name = message.video.file_name or ""
        file_id = message.video.file_id
        file_type = "video"
    elif message.audio:
        file_name = message.audio.file_name or ""
        file_id = message.audio.file_id
        file_type = "audio"
    
    if file_id:
        await save_file(message.chat.id, file_id, file_name, file_type, message.caption or "")
        await log_message(f"📥 New file indexed in {message.chat.title}:\n`{file_name}`")

# Start the bot
if __name__ == "__main__":
    print("Starting AutoFilter Bot...")
    app.run()
