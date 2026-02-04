import asyncio
import os
import math
from pyrogram.client import Client
from pyrogram.raw import functions, types
from typing import Callable, Union, Optional
import logging

class FastUpload:
    def __init__(self, client: Client):
        self.client = client

    async def upload(
        self,
        chat_id: Union[int, str],
        path: str,
        caption: str = "",
        progress: Optional[Callable] = None,
        progress_args: tuple = (),
        video_metadata: dict = None,
        **kwargs
    ):
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")

        file_size = os.path.getsize(path)
        file_name = os.path.basename(path)
        chunk_size = 512 * 1024  # 512KB
        is_big = file_size > 10 * 1024 * 1024
        
        num_chunks = math.ceil(file_size / chunk_size)
        semaphore = asyncio.Semaphore(8)
        completed_bytes = 0

        import random
        file_id = random.randint(0, 2**63 - 1)

        async def upload_chunk(chunk_index):
            nonlocal completed_bytes
            async with semaphore:
                with open(path, "rb") as f:
                    f.seek(chunk_index * chunk_size)
                    chunk_data = f.read(chunk_size)

                if is_big:
                    await self.client.invoke(
                        functions.upload.SaveBigFilePart(
                            file_id=file_id,
                            file_part=chunk_index,
                            file_total_parts=num_chunks,
                            bytes=chunk_data
                        )
                    )
                else:
                    await self.client.invoke(
                        functions.upload.SaveFilePart(
                            file_id=file_id,
                            file_part=chunk_index,
                            bytes=chunk_data
                        )
                    )
                
                completed_bytes += len(chunk_data)
                if progress:
                    await progress(completed_bytes, file_size, *progress_args)

        tasks = [upload_chunk(i) for i in range(num_chunks)]
        await asyncio.gather(*tasks)

        if is_big:
            input_file = types.InputFileBig(
                id=file_id,
                parts=num_chunks,
                name=file_name
            )
        else:
            input_file = types.InputFile(
                id=file_id,
                parts=num_chunks,
                name=file_name,
                md5_checksum=""
            )

        # Detect if it's a video
        video_extensions = (".mp4", ".mkv", ".mov", ".avi", ".flv", ".wmv", ".webm", ".m4v", ".3gp")
        is_video = path.lower().endswith(video_extensions)
        mime = "video/mp4" if is_video else "application/octet-stream"

        # Extract metadata from video_metadata dict if provided
        video_metadata = video_metadata or {}
        duration = video_metadata.get("duration", 0)
        width = video_metadata.get("width", 1280)
        height = video_metadata.get("height", 720)
        thumb_path = video_metadata.get("thumb_path")

        # Set Attributes
        attributes = [types.DocumentAttributeFilename(file_name=file_name)]
        if is_video:
            attributes.append(
                types.DocumentAttributeVideo(
                    duration=duration,
                    w=width,
                    h=height,
                    supports_streaming=True
                )
            )

        # Upload thumbnail if available
        input_thumb = None
        if thumb_path and os.path.exists(thumb_path):
            try:
                thumb_size = os.path.getsize(thumb_path)
                thumb_chunks = math.ceil(thumb_size / chunk_size)
                thumb_file_id = random.randint(0, 2**63 - 1)
                
                # Upload thumbnail
                with open(thumb_path, "rb") as f:
                    thumb_data = f.read()
                
                await self.client.invoke(
                    functions.upload.SaveFilePart(
                        file_id=thumb_file_id,
                        file_part=0,
                        bytes=thumb_data
                    )
                )
                
                input_thumb = types.InputFile(
                    id=thumb_file_id,
                    parts=1,
                    name=os.path.basename(thumb_path),
                    md5_checksum=""
                )
                
                # Cleanup thumbnail file
                os.remove(thumb_path)
            except Exception as e:
                print(f"Thumbnail upload error: {e}")
                input_thumb = None

        # Finalize using raw invoke
        peer = await self.client.resolve_peer(chat_id)
        
        media = types.InputMediaUploadedDocument(
            file=input_file,
            mime_type=mime,
            attributes=attributes,
            thumb=input_thumb
        )

        return await self.client.invoke(
            functions.messages.SendMedia(
                peer=peer,
                media=media,
                message=caption or "",
                random_id=self.client.rnd_id()
            )
        )
