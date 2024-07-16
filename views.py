from http import HTTPStatus

from fastapi import Depends, Request
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException
from starlette.responses import HTMLResponse

from lnbits.core.models import User
from lnbits.decorators import check_user_exists
from lnbits.settings import settings

from . import nwcservice_ext, nwcservice_renderer
from .crud import get_nwcservice

myex = Jinja2Templates(directory="myex")


#######################################
##### ADD YOUR PAGE ENDPOINTS HERE ####
#######################################


# Backend admin page


@nwcservice_ext.get("/", response_class=HTMLResponse)
async def index(request: Request, user: User = Depends(check_user_exists)):
    return nwcservice_renderer().TemplateResponse(
        "nwcservice/index.html", {"request": request, "user": user.dict()}
    )


# Frontend shareable page


@nwcservice_ext.get("/{nwcservice_id}")
async def nwcservice(request: Request, nwcservice_id):
    nwcservice = await get_nwcservice(nwcservice_id, request)
    if not nwcservice:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="NWCService does not exist."
        )
    return nwcservice_renderer().TemplateResponse(
        "nwcservice/nwcservice.html",
        {
            "request": request,
            "nwcservice_id": nwcservice_id,
            "lnurlpay": nwcservice.lnurlpay,
            "web_manifest": f"/nwcservice/manifest/{nwcservice_id}.webmanifest",
        },
    )


# Manifest for public page, customise or remove manifest completely


@nwcservice_ext.get("/manifest/{nwcservice_id}.webmanifest")
async def manifest(nwcservice_id: str):
    nwcservice = await get_nwcservice(nwcservice_id)
    if not nwcservice:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="NWCService does not exist."
        )

    return {
        "short_name": settings.lnbits_site_title,
        "name": nwcservice.name + " - " + settings.lnbits_site_title,
        "icons": [
            {
                "src": settings.lnbits_custom_logo
                if settings.lnbits_custom_logo
                else "https://cdn.jsdelivr.net/gh/lnbits/lnbits@0.3.0/docs/logos/lnbits.png",
                "type": "image/png",
                "sizes": "900x900",
            }
        ],
        "start_url": "/nwcservice/" + nwcservice_id,
        "background_color": "#1F2234",
        "description": "Minimal extension to build on",
        "display": "standalone",
        "scope": "/nwcservice/" + nwcservice_id,
        "theme_color": "#1F2234",
        "shortcuts": [
            {
                "name": nwcservice.name + " - " + settings.lnbits_site_title,
                "short_name": nwcservice.name,
                "description": nwcservice.name + " - " + settings.lnbits_site_title,
                "url": "/nwcservice/" + nwcservice_id,
            }
        ],
    }
