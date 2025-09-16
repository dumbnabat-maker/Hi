from telegram import Update
from itertools import groupby
import math
from html import escape 
import random

from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from shivu import collection, user_collection, application, SUPPORT_CHAT

async def sorts(update: Update, context: CallbackContext) -> None:
    """Set harem sorting preference - rarity or name"""
    user_id = update.effective_user.id
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "🔧 <b>Harem Sorting</b>\n\n"
            "Set how you want your harem displayed:\n\n"
            "📝 <b>Available options:</b>\n"
            "• <code>/sorts rarity</code> - Sort by rarity\n"
            "• <code>/sorts name</code> - Sort by character name\n\n"
            "💡 Your current sorting will be remembered for future /harem displays!",
            parse_mode='HTML'
        )
        return
    
    sort_type = args[0].lower()
    
    if sort_type not in ['rarity', 'name']:
        await update.message.reply_text(
            "❌ Invalid sort type!\n\n"
            "Available options:\n"
            "• <code>/sorts rarity</code>\n"
            "• <code>/sorts name</code>",
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
    user_id = update.effective_user.id

    user = await user_collection.find_one({'id': user_id})
    if not user:
        if update.message:
            await update.message.reply_text('You Have Not Guessed any Characters Yet..')
        else:
            await update.callback_query.edit_message_text('You Have Not Guessed any Characters Yet..')
        return

    # Get user's sort preference
    sort_preference = user.get('sort_preference', 'anime')  # Default to anime (current behavior)
    
    if sort_preference == 'rarity':
        # Sort by rarity (rarest first) then by name
        rarity_order = ["Limited Edition", "Arcane", "Celestial", "Mythic", "Legendary", "Epic", "Rare", "Uncommon", "Common"]
        characters = sorted(user['characters'], key=lambda x: (rarity_order.index(x.get('rarity', 'Common')), x['name']))
    elif sort_preference == 'name':
        # Sort by character name alphabetically
        characters = sorted(user['characters'], key=lambda x: x['name'])
    else:
        # Default: sort by anime then ID (existing behavior)
        characters = sorted(user['characters'], key=lambda x: (x['anime'], x['id']))

    character_counts = {k: len(list(v)) for k, v in groupby(characters, key=lambda x: x['id'])}

    
    unique_characters = list({character['id']: character for character in characters}.values())

    
    total_pages = math.ceil(len(unique_characters) / 15)  

    if page < 0 or page >= total_pages:
        page = 0  

    harem_message = f"<b>{escape(update.effective_user.first_name)}'s Harem - Page {page+1}/{total_pages}</b>\n"

    
    current_characters = unique_characters[page*15:(page+1)*15]

    
    current_grouped_characters = {k: list(v) for k, v in groupby(current_characters, key=lambda x: x['anime'])}

    for anime, characters in current_grouped_characters.items():
        harem_message += f'\n<b>{anime} {len(characters)}/{await collection.count_documents({"anime": anime})}</b>\n'

        for character in characters:
            
            count = character_counts[character['id']]  
            harem_message += f'{character["id"]} {character["name"]} ×{count}\n'


    total_count = len(user['characters'])
    
    keyboard = [
        [InlineKeyboardButton(f"See Collection ({total_count})", switch_inline_query_current_chat=f"collection.{user_id}")],
        [InlineKeyboardButton(f"📊 Database", url=f"https://t.me/waifuscollectorbot?start={user_id}")]
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
                from shivu import process_image_url
                processed_url = await process_image_url(fav_character['img_url'])
                await update.message.reply_photo(photo=processed_url, parse_mode='HTML', caption=harem_message, reply_markup=reply_markup)
            else:
                
                if update.callback_query.message.caption != harem_message:
                    await update.callback_query.edit_message_caption(caption=harem_message, reply_markup=reply_markup, parse_mode='HTML')
        else:
            if update.message:
                await update.message.reply_text(harem_message, parse_mode='HTML', reply_markup=reply_markup)
            else:
                
                if update.callback_query.message.text != harem_message:
                    await update.callback_query.edit_message_text(harem_message, parse_mode='HTML', reply_markup=reply_markup)
    else:
        
        if user['characters']:
        
            random_character = random.choice(user['characters'])

            if 'img_url' in random_character:
                if update.message:
                    await update.message.reply_photo(photo=random_character['img_url'], parse_mode='HTML', caption=harem_message, reply_markup=reply_markup)
                else:
                    
                    if update.callback_query.message.caption != harem_message:
                        await update.callback_query.edit_message_caption(caption=harem_message, reply_markup=reply_markup, parse_mode='HTML')
            else:
                if update.message:
                    await update.message.reply_text(harem_message, parse_mode='HTML', reply_markup=reply_markup)
                else:
                
                    if update.callback_query.message.text != harem_message:
                        await update.callback_query.edit_message_text(harem_message, parse_mode='HTML', reply_markup=reply_markup)
        else:
            if update.message:
                await update.message.reply_text("Your List is Empty :)")


async def harem_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    data = query.data


    _, page, user_id = data.split(':')


    page = int(page)
    user_id = int(user_id)

    
    if query.from_user.id != user_id:
        await query.answer("its Not Your Harem", show_alert=True)
        return

    
    await harem(update, context, page)




application.add_handler(CommandHandler(["harem", "collection"], harem,block=False))
application.add_handler(CommandHandler("sorts", sorts, block=False))
harem_handler = CallbackQueryHandler(harem_callback, pattern='^harem', block=False)
application.add_handler(harem_handler)
    
