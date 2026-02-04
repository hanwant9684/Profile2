import asyncio
import os
import time
import io
import re
import aiofiles
from pyrogram import filters, Client
import pyrogram
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from bot.config import app, API_ID, API_HASH
from bot.database import get_user, check_and_update_quota, get_setting
from bot.utils import progress_bar

async def is_public_chat(client: Client, chat_id: str):
    """Checks if a chat is a public channel or group."""
    try:
        chat = await client.get_chat(str(chat_id))
        # Public chats have a username
        is_public = getattr(chat, 'username', None) is not None
        # Check if it's a channel or group
        is_chat_type = str(chat.type) in ["ChatType.CHANNEL", "ChatType.SUPERGROUP", "ChatType.GROUP"]
        return is_public and is_chat_type
    except Exception:
        return False

async def parse_tg_link(link: str):
    """Extracts chat_id and message_id from a Telegram link."""
    # Matches: t.me/username/123 or t.me/c/123456789/123
    TG_LINK_RE = re.compile(r"t\.me/(?:c/)?([^/]+)/(\d+)")
    match = TG_LINK_RE.search(link)
    if not match:
        return None, None
    chat_id_raw, msg_id = match.groups()
    
    # Private channel IDs look like numbers in the URL (prefixed with 'c/')
    if chat_id_raw.isdigit():
        chat_id = int(f"-100{chat_id_raw}")
    else:
        chat_id = chat_id_raw
    return chat_id, int(msg_id)

@app.on_message(filters.private & filters.text & ~filters.command(["start", "help", "login", "logout", "myinfo"]))
async def handle_link(client: Client, message: Message):
    user_id = message.from_user.id
    link = message.text.strip()
    
    chat_id, msg_id = await parse_tg_link(link)
    if not chat_id:
        return # Not a valid TG link
        
    # Step 1: Check if it's public (channel or group)
    public = await is_public_chat(client, chat_id)
    
    # Logic update:
    # 1. If public channel: Link checking (direct extraction) is allowed.
    # 2. If public group: Use download/upload method (restricted logic).
    # 3. If private: Use download/upload method (restricted logic).
    
    is_public_channel_only = False
    if public:
        try:
            chat = await client.get_chat(str(chat_id))
            if str(chat.type) == "ChatType.CHANNEL":
                is_public_channel_only = True
        except:
            pass

    if is_public_channel_only:
        status_msg = await message.reply("⏳ **Processing public channel...**")
        try:
            # Direct Extraction via the bot client itself
            msg_response = await client.get_messages(chat_id, msg_id)
            if msg_response:
                # get_messages returns a list if multiple IDs or a single message
                msg = msg_response[0] if isinstance(msg_response, list) else msg_response
                if msg.media_group_id:
                    # It's part of a group, get all messages in that group
                    await status_msg.edit("📦 **Downloading media group...**")
                    messages = await client.get_media_group(chat_id, msg_id)
                    for m in messages:
                        if m.media:
                            await m.copy(message.chat.id, caption=m.caption)
                    await status_msg.edit("✅ **Download Complete!**")
                elif msg.media:
                    await status_msg.edit("📦 **Downloading...**")
                    await msg.copy(message.chat.id, caption=msg.caption)
                    await status_msg.edit("✅ **Download Complete!**")
                else:
                    await status_msg.edit("❌ This message does not contain media.")
            else:
                await status_msg.edit("❌ Message not found.")
            
            # Auto-delete status message after 10 seconds
            await asyncio.sleep(10)
            await status_msg.delete()
            return
            
        except Exception as e:
            await status_msg.edit(f"❌ Extraction failed: {str(e)}")
            await asyncio.sleep(10)
            await status_msg.delete()
            return
    
    # For public groups, private channels, private groups, or bots:
    # Use download and upload method (Restricted Content Logic)
    status_msg = await message.reply("⏳ **Processing via download/upload...**")
    try:
        from bot.transfer import fast_download_with_metadata, fast_upload
        
        # Check if user is logged in
        user_data = await get_user(user_id)
        # Fix: The database uses 'phone_session_string' but the code checks for 'session'
        session_string = user_data.get("phone_session_string") if user_data else None
        
        if not session_string:
            await status_msg.edit("❌ Please /login first to download this content.")
            return

        async with Client("user_session", session_string=session_string, api_id=int(API_ID) if str(API_ID).isdigit() else 0, api_hash=str(API_HASH)) as user_client:
            msg_response = await user_client.get_messages(chat_id, msg_id)
            if not msg_response:
                await status_msg.edit("❌ No media found.")
                return
            
            msg = msg_response[0] if isinstance(msg_response, list) else msg_response
            if not msg or not msg.media:
                await status_msg.edit("❌ No media found.")
                return
            
            await status_msg.edit("📥 **Downloading...**")
            start_time = time.time()
            file_path, video_metadata = await fast_download_with_metadata(
                user_client, 
                msg,
                progress=progress_bar,
                progress_args=(status_msg, start_time)
            )
            
            if not file_path:
                await status_msg.edit("❌ Download failed.")
                return
                
            await status_msg.edit("📤 **Uploading to you...**")
            start_time = time.time()
            sent = await fast_upload(
                client, 
                message.chat.id, 
                file_path, 
                caption=msg.caption,
                progress=progress_bar,
                progress_args=(status_msg, start_time),
                video_metadata=video_metadata
            )
            
            if sent:
                await status_msg.edit("✅ **Transfer Complete!**")
            else:
                await status_msg.edit("❌ Upload failed.")
                
    except Exception as e:
        await status_msg.edit(f"❌ Error: {str(e)}")
    
    await asyncio.sleep(5)
    await status_msg.delete()

async def verify_force_sub(client, user_id):
    from bot.config import OWNER_ID
    
    # Check database setting for force sub channel
    setting = await get_setting("force_sub_channel")
    if not setting or not setting.get('value'):
        return True, None
        
    channel = setting['value']
    # Ensure channel starts with @ for compatibility
    if not channel.startswith("@") and not channel.startswith("-100"):
        channel = f"@{channel}"
        
    try:
        member = await client.get_chat_member(channel, user_id)
        if member.status in ["left", "kicked"]:
             return False, channel
        return True, None
    except Exception as e:
        # If user is not in the channel, pyrogram raises an error
        # We catch it and return False to trigger the join prompt
        return False, channel

@app.on_message(filters.command("help") & filters.private)
async def help_command(client, message):
    from bot.config import OWNER_USERNAME, SUPPORT_CHAT_LINK
    help_text = (
        "📖 **Help Menu**\n\n"
        "⚡ **Commands**\n"
        "• /start - Start the bot\n"
        "• /login - Connect your Telegram account\n"
        "• /logout - Disconnect your account\n"
        "• /myinfo - Check your account stats\n"
        "• /help - Show this menu\n"
    )
    await message.reply(
        help_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Support Chat", url=SUPPORT_CHAT_LINK)],
            [InlineKeyboardButton("👤 Contact Owner", url=f"https://t.me/{OWNER_USERNAME}")]
        ])
    )
