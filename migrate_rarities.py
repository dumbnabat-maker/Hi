#!/usr/bin/env python3
"""
Standalone script to migrate rarity values in MongoDB
Changes: "Celestial" -> "Retro" and "Arcane" -> "Zenith" 
"""
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def migrate_rarities():
    """Migrate old rarity names to new ones in the database"""
    
    # Get MongoDB URL from environment
    mongo_url = os.environ.get("MONGODB_URL")
    if not mongo_url:
        print("❌ Error: MONGODB_URL environment variable not found")
        return
    
    # Clean and validate MongoDB URL
    mongo_url = mongo_url.strip()
    if mongo_url.endswith(','):
        mongo_url = mongo_url.rstrip(',')
    if not mongo_url or mongo_url == ',':
        print("❌ Error: MONGODB_URL is empty or invalid")
        return
    
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(mongo_url)
        db = client['Character_catcher']
        collection = db['anime_characters_lol']
        user_collection = db["user_collection_lmaoooo"]
        
        print('🔄 Starting rarity migration...\n')
        print('Updating database to change:\n• Celestial → Retro\n• Arcane → Zenith\n')
        
        # Check current counts before migration
        celestial_before = await collection.count_documents({'rarity': 'Celestial'})
        arcane_before = await collection.count_documents({'rarity': 'Arcane'})
        retro_before = await collection.count_documents({'rarity': 'Retro'})
        zenith_before = await collection.count_documents({'rarity': 'Zenith'})
        
        print(f'📊 Before migration:')
        print(f'• Celestial: {celestial_before}')
        print(f'• Arcane: {arcane_before}')
        print(f'• Retro: {retro_before}')
        print(f'• Zenith: {zenith_before}\n')
        
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
        celestial_after = await collection.count_documents({'rarity': 'Celestial'})
        arcane_after = await collection.count_documents({'rarity': 'Arcane'})
        retro_after = await collection.count_documents({'rarity': 'Retro'})
        zenith_after = await collection.count_documents({'rarity': 'Zenith'})
        
        success_message = (
            f'✅ Migration Completed!\n\n'
            f'📊 Characters updated:\n'
            f'• Celestial → Retro: {result_celestial.modified_count}\n'
            f'• Arcane → Zenith: {result_arcane.modified_count}\n\n'
            f'👥 User collections updated:\n'
            f'• Celestial → Retro: {user_result_celestial.modified_count} users\n'
            f'• Arcane → Zenith: {user_result_arcane.modified_count} users\n\n'
            f'🔍 After migration:\n'
            f'• Retro: {retro_after}\n'
            f'• Zenith: {zenith_after}\n'
            f'• Old Celestial remaining: {celestial_after}\n'
            f'• Old Arcane remaining: {arcane_after}'
        )
        
        print(success_message)
        
        # Close connection
        client.close()
        
    except Exception as e:
        print(f'❌ Error during migration: {str(e)}')

if __name__ == "__main__":
    asyncio.run(migrate_rarities())