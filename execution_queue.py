import asyncio
from typing import Any, Dict

execution_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()


async def enqueue(action):
    future = asyncio.Future()
    execution_queue.put_nowait({"action": action, "future": future})
    return await future
