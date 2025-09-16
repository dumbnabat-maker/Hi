import random
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters
import os

message_count = {}  # Tracks messages per chat

# Extract owner ID from environment variable (handle extra text)
owner_id_str = os.environ.get("OWNER_ID", "0")
# Extract just the numbers from the string
import re
owner_id_match = re.search(r'\d+', owner_id_str)
OWNER_ID = int(owner_id_match.group()) if owner_id_match else 0

# --- Global Variables ---

rarities = {
    "Common": 20,
    "Uncommon": 20,
    "Rare": 20,
    "Epic": 20,
    "Legendary": 10,
    "Mythic": 5,
    "Celestial": 2,
    "Arcane": 1,
    "Limited Edition": 0
}

rarity_styles = {
    "Common": "⚪️",
    "Uncommon": "🟢",
    "Rare": "🔵",
    "Epic": "🟣",
    "Legendary": "🟡",
    "Mythic": "🟥",
    "Celestial": "🌌",
    "Arcane": "🔥",
    "Limited Edition": "💎"
}

# Example characters (you can replace with your real image URLs later)
characters = {
    "Common": [
        {"name": "Azure Knight", "url": "https://telegra.ph/file/b925c3985f0f325e62e17.jpg"},
        {"name": "Forest Guardian", "url": "https://telegra.ph/file/4211fb191383d895dab9d.jpg"}
    ],
    "Uncommon": [
        {"name": "Storm Mage", "url": "https://telegra.ph/file/b925c3985f0f325e62e17.jpg"},
        {"name": "Shadow Warrior", "url": "https://telegra.ph/file/4211fb191383d895dab9d.jpg"}
    ],
    "Rare": [
        {"name": "Crystal Sage", "url": "https://telegra.ph/file/b925c3985f0f325e62e17.jpg"},
        {"name": "Fire Empress", "url": "https://telegra.ph/file/4211fb191383d895dab9d.jpg"}
    ],
    "Epic": [
        {"name": "Dragon Lord", "url": "https://telegra.ph/file/b925c3985f0f325e62e17.jpg"},
        {"name": "Ice Queen", "url": "https://telegra.ph/file/4211fb191383d895dab9d.jpg"}
    ],
    "Legendary": [
        {"name": "Phoenix Master", "url": "https://telegra.ph/file/b925c3985f0f325e62e17.jpg"},
        {"name": "Void Keeper", "url": "https://telegra.ph/file/4211fb191383d895dab9d.jpg"}
    ],
    "Mythic": [
        {"name": "Celestial Dragon", "url": "https://telegra.ph/file/b925c3985f0f325e62e17.jpg"},
        {"name": "Eternal Guardian", "url": "https://telegra.ph/file/4211fb191383d895dab9d.jpg"}
    ],
    "Celestial": [
        {"name": "Star Weaver", "url": "https://telegra.ph/file/b925c3985f0f325e62e17.jpg"},
        {"name": "Cosmic Entity", "url": "https://telegra.ph/file/4211fb191383d895dab9d.jpg"}
    ],
    "Arcane": [
        {"name": "Reality Bender", "url": "https://telegra.ph/file/b925c3985f0f325e62e17.jpg"},
        {"name": "Time Weaver", "url": "https://telegra.ph/file/4211fb191383d895dab9d.jpg"}
    ]
}

# Track last summoned characters per user (temporary storage)
last_summons = {}
user_collections = {}
# Store user favorites
favorites = {}

# --- Bot Functions ---

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "✨ Welcome to the waifu collector Bot!\n\n"
        "Commands:\n"
        "/summon - Summon a random character\n"
        "/marry - Marry your last summoned character\n"
        "/collection - View your collection\n"
        "/fav - View your favorite character\n"
        "/setfav - Set your last summoned character as favorite"
    )

