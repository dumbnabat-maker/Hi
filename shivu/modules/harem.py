from telegram import Update
from itertools import groupby
from collections import Counter, defaultdict
import math
from html import escape 
import random

from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from shivu import collection, user_collection, application, SUPPORT_CHAT, CHARA_CHANNEL_ID

async def sorts(update: Update, context: CallbackContext) -> None:
    """Set harem sorting preference - rarity or name"""
    if not update.effective_user or not update.message:
        return
        
    user_id = update.effective_user.id
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "🔧 <b>Harem Sorting</b>\n\n"
            "Set how you want your harem displayed:\n\n"
            "📝 <b>Available options:</b>\n"
            "• <code>/sorts rarity</code> - Sort by rarity\n"
            "• <code>/sorts name</code> - Sort by character name\n"
            "• <code>/sorts limited_time</code> - Show limited time cards first\n\n"
            "💡 Your current sorting will be remembered for future /harem displays!",
            parse_mode='HTML'
        )
        return
    
    sort_type = args[0].lower()
    
    if sort_type not in ['rarity', 'name', 'limited_time']:
        await update.message.reply_text(
            "❌ Invalid sort type!\n\n"
            "Available options:\n"
            "• <code>/sorts rarity</code>\n"
            "• <code>/sorts name</code>\n"
            "• <code>/sorts limited_time</code>",
            parse_mode='HTML'
        )
        return
    
    # Update user's sort preference
    await user_collection.update_one(
        {'id': user_id}, 
        {'$set': {'sort_preference': sort_type}}, 
        upsert=True
    )
    
    await update.message.reply_text(
        f"✅ Harem sorting set to <b>{sort_type}</b>!\n\n"
        f"Your /harem will now be sorted by {sort_type}. 📋",
        parse_mode='HTML'
    )


