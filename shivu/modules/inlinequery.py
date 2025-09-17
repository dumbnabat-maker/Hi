import re
import time
from html import escape
from cachetools import TTLCache
from pymongo import MongoClient, ASCENDING

from telegram import Update, InlineQueryResultPhoto
from telegram.ext import InlineQueryHandler, CallbackContext, CommandHandler 
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from shivu import user_collection, collection, application, db, LOGGER


# Database indexes will be created automatically by MongoDB when needed
# Removed manual index creation to avoid async/await issues

all_characters_cache = TTLCache(maxsize=10000, ttl=36000)
user_collection_cache = TTLCache(maxsize=10000, ttl=60)

async def inlinequery(update: Update, context: CallbackContext) -> None:
    if not update.inline_query:
        return
        
    query = update.inline_query.query.strip()
    offset = int(update.inline_query.offset) if update.inline_query.offset else 0
    
    # Debug logging to help troubleshoot
    LOGGER.info(f"Inline query received: '{query}', offset: {offset}")

    if query.startswith('collection.'):
        # Handle user collection queries
        user = None  # Initialize to prevent NameError
        all_characters = []
        
        try:
            # Parse the query: "collection.user_id optional_search_terms"
            parts = query.split(' ', 1)  # Split into max 2 parts
            collection_part = parts[0]  # "collection.user_id"
            search_terms = parts[1] if len(parts) > 1 else ""  # Optional search terms
            
            # Extract user_id from "collection.user_id"
            if '.' in collection_part:
                user_id = collection_part.split('.')[1]
                
                if user_id.isdigit():
                    user_id_int = int(user_id)
                    
                    # Get user from cache or database
                    if user_id in user_collection_cache:
                        user = user_collection_cache[user_id]
                    else:
                        user = await user_collection.find_one({'id': user_id_int})
                        if user:
                            user_collection_cache[user_id] = user

                    if user and 'characters' in user:
                        # Get unique characters by ID
                        all_characters = list({v['id']:v for v in user['characters']}.values())
                        
                        # Apply search filter if provided
                        if search_terms.strip():
                            regex = re.compile(search_terms.strip(), re.IGNORECASE)
                            all_characters = [character for character in all_characters 
                                           if regex.search(character.get('name', '')) or 
                                              regex.search(character.get('anime', ''))]
                        
                        LOGGER.info(f"Found {len(all_characters)} characters for user {user_id}")
                    else:
                        all_characters = []
                        LOGGER.info(f"No user found or no characters for user {user_id}")
                else:
                    all_characters = []
                    LOGGER.info(f"Invalid user ID format: {user_id}")
            else:
                all_characters = []
                LOGGER.info(f"Invalid collection query format: {query}")
        except Exception as e:
            LOGGER.error(f"Error processing collection query '{query}': {str(e)}")
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
            
            # Process image URL for compatibility (handles JFIF and other formats)
            from shivu import process_image_url
            processed_url = await process_image_url(character['img_url'])
            
            results.append(
                InlineQueryResultPhoto(
                    thumbnail_url=processed_url,
                    id=f"{character['id']}_{time.time()}",
                    photo_url=processed_url,
                    caption=caption,
                    parse_mode='HTML'
                )
            )
        except Exception as e:
            # Skip problematic characters to prevent the entire query from failing
            continue

    await update.inline_query.answer(results, next_offset=next_offset, cache_time=5)

application.add_handler(InlineQueryHandler(inlinequery, block=False))
