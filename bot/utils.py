import time
import math

async def progress_bar(current, total, message, start_time):
    now = time.time()
    diff = now - start_time
    # Only update every 2 seconds or when finished
    if round(diff % 2.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff if diff > 0 else 0
        elapsed_time = round(diff)
        eta = round((total - current) / speed) if speed > 0 else 0
        
        progress = "[{0}{1}]".format(
            '●' * int(percentage / 10),
            '○' * (10 - int(percentage / 10))
        )
        
        tmp = f"{progress} {round(percentage, 2)}%\n" \
              f"🚀 Speed: {humanbytes(speed)}/s\n" \
              f"⏱️ ETA: {time_formatter(eta)}"
              
        try:
            await message.edit_text(f"**Transferring...**\n\n{tmp}")
        except:
            pass

def humanbytes(size):
    if not size: return "0 B"
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti']:
        if size < 1024: return f"{size:.2f} {unit}B"
        size /= 1024

def time_formatter(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"
