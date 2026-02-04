# Telegram Restricted Content Downloader Bot

## Overview

This is a Telegram bot designed to download and forward restricted content from Telegram channels/groups where saving and forwarding is disabled. The bot uses a dual-authentication approach with both a User Session (for accessing restricted content) and a Bot Token (for user interaction). It's optimized for speed using TgCrypto for encryption, uvloop for async operations, and parallel download/upload strategies.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Authentication Model
- **Dual-client approach**: Bot token for user commands, user session strings for accessing restricted channels
- **Session management**: Users can login with their phone numbers to generate session strings stored in SQLite
- **Role-based access**: Free, premium, admin, and owner roles with different capabilities

### Core Components

**Bot Framework**
- Pyrogram as the Telegram MTProto framework
- Handler-based architecture with separate modules for login, commands, admin functions
- In-memory bot session for reduced disk I/O

**Database Layer**
- SQLite with WAL mode for concurrent access
- Thread-safe with locking mechanism
- Stores user data, sessions, roles, and ad tracking
- Cloud backup integration with GitHub for persistence

**Performance Optimizations**
- TgCrypto for 2-4x faster encryption/decryption
- uvloop as async event loop replacement
- Memory limits set for 1.5GB VPS environments
- Periodic garbage collection every 30 minutes
- Rotating log files to manage disk space

**Fast Download Engine** (`fast_dl/`)
- Multi-threaded parallel chunk downloads
- Custom chunk sizing for MTProto optimization
- Direct DC connection for file transfers
- Video metadata extraction (duration, dimensions, thumbnail) for proper streaming video uploads

## Recent Changes

### February 4, 2026
- Fixed streaming video upload issue: Videos from private channels now upload with correct duration and thumbnail instead of showing 0:00 duration
- Added `download_with_metadata()` function to extract video duration, width, height, and thumbnail during download
- Updated `fast_upload()` to accept and use video metadata for proper video attributes
- Thumbnail is now downloaded from original video and included in the re-upload

### Request Flow
1. User sends Telegram link to bot
2. Bot parses link to extract channel/message ID
3. Checks if public (bot can access) or private (needs user session)
4. Downloads content using parallel chunk strategy
5. Re-uploads to user's chat

### Web Server
- Flask health check endpoint for monitoring
- Runs in daemon thread alongside bot

## External Dependencies

### Telegram APIs
- **Pyrogram**: MTProto client library
- **TgCrypto**: C extension for fast encryption (required for speed)
- **API credentials**: API_ID, API_HASH from my.telegram.org, BOT_TOKEN from BotFather

### Database
- **SQLite**: Local file-based storage (`telegram_bot.db`)
- GitHub integration for cloud backups (periodic every 10 minutes)

### Monetization
- **RichAds**: Ad network integration with publisher/widget IDs
- Daily ad limits and premium user exemptions configurable

### Environment Variables Required
- `API_ID`, `API_HASH`, `BOT_TOKEN` (critical)
- `OWNER_ID`, `OWNER_USERNAME`
- `DATABASE_PATH` (defaults to telegram_bot.db)
- `RICHADS_PUBLISHER_ID`, `RICHADS_WIDGET_ID`
- `AD_DAILY_LIMIT`, `AD_FOR_PREMIUM`
- `SUPPORT_CHAT_LINK`

### Python Dependencies
- pyrogram, tgcrypto, uvloop (core bot)
- aiohttp, aiofiles (async I/O)
- python-dotenv (configuration)
- flask (health checks)
- psutil (memory monitoring)
- motor (MongoDB driver, listed but SQLite is primary)