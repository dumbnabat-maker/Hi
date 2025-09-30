import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def check_video_urls():
    """Check what video URLs are stored in the database"""
    
    # Connect to MongoDB
    mongo_url = os.environ.get('MONGODB_URL', '')
    if not mongo_url:
        print("❌ MONGODB_URL environment variable not set")
        return
    
    client = AsyncIOMotorClient(mongo_url)
    db = client['Character_catcher']
    collection = db['anime_characters_lol']
    
    # Define is_video_url function
    def is_video_url(url):
        """Check if a URL points to a video file"""
        if not url:
            return False
        return any(ext in url.lower() for ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv'])
    
    # Get all characters
    all_characters = await collection.find({}).to_list(length=None)
    
    print(f"\n📊 Total characters in database: {len(all_characters)}")
    print("=" * 80)
    
    # Check for video URLs
    video_characters = []
    discord_videos = []
    non_discord_videos = []
    
    for char in all_characters:
        img_url = char.get('img_url', '')
        if is_video_url(img_url):
            video_characters.append(char)
            
            # Check if it's a Discord CDN URL
            is_discord = any(host in img_url.lower() for host in [
                'cdn.discordapp.com',
                'media.discordapp.net',
                'attachments.discordapp.net',
                'cdn.discord.com',
                'media.discord.com'
            ])
            
            if is_discord:
                discord_videos.append(char)
            else:
                non_discord_videos.append(char)
    
    print(f"\n🎬 Total video characters: {len(video_characters)}")
    print(f"   - Discord CDN videos: {len(discord_videos)}")
    print(f"   - Non-Discord videos: {len(non_discord_videos)}")
    print("=" * 80)
    
    if non_discord_videos:
        print(f"\n⚠️  NON-DISCORD VIDEO CHARACTERS:")
        print("=" * 80)
        for i, char in enumerate(non_discord_videos[:10], 1):  # Show first 10
            print(f"\n{i}. ID: {char.get('id')}")
            print(f"   Name: {char.get('name')}")
            print(f"   Anime: {char.get('anime')}")
            print(f"   Rarity: {char.get('rarity')}")
            print(f"   URL: {char.get('img_url')}")
            
            # Check URL characteristics
            url = char.get('img_url', '')
            print(f"   URL length: {len(url)}")
            print(f"   Has query params: {'?' in url}")
            print(f"   Extension detected: {[ext for ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv'] if ext in url.lower()]}")
        
        if len(non_discord_videos) > 10:
            print(f"\n... and {len(non_discord_videos) - 10} more non-Discord videos")
    
    # Check for URLs that might be videos but aren't detected
    print(f"\n\n🔍 CHECKING FOR POTENTIALLY MISSED VIDEOS:")
    print("=" * 80)
    
    potential_videos = []
    for char in all_characters:
        img_url = char.get('img_url', '').lower()
        if not is_video_url(img_url):
            # Check if URL might contain video keywords
            if any(keyword in img_url for keyword in ['video', 'mp4', 'mov', 'webm']):
                potential_videos.append(char)
    
    if potential_videos:
        print(f"Found {len(potential_videos)} URLs with video keywords but not detected as videos:")
        for i, char in enumerate(potential_videos[:5], 1):
            print(f"\n{i}. ID: {char.get('id')} - {char.get('name')}")
            print(f"   URL: {char.get('img_url')}")
    else:
        print("✅ No missed video URLs found")
    
    print("\n" + "=" * 80)
    print("✅ Database check complete!")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_video_urls())