async def summon(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    # Debug logging (remove after testing)
    print(f"DEBUG: User ID: {user_id}, Owner ID: {OWNER_ID}, Type: {type(user_id)}, {type(OWNER_ID)}")
    
    # Check if user is the bot owner
    if user_id != OWNER_ID:
        await update.message.reply_text(f"🚫 Only the bot owner can manually summon characters!\nYour ID: {user_id}, Owner ID: {OWNER_ID}")
        return
    
    rarity = random.choices(
        population=list(rarities.keys()),
        weights=list(rarities.values()),
        k=1
    )[0]

    if rarity in characters and characters[rarity]:
        character = random.choice(characters[rarity])
        style = rarity_styles.get(rarity, "")
        caption = f"{style} A beauty has been summoned! Use /marry to add them to your harem!"

        # Store the summoned character for this user
        last_summons[user_id] = {
            "name": character["name"],
            "rarity": rarity,
            "url": character["url"],
            "style": style
        }

        # For now using basic functionality - can add JFIF support later if needed in this file
        await update.message.reply_photo(
            character["url"],
            caption=caption
        )
    else:
        await update.message.reply_text("⚠️ No characters found for this rarity yet.")

async def marry(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    if user_id in last_summons:
        summon_info = last_summons[user_id]
        
        # Initialize user collection if not exists
        if user_id not in user_collections:
            user_collections[user_id] = []
        
        # Add character to collection
        user_collections[user_id].append(summon_info)
        
        # Remove from last summons
        del last_summons[user_id]
        
        await update.message.reply_text(
            f"✅ You married {summon_info['style']} {summon_info['name']} ({summon_info['rarity']})!\n\n"
            f"Total characters in collection: {len(user_collections[user_id])}"
        )
    else:
        await update.message.reply_text("❌ You need to /summon first before you can /marry.")

async def collection(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    if user_id not in user_collections or not user_collections[user_id]:
        await update.message.reply_text("📦 Your collection is empty! Use /summon to find characters.")
        return
    
    collection_text = "🎴 Your Collection:\n\n"
    
    # Group by rarity
    rarity_counts = {}
    for char in user_collections[user_id]:
        rarity = char['rarity']
        if rarity not in rarity_counts:
            rarity_counts[rarity] = []
        rarity_counts[rarity].append(char['name'])
    
    # Display by rarity (highest to lowest)
    rarity_order = ["Limited Edition", "Arcane", "Celestial", "Mythic", "Legendary", "Epic", "Rare", "Uncommon", "Common"]
    
    for rarity in rarity_order:
        if rarity in rarity_counts:
            style = rarity_styles.get(rarity, "")
            collection_text += f"{style} {rarity} ({len(rarity_counts[rarity])}):\n"
            for name in rarity_counts[rarity]:
                collection_text += f"  • {name}\n"
            collection_text += "\n"
    
    collection_text += f"📊 Total: {len(user_collections[user_id])} characters"
    
    await update.message.reply_text(collection_text)

async def handle_message(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    # Increase message count for this chat
    if chat_id not in message_count:
        message_count[chat_id] = 0
    message_count[chat_id] += 1

    # Check if 100 messages reached
    if message_count[chat_id] >= 100:
        message_count[chat_id] = 0  # reset counter
        await summon(update, context)  # call your summon function

async def fav(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id in favorites:
        fav_character = favorites[user_id]
        await update.message.reply_text(f"💖 Your favorite is {fav_character['name']} ({fav_character['rarity']})!")
        # Show the favorite character image
        await update.message.reply_photo(fav_character['url'])
    else:
        await update.message.reply_text("You don't have a favorite yet. Use /setfav first!")

async def setfav(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id in last_summons:
        favorites[user_id] = last_summons[user_id]
        await update.message.reply_text(f"💖 {last_summons[user_id]['name']} is now your favorite!")
    else:
        await update.message.reply_text("You haven't summoned any character yet!")

async def post_init(application):
    """Set bot commands after application starts to make them visible in Telegram"""
    commands = [
        BotCommand("start", "Start the bot and get help"),
        BotCommand("summon", "Summon a random character (owner only)"),
        BotCommand("marry", "Marry your last summoned character"),
        BotCommand("collection", "View your character collection"),
        BotCommand("fav", "View your favorite character"),
        BotCommand("setfav", "Set your last summoned character as favorite"),
    ]
    
    await application.bot.set_my_commands(commands)
    print("🤖 Bot commands registered successfully")

# --- Main Function ---
def main():
    # Get token from environment variable
    token = os.environ.get("7814983224:AAE3J1yPGVHS6n49Cz_RiZ5_6bAMHAhKPDc")
    
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set!")
        return
    
    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("summon", summon))
    application.add_handler(CommandHandler("marry", marry))
    application.add_handler(CommandHandler("collection", collection))
    application.add_handler(CommandHandler("fav", fav))
    application.add_handler(CommandHandler("setfav", setfav))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Set up post-init callback to register bot commands for Telegram visibility
    application.post_init = post_init

    print("🤖 Summon Bot is starting...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()