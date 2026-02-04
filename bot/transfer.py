import asyncio
import math
import os
import time
from pyrogram.client import Client
from pyrogram.errors import FloodWait
from bot.config import API_ID, API_HASH

from fast_dl.fast_download import FastDownload
from fast_dl.fast_upload import FastUpload

async def fast_download(client: Client, message, chunk_size=1024*1024, num_workers=8, progress=None, progress_args=()):
    """
    Optimized download using FastDownload helper.
    """
    try:
        downloader = FastDownload(client)
        file_path = await downloader.download(
            message,
            progress=progress,
            progress_args=progress_args
        )
        return file_path
    except FloodWait as e:
        await asyncio.sleep(float(getattr(e, 'value', 0) or getattr(e, 'x', 0)))
        return await fast_download(client, message, chunk_size, num_workers)
    except Exception as e:
        print(f"Download error: {e}")
        return None

async def fast_download_with_metadata(client: Client, message, chunk_size=1024*1024, num_workers=8, progress=None, progress_args=()):
    """
    Optimized download with video metadata extraction.
    Returns: (file_path, metadata_dict)
    """
    try:
        downloader = FastDownload(client)
        file_path, metadata = await downloader.download_with_metadata(
            message,
            progress=progress,
            progress_args=progress_args
        )
        return file_path, metadata
    except FloodWait as e:
        await asyncio.sleep(float(getattr(e, 'value', 0) or getattr(e, 'x', 0)))
        return await fast_download_with_metadata(client, message, chunk_size, num_workers)
    except Exception as e:
        print(f"Download error: {e}")
        return None, {}

async def fast_upload(client: Client, chat_id, file_path, caption=None, num_workers=8, progress=None, progress_args=(), video_metadata=None):
    """
    Optimized upload using FastUpload helper.
    """
    try:
        uploader = FastUpload(client)
        sent = await uploader.upload(
            chat_id,
            file_path,
            caption=caption or "",
            progress=progress,
            progress_args=progress_args,
            video_metadata=video_metadata
        )
        
        # Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)
            
        return sent
    except FloodWait as e:
        await asyncio.sleep(float(getattr(e, 'value', 0) or getattr(e, 'x', 0)))
        return await fast_upload(client, chat_id, file_path, caption, num_workers, video_metadata=video_metadata)
    except Exception as e:
        print(f"Upload error: {e}")
        return None
