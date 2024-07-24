
from fastapi import Depends, Request
from starlette.responses import HTMLResponse
from lnbits.core.models import User
from lnbits.decorators import check_user_exists
from lnbits.decorators import check_admin

from . import nwcprovider_ext,nwcprovider_renderer


@nwcprovider_ext.get("/", response_class=HTMLResponse)
async def index(request: Request, user: User = Depends(check_user_exists)):
    return nwcprovider_renderer().TemplateResponse(
        "nwcprovider/index.html", {"request": request, "user": user.dict()}
    )

@nwcprovider_ext.get("/admin", response_class=HTMLResponse)
async def admin(request: Request, user: User = Depends(check_admin)):
    return nwcprovider_renderer().TemplateResponse(
        "nwcprovider/admin.html", {"request": request, "user": user.dict()}
    )
