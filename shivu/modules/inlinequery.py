import re
import time
from html import escape
from cachetools import TTLCache
from pymongo import MongoClient, ASCENDING

from telegram import Update, InlineQueryResultPhoto
from telegram.ext import InlineQueryHandler, CallbackContext, CommandHandler 
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from shivu import user_collection, collection, application, db


# collection
db.characters.create_index([('id', ASCENDING)])
db.characters.create_index([('anime', ASCENDING)])
db.characters.create_index([('img_url', ASCENDING)])

# user_collection
db.user_collection.create_index([('characters.id', ASCENDING)])
db.user_collection.create_index([('characters.name', ASCENDING)])
db.user_collection.create_index([('characters.img_url', ASCENDING)])

all_characters_cache = TTLCache(maxsize=10000, ttl=36000)
user_collection_cache = TTLCache(maxsize=10000, ttl=60)

async def inlinequery(update: Update, context: CallbackContext) -> None:
    if not update.inline_query:
        return
        
    query = update.inline_query.query.strip()
    offset = int(update.inline_query.offset) if update.inline_query.offset else 0

    if query.startswith('collection.'):
        # Handle user collection queries
        user_id, *search_terms = query.split(' ')[0].split('.')[1], ' '.join(query.split(' ')[1:])
        if user_id.isdigit():
            if user_id in user_collection_cache:
                user = user_collection_cache[user_id]
            else:
                user = await user_collection.find_one({'id': int(user_id)})
                user_collection_cache[user_id] = user

            if user:
                all_characters = list({v['id']:v for v in user['characters']}.values())
                if search_terms:
                    regex = re.compile(' '.join(search_terms), re.IGNORECASE)
                    all_characters = [character for character in all_characters if regex.search(character['name']) or regex.search(character['anime'])]
            else:
                all_characters = []
        else:
            all_characters = []
    else:
        # Handle general character search
        if query:
            # Search for specific characters by name or anime
            regex = re.compile(query, re.IGNORECASE)
            all_characters = list(await collection.find({"$or": [{"name": regex}, {"anime": regex}]}).to_list(length=None))
        else:
            # Empty query - show popular/random characters like Yandex image search
            if 'all_characters' in all_characters_cache:
                all_characters = all_characters_cache['all_characters']
            else:
                # Get a diverse selection of characters (limit to prevent too much load)
                all_characters = list(await collection.find({}).limit(200).to_list(length=None))
                all_characters_cache['all_characters'] = all_characters

    # Limit characters per page for better performance
    characters = all_characters[offset:offset+50]
    if len(all_characters) > offset + 50:
        next_offset = str(offset + 50)
    else:
        next_offset = ""

    results = []
    for character in characters:
        try:
            # Optimized to reduce database queries for empty query (showing popular characters)
            if query.startswith('collection.') and user:
                # For user collections, show detailed stats
                global_count = await user_collection.count_documents({'characters.id': character['id']})
                anime_characters = await collection.count_documents({'anime': character['anime']})
                user_character_count = sum(c['id'] == character['id'] for c in user['characters'])
                user_anime_characters = sum(c['anime'] == character['anime'] for c in user['characters'])
                caption = f"<b> Look At <a href='tg://user?id={user['id']}'>{(escape(user.get('first_name', user['id'])))}</a>'s Character</b>\n\n🌸: <b>{character['name']} (x{user_character_count})</b>\n🏖️: <b>{character['anime']} ({user_anime_characters}/{anime_characters})</b>\n<b>{character['rarity']}</b>\n\n<b>🆔️:</b> {character['id']}"
            elif query:
                # For search queries, show detailed stats
                global_count = await user_collection.count_documents({'characters.id': character['id']})
                caption = f"<b>Look At This Character !!</b>\n\n🌸:<b> {character['name']}</b>\n🏖️: <b>{character['anime']}</b>\n<b>{character['rarity']}</b>\n🆔️: <b>{character['id']}</b>\n\n<b>Globally Guessed {global_count} Times...</b>"
            else:
                # For empty query (like Yandex), show simplified info for better performance
                caption = f"<b>{character['name']}</b>\n🏖️: <b>{character['anime']}</b>\n✨ <b>{character['rarity']}</b>\n🆔️: <b>{character['id']}</b>"
            
            results.append(
                InlineQueryResultPhoto(
                    thumbnail_url=character['img_url'],
                    id=f"{character['id']}_{time.time()}",
                    photo_url=character['img_url'],
                    caption=caption,
                    parse_mode='HTML'
                )
            )
        except Exception as e:
            # Skip problematic characters to prevent the entire query from failing
            continue

    await update.inline_query.answer(results, next_offset=next_offset, cache_time=5)

application.add_handler(InlineQueryHandler(inlinequery, block=False))
