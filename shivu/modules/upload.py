import urllib.request
import urllib.parse
import urllib.error
import re
from pymongo import ReturnDocument

from telegram import Update
from telegram.ext import CommandHandler, CallbackContext

from shivu import application, sudo_users, uploading_users, collection, db, CHARA_CHANNEL_ID, SUPPORT_CHAT, user_collection

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

✅ Supported: Discord CDN links, direct image/video URLs (including MP4), and other standard hosting services"""


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
            # Check if it's an image or video by checking content type or URL
            content_type = response.headers.get('Content-Type', '')
            if content_type.startswith('image/') or content_type.startswith('video/'):
                return True, f"Valid {'image' if content_type.startswith('image/') else 'video'} URL"
            elif any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.mp4', '.mov', '.avi', '.mkv']):
                return True, "Valid media URL"
            else:
                return False, "URL does not appear to be an image or video"
                
    except urllib.error.HTTPError as e:
        return False, f"HTTP Error: {e.code}"
    except urllib.error.URLError as e:
        return False, f"URL Error: {str(e)}"
    except Exception as e:
        return False, f"Validation Error: {str(e)}"



async def can_upload(user_id):
    """Check if user has upload permissions (sudo_users, uploading_users env var, or dynamic uploading_users)"""
    user_id_str = str(user_id)
    
    # Check if user is in sudo_users or env uploading_users
    if user_id_str in sudo_users or user_id_str in uploading_users:
        return True
    
    # Check if user is in dynamic uploading_users collection
    dynamic_uploaders_collection = db['dynamic_uploading_users']
    uploader = await dynamic_uploaders_collection.find_one({'user_id': user_id_str})
    return uploader is not None

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
        
    if not await can_upload(update.effective_user.id):
        await update.message.reply_text('Ask My Owner or authorized uploader...')
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
        
        # Check if it's a video based on validation message or URL extension
        is_video = 'video' in validation_message.lower() or any(ext in args[0].lower() for ext in ['.mp4', '.mov', '.avi', '.mkv'])
        
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
            
            if is_video:
                message = await context.bot.send_video(
                    chat_id=CHARA_CHANNEL_ID,
                    video=processed_url,
                    caption=caption,
                    parse_mode='HTML'
                )
            else:
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
            # Also remove from all user collections
            from shivu import user_collection
            user_result = await user_collection.update_many(
                {'characters.id': args[0]},
                {'$pull': {'characters': {'id': args[0]}}}
            )
            
            await context.bot.delete_message(chat_id=CHARA_CHANNEL_ID, message_id=character['message_id'])
            await update.message.reply_text(f'✅ Character deleted from database and removed from {user_result.modified_count} user collections.')
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


async def remove_character_from_user(update: Update, context: CallbackContext) -> None:
    """Remove a specific character from a user's harem - Admin only"""
    if not update.effective_user or not update.message:
        return
        
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('Ask My Owner to use this Command...')
        return

    try:
        args = context.args
        if not args or len(args) != 2:
            await update.message.reply_text('❌ Incorrect format!\n\nUsage: /remove <character_id> <user_id>\nExample: /remove 123 987654321')
            return

        character_id = args[0]
        user_id_str = args[1]
        
        try:
            user_id = int(user_id_str)
        except ValueError:
            await update.message.reply_text('❌ Invalid user ID format!')
            return

        # Find the character first to show details
        character = await collection.find_one({'id': character_id})
        if not character:
            await update.message.reply_text(f'❌ Character with ID #{character_id} not found in database!')
            return

        # Find the user
        from shivu import user_collection
        user = await user_collection.find_one({'id': user_id})
        if not user:
            await update.message.reply_text(f'❌ User with ID {user_id} not found!')
            return

        # Check if user has this character
        user_character_count = sum(1 for c in user.get('characters', []) if c.get('id') == character_id)
        if user_character_count == 0:
            await update.message.reply_text(f'❌ User does not have character #{character_id} ({character["name"]}) in their harem!')
            return

        # Remove one instance of the character
        # Remove only one instance of the character (two-step process)
        # First, unset the first matching character to null
        await user_collection.update_one(
            {'id': user_id, 'characters.id': character_id},
            {'$unset': {'characters.$': 1}}
        )
        # Then pull the null values
        result = await user_collection.update_one(
            {'id': user_id},
            {'$pull': {'characters': None}}
        )

        if result.modified_count > 0:
            remaining_count = user_character_count - 1
            user_name = user.get('first_name', 'User')
            await update.message.reply_text(
                f'✅ <b>Character Removed!</b>\n\n'
                f'🗑️ Removed: {character["name"]} (#{character_id})\n'
                f'👤 From: <a href="tg://user?id={user_id}">{user_name}</a>\n'
                f'📊 Remaining: {remaining_count} copies',
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text('❌ Failed to remove character from user harem!')
            
    except Exception as e:
        await update.message.reply_text(f'❌ Error removing character: {str(e)}')


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
        rarity_emoji = rarity_styles.get(character.get('rarity', ''), "✨")
        
        # Find global catchers - users who have this character
        global_catchers = []
        total_caught = 0
        
        users_with_character = user_collection.find({"characters.id": character_id})
        async for user in users_with_character:
            user_id = user['id']
            character_count = sum(1 for c in user.get('characters', []) if c.get('id') == character_id)
            if character_count > 0:
                user_name = user.get('first_name', f'User{user_id}')
                global_catchers.append({
                    'user_id': user_id,
                    'name': user_name,
                    'count': character_count
                })
                total_caught += character_count
        
        # Sort by count and get top 10
        global_catchers.sort(key=lambda x: x['count'], reverse=True)
        top_10 = global_catchers[:10]
        
        # Create new format caption
        caption = f"OwO! Look out this character!\n\n"
        caption += f"{character['anime']}\n"
        caption += f"{character['id']}: {character['name']}\n"
        caption += f"({rarity_emoji} 𝙍𝘼𝙍𝙄𝙏𝙔: {character.get('rarity', 'Unknown').lower()})\n\n"
        caption += f"⦿ ɢʟᴏʙᴀʟʟʏ ᴄᴀᴜɢʜᴛ : {total_caught} ᴛɪᴍᴇs\n\n"
        caption += "🏆 ᴛᴏᴘ 10 ɢʟᴏʙᴀʟ ᴄᴀᴛᴄʜᴇʀs\n"
        
        for i in range(10):
            if i < len(top_10):
                catcher = top_10[i]
                caption += f"{i+1}. {catcher['name']} → {catcher['count']}\n"
            elif i == 4:  # Add the special invisible line at position 5
                caption += "5. ⁭⁯⁯⁭⁯⁭⁯⁯⁭⁯⁭⁯⁯⁭⁯⁭⁯⁯⁭⁯⁭⁯⁯⁭⁯⁭⁯⁯⁭⁯⁭⁯⁯⁭⁯⁭⁯⁯⁭⁯⁭⁯⁯⁭⁯⁭⁯⁯⁭⁯⁭⁯⁯⁭⁯⁭⁯⁯⁭⁯⁭⁯⁯⁭\n"
            else:
                caption += f"{i+1}. \n"
        
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

        # Update user collections when character properties change
        from shivu import user_collection
        if args[1] in ['name', 'anime', 'rarity']:
            await user_collection.update_many(
                {'characters.id': args[0]},
                {'$set': {f'characters.$[elem].{args[1]}': new_value}},
                array_filters=[{'elem.id': args[0]}]
            )

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
            # Update character dict with new value for accurate caption
            character[args[1]] = new_value
            
            rarity_emoji = rarity_styles.get(character["rarity"], "")
            
            # Create updated beautiful caption with fresh values
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


async def migrate_rarities(update: Update, context: CallbackContext) -> None:
    """Migrate old rarity names to new ones in the database - Admin only"""
    if not update.effective_user or not update.message:
        return
        
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('You do not have permission to use this command.')
        return

    try:
        await update.message.reply_text('🔄 Starting rarity migration...\n\nUpdating database to change:\n• Celestial → Retro\n• Arcane → Zenith')
        
        # Update main character collection
        result_celestial = await collection.update_many(
            {'rarity': 'Celestial'},
            {'$set': {'rarity': 'Retro'}}
        )
        
        result_arcane = await collection.update_many(
            {'rarity': 'Arcane'}, 
            {'$set': {'rarity': 'Zenith'}}
        )
        
        # Update user collections
        from shivu import user_collection
        
        user_result_celestial = await user_collection.update_many(
            {'characters.rarity': 'Celestial'},
            {'$set': {'characters.$[elem].rarity': 'Retro'}},
            array_filters=[{'elem.rarity': 'Celestial'}]
        )
        
        user_result_arcane = await user_collection.update_many(
            {'characters.rarity': 'Arcane'},
            {'$set': {'characters.$[elem].rarity': 'Zenith'}},
            array_filters=[{'elem.rarity': 'Arcane'}]
        )
        
        # Verify changes
        celestial_count = await collection.count_documents({'rarity': 'Celestial'})
        arcane_count = await collection.count_documents({'rarity': 'Arcane'})
        retro_count = await collection.count_documents({'rarity': 'Retro'})
        zenith_count = await collection.count_documents({'rarity': 'Zenith'})
        
        success_message = (
            f'✅ <b>Migration Completed!</b>\n\n'
            f'📊 <b>Characters updated:</b>\n'
            f'• Celestial → Retro: {result_celestial.modified_count}\n'
            f'• Arcane → Zenith: {result_arcane.modified_count}\n\n'
            f'👥 <b>User collections updated:</b>\n'
            f'• Celestial → Retro: {user_result_celestial.modified_count} users\n'
            f'• Arcane → Zenith: {user_result_arcane.modified_count} users\n\n'
            f'🔍 <b>Current counts:</b>\n'
            f'• Retro: {retro_count}\n'
            f'• Zenith: {zenith_count}\n'
            f'• Old Celestial remaining: {celestial_count}\n'
            f'• Old Arcane remaining: {arcane_count}'
        )
        
        await update.message.reply_text(success_message, parse_mode='HTML')
        
    except Exception as e:
        await update.message.reply_text(f'❌ Error during migration: {str(e)}')


async def adduploader(update: Update, context: CallbackContext) -> None:
    """Add a user to the uploading users list (owners only)"""
    if not update.effective_user or not update.message:
        return
    
    # Check if user is an owner
    OWNERS = ["8376223999", "6702213812"]
    if str(update.effective_user.id) not in OWNERS:
        await update.message.reply_text('🚫 Only owners can use this command.')
        return
    
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            '📝 **Add Uploader Usage:**\n\n'
            '`/adduploader [user_id]`\n\n'
            '**Example:** `/adduploader 123456789`\n\n'
            'This will give the user upload permissions.',
            parse_mode='Markdown'
        )
        return
    
    try:
        user_id_to_add = context.args[0]
        
        # Validate user_id is numeric
        if not user_id_to_add.isdigit():
            await update.message.reply_text('❌ Invalid user ID! Please provide a numeric user ID.')
            return
        
        # Check if already an uploader
        dynamic_uploaders_collection = db['dynamic_uploading_users']
        existing = await dynamic_uploaders_collection.find_one({'user_id': user_id_to_add})
        
        if existing:
            await update.message.reply_text(f'⚠️ User `{user_id_to_add}` is already an uploader!')
            return
        
        # Check if already sudo user
        if user_id_to_add in sudo_users:
            await update.message.reply_text(f'⚠️ User `{user_id_to_add}` is already a sudo user (has all permissions)!')
            return
        
        # Add to uploaders collection
        await dynamic_uploaders_collection.insert_one({
            'user_id': user_id_to_add,
            'added_by': update.effective_user.id,
            'added_by_username': update.effective_user.username or update.effective_user.first_name,
            'added_at': update.message.date
        })
        
        await update.message.reply_text(
            f'✅ **Uploader Added!**\n\n'
            f'👤 **User ID:** `{user_id_to_add}`\n'
            f'🔑 **Permissions:** Upload characters only\n'
            f'👨‍💼 **Added by:** {update.effective_user.first_name}\n\n'
            f'The user can now use the `/upload` command.',
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await update.message.reply_text(f'❌ Error adding uploader: {str(e)}')


async def removeuploader(update: Update, context: CallbackContext) -> None:
    """Remove a user from the uploading users list (owners only)"""
    if not update.effective_user or not update.message:
        return
    
    # Check if user is an owner
    OWNERS = ["8376223999", "6702213812"]
    if str(update.effective_user.id) not in OWNERS:
        await update.message.reply_text('🚫 Only owners can use this command.')
        return
    
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            '📝 **Remove Uploader Usage:**\n\n'
            '`/removeuploader [user_id]`\n\n'
            '**Example:** `/removeuploader 123456789`\n\n'
            'This will remove the user\'s upload permissions.',
            parse_mode='Markdown'
        )
        return
    
    try:
        user_id_to_remove = context.args[0]
        
        # Validate user_id is numeric
        if not user_id_to_remove.isdigit():
            await update.message.reply_text('❌ Invalid user ID! Please provide a numeric user ID.')
            return
        
        # Check if user is in uploaders collection
        dynamic_uploaders_collection = db['dynamic_uploading_users']
        uploader = await dynamic_uploaders_collection.find_one({'user_id': user_id_to_remove})
        
        if not uploader:
            await update.message.reply_text(f'❌ User `{user_id_to_remove}` is not currently an uploader!')
            return
        
        # Remove from uploaders collection
        await dynamic_uploaders_collection.delete_one({'user_id': user_id_to_remove})
        
        await update.message.reply_text(
            f'✅ **Uploader Removed!**\n\n'
            f'👤 **User ID:** `{user_id_to_remove}`\n'
            f'❌ **Permissions:** Upload access revoked\n'
            f'👨‍💼 **Removed by:** {update.effective_user.first_name}\n\n'
            f'The user can no longer use the `/upload` command.',
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await update.message.reply_text(f'❌ Error removing uploader: {str(e)}')


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
EDIT_HANDLER = CommandHandler('edit', update, block=False)
application.add_handler(EDIT_HANDLER)
REMOVE_HANDLER = CommandHandler('remove', remove_character_from_user, block=False)
application.add_handler(REMOVE_HANDLER)
MIGRATE_HANDLER = CommandHandler('migrate_rarities', migrate_rarities, block=False)
application.add_handler(MIGRATE_HANDLER)
ADDUPLOADER_HANDLER = CommandHandler('adduploader', adduploader, block=False)
application.add_handler(ADDUPLOADER_HANDLER)
REMOVEUPLOADER_HANDLER = CommandHandler('removeuploader', removeuploader, block=False)
application.add_handler(REMOVEUPLOADER_HANDLER)
