import asyncio

from fastapi import APIRouter

from lnbits.db import Database
from lnbits.helpers import template_renderer
from lnbits.tasks import create_permanent_unique_task
from loguru import logger

logger.debug("This logged message is from nwc_service/__init__.py, you can debug in your extension using 'import logger from loguru' and 'logger.debug(<thing-to-log>)'.")

db = Database("ext_nwc_service")

nwc_service_ext: APIRouter = APIRouter(
    prefix="/nwc_service", tags=["NWCService"]
)

nwc_service_static_files = [
    {
        "path": "/nwc_service/static",
        "name": "nwc_service_static",
    }
]


def nwc_service_renderer():
    return template_renderer(["nwc_service/templates"])


from .lnurl import *
from .tasks import wait_for_paid_invoices
from .views import *
from .views_api import *

scheduled_tasks: list[asyncio.Task] = []

def nwc_service_stop():
    for task in scheduled_tasks:
        try:
            task.cancel()
        except Exception as ex:
            logger.warning(ex)

def nwc_service_start():
    task = create_permanent_unique_task("ext_nwc_service", wait_for_paid_invoices)
    scheduled_tasks.append(task)