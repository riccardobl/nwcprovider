from typing import List, Optional, Union

from lnbits.helpers import urlsafe_short_hash
from lnbits.lnurl import encode as lnurl_encode
from . import db
from .models import CreateNWCServiceData, NWCService
from loguru import logger
from fastapi import Request
from lnurl import encode as lnurl_encode
import shortuuid


async def create_nwc_service(
    wallet_id: str, data: CreateNWCServiceData, req: Request
) -> NWCService:
    nwc_service_id = urlsafe_short_hash()
    await db.execute(
        """
        INSERT INTO nwc_service.maintable (id, wallet, name, lnurlpayamount, lnurlwithdrawamount)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            nwc_service_id,
            wallet_id,
            data.name,
            data.lnurlpayamount,
            data.lnurlwithdrawamount,
        ),
    )
    nwc_service = await get_nwc_service(nwc_service_id, req)
    assert nwc_service, "Newly created table couldn't be retrieved"
    return nwc_service


async def get_nwc_service(
    nwc_service_id: str, req: Optional[Request] = None
) -> Optional[NWCService]:
    row = await db.fetchone(
        "SELECT * FROM nwc_service.maintable WHERE id = ?", (nwc_service_id,)
    )
    if not row:
        return None
    rowAmended = NWCService(**row)
    if req:
        rowAmended.lnurlpay = lnurl_encode(
            req.url_for("nwc_service.api_lnurl_pay", nwc_service_id=row.id)._url
        )
        rowAmended.lnurlwithdraw = lnurl_encode(
            req.url_for(
                "nwc_service.api_lnurl_withdraw",
                nwc_service_id=row.id,
                tickerhash=shortuuid.uuid(name=rowAmended.id + str(rowAmended.ticker)),
            )._url
        )
    return rowAmended


async def get_nwc_services(
    wallet_ids: Union[str, List[str]], req: Optional[Request] = None
) -> List[NWCService]:
    if isinstance(wallet_ids, str):
        wallet_ids = [wallet_ids]

    q = ",".join(["?"] * len(wallet_ids))
    rows = await db.fetchall(
        f"SELECT * FROM nwc_service.maintable WHERE wallet IN ({q})", (*wallet_ids,)
    )
    tempRows = [NWCService(**row) for row in rows]
    if req:
        for row in tempRows:
            row.lnurlpay = lnurl_encode(
                req.url_for("nwc_service.api_lnurl_pay", nwc_service_id=row.id)._url
            )
            row.lnurlwithdraw = lnurl_encode(
                req.url_for(
                    "nwc_service.api_lnurl_withdraw",
                    nwc_service_id=row.id,
                    tickerhash=shortuuid.uuid(name=row.id + str(row.ticker)),
                )._url
            )
    return tempRows


async def update_nwc_service(
    nwc_service_id: str, req: Optional[Request] = None, **kwargs
) -> NWCService:
    q = ", ".join([f"{field[0]} = ?" for field in kwargs.items()])
    await db.execute(
        f"UPDATE nwc_service.maintable SET {q} WHERE id = ?",
        (*kwargs.values(), nwc_service_id),
    )
    nwc_service = await get_nwc_service(nwc_service_id, req)
    assert nwc_service, "Newly updated nwc_service couldn't be retrieved"
    return nwc_service


async def delete_nwc_service(nwc_service_id: str) -> None:
    await db.execute(
        "DELETE FROM nwc_service.maintable WHERE id = ?", (nwc_service_id,)
    )
