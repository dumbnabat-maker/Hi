import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def check_character():
    """Check character ID 1069"""
    
    # Connect to MongoDB
    mongo_url = os.environ.get('MONGODB_URL', '')
    if not mongo_url:
        print("❌ MONGODB_URL environment variable not set")
        return
    
    client = AsyncIOMotorClient(mongo_url)
    db = client['Character_catcher']
    collection = db['anime_characters_lol']
    
    # Find character 1069
    char = await collection.find_one({'id': '1069'})
    
    if not char:
        print("❌ Character ID 1069 not found in database")
    else:
        print("\n📋 Character ID 1069:")
        print("=" * 80)
        print(f"Name: {char.get('name')}")
        print(f"Anime: {char.get('anime')}")
        print(f"Rarity: {char.get('rarity')}")
        print(f"URL: {char.get('img_url')}")
        print("=" * 80)
        
        # Check URL characteristics
        url = char.get('img_url', '')
        print(f"\n🔍 URL Analysis:")
        print(f"   Length: {len(url)}")
        print(f"   Has .mp4: {'.mp4' in url.lower()}")
        print(f"   Has .mov: {'.mov' in url.lower()}")
        print(f"   Has video extensions: {any(ext in url.lower() for ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv'])}")
        print(f"   Has query params: {'?' in url}")
        print(f"   Domain: {url.split('/')[2] if len(url.split('/')) > 2 else 'unknown'}")
        
        # Test is_video_url function
        def is_video_url(url):
            if not url:
                return False
            return any(ext in url.lower() for ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv'])
        
        print(f"\n❓ Current is_video_url() result: {is_video_url(url)}")
        print("\n⚠️  This URL has NO file extension, so it's NOT detected as a video!")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_character())
