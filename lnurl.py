# Maybe your extension needs some LNURL stuff.
# Here is a very simple example of how to do it.
# Feel free to delete this file if you don't need it.

from http import HTTPStatus
from fastapi import Depends, Query, Request
from . import nwcservice_ext
from .crud import get_nwcservice
from lnbits.core.services import create_invoice, pay_invoice
from loguru import logger
from typing import Optional
from .crud import update_nwcservice
from .models import NWCService
import shortuuid

#################################################
########### A very simple LNURLpay ##############
# https://github.com/lnurl/luds/blob/luds/06.md #
#################################################
#################################################


@nwcservice_ext.get(
    "/api/v1/lnurl/pay/{nwcservice_id}",
    status_code=HTTPStatus.OK,
    name="nwcservice.api_lnurl_pay",
)
async def api_lnurl_pay(
    request: Request,
    nwcservice_id: str,
):
    nwcservice = await get_nwcservice(nwcservice_id)
    if not nwcservice:
        return {"status": "ERROR", "reason": "No nwcservice found"}
    return {
        "callback": str(
            request.url_for(
                "nwcservice.api_lnurl_pay_callback", nwcservice_id=nwcservice_id
            )
        ),
        "maxSendable": nwcservice.lnurlpayamount * 1000,
        "minSendable": nwcservice.lnurlpayamount * 1000,
        "metadata": '[["text/plain", "' + nwcservice.name + '"]]',
        "tag": "payRequest",
    }


@nwcservice_ext.get(
    "/api/v1/lnurl/paycb/{nwcservice_id}",
    status_code=HTTPStatus.OK,
    name="nwcservice.api_lnurl_pay_callback",
)
async def api_lnurl_pay_cb(
    request: Request,
    nwcservice_id: str,
    amount: int = Query(...),
):
    nwcservice = await get_nwcservice(nwcservice_id)
    logger.debug(nwcservice)
    if not nwcservice:
        return {"status": "ERROR", "reason": "No nwcservice found"}

    payment_hash, payment_request = await create_invoice(
        wallet_id=nwcservice.wallet,
        amount=int(amount / 1000),
        memo=nwcservice.name,
        unhashed_description=f'[["text/plain", "{nwcservice.name}"]]'.encode(),
        extra={
            "tag": "NWCService",
            "nwcserviceId": nwcservice_id,
            "extra": request.query_params.get("amount"),
        },
    )
    return {
        "pr": payment_request,
        "routes": [],
        "successAction": {"tag": "message", "message": f"Paid {nwcservice.name}"},
    }


#################################################
######## A very simple LNURLwithdraw ############
# https://github.com/lnurl/luds/blob/luds/03.md #
#################################################
## withdraws are unique, removing 'tickerhash' ##
## here and crud.py will allow muliple pulls ####
#################################################


@nwcservice_ext.get(
    "/api/v1/lnurl/withdraw/{nwcservice_id}/{tickerhash}",
    status_code=HTTPStatus.OK,
    name="nwcservice.api_lnurl_withdraw",
)
async def api_lnurl_withdraw(
    request: Request,
    nwcservice_id: str,
    tickerhash: str,
):
    nwcservice = await get_nwcservice(nwcservice_id)
    if not nwcservice:
        return {"status": "ERROR", "reason": "No nwcservice found"}
    k1 = shortuuid.uuid(name=nwcservice.id + str(nwcservice.ticker))
    if k1 != tickerhash:
        return {"status": "ERROR", "reason": "LNURLw already used"}

    return {
        "tag": "withdrawRequest",
        "callback": str(
            request.url_for(
                "nwcservice.api_lnurl_withdraw_callback", nwcservice_id=nwcservice_id
            )
        ),
        "k1": k1,
        "defaultDescription": nwcservice.name,
        "maxWithdrawable": nwcservice.lnurlwithdrawamount * 1000,
        "minWithdrawable": nwcservice.lnurlwithdrawamount * 1000,
    }


@nwcservice_ext.get(
    "/api/v1/lnurl/withdrawcb/{nwcservice_id}",
    status_code=HTTPStatus.OK,
    name="nwcservice.api_lnurl_withdraw_callback",
)
async def api_lnurl_withdraw_cb(
    request: Request,
    nwcservice_id: str,
    pr: Optional[str] = None,
    k1: Optional[str] = None,
):
    assert k1, "k1 is required"
    assert pr, "pr is required"
    nwcservice = await get_nwcservice(nwcservice_id)
    if not nwcservice:
        return {"status": "ERROR", "reason": "No nwcservice found"}

    k1Check = shortuuid.uuid(name=nwcservice.id + str(nwcservice.ticker))
    if k1Check != k1:
        return {"status": "ERROR", "reason": "Wrong k1 check provided"}

    await update_nwcservice(
        nwcservice_id=nwcservice_id, ticker=nwcservice.ticker + 1
    )
    await pay_invoice(
        wallet_id=nwcservice.wallet,
        payment_request=pr,
        max_sat=int(nwcservice.lnurlwithdrawamount * 1000),
        extra={
            "tag": "NWCService",
            "nwcserviceId": nwcservice_id,
            "lnurlwithdraw": True,
        },
    )
    return {"status": "OK"}
