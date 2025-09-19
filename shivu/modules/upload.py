import urllib.request
import urllib.parse
import urllib.error
import re
from pymongo import ReturnDocument

from telegram import Update
from telegram.ext import CommandHandler, CallbackContext

from shivu import application, sudo_users, collection, db, CHARA_CHANNEL_ID, SUPPORT_CHAT

# Rarity styles for display purposes
rarity_styles = {
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

WRONG_FORMAT_TEXT = """Wrong ❌️ format...  eg. /upload Img_url muzan-kibutsuji Demon-slayer 5

img_url character-name anime-name rarity-number

Use rarity number accordingly:

1 = ⚪️ Common
2 = 🟢 Uncommon  
3 = 🔵 Rare
4 = 🟣 Epic
5 = 🟡 Legendary
6 = 🏵 Mythic
7 = 🍥 Retro
8 = 🪩 Zenith
9 = 🍬 Limited Edition

✅ Supported: Discord CDN links, direct image URLs, and other standard image hosting services"""


def is_discord_cdn_url(url):
    """Check if the URL is a Discord CDN link"""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ['http', 'https']:
            return False
        
        discord_hosts = [
            'cdn.discordapp.com',
            'media.discordapp.net',
            'attachments.discordapp.net',
            'cdn.discord.com',
            'media.discord.com'
        ]
        
        return parsed.netloc in discord_hosts
    except:
        return False


def validate_url(url):
    """
    Validate a URL and return whether it's accessible.
    Handles Discord CDN links with special logic.
    """
    # For Discord CDN links, bypass full validation and just check structure
    if is_discord_cdn_url(url):
        try:
            parsed = urllib.parse.urlparse(url)
            # Basic validation for Discord CDN structure
            if parsed.path and ('/' in parsed.path[1:]):  # Has meaningful path
                return True, "Discord CDN link (validation bypassed)"
            else:
                return False, "Invalid Discord CDN link structure"
        except:
            return False, "Invalid Discord CDN URL format"
    
    # For non-Discord URLs, perform full validation
    try:
        # Create request with appropriate headers
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        # Try to open the URL
        with urllib.request.urlopen(req, timeout=10) as response:
            # Check if it's actually an image by checking content type or URL
            content_type = response.headers.get('Content-Type', '')
            if content_type.startswith('image/') or any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']):
                return True, "Valid image URL"
            else:
                return False, "URL does not appear to be an image"
                
    except urllib.error.HTTPError as e:
        return False, f"HTTP Error: {e.code}"
    except urllib.error.URLError as e:
        return False, f"URL Error: {str(e)}"
    except Exception as e:
        return False, f"Validation Error: {str(e)}"



async def get_next_sequence_number(sequence_name):
    sequence_collection = db.sequences
    sequence_document = await sequence_collection.find_one_and_update(
        {'_id': sequence_name}, 
        {'$inc': {'sequence_value': 1}}, 
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    return sequence_document['sequence_value']

async def upload(update: Update, context: CallbackContext) -> None:
    if not update.effective_user or not update.message:
        return
        
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('Ask My Owner...')
        return

    try:
        args = context.args
        if not args or len(args) != 4:
            await update.message.reply_text(WRONG_FORMAT_TEXT)
            return

        character_name = args[1].replace('-', ' ').title()
        anime = args[2].replace('-', ' ').title()

        # Validate URL with enhanced Discord CDN support
        is_valid, validation_message = validate_url(args[0])
        if not is_valid:
            await update.message.reply_text(f'Invalid URL: {validation_message}')
            return
        
        # If it's a Discord CDN link, inform the user
        if is_discord_cdn_url(args[0]):
            await update.message.reply_text('✅ Discord CDN link detected - processing...', reply_to_message_id=update.message.message_id)

        rarity_map = {
            1: "Common", 
            2: "Uncommon", 
            3: "Rare", 
            4: "Epic", 
            5: "Legendary", 
            6: "Mythic", 
            7: "Retro", 
            8: "Zenith", 
            9: "Limited Edition"
        }
        try:
            rarity = rarity_map[int(args[3])]
        except KeyError:
            await update.message.reply_text('Invalid rarity. Please use 1-9:\n1=Common, 2=Uncommon, 3=Rare, 4=Epic, 5=Legendary, 6=Mythic, 7=Retro, 8=Zenith, 9=Limited Edition')
            return

        id = str(await get_next_sequence_number('character_id'))

        character = {
            'img_url': args[0],
            'name': character_name,
            'anime': anime,
            'rarity': rarity,
            'id': id
        }

        try:
            rarity_emoji = rarity_styles.get(rarity, "")
            from shivu import process_image_url
            processed_url = await process_image_url(args[0])
            # Create neat and pretty caption format
            caption = (
                f"✨ <b>{character_name}</b> ✨\n"
                f"🎌 <i>{anime}</i>\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"{rarity_emoji} <b>{rarity}</b>\n"
                f"🆔 <b>ID:</b> #{id}\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"📤 Added by <a href='tg://user?id={update.effective_user.id}'>{update.effective_user.first_name}</a>"
            )
            
            message = await context.bot.send_photo(
                chat_id=CHARA_CHANNEL_ID,
                photo=processed_url,
                caption=caption,
                parse_mode='HTML'
            )
            character['message_id'] = message.message_id
            await collection.insert_one(character)
            await update.message.reply_text('CHARACTER ADDED....')
        except:
            await collection.insert_one(character)
            await update.effective_message.reply_text("Character Added but no Database Channel Found, Consider adding one.")
        
    except Exception as e:
        await update.message.reply_text(f'Character Upload Unsuccessful. Error: {str(e)}\nIf you think this is a source error, forward to: {SUPPORT_CHAT}')

async def delete(update: Update, context: CallbackContext) -> None:
    if not update.effective_user or not update.message:
        return
        
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('Ask my Owner to use this Command...')
        return

    try:
        args = context.args
        if not args or len(args) != 1:
            await update.message.reply_text('Incorrect format... Please use: /delete ID')
            return

        
        character = await collection.find_one_and_delete({'id': args[0]})

        if character:
            
            await context.bot.delete_message(chat_id=CHARA_CHANNEL_ID, message_id=character['message_id'])
            await update.message.reply_text('DONE')
        else:
            await update.message.reply_text('Deleted Successfully from db, but character not found In Channel')
    except Exception as e:
        await update.message.reply_text(f'{str(e)}')

async def summon(update: Update, context: CallbackContext) -> None:
    """Summon a random character for testing (sudo users only)"""
    if not update.effective_user or not update.message:
        return
        
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('Ask My Owner...')
        return
        
    try:
        # Get total character count
        total_characters = await collection.count_documents({})
        
        if total_characters == 0:
            await update.message.reply_text('📭 No characters in database to summon!\n\nUpload some characters first using /upload')
            return
        
        # Get characters grouped by rarity for weighted selection
        rarities_weights = {
            "Common": 20,
            "Uncommon": 20,
            "Rare": 20,
            "Epic": 20,
            "Legendary": 2,
            "Mythic": 0.8,
            "Retro": 0.3,
            "Zenith": 0,
            "Limited Edition": 0
        }
        
        # Get available rarities from database (excluding Limited Edition)
        available_rarities = await collection.distinct('rarity', {'rarity': {'$ne': 'Limited Edition'}})
        
        if not available_rarities:
            await update.message.reply_text('❌ No spawnable characters available!\n\nAll characters in the database appear to be Limited Edition or non-spawnable. Please upload some common characters using /upload.')
            return
        
        # Filter weights to only include available rarities
        available_weights = {rarity: rarities_weights.get(rarity, 0) for rarity in available_rarities if rarities_weights.get(rarity, 0) > 0}
        
        if not available_weights:
            await update.message.reply_text('❌ No spawnable characters available!\n\nAll available character rarities have 0 spawn weight. Please upload some common characters using /upload.')
            return
        
        # Use weighted random selection for rarity
        import random
        selected_rarity = random.choices(
            population=list(available_weights.keys()),
            weights=list(available_weights.values()),
            k=1
        )[0]
        
        # Get a random character from the selected rarity
        random_character = await collection.aggregate([
            {'$match': {'rarity': selected_rarity}},
            {'$sample': {'size': 1}}
        ]).to_list(length=1)
        
        if not random_character:
            await update.message.reply_text('❌ No spawnable characters available!\n\nAll characters in the database appear to be Limited Edition or non-spawnable. Please upload some common characters using /upload.')
            return
            
        character = random_character[0]
        chat_id = update.effective_chat.id
        
        # Store character for marry command to find it
        from shivu.__main__ import last_characters, first_correct_guesses, manually_summoned
        last_characters[chat_id] = character
        
        # Mark as manually summoned to allow multiple marriages
        manually_summoned[chat_id] = True
        
        # Clear any existing guesses for this chat
        if chat_id in first_correct_guesses:
            del first_correct_guesses[chat_id]
        
        # Get rarity emoji
        rarity_emoji = rarity_styles.get(character.get('rarity', ''), "")
        
        # Create beautiful summon display with hidden character details
        caption = f"{rarity_emoji} A beauty has been summoned! Use /marry to add them to your harem!"
        
        # Process the image URL for compatibility and handle errors gracefully
        try:
            from shivu import process_image_url
            processed_url = await process_image_url(character['img_url'])
            
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=processed_url,
                caption=caption,
                parse_mode='HTML'
            )
        except Exception as img_error:
            # If image fails to load, send text message instead
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"{caption}\n\n⚠️ Image could not be loaded - {character['name']} from {character['anime']}",
                parse_mode='HTML'
            )
        
    except Exception as e:
        await update.message.reply_text(f'❌ Error summoning character: {str(e)}')


