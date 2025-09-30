# Overview

This is a Telegram character catcher bot called "Waifu & Husbando Catcher" that operates as a gamified character collection system. The bot sends anime character images to Telegram groups after every 100 messages, and users can guess the character names to add them to their personal collections. The system includes trading, gifting, favorites, and leaderboard features to create an engaging community-driven game.

# Recent Changes

## September 30, 2025
- **Video Detection Fix for URLs Without Extensions**: Fixed video detection to work with URLs that don't have file extensions (like cloudflare /dl/ links)
  - Changed all video detection checks from `is_video_url()` to `is_video_character()` across harem.py, inlinequery.py, and upload.py
  - Now correctly detects videos using both URL extensions AND the 🎬 emoji marker in character names
  - Fixes issue where videos served from cloudflare and other services without file extensions in URLs weren't being recognized as videos
  - Affected commands: `/harem`, `/fav`, `/find`, and inline queries
- **Non-Discord MP4 Fallback Handling**: Fixed issue where non-Discord MP4 links weren't displaying in commands and inline queries
  - Added comprehensive video-to-photo fallback system across all display paths
  - When video format fails (especially in Telegram inline queries), gracefully falls back to displaying as photo with 🎬 indicator
  - Implemented fallback handling in `/find`, `/fav`, harem display (both message and callback paths), and inline queries
  - Added detailed error logging to track URL failures and diagnose issues with video display
  - All video fallbacks now consistently mark with 🎬 [Video] indicator so users know it's a video character
- **Video Upload Support**: Added MP4 and other video format support to `/upload` command. Videos are now validated and sent using `send_video` API
- **Video Display Support**: Fixed all display commands to properly play videos instead of showing them as broken images
  - `/find` command now displays videos correctly
  - `/fav` command plays videos when favoriting video characters
  - Harem preview shows videos for favorite and random characters
  - Inline queries support video results with proper MIME types (MP4, WEBM, MOV, AVI, MKV, FLV)
- **Character Name Filtering**: Fixed `/sorts character` command to support partial name matching. Now "Ashley" will match "Ashley Graves ⛩️" and other character names with emojis
- **Locked Spawns Display**: Fixed `lockedspawns` command to include Retro rarity characters in the display
- **Pagination Enhancement**: Added next/previous navigation buttons to `lockedspawns` command for better navigation through locked characters (20 per page)

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Core Bot Framework
- **Telegram Bot API**: Uses python-telegram-bot v20.6 for main bot functionality and command handling
- **Pyrogram**: Secondary Telegram client library for additional features like admin controls and message handling
- **Dual Client Pattern**: Implements both python-telegram-bot (application) and Pyrogram (shivuu) clients for different use cases

## Database Design
- **MongoDB with Motor**: Async MongoDB driver for all data persistence
- **Collections Structure**:
  - `anime_characters_lol`: Stores character data (id, name, anime, rarity, image URL)
  - `user_collection_lmaoooo`: User's collected characters
  - `user_totals_lmaoooo`: User statistics and totals
  - `group_user_totalsssssss`: Group-specific user statistics
  - `top_global_groups`: Global group leaderboards
  - `total_pm_users`: Private message users tracking

## Message Processing Architecture
- **Message Counter System**: Tracks messages per group with customizable frequency (default 100 messages)
- **Async Locks**: Prevents race conditions using asyncio locks per chat
- **Character Spawning**: Automatic character deployment based on message thresholds
- **Spam Prevention**: Built-in rate limiting and spam counters

## Command System
- **Modular Design**: Commands organized in separate modules for maintainability
- **Admin Controls**: Role-based permissions using Pyrogram's chat member status
- **User Commands**: `/guess`, `/fav`, `/trade`, `/gift`, `/collection`, `/topgroups`
- **Admin Commands**: `/upload`, `/changetime`, `/broadcast`

## Caching Strategy
- **TTL Cache**: Uses cachetools for temporary data storage
- **User Collection Cache**: 60-second TTL for frequently accessed user data
- **Character Cache**: 10-hour TTL for character data
- **Database Indexing**: Strategic indexes on frequently queried fields

## Rarity System
- **Tiered Rarity**: 4-tier system (Common ⚪️, Medium 🟢, Rare 🟣, Legendary 🟡)
- **Auto-incrementing IDs**: Sequence-based character ID generation
- **Image Validation**: URL validation before character upload

# External Dependencies

## Database Services
- **MongoDB Atlas**: Cloud MongoDB instance for data persistence
- **Connection String**: Configured via environment variables for security

## Telegram Platform
- **Bot API**: Official Telegram Bot API for bot operations
- **MTProto API**: Direct Telegram API access via Pyrogram for advanced features
- **File Storage**: Telegram's built-in file hosting for character images

## Image Hosting
- **Telegraph**: Primary image hosting service for character images
- **URL Validation**: Validates image URLs before storing in database

## Python Libraries
- **Core**: python-telegram-bot, pyrogram, motor (async MongoDB)
- **Utilities**: aiohttp, requests, python-dotenv, cachetools
- **Scheduling**: apscheduler for background tasks
- **Rate Limiting**: pyrate-limiter for API call management

## Configuration Management
- **Environment Variables**: Sensitive data stored in environment variables
- **Config Classes**: Separate Production/Development configuration classes
- **Runtime**: Python 3.11.0 specified for deployment compatibility