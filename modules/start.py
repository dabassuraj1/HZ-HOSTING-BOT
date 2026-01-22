# modules/start.py

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

from utils.config import config
from utils.database import add_user

# Define the keyboard layout
# In modules/start.py

# Define the keyboard layout
start_keyboard = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("👑 Owner", url="https://t.me/https://t.me/HZHOSTINGBOTT"),
            InlineKeyboardButton("📢 Channel", url="https://t.me/HZZHOSTINGBOT")
        ],
        # CORRECTED: Use callback_data for the button
        [
            InlineKeyboardButton("🚀 My Projects", callback_data="my_projects_list"),
            InlineKeyboardButton("⭐ Buy Slots", callback_data="buy_project_slot")
        ]
    ]
)

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Add the user to the database
    # The new add_user function will set the default quota
    await add_user(user_id, username)
    
    # Updated start message to be more informative
    start_text = (
        "**👋 Welcome to the Python Project Hoster!**\n\n"
        "I'm your personal bot for securely deploying and managing your Python scripts and applications, right here from Telegram.\n\n"
        "**Key Features:**\n"
        "🚀 **Deploy Instantly:** Upload your code as a `.zip` or `.py` file.\n"
        "📂 **Easy Management:** Use the built-in web file manager to edit code live.\n"
        "🤖 **Full Control:** Start, stop, restart, and view logs for all your projects.\n\n"
        "**Project Tiers:**\n"
        f"🆓 **Free Tier:** You get **{config.User.FREE_USER_PROJECT_QUOTA} project slot** with **{config.User.FREE_USER_RAM_MB}MB RAM** to start.\n"
        f"⭐ **Premium Tier:** Need more power? Purchase additional slots for **{config.Premium.PLANS['1']['stars']} Stars**, each giving you **{config.Premium.PLANS['1']['ram_mb']}MB RAM** and renewing monthly.\n\n"
        "👇 **Get Started**\n"
        "Use **/newproject** to deploy your first application!"
    )
    
    await message.reply_text(
        text=start_text,
        reply_markup=start_keyboard,
        disable_web_page_preview=True
    )
