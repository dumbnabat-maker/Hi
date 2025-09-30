from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import math

from shivu import collection, locked_spawns_collection, shivuu
from shivu.config import Config

@shivuu.on_message(filters.command("lockspawn"))
async def lockspawn(client, message):
    """Lock a character from spawning (sudo users only)"""
    sender_id = message.from_user.id
    
    # Check if user is admin
    if str(sender_id) not in [str(u) for u in Config.sudo_users]:
        await message.reply_text("🚫 This command is only available to administrators.")
        return
    
    if len(message.command) != 2:
        await message.reply_text(
            "📝 **Lock Spawn Usage:**\n\n"
            "`/lockspawn [character_id]`\n\n"
            "**Example:** `/lockspawn 123`\n\n"
            "This will prevent the character from appearing in spawns.",
            parse_mode=enums.ParseMode.MARKDOWN
        )
        return
    
    character_id = message.command[1]
    
    # Check if character exists
    character = await collection.find_one({'id': character_id})
    if not character:
        await message.reply_text(f"❌ Character with ID `{character_id}` not found!")
        return
    
    # Check if already locked
    existing_lock = await locked_spawns_collection.find_one({'character_id': character_id})
    if existing_lock:
        await message.reply_text(
            f"⚠️ **Already Locked!**\n\n"
            f"🎴 **Character:** {character['name']}\n"
            f"📺 **Anime:** {character['anime']}\n"
            f"🆔 **ID:** `{character_id}`\n\n"
            f"This character is already locked from spawning."
        )
        return
    
    # Lock the character
    await locked_spawns_collection.insert_one({
        'character_id': character_id,
        'character_name': character['name'],
        'anime': character['anime'],
        'rarity': character['rarity'],
        'locked_by': sender_id,
        'locked_by_username': message.from_user.username or message.from_user.first_name
    })
    
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
    
    rarity_emoji = rarity_emojis.get(character.get('rarity', 'Common'), "✨")
    
    await message.reply_text(
        f"🔒 **Spawn Locked!**\n\n"
        f"🎴 **Character:** {character['name']}\n"
        f"📺 **Anime:** {character['anime']}\n"
        f"🌟 **Rarity:** {rarity_emoji} {character['rarity']}\n"
        f"🆔 **ID:** `{character_id}`\n\n"
        f"✅ This character will no longer appear in spawns."
    )

@shivuu.on_message(filters.command("unlockspawn"))
async def unlockspawn(client, message):
    """Unlock a character from spawn restrictions (sudo users only)"""
    sender_id = message.from_user.id
    
    # Check if user is admin
    if str(sender_id) not in [str(u) for u in Config.sudo_users]:
        await message.reply_text("🚫 This command is only available to administrators.")
        return
    
    if len(message.command) != 2:
        await message.reply_text(
            "📝 **Unlock Spawn Usage:**\n\n"
            "`/unlockspawn [character_id]`\n\n"
            "**Example:** `/unlockspawn 123`\n\n"
            "This will allow the character to appear in spawns again.",
            parse_mode=enums.ParseMode.MARKDOWN
        )
        return
    
    character_id = message.command[1]
    
    # Check if character is locked
    locked_character = await locked_spawns_collection.find_one({'character_id': character_id})
    if not locked_character:
        await message.reply_text(f"❌ Character with ID `{character_id}` is not currently locked!")
        return
    
    # Unlock the character
    await locked_spawns_collection.delete_one({'character_id': character_id})
    
    await message.reply_text(
        f"🔓 **Spawn Unlocked!**\n\n"
        f"🎴 **Character:** {locked_character['character_name']}\n"
        f"📺 **Anime:** {locked_character['anime']}\n"
        f"🆔 **ID:** `{character_id}`\n\n"
        f"✅ This character can now appear in spawns again."
    )

@shivuu.on_message(filters.command("lockedspawns"))
async def lockedspawns(client, message, page=0):
    """View all currently locked spawn characters with pagination"""
    
    locked_characters = await locked_spawns_collection.find().to_list(length=None)
    
    if not locked_characters:
        await message.reply_text(
            "🔓 **No Locked Spawns**\n\n"
            "There are currently no characters locked from spawning.",
            parse_mode='markdown'
        )
        return
    
    # Items per page
    items_per_page = 20
    total_pages = math.ceil(len(locked_characters) / items_per_page)
    
    # Ensure valid page
    if page < 0 or page >= total_pages:
        page = 0
    
    # Get characters for current page
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    current_page_chars = locked_characters[start_idx:end_idx]
    
    # Group by rarity
    rarity_groups = {}
    for char in current_page_chars:
        rarity = char.get('rarity', 'Common')
        if rarity not in rarity_groups:
            rarity_groups[rarity] = []
        rarity_groups[rarity].append(char)
    
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
    
    message_text = f"🔒 **Locked Spawn Characters** - Page {page+1}/{total_pages}\n"
    
    for rarity in ["Limited Edition", "Zenith", "Retro", "Mythic", "Legendary", "Epic", "Rare", "Uncommon", "Common"]:
        if rarity in rarity_groups:
            rarity_emoji = rarity_emojis.get(rarity, "✨")
            message_text += f"\n{rarity_emoji} **{rarity}:**\n"
            
            for char in rarity_groups[rarity]:
                message_text += f"• `{char['character_id']}` - {char['character_name']} ({char['anime']})\n"
    
    message_text += f"\n📊 **Total Locked:** {len(locked_characters)} characters"
    
    # Add pagination buttons if needed
    keyboard = None
    if total_pages > 1:
        buttons = []
        if page > 0:
            buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"lockedspawns:{page-1}"))
        if page < total_pages - 1:
            buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"lockedspawns:{page+1}"))
        
        if buttons:
            keyboard = InlineKeyboardMarkup([buttons])
    
    await message.reply_text(message_text, parse_mode=enums.ParseMode.MARKDOWN, reply_markup=keyboard)

