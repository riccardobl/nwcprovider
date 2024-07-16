import asyncio
from fastapi import APIRouter
from lnbits.db import Database
from lnbits.helpers import template_renderer
from lnbits.tasks import create_permanent_unique_task
from loguru import logger


db = Database("ext_nwcprovider")
execution_queue = asyncio.Queue()
scheduled_tasks: list[asyncio.Task] = []

nwcprovider_ext: APIRouter = APIRouter(
    prefix="/nwcprovider", tags=["NWC Service Provider"]
)

nwcprovider_static_files = [
    {
        "path": "/nwcprovider/static",
        "name": "nwcprovider",
    }
]


def nwcprovider_renderer():
    return template_renderer(["nwcprovider/templates"])


async def enqueue(action):
    future = asyncio.Future()
    execution_queue.put_nowait({
        "action": action,
        "future": future
    })
    return await future

from .views import *
from .views_api import *
from .tasks import handle_nwc, handle_execution_queue




def nwcprovider_stop():
    for task in scheduled_tasks:
        try:
            task.cancel()
        except Exception as ex:
            logger.warning(ex)


def nwcprovider_start():
    task = create_permanent_unique_task("ext_nwcprovider", handle_nwc)
    scheduled_tasks.append(task)
    task = create_permanent_unique_task(
        "ext_nwcprovider_execution_queue", handle_execution_queue)
    scheduled_tasks.append(task)

