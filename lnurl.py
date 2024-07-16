# Maybe your extension needs some LNURL stuff.
# Here is a very simple example of how to do it.
# Feel free to delete this file if you don't need it.

from http import HTTPStatus
from fastapi import Depends, Query, Request
from . import nwc_service_ext
from .crud import get_nwc_service
from lnbits.core.services import create_invoice, pay_invoice
from loguru import logger
from typing import Optional
from .crud import update_nwc_service
from .models import NWCService
import shortuuid

#################################################
########### A very simple LNURLpay ##############
# https://github.com/lnurl/luds/blob/luds/06.md #
#################################################
#################################################


@nwc_service_ext.get(
    "/api/v1/lnurl/pay/{nwc_service_id}",
    status_code=HTTPStatus.OK,
    name="nwc_service.api_lnurl_pay",
)
async def api_lnurl_pay(
    request: Request,
    nwc_service_id: str,
):
    nwc_service = await get_nwc_service(nwc_service_id)
    if not nwc_service:
        return {"status": "ERROR", "reason": "No nwc_service found"}
    return {
        "callback": str(
            request.url_for(
                "nwc_service.api_lnurl_pay_callback", nwc_service_id=nwc_service_id
            )
        ),
        "maxSendable": nwc_service.lnurlpayamount * 1000,
        "minSendable": nwc_service.lnurlpayamount * 1000,
        "metadata": '[["text/plain", "' + nwc_service.name + '"]]',
        "tag": "payRequest",
    }


@nwc_service_ext.get(
    "/api/v1/lnurl/paycb/{nwc_service_id}",
    status_code=HTTPStatus.OK,
    name="nwc_service.api_lnurl_pay_callback",
)
async def api_lnurl_pay_cb(
    request: Request,
    nwc_service_id: str,
    amount: int = Query(...),
):
    nwc_service = await get_nwc_service(nwc_service_id)
    logger.debug(nwc_service)
    if not nwc_service:
        return {"status": "ERROR", "reason": "No nwc_service found"}

    payment_hash, payment_request = await create_invoice(
        wallet_id=nwc_service.wallet,
        amount=int(amount / 1000),
        memo=nwc_service.name,
        unhashed_description=f'[["text/plain", "{nwc_service.name}"]]'.encode(),
        extra={
            "tag": "NWCService",
            "nwc_serviceId": nwc_service_id,
            "extra": request.query_params.get("amount"),
        },
    )
    return {
        "pr": payment_request,
        "routes": [],
        "successAction": {"tag": "message", "message": f"Paid {nwc_service.name}"},
    }


#################################################
######## A very simple LNURLwithdraw ############
# https://github.com/lnurl/luds/blob/luds/03.md #
#################################################
## withdraws are unique, removing 'tickerhash' ##
## here and crud.py will allow muliple pulls ####
#################################################


@nwc_service_ext.get(
    "/api/v1/lnurl/withdraw/{nwc_service_id}/{tickerhash}",
    status_code=HTTPStatus.OK,
    name="nwc_service.api_lnurl_withdraw",
)
async def api_lnurl_withdraw(
    request: Request,
    nwc_service_id: str,
    tickerhash: str,
):
    nwc_service = await get_nwc_service(nwc_service_id)
    if not nwc_service:
        return {"status": "ERROR", "reason": "No nwc_service found"}
    k1 = shortuuid.uuid(name=nwc_service.id + str(nwc_service.ticker))
    if k1 != tickerhash:
        return {"status": "ERROR", "reason": "LNURLw already used"}

    return {
        "tag": "withdrawRequest",
        "callback": str(
            request.url_for(
                "nwc_service.api_lnurl_withdraw_callback", nwc_service_id=nwc_service_id
            )
        ),
        "k1": k1,
        "defaultDescription": nwc_service.name,
        "maxWithdrawable": nwc_service.lnurlwithdrawamount * 1000,
        "minWithdrawable": nwc_service.lnurlwithdrawamount * 1000,
    }


@nwc_service_ext.get(
    "/api/v1/lnurl/withdrawcb/{nwc_service_id}",
    status_code=HTTPStatus.OK,
    name="nwc_service.api_lnurl_withdraw_callback",
)
async def api_lnurl_withdraw_cb(
    request: Request,
    nwc_service_id: str,
    pr: Optional[str] = None,
    k1: Optional[str] = None,
):
    assert k1, "k1 is required"
    assert pr, "pr is required"
    nwc_service = await get_nwc_service(nwc_service_id)
    if not nwc_service:
        return {"status": "ERROR", "reason": "No nwc_service found"}

    k1Check = shortuuid.uuid(name=nwc_service.id + str(nwc_service.ticker))
    if k1Check != k1:
        return {"status": "ERROR", "reason": "Wrong k1 check provided"}

    await update_nwc_service(
        nwc_service_id=nwc_service_id, ticker=nwc_service.ticker + 1
    )
    await pay_invoice(
        wallet_id=nwc_service.wallet,
        payment_request=pr,
        max_sat=int(nwc_service.lnurlwithdrawamount * 1000),
        extra={
            "tag": "NWCService",
            "nwc_serviceId": nwc_service_id,
            "lnurlwithdraw": True,
        },
    )
    return {"status": "OK"}
