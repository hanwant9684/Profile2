import asyncio
import aiofiles
import os
from pyrogram import Client

class FastDownload:
    def __init__(self, client: Client):
        self.client = client

    async def download(self, message, file_name: str = "", progress=None, progress_args=()):
        # 1. Identify the media object in the message
        media = getattr(message, message.media.value) if message.media else None
        if not media:
            return None

        # 2. Determine file name (handle None values properly)
        media_file_name = getattr(media, "file_name", None)
        
        # Determine extension based on media type if no filename exists
        ext = ".bin"
        if message.video:
            ext = ".mp4"
        elif message.audio:
            ext = ".mp3"
        elif message.document:
            ext = ".pdf"
        elif message.photo:
            ext = ".jpg"

        default_name = f"{media.file_id[:10]}{ext}"
        file_path = file_name or media_file_name or default_name
        
        # 3. Stream and write to file
        async with aiofiles.open(file_path, "wb") as f:
            async for chunk in self.client.stream_media(message):
                await f.write(chunk)
        
        return file_path

    async def download_with_metadata(self, message, file_name: str = "", progress=None, progress_args=()):
        """
        Downloads file and returns metadata for videos (duration, dimensions, thumbnail).
        Returns: (file_path, metadata_dict)
        """
        media = getattr(message, message.media.value) if message.media else None
        if not media:
            return None, {}

        media_file_name = getattr(media, "file_name", None)
        
        ext = ".bin"
        if message.video:
            ext = ".mp4"
        elif message.audio:
            ext = ".mp3"
        elif message.document:
            ext = ".pdf"
        elif message.photo:
            ext = ".jpg"

        default_name = f"{media.file_id[:10]}{ext}"
        file_path = file_name or media_file_name or default_name
        
        # Extract video metadata before downloading
        metadata = {}
        if message.video:
            video = message.video
            metadata = {
                "duration": getattr(video, "duration", 0) or 0,
                "width": getattr(video, "width", 1280) or 1280,
                "height": getattr(video, "height", 720) or 720,
                "is_video": True
            }
            
            # Download thumbnail if available
            if video.thumbs and len(video.thumbs) > 0:
                try:
                    thumb = video.thumbs[-1]  # Get largest thumbnail
                    thumb_path = f"{file_path}_thumb.jpg"
                    # Download thumbnail using its file_id
                    if hasattr(thumb, 'file_id') and thumb.file_id:
                        await self.client.download_media(
                            thumb.file_id,
                            file_name=thumb_path
                        )
                        if os.path.exists(thumb_path):
                            metadata["thumb_path"] = thumb_path
                except Exception as e:
                    print(f"Thumbnail download error: {e}")
        
        # Stream and write to file
        async with aiofiles.open(file_path, "wb") as f:
            async for chunk in self.client.stream_media(message):
                await f.write(chunk)
        
        return file_path, metadata