@shivuu.on_callback_query(filters.create(lambda _, __, query: query.data.startswith("lockedspawns:")))
async def lockedspawns_callback(client, callback_query):
    """Handle lockedspawns pagination"""
    try:
        page = int(callback_query.data.split(":")[1])
        
        # Get locked characters
        locked_characters = await locked_spawns_collection.find().to_list(length=None)
        
        if not locked_characters:
            await callback_query.answer("No locked spawns available!", show_alert=True)
            return
        
        # Items per page
        items_per_page = 20
        total_pages = math.ceil(len(locked_characters) / items_per_page)
        
        # Ensure valid page
        if page < 0 or page >= total_pages:
            page = 0
        
        # Get characters for current page
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        current_page_chars = locked_characters[start_idx:end_idx]
        
        # Group by rarity
        rarity_groups = {}
        for char in current_page_chars:
            rarity = char.get('rarity', 'Common')
            if rarity not in rarity_groups:
                rarity_groups[rarity] = []
            rarity_groups[rarity].append(char)
        
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
        
        message_text = f"🔒 **Locked Spawn Characters** - Page {page+1}/{total_pages}\n"
        
        for rarity in ["Limited Edition", "Zenith", "Retro", "Mythic", "Legendary", "Epic", "Rare", "Uncommon", "Common"]:
            if rarity in rarity_groups:
                rarity_emoji = rarity_emojis.get(rarity, "✨")
                message_text += f"\n{rarity_emoji} **{rarity}:**\n"
                
                for char in rarity_groups[rarity]:
                    message_text += f"• `{char['character_id']}` - {char['character_name']} ({char['anime']})\n"
        
        message_text += f"\n📊 **Total Locked:** {len(locked_characters)} characters"
        
        # Add pagination buttons if needed
        keyboard = None
        if total_pages > 1:
            buttons = []
            if page > 0:
                buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"lockedspawns:{page-1}"))
            if page < total_pages - 1:
                buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"lockedspawns:{page+1}"))
            
            if buttons:
                keyboard = InlineKeyboardMarkup([buttons])
        
        await callback_query.edit_message_text(message_text, parse_mode=enums.ParseMode.MARKDOWN, reply_markup=keyboard)
        await callback_query.answer()
        
    except Exception as e:
        await callback_query.answer(f"Error: {str(e)}", show_alert=True)

@shivuu.on_message(filters.command("rarity"))
async def rarity(client, message):
    """Show all rarities and their spawn rates"""
    
    rarity_info = {
        "Common": {"emoji": "⚪️", "rate": "20%", "spawns": "✅"},
        "Uncommon": {"emoji": "🟢", "rate": "20%", "spawns": "✅"}, 
        "Rare": {"emoji": "🔵", "rate": "20%", "spawns": "✅"},
        "Epic": {"emoji": "🟣", "rate": "20%", "spawns": "✅"},
        "Legendary": {"emoji": "🟡", "rate": "2%", "spawns": "✅"},
        "Mythic": {"emoji": "🏵", "rate": "0.8%", "spawns": "✅"},
        "Retro": {"emoji": "🍥", "rate": "0.3%", "spawns": "🔥 Special (4000 msgs)"},
        "Zenith": {"emoji": "🪩", "rate": "0%", "spawns": "❌ Never spawns"},
        "Limited Edition": {"emoji": "🍬", "rate": "0%", "spawns": "❌ Never spawns"}
    }
    
    message_text = (
        "🌟 **Character Rarity System** 🌟\n\n"
        "Here's how character rarities work in our bot:\n\n"
    )
    
    # Add regular spawning rarities
    message_text += "📊 **Regular Spawns (every 100 messages):**\n"
    for rarity in ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic"]:
        info = rarity_info[rarity]
        message_text += f"{info['emoji']} **{rarity}:** {info['rate']} chance\n"
    
    message_text += "\n🔥 **Special Spawns:**\n"
    message_text += f"{rarity_info['Retro']['emoji']} **Retro:** {rarity_info['Retro']['rate']} chance (every 4000 messages)\n"
    
    message_text += "\n❌ **Non-Spawning Rarities:**\n"
    for rarity in ["Zenith", "Limited Edition"]:
        info = rarity_info[rarity]
        message_text += f"{info['emoji']} **{rarity}:** {info['spawns']}\n"
    
    message_text += (
        "\n💡 **Tips:**\n"
        "• Higher rarity = lower spawn chance\n"
        "• Zenith & Limited Edition cards are exclusive\n"
        "• Retro cards only spawn every 4000 messages\n"
        "• Use `/lockspawn` to prevent specific cards from spawning (admin only)\n\n"
        "✨ Good luck collecting!"
    )
  
    await message.reply_text(message_text, parse_mode=enums.ParseMode.MARKDOWN)

