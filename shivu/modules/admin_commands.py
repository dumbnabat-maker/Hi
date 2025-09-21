from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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
            parse_mode='Markdown'
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
            parse_mode='Markdown'
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
async def lockedspawns(client, message):
    """View all currently locked spawn characters"""
    
    locked_characters = await locked_spawns_collection.find().to_list(length=None)
    
    if not locked_characters:
        await message.reply_text(
            "🔓 **No Locked Spawns**\n\n"
            "There are currently no characters locked from spawning."
        )
        return
    
    # Group by rarity
    rarity_groups = {}
    for char in locked_characters:
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
    
    message_parts = ["🔒 **Locked Spawn Characters**\n"]
    
    for rarity in ["Limited Edition", "Zenith", "Mythic", "Legendary", "Epic", "Rare", "Uncommon", "Common"]:
        if rarity in rarity_groups:
            rarity_emoji = rarity_emojis.get(rarity, "✨")
            message_parts.append(f"\n{rarity_emoji} **{rarity}:**")
            
            for char in rarity_groups[rarity]:
                message_parts.append(f"• `{char['character_id']}` - {char['character_name']} ({char['anime']})")
    
    message_parts.append(f"\n📊 **Total Locked:** {len(locked_characters)} characters")
    
    full_message = "\n".join(message_parts)
    
    # Split message if too long
    if len(full_message) > 4000:
        parts = []
        current_part = "🔒 **Locked Spawn Characters**\n"
        
        for line in message_parts[1:]:
            if len(current_part + line + "\n") > 4000:
                parts.append(current_part)
                current_part = line + "\n"
            else:
                current_part += line + "\n"
        
        if current_part:
            parts.append(current_part)
        
        for i, part in enumerate(parts):
            if i == 0:
                await message.reply_text(part, parse_mode='Markdown')
            else:
                await message.reply_text(f"**Continued...**\n\n{part}", parse_mode='Markdown')
    else:
        await message.reply_text(full_message, parse_mode='Markdown')

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
        "Retro": {"emoji": "🍥", "rate": "0.3%", "spawns": "🔥 Special (1000 msgs)"},
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
    message_text += f"{rarity_info['Retro']['emoji']} **Retro:** {rarity_info['Retro']['rate']} chance (every 1000 messages)\n"
    
    message_text += "\n❌ **Non-Spawning Rarities:**\n"
    for rarity in ["Zenith", "Limited Edition"]:
        info = rarity_info[rarity]
        message_text += f"{info['emoji']} **{rarity}:** {info['spawns']}\n"
    
    message_text += (
        "\n💡 **Tips:**\n"
        "• Higher rarity = lower spawn chance\n"
        "• Zenith & Limited Edition cards are exclusive\n"
        "• Retro cards only spawn every 1000 messages\n"
        "• Use `/lockspawn` to prevent specific cards from spawning (admin only)\n\n"
        "✨ Good luck collecting!"
    )
    
    await message.reply_text(message_text, parse_mode='Markdown')