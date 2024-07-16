from http import HTTPStatus

from fastapi import Depends, Request
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException
from starlette.responses import HTMLResponse

from lnbits.core.models import User
from lnbits.decorators import check_user_exists
from lnbits.settings import settings

from . import nwc_service_ext, nwc_service_renderer
from .crud import get_nwc_service

myex = Jinja2Templates(directory="myex")


#######################################
##### ADD YOUR PAGE ENDPOINTS HERE ####
#######################################


# Backend admin page


@nwc_service_ext.get("/", response_class=HTMLResponse)
async def index(request: Request, user: User = Depends(check_user_exists)):
    return nwc_service_renderer().TemplateResponse(
        "nwc_service/index.html", {"request": request, "user": user.dict()}
    )


# Frontend shareable page


@nwc_service_ext.get("/{nwc_service_id}")
async def nwc_service(request: Request, nwc_service_id):
    nwc_service = await get_nwc_service(nwc_service_id, request)
    if not nwc_service:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="NWCService does not exist."
        )
    return nwc_service_renderer().TemplateResponse(
        "nwc_service/nwc_service.html",
        {
            "request": request,
            "nwc_service_id": nwc_service_id,
            "lnurlpay": nwc_service.lnurlpay,
            "web_manifest": f"/nwc_service/manifest/{nwc_service_id}.webmanifest",
        },
    )


# Manifest for public page, customise or remove manifest completely


@nwc_service_ext.get("/manifest/{nwc_service_id}.webmanifest")
async def manifest(nwc_service_id: str):
    nwc_service = await get_nwc_service(nwc_service_id)
    if not nwc_service:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="NWCService does not exist."
        )

    return {
        "short_name": settings.lnbits_site_title,
        "name": nwc_service.name + " - " + settings.lnbits_site_title,
        "icons": [
            {
                "src": settings.lnbits_custom_logo
                if settings.lnbits_custom_logo
                else "https://cdn.jsdelivr.net/gh/lnbits/lnbits@0.3.0/docs/logos/lnbits.png",
                "type": "image/png",
                "sizes": "900x900",
            }
        ],
        "start_url": "/nwc_service/" + nwc_service_id,
        "background_color": "#1F2234",
        "description": "Minimal extension to build on",
        "display": "standalone",
        "scope": "/nwc_service/" + nwc_service_id,
        "theme_color": "#1F2234",
        "shortcuts": [
            {
                "name": nwc_service.name + " - " + settings.lnbits_site_title,
                "short_name": nwc_service.name,
                "description": nwc_service.name + " - " + settings.lnbits_site_title,
                "url": "/nwc_service/" + nwc_service_id,
            }
        ],
    }