async def find(update: Update, context: CallbackContext) -> None:
    """Find a character by ID number"""
    if not update.effective_chat or not update.message:
        return
        
    try:
        args = context.args
        if not args:
            await update.message.reply_text('🔍 <b>Find Character</b>\n\nUsage: /find <id>\nExample: /find 1', parse_mode='HTML')
            return
        
        character_id = args[0]
        
        # Search for character by ID
        character = await collection.find_one({'id': character_id})
        
        if not character:
            await update.message.reply_text(f'❌ No character found with ID #{character_id}')
            return
        
        # Get rarity emoji
        rarity_emoji = rarity_styles.get(character.get('rarity', ''), "")
        
        # Create beautiful character display
        caption = (
            f"✨ <b>{character['name']}</b> ✨\n"
            f"🎌 <i>{character['anime']}</i>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"{rarity_emoji} <b>{character['rarity']}</b>\n"
            f"🆔 <b>ID:</b> #{character['id']}\n"
            f"━━━━━━━━━━━━━━━━"
        )
        
        # Process the image URL for compatibility
        from shivu import process_image_url
        processed_url = await process_image_url(character['img_url'])
        
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=processed_url,
            caption=caption,
            parse_mode='HTML'
        )
        
    except Exception as e:
        await update.message.reply_text(f'❌ Error finding character: {str(e)}')


