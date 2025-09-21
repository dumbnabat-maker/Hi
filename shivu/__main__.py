import importlib
import random
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, filters
from html import escape

from shivu import collection, top_global_groups_collection, group_user_totals_collection, user_collection, user_totals_collection, locked_spawns_collection, shivuu
from shivu import application, SUPPORT_CHAT, UPDATE_CHAT, db, LOGGER
from shivu.modules import ALL_MODULES


locks = {}
last_characters = {}
sent_characters = {}
first_correct_guesses = {}
message_counts = {}
retro_message_counts = {}  # Track messages for Retro spawns (every 4k messages)
manually_summoned = {}  # Track manually summoned characters to allow multiple marriages


for module_name in ALL_MODULES:
    imported_module = importlib.import_module("shivu.modules." + module_name)




async def message_counter(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id

    if chat_id not in locks:
        locks[chat_id] = asyncio.Lock()
    lock = locks[chat_id]

    async with lock:
        
        chat_frequency = await user_totals_collection.find_one({'chat_id': str(chat_id)})
        if chat_frequency:
            message_frequency = chat_frequency.get('message_frequency', 100)
        else:
            message_frequency = 100

        
        if chat_id in message_counts:
            message_counts[chat_id] += 1
        else:
            message_counts[chat_id] = 1

        
        if message_counts[chat_id] % message_frequency == 0:
            await send_image(update, context)
            
            message_counts[chat_id] = 0
        
        # Check for Retro spawn (every 4000 messages)
        if chat_id in retro_message_counts:
            retro_message_counts[chat_id] += 1
        else:
            retro_message_counts[chat_id] = 1
            
        if retro_message_counts[chat_id] % 4000 == 0:
            await send_retro_character(update, context)
            retro_message_counts[chat_id] = 0
            
async def send_image(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id

    # Get locked character IDs
    locked_character_ids = [doc['character_id'] for doc in await locked_spawns_collection.find().to_list(length=None)]
    
    # Only get spawnable characters (exclude Limited Edition, Zenith, Retro, and locked characters)
    filter_criteria = {
        'rarity': {'$nin': ['Limited Edition', 'Zenith', 'Retro']},
        'id': {'$nin': locked_character_ids}
    }
    all_characters = list(await collection.find(filter_criteria).to_list(length=None))
    
    # Check if there are any spawnable characters
    if not all_characters:
        LOGGER.warning("No spawnable characters available - all are Limited Edition or Zenith")
        return
    
    if chat_id not in sent_characters:
        sent_characters[chat_id] = []

    if len(sent_characters[chat_id]) == len(all_characters):
        sent_characters[chat_id] = []

    available_characters = [c for c in all_characters if c['id'] not in sent_characters[chat_id]]
    if not available_characters:
        # This shouldn't happen due to the reset above, but just in case
        available_characters = all_characters
        sent_characters[chat_id] = []
    
    character = random.choice(available_characters)

    sent_characters[chat_id].append(character['id'])
    last_characters[chat_id] = character

    if chat_id in first_correct_guesses:
        del first_correct_guesses[chat_id]
    
    # Clear manually summoned flag for automatic spawns
    if chat_id in manually_summoned:
        del manually_summoned[chat_id]

    # Rarity emoji mapping
    rarity_emojis = {
        "Common": "⚪️",
        "Uncommon": "🟢", 
        "Rare": "🔵",
        "Epic": "🟣",
        "Legendary": "🟡",
        "Mythic": "🏵",
        "Retro": "🍥",
        "Zenith": "🪩",
        "Limited Edition": "🍬"
    }
    
    rarity_emoji = rarity_emojis.get(character['rarity'], "✨")

    try:
        from shivu import process_image_url
        processed_url = await process_image_url(character['img_url'])
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=processed_url,
            caption=f"""{rarity_emoji} A beauty has been summoned! Use /marry to add them to your harem!""",
            parse_mode='Markdown')
    except Exception as e:
        LOGGER.error(f"Error sending character image: {str(e)}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{rarity_emoji} A beauty has been summoned! Use /marry to add them to your harem!\n\n⚠️ Image could not be loaded",
            parse_mode='Markdown')


async def send_retro_character(update: Update, context: CallbackContext) -> None:
    """Send a Retro character every 4000 messages"""
    chat_id = update.effective_chat.id
    
    # Get only Retro characters
    retro_characters = list(await collection.find({
        'rarity': 'Retro'
    }).to_list(length=None))
    
    if not retro_characters:
        LOGGER.warning("No Retro characters available to spawn")
        return
    
    # Track sent Retro characters separately to avoid repeats
    retro_sent_key = f"{chat_id}_retro"
    
    if retro_sent_key not in sent_characters:
        sent_characters[retro_sent_key] = []

    if len(sent_characters[retro_sent_key]) == len(retro_characters):
        sent_characters[retro_sent_key] = []

    available_retro = [c for c in retro_characters if c['id'] not in sent_characters[retro_sent_key]]
    if not available_retro:
        available_retro = retro_characters
        sent_characters[retro_sent_key] = []
    
    character = random.choice(available_retro)
    sent_characters[retro_sent_key].append(character['id'])
    last_characters[chat_id] = character

    if chat_id in first_correct_guesses:
        del first_correct_guesses[chat_id]
    
    # Clear manually summoned flag for automatic spawns
    if chat_id in manually_summoned:
        del manually_summoned[chat_id]

    try:
        from shivu import process_image_url
        processed_url = await process_image_url(character['img_url'])
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=processed_url,
            caption=f"🍥 A rare RETRO beauty has appeared! Use /marry to add them to your harem!",
            parse_mode='Markdown')
    except Exception as e:
        LOGGER.error(f"Error sending retro character image: {str(e)}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🍥 A rare RETRO beauty has appeared! Use /marry to add them to your harem!\n\n⚠️ Image could not be loaded",
            parse_mode='Markdown')


