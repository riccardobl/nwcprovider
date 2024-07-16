from http import HTTPStatus
import json

import httpx
from fastapi import Depends, Query, Request
from lnurl import decode as decode_lnurl
from loguru import logger
from starlette.exceptions import HTTPException

from lnbits.core.crud import get_user
from lnbits.core.models import Payment
from lnbits.core.services import create_invoice
from lnbits.core.views.api import api_payment
from lnbits.decorators import (
    WalletTypeInfo,
    check_admin,
    get_key_type,
    require_admin_key,
    require_invoice_key,
)

from . import nwcservice_ext
from .crud import (
    create_nwcservice,
    update_nwcservice,
    delete_nwcservice,
    get_nwcservice,
    get_nwcservices,
)
from .models import CreateNWCServiceData


#######################################
##### ADD YOUR API ENDPOINTS HERE #####
#######################################

## Get all the records belonging to the user


@nwcservice_ext.get("/api/v1/myex", status_code=HTTPStatus.OK)
async def api_nwcservices(
    req: Request,
    all_wallets: bool = Query(False),
    wallet: WalletTypeInfo = Depends(get_key_type),
):
    wallet_ids = [wallet.wallet.id]
    if all_wallets:
        user = await get_user(wallet.wallet.user)
        wallet_ids = user.wallet_ids if user else []
    return [
        nwcservice.dict() for nwcservice in await get_nwcservices(wallet_ids, req)
    ]


## Get a single record


@nwcservice_ext.get("/api/v1/myex/{nwcservice_id}", status_code=HTTPStatus.OK)
async def api_nwcservice(
    req: Request, nwcservice_id: str, WalletTypeInfo=Depends(get_key_type)
):
    nwcservice = await get_nwcservice(nwcservice_id, req)
    if not nwcservice:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="NWCService does not exist."
        )
    return nwcservice.dict()


## update a record


@nwcservice_ext.put("/api/v1/myex/{nwcservice_id}")
async def api_nwcservice_update(
    req: Request,
    data: CreateNWCServiceData,
    nwcservice_id: str,
    wallet: WalletTypeInfo = Depends(get_key_type),
):
    if not nwcservice_id:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="NWCService does not exist."
        )
    nwcservice = await get_nwcservice(nwcservice_id, req)
    assert nwcservice, "NWCService couldn't be retrieved"

    if wallet.wallet.id != nwcservice.wallet:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your NWCService."
        )
    nwcservice = await update_nwcservice(
        nwcservice_id=nwcservice_id, **data.dict(), req=req
    )
    return nwcservice.dict()


## Create a new record


@nwcservice_ext.post("/api/v1/myex", status_code=HTTPStatus.CREATED)
async def api_nwcservice_create(
    req: Request,
    data: CreateNWCServiceData,
    wallet: WalletTypeInfo = Depends(require_admin_key),
):
    nwcservice = await create_nwcservice(
        wallet_id=wallet.wallet.id, data=data, req=req
    )
    return nwcservice.dict()


## Delete a record


@nwcservice_ext.delete("/api/v1/myex/{nwcservice_id}")
async def api_nwcservice_delete(
    nwcservice_id: str, wallet: WalletTypeInfo = Depends(require_admin_key)
):
    nwcservice = await get_nwcservice(nwcservice_id)

    if not nwcservice:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="NWCService does not exist."
        )

    if nwcservice.wallet != wallet.wallet.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your NWCService."
        )

    await delete_nwcservice(nwcservice_id)
    return "", HTTPStatus.NO_CONTENT


# ANY OTHER ENDPOINTS YOU NEED

## This endpoint creates a payment


@nwcservice_ext.post(
    "/api/v1/myex/payment/{nwcservice_id}", status_code=HTTPStatus.CREATED
)
async def api_tpos_create_invoice(
    nwcservice_id: str, amount: int = Query(..., ge=1), memo: str = ""
) -> dict:
    nwcservice = await get_nwcservice(nwcservice_id)

    if not nwcservice:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="NWCService does not exist."
        )

    # we create a payment and add some tags, so tasks.py can grab the payment once its paid

    try:
        payment_hash, payment_request = await create_invoice(
            wallet_id=nwcservice.wallet,
            amount=amount,
            memo=f"{memo} to {nwcservice.name}" if memo else f"{nwcservice.name}",
            extra={
                "tag": "nwcservice",
                "amount": amount,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(e))

    return {"payment_hash": payment_hash, "payment_request": payment_request}