async def harem(update: Update, context: CallbackContext, page=0) -> None:
    if not update.effective_user:
        return
        
    user_id = update.effective_user.id

    user = await user_collection.find_one({'id': user_id})
    if not user:
        if update.message:
            await update.message.reply_text('You Have Not Guessed any Characters Yet..')
        elif update.callback_query:
            await update.callback_query.edit_message_text('You Have Not Guessed any Characters Yet..')
        return

    # Get user's sort preference
    sort_preference = user.get('sort_preference', 'anime')  # Default to anime (current behavior)
    
    if sort_preference == 'rarity':
        # Sort by rarity (rarest first) then by name
        rarity_order = ["Limited Edition", "Zenith", "Retro", "Mythic", "Legendary", "Epic", "Rare", "Uncommon", "Common"]
        characters = sorted(user['characters'], key=lambda x: (rarity_order.index(x.get('rarity', 'Common')), x['name']))
    elif sort_preference == 'name':
        # Sort by character name alphabetically
        characters = sorted(user['characters'], key=lambda x: x['name'])
    elif sort_preference == 'limited_time':
        # Sort by limited time cards first, then by rarity, then by name
        rarity_order = ["Limited Edition", "Zenith", "Retro", "Mythic", "Legendary", "Epic", "Rare", "Uncommon", "Common"]
        characters = sorted(user['characters'], key=lambda x: (
            0 if x.get('rarity') == 'Limited Edition' else 1,  # Limited Edition first
            rarity_order.index(x.get('rarity', 'Common')),
            x['name']
        ))
    else:
        # Default: sort by anime then ID (existing behavior)
        characters = sorted(user['characters'], key=lambda x: (x['anime'], x['id']))

    # Use Counter to properly count character occurrences regardless of sort order
    character_counts = Counter(character['id'] for character in user['characters'])

    
    unique_characters = list({character['id']: character for character in characters}.values())

    
    total_pages = math.ceil(len(unique_characters) / 15)  

    if page < 0 or page >= total_pages:
        page = 0  

    user_name = update.effective_user.first_name or "User"
    harem_message = f"<b>{escape(user_name)}'s Harem - Page {page+1}/{total_pages}</b>\n"

    
    current_characters = unique_characters[page*15:(page+1)*15]

    # Group characters by anime properly regardless of sort order
    current_grouped_characters = defaultdict(list)
    for character in current_characters:
        current_grouped_characters[character['anime']].append(character)

    for anime, characters in current_grouped_characters.items():
        # Get total count of anime characters in database
        anime_total = await collection.count_documents({"anime": anime})
        
        # Stylish anime header with count
        harem_message += f'\n✢ {anime} 「 {len(characters)}/{anime_total} 」\n'
        harem_message += '⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋\n'

        for character in characters:
            # Add rarity emoji to make it more beautiful
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
            count = character_counts[character['id']]
            
            # Random emojis for variety (like the examples showed [🏖], [👘], etc.)
            variety_emojis = ['🏖', '👘', '🎒', '🏀', '☃️', '🎮', '🌸', '🎭', '🎨', '🎪']
            variety_emoji = random.choice(variety_emojis)
            
            # Stylish character entry format
            harem_message += f'➥ {character["id"]}〔{rarity_emoji} 〕{character["name"]} [{variety_emoji}] x{count}\n'

        # Add separator after each anime section
        harem_message += '⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋⚋\n'


    total_count = len(user['characters'])
    
    keyboard = [
        [InlineKeyboardButton(f"See Collection ({total_count})", switch_inline_query_current_chat=f"collection.{user_id}")],
        [InlineKeyboardButton(f"📊 Database", url=f"https://t.me/c/{str(CHARA_CHANNEL_ID).replace('-100', '')}")]
    ]


    if total_pages > 1:
        
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"harem:{page-1}:{user_id}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"harem:{page+1}:{user_id}"))
        keyboard.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)

    if 'favorites' in user and user['favorites']:
        
        fav_character_id = user['favorites'][0]
        fav_character = next((c for c in user['characters'] if c['id'] == fav_character_id), None)

        if fav_character and 'img_url' in fav_character:
            if update.message:
                try:
                    from shivu import process_image_url
                    processed_url = await process_image_url(fav_character['img_url'])
                    await update.message.reply_photo(photo=processed_url, parse_mode='HTML', caption=harem_message, reply_markup=reply_markup)
                except Exception as e:
                    # If image fails, send text instead
                    await update.message.reply_text(harem_message, parse_mode='HTML', reply_markup=reply_markup)
            else:
                # For callback queries, update image and caption using media edit
                try:
                    from shivu import process_image_url
                    from telegram import InputMediaPhoto
                    processed_url = await process_image_url(fav_character['img_url'])
                    media = InputMediaPhoto(media=processed_url, caption=harem_message, parse_mode='HTML')
                    await update.callback_query.edit_message_media(media=media, reply_markup=reply_markup)
                    await update.callback_query.answer()
                except Exception:
                    # Fallback to just editing caption if media edit fails
                    try:
                        if update.callback_query and update.callback_query.message and update.callback_query.message.caption != harem_message:
                            await update.callback_query.edit_message_caption(caption=harem_message, reply_markup=reply_markup, parse_mode='HTML')
                        if update.callback_query:
                            await update.callback_query.answer()
                    except Exception:
                        if update.callback_query:
                            await update.callback_query.answer("Failed to update image")
        else:
            if update.message:
                await update.message.reply_text(harem_message, parse_mode='HTML', reply_markup=reply_markup)
            else:
                
                if update.callback_query and update.callback_query.message and update.callback_query.message.text != harem_message:
                    await update.callback_query.edit_message_text(harem_message, parse_mode='HTML', reply_markup=reply_markup)
    else:
        
        if user['characters']:
        
            random_character = random.choice(user['characters'])

            if 'img_url' in random_character:
                if update.message:
                    try:
                        from shivu import process_image_url
                        processed_url = await process_image_url(random_character['img_url'])
                        await update.message.reply_photo(photo=processed_url, parse_mode='HTML', caption=harem_message, reply_markup=reply_markup)
                    except Exception as e:
                        # If image fails, send text instead
                        await update.message.reply_text(harem_message, parse_mode='HTML', reply_markup=reply_markup)
                else:
                    # For callback queries, update image and caption using media edit
                    try:
                        from shivu import process_image_url
                        from telegram import InputMediaPhoto
                        processed_url = await process_image_url(random_character['img_url'])
                        media = InputMediaPhoto(media=processed_url, caption=harem_message, parse_mode='HTML')
                        await update.callback_query.edit_message_media(media=media, reply_markup=reply_markup)
                        await update.callback_query.answer()
                    except Exception:
                        # Fallback to just editing caption if media edit fails
                        try:
                            if update.callback_query and update.callback_query.message and update.callback_query.message.caption != harem_message:
                                await update.callback_query.edit_message_caption(caption=harem_message, reply_markup=reply_markup, parse_mode='HTML')
                            if update.callback_query:
                                await update.callback_query.answer()
                        except Exception:
                            if update.callback_query:
                                await update.callback_query.answer("Failed to update image")
            else:
                if update.message:
                    await update.message.reply_text(harem_message, parse_mode='HTML', reply_markup=reply_markup)
                else:
                
                    if update.callback_query and update.callback_query.message and update.callback_query.message.text != harem_message:
                        await update.callback_query.edit_message_text(harem_message, parse_mode='HTML', reply_markup=reply_markup)
        else:
            if update.message:
                await update.message.reply_text("Your List is Empty :)")


async def harem_callback(update: Update, context: CallbackContext) -> None:
    if not update.callback_query or not update.callback_query.data:
        return
        
    query = update.callback_query
    data = query.data

    data_parts = data.split(':')
    if len(data_parts) != 3:
        return
        
    _, page_str, user_id_str = data_parts

    try:
        page = int(page_str)
        user_id = int(user_id_str)
    except ValueError:
        return

    if query.from_user and query.from_user.id != user_id:
        await query.answer("its Not Your Harem", show_alert=True)
        return

    
    await harem(update, context, page)




application.add_handler(CommandHandler(["harem", "collection"], harem,block=False))
application.add_handler(CommandHandler("sorts", sorts, block=False))
harem_handler = CallbackQueryHandler(harem_callback, pattern='^harem', block=False)
application.add_handler(harem_handler)
    
