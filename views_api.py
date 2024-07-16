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

from . import nwc_service_ext
from .crud import (
    create_nwc_service,
    update_nwc_service,
    delete_nwc_service,
    get_nwc_service,
    get_nwc_services,
)
from .models import CreateNWCServiceData


#######################################
##### ADD YOUR API ENDPOINTS HERE #####
#######################################

## Get all the records belonging to the user


@nwc_service_ext.get("/api/v1/myex", status_code=HTTPStatus.OK)
async def api_nwc_services(
    req: Request,
    all_wallets: bool = Query(False),
    wallet: WalletTypeInfo = Depends(get_key_type),
):
    wallet_ids = [wallet.wallet.id]
    if all_wallets:
        user = await get_user(wallet.wallet.user)
        wallet_ids = user.wallet_ids if user else []
    return [
        nwc_service.dict() for nwc_service in await get_nwc_services(wallet_ids, req)
    ]


## Get a single record


@nwc_service_ext.get("/api/v1/myex/{nwc_service_id}", status_code=HTTPStatus.OK)
async def api_nwc_service(
    req: Request, nwc_service_id: str, WalletTypeInfo=Depends(get_key_type)
):
    nwc_service = await get_nwc_service(nwc_service_id, req)
    if not nwc_service:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="NWCService does not exist."
        )
    return nwc_service.dict()


## update a record


@nwc_service_ext.put("/api/v1/myex/{nwc_service_id}")
async def api_nwc_service_update(
    req: Request,
    data: CreateNWCServiceData,
    nwc_service_id: str,
    wallet: WalletTypeInfo = Depends(get_key_type),
):
    if not nwc_service_id:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="NWCService does not exist."
        )
    nwc_service = await get_nwc_service(nwc_service_id, req)
    assert nwc_service, "NWCService couldn't be retrieved"

    if wallet.wallet.id != nwc_service.wallet:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your NWCService."
        )
    nwc_service = await update_nwc_service(
        nwc_service_id=nwc_service_id, **data.dict(), req=req
    )
    return nwc_service.dict()


## Create a new record


@nwc_service_ext.post("/api/v1/myex", status_code=HTTPStatus.CREATED)
async def api_nwc_service_create(
    req: Request,
    data: CreateNWCServiceData,
    wallet: WalletTypeInfo = Depends(require_admin_key),
):
    nwc_service = await create_nwc_service(
        wallet_id=wallet.wallet.id, data=data, req=req
    )
    return nwc_service.dict()


## Delete a record


@nwc_service_ext.delete("/api/v1/myex/{nwc_service_id}")
async def api_nwc_service_delete(
    nwc_service_id: str, wallet: WalletTypeInfo = Depends(require_admin_key)
):
    nwc_service = await get_nwc_service(nwc_service_id)

    if not nwc_service:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="NWCService does not exist."
        )

    if nwc_service.wallet != wallet.wallet.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="Not your NWCService."
        )

    await delete_nwc_service(nwc_service_id)
    return "", HTTPStatus.NO_CONTENT


# ANY OTHER ENDPOINTS YOU NEED

## This endpoint creates a payment


@nwc_service_ext.post(
    "/api/v1/myex/payment/{nwc_service_id}", status_code=HTTPStatus.CREATED
)
async def api_tpos_create_invoice(
    nwc_service_id: str, amount: int = Query(..., ge=1), memo: str = ""
) -> dict:
    nwc_service = await get_nwc_service(nwc_service_id)

    if not nwc_service:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="NWCService does not exist."
        )

    # we create a payment and add some tags, so tasks.py can grab the payment once its paid

    try:
        payment_hash, payment_request = await create_invoice(
            wallet_id=nwc_service.wallet,
            amount=amount,
            memo=f"{memo} to {nwc_service.name}" if memo else f"{nwc_service.name}",
            extra={
                "tag": "nwc_service",
                "amount": amount,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(e))

    return {"payment_hash": payment_hash, "payment_request": payment_request}