async def update(update: Update, context: CallbackContext) -> None:
    if not update.effective_user or not update.message:
        return
        
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('You do not have permission to use this command.')
        return

    try:
        args = context.args
        if not args or len(args) != 3:
            await update.message.reply_text('Incorrect format. Please use: /update id field new_value')
            return

        # Get character by ID
        character = await collection.find_one({'id': args[0]})
        if not character:
            await update.message.reply_text('Character not found.')
            return

        # Check if field is valid
        valid_fields = ['img_url', 'name', 'anime', 'rarity']
        if args[1] not in valid_fields:
            await update.message.reply_text(f'Invalid field. Please use one of the following: {", ".join(valid_fields)}')
            return

        # Update field
        if args[1] in ['name', 'anime']:
            new_value = args[2].replace('-', ' ').title()
        elif args[1] == 'rarity':
            rarity_map = {
                1: "Common", 
                2: "Uncommon", 
                3: "Rare", 
                4: "Epic", 
                5: "Legendary", 
                6: "Mythic", 
                7: "Retro", 
                8: "Zenith", 
                9: "Limited Edition"
            }
            try:
                new_value = rarity_map[int(args[2])]
            except KeyError:
                await update.message.reply_text('Invalid rarity. Please use 1-9:\n1=Common, 2=Uncommon, 3=Rare, 4=Epic, 5=Legendary, 6=Mythic, 7=Retro, 8=Zenith, 9=Limited Edition')
                return
        else:
            new_value = args[2]

        await collection.find_one_and_update({'id': args[0]}, {'$set': {args[1]: new_value}})

        
        if args[1] == 'img_url':
            await context.bot.delete_message(chat_id=CHARA_CHANNEL_ID, message_id=character['message_id'])
            rarity_emoji = rarity_styles.get(character["rarity"], "")
            message = await context.bot.send_photo(
                chat_id=CHARA_CHANNEL_ID,
                photo=new_value,
                caption=(
                    f"✨ <b>{character['name']}</b> ✨\n"
                    f"🎌 <i>{character['anime']}</i>\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"{rarity_emoji} <b>{character['rarity']}</b>\n"
                    f"🆔 <b>ID:</b> #{character['id']}\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"📝 Updated by <a href='tg://user?id={update.effective_user.id}'>{update.effective_user.first_name}</a>"
                ),
                parse_mode='HTML'
            )
            character['message_id'] = message.message_id
            await collection.find_one_and_update({'id': args[0]}, {'$set': {'message_id': message.message_id}})
        else:
            
            rarity_emoji = rarity_styles.get(character["rarity"], "")
            
            # Create updated beautiful caption
            updated_caption = (
                f"✨ <b>{character['name']}</b> ✨\n"
                f"🎌 <i>{character['anime']}</i>\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"{rarity_emoji} <b>{character['rarity']}</b>\n"
                f"🆔 <b>ID:</b> #{character['id']}\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"📝 Updated by <a href='tg://user?id={update.effective_user.id}'>{update.effective_user.first_name}</a>"
            )
            
            await context.bot.edit_message_caption(
                chat_id=CHARA_CHANNEL_ID,
                message_id=character['message_id'],
                caption=updated_caption,
                parse_mode='HTML'
            )

        await update.message.reply_text('Updated Done in Database.... But sometimes it Takes Time to edit Caption in Your Channel..So wait..')
    except Exception as e:
        await update.message.reply_text(f'I guess did not added bot in channel.. or character uploaded Long time ago.. Or character not exits.. orr Wrong id')

UPLOAD_HANDLER = CommandHandler('upload', upload, block=False)
application.add_handler(UPLOAD_HANDLER)
DELETE_HANDLER = CommandHandler('delete', delete, block=False)
application.add_handler(DELETE_HANDLER)
SUMMON_HANDLER = CommandHandler('summon', summon, block=False)
application.add_handler(SUMMON_HANDLER)
FIND_HANDLER = CommandHandler('find', find, block=False)
application.add_handler(FIND_HANDLER)
UPDATE_HANDLER = CommandHandler('update', update, block=False)
application.add_handler(UPDATE_HANDLER)
