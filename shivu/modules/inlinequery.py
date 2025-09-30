import re
import time
from html import escape
from cachetools import TTLCache
from pymongo import MongoClient, ASCENDING

from telegram import Update, InlineQueryResultPhoto, InlineQueryResultVideo
from telegram.ext import InlineQueryHandler, CallbackContext, CommandHandler 
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from shivu import user_collection, collection, application, db, LOGGER

def is_video_url(url):
    """Check if a URL points to a video file"""
    if not url:
        return False
    return any(ext in url.lower() for ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv'])

# Rarity emojis configuration (updated to match latest rarities)
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
            # Get rarity emoji for consistent display
            rarity_emoji = rarity_emojis.get(character.get('rarity', 'Common'), "✨")
            
            # Get enhanced statistics
            global_count = await user_collection.count_documents({'characters.id': character['id']})
            
            # Optimized display with proper rarity emojis and enhanced styling
            if query.startswith('collection.') and user:
                # For user collections, show detailed stats with owner info
                anime_characters = await collection.count_documents({'anime': character['anime']})
                user_character_count = sum(c['id'] == character['id'] for c in user['characters'])
                user_anime_characters = sum(c['anime'] == character['anime'] for c in user['characters'])
                
                # Get top 5 users who have this character
                top_users = await user_collection.find(
                    {'characters.id': character['id']}, 
                    {'first_name': 1, 'characters': 1}
                ).limit(5).to_list(length=5)
                user_list = ", ".join([f"{user.get('first_name', 'User')} (x{sum(1 for c in user.get('characters', []) if c['id'] == character['id'])})" for user in top_users])
                
                caption = (
                    f"OwO! Check out this waifu!\n\n"
                    f"{character['anime']}\n"
                    f"{character['id']}: {character['name']} \n"
                    f"({rarity_emoji}𝙍𝘼𝙍𝙄𝙏𝙔:  {character.get('rarity', 'Unknown').lower()})"
                )
            elif query:
                # For search queries, show detailed global stats
                # Get top 3 users who have this character for display
                top_users = await user_collection.find(
                    {'characters.id': character['id']}, 
                    {'first_name': 1, 'characters': 1}
                ).limit(3).to_list(length=3)
                user_list = ", ".join([f"{user.get('first_name', 'User')} (x{sum(1 for c in user.get('characters', []) if c['id'] == character['id'])})" for user in top_users])
                
                caption = (
                    f"OwO! Check out this waifu!\n\n"
                    f"{character['anime']}\n"
                    f"{character['id']}: {character['name']} \n"
                    f"({rarity_emoji}𝙍𝘼𝙍𝙄𝙏𝙔:  {character.get('rarity', 'Unknown').lower()})"
                )
            else:
                # For empty query, show simplified but styled info
                caption = (
                    f"OwO! Check out this waifu!\n\n"
                    f"{character['anime']}\n"
                    f"{character['id']}: {character['name']} \n"
                    f"({rarity_emoji}𝙍𝘼𝙍𝙄𝙏𝙔:  {character.get('rarity', 'Unknown').lower()})"
                )
            
            # Process image URL for compatibility (handles JFIF and other formats)
            from shivu import process_image_url
            processed_url = await process_image_url(character['img_url'])
            
            # Check if it's a video and use appropriate result type
            if is_video_url(character['img_url']):
                # Determine mime type based on file extension
                if '.webm' in character['img_url'].lower():
                    mime_type = 'video/webm'
                elif '.mov' in character['img_url'].lower():
                    mime_type = 'video/quicktime'
                elif '.avi' in character['img_url'].lower():
                    mime_type = 'video/x-msvideo'
                elif '.mkv' in character['img_url'].lower():
                    mime_type = 'video/x-matroska'
                elif '.flv' in character['img_url'].lower():
                    mime_type = 'video/x-flv'
                else:
                    mime_type = 'video/mp4'
                
                # Use a placeholder thumbnail (must be JPEG for Telegram API)
                placeholder_thumbnail = 'https://via.placeholder.com/320x180.jpg'
                
                results.append(
                    InlineQueryResultVideo(
                        id=f"{character['id']}_{time.time()}",
                        video_url=processed_url,
                        mime_type=mime_type,
                        thumbnail_url=placeholder_thumbnail,
                        title=f"{character['name']} - {character['anime']}",
                        caption=caption
                    )
                )
            else:
                results.append(
                    InlineQueryResultPhoto(
                        thumbnail_url=processed_url,
                        id=f"{character['id']}_{time.time()}",
                        photo_url=processed_url,
                        caption=caption
                    )
                )
        except Exception as e:
            # Skip problematic characters to prevent the entire query from failing
            continue

    await update.inline_query.answer(results, next_offset=next_offset, cache_time=5)

application.add_handler(InlineQueryHandler(inlinequery, block=False))