async def guess(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if chat_id not in last_characters:
        await update.message.reply_text('🚫 No character has been summoned yet!\n\nCharacters appear automatically every 100 messages, or admins can use /summon to spawn one manually.')
        return

    # Only prevent multiple guesses for automatically spawned characters
    # Allow multiple marriages for manually summoned characters
    if chat_id in first_correct_guesses and chat_id not in manually_summoned:
        await update.message.reply_text(f'❌️ Already Guessed By Someone.. Try Next Time Bruhh ')
        return

    guess = ' '.join(context.args).lower() if context.args else ''
    
    if "()" in guess or "&" in guess.lower():
        await update.message.reply_text("Nahh You Can't use This Types of words in your guess..❌️")
        return


    name_parts = last_characters[chat_id]['name'].lower().split()

    # Smart matching: exact parts, partial matches, or fuzzy matches
    def smart_name_match(guess, name_parts):
        guess = guess.strip()
        if not guess:
            return False
            
        # 1. Exact full name match (any word order)
        if sorted(name_parts) == sorted(guess.split()):
            return True
            
        # 2. Exact single part match 
        if any(part == guess for part in name_parts):
            return True
            
        # 3. Partial match - guess is start of any name part (min 3 chars)
        if len(guess) >= 3:
            if any(part.startswith(guess) for part in name_parts):
                return True
                
        # 4. Fuzzy match - guess contains or is contained in any part
        if len(guess) >= 3:
            if any(guess in part or part in guess for part in name_parts):
                return True
                
        return False

    if smart_name_match(guess, name_parts):
        # For manually summoned characters, don't prevent multiple marriages
        if chat_id not in manually_summoned:
            first_correct_guesses[chat_id] = user_id
        
        user = await user_collection.find_one({'id': user_id})
        if user:
            update_fields = {}
            if hasattr(update.effective_user, 'username') and update.effective_user.username != user.get('username'):
                update_fields['username'] = update.effective_user.username
            if update.effective_user.first_name != user.get('first_name'):
                update_fields['first_name'] = update.effective_user.first_name
            
            # Ensure characters field exists as a list
            if 'characters' not in user or user['characters'] is None:
                update_fields['characters'] = []
                
            if update_fields:
                await user_collection.update_one({'id': user_id}, {'$set': update_fields})
            
            await user_collection.update_one({'id': user_id}, {'$push': {'characters': last_characters[chat_id]}})
      
        elif hasattr(update.effective_user, 'username'):
            await user_collection.insert_one({
                'id': user_id,
                'username': update.effective_user.username,
                'first_name': update.effective_user.first_name,
                'characters': [last_characters[chat_id]],
            })

        
        group_user_total = await group_user_totals_collection.find_one({'user_id': user_id, 'group_id': chat_id})
        if group_user_total:
            update_fields = {}
            if hasattr(update.effective_user, 'username') and update.effective_user.username != group_user_total.get('username'):
                update_fields['username'] = update.effective_user.username
            if update.effective_user.first_name != group_user_total.get('first_name'):
                update_fields['first_name'] = update.effective_user.first_name
            if update_fields:
                await group_user_totals_collection.update_one({'user_id': user_id, 'group_id': chat_id}, {'$set': update_fields})
            
            await group_user_totals_collection.update_one({'user_id': user_id, 'group_id': chat_id}, {'$inc': {'count': 1}})
      
        else:
            await group_user_totals_collection.insert_one({
                'user_id': user_id,
                'group_id': chat_id,
                'username': update.effective_user.username,
                'first_name': update.effective_user.first_name,
                'count': 1,
            })


    
        group_info = await top_global_groups_collection.find_one({'group_id': chat_id})
        if group_info:
            update_fields = {}
            if update.effective_chat.title != group_info.get('group_name'):
                update_fields['group_name'] = update.effective_chat.title
            if update_fields:
                await top_global_groups_collection.update_one({'group_id': chat_id}, {'$set': update_fields})
            
            await top_global_groups_collection.update_one({'group_id': chat_id}, {'$inc': {'count': 1}})
      
        else:
            await top_global_groups_collection.insert_one({
                'group_id': chat_id,
                'group_name': update.effective_chat.title,
                'count': 1,
            })


        
        keyboard = [[InlineKeyboardButton(f"See Harem", switch_inline_query_current_chat=f"collection.{user_id}")]]


        await update.message.reply_text(f'<b><a href="tg://user?id={user_id}">{escape(update.effective_user.first_name)}</a></b> You Guessed a New Character ✅️ \n\n𝗡𝗔𝗠𝗘: <b>{last_characters[chat_id]["name"]}</b> \n𝗔𝗡𝗜𝗠𝗘: <b>{last_characters[chat_id]["anime"]}</b> \n𝗥𝗔𝗥𝗜𝗧𝗬: <b>{last_characters[chat_id]["rarity"]}</b>\n\nThis Character added in Your harem.. use /harem To see your harem', parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

    else:
        await update.message.reply_text('Please Write Correct Character Name... ❌️')
   



async def post_init(application):
    """Set bot commands after application starts"""
    from telegram import BotCommand
    
    commands = [
        BotCommand("start", "Start the bot and get help"),
        BotCommand("harem", "View your character collection"),
        BotCommand("fav", "Set favorite character by ID"),
        BotCommand("find", "Find character by ID number"),  
        BotCommand("sorts", "Set harem sorting preference"),
        BotCommand("marry", "Guess and collect a character"),
        BotCommand("upload", "Upload new character (admin only)"),
        BotCommand("summon", "Test character summon (admin only)"),
        BotCommand("changetime", "Change spawn frequency (admin only)"),
        BotCommand("ping", "Check bot status"),
        BotCommand("topgroups", "View top groups leaderboard"),
    ]
    
    await application.bot.set_my_commands(commands)
    LOGGER.info("Bot commands set successfully")


def main() -> None:
    """Run bot."""
    
    application.add_handler(CommandHandler(["marry"], guess, block=False))
    application.add_handler(MessageHandler(filters.ALL, message_counter, block=False))

    # Set up post-init callback for bot commands
    application.post_init = post_init

    application.run_polling(drop_pending_updates=True)
    
if __name__ == "__main__":
    shivuu.start()
    LOGGER.info("Bot started")
    main()
