from typing import List, Optional, Union

from lnbits.helpers import urlsafe_short_hash
from lnbits.lnurl import encode as lnurl_encode
from . import db
from .models import CreateNWCServiceData, NWCService
from loguru import logger
from fastapi import Request
from lnurl import encode as lnurl_encode
import shortuuid


async def create_nwcservice(
    wallet_id: str, data: CreateNWCServiceData, req: Request
) -> NWCService:
    nwcservice_id = urlsafe_short_hash()
    await db.execute(
        """
        INSERT INTO nwcservice.maintable (id, wallet, name, lnurlpayamount, lnurlwithdrawamount)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            nwcservice_id,
            wallet_id,
            data.name,
            data.lnurlpayamount,
            data.lnurlwithdrawamount,
        ),
    )
    nwcservice = await get_nwcservice(nwcservice_id, req)
    assert nwcservice, "Newly created table couldn't be retrieved"
    return nwcservice


async def get_nwcservice(
    nwcservice_id: str, req: Optional[Request] = None
) -> Optional[NWCService]:
    row = await db.fetchone(
        "SELECT * FROM nwcservice.maintable WHERE id = ?", (nwcservice_id,)
    )
    if not row:
        return None
    rowAmended = NWCService(**row)
    if req:
        rowAmended.lnurlpay = lnurl_encode(
            req.url_for("nwcservice.api_lnurl_pay", nwcservice_id=row.id)._url
        )
        rowAmended.lnurlwithdraw = lnurl_encode(
            req.url_for(
                "nwcservice.api_lnurl_withdraw",
                nwcservice_id=row.id,
                tickerhash=shortuuid.uuid(name=rowAmended.id + str(rowAmended.ticker)),
            )._url
        )
    return rowAmended


async def get_nwcservices(
    wallet_ids: Union[str, List[str]], req: Optional[Request] = None
) -> List[NWCService]:
    if isinstance(wallet_ids, str):
        wallet_ids = [wallet_ids]

    q = ",".join(["?"] * len(wallet_ids))
    rows = await db.fetchall(
        f"SELECT * FROM nwcservice.maintable WHERE wallet IN ({q})", (*wallet_ids,)
    )
    tempRows = [NWCService(**row) for row in rows]
    if req:
        for row in tempRows:
            row.lnurlpay = lnurl_encode(
                req.url_for("nwcservice.api_lnurl_pay", nwcservice_id=row.id)._url
            )
            row.lnurlwithdraw = lnurl_encode(
                req.url_for(
                    "nwcservice.api_lnurl_withdraw",
                    nwcservice_id=row.id,
                    tickerhash=shortuuid.uuid(name=row.id + str(row.ticker)),
                )._url
            )
    return tempRows


async def update_nwcservice(
    nwcservice_id: str, req: Optional[Request] = None, **kwargs
) -> NWCService:
    q = ", ".join([f"{field[0]} = ?" for field in kwargs.items()])
    await db.execute(
        f"UPDATE nwcservice.maintable SET {q} WHERE id = ?",
        (*kwargs.values(), nwcservice_id),
    )
    nwcservice = await get_nwcservice(nwcservice_id, req)
    assert nwcservice, "Newly updated nwcservice couldn't be retrieved"
    return nwcservice


async def delete_nwcservice(nwcservice_id: str) -> None:
    await db.execute(
        "DELETE FROM nwcservice.maintable WHERE id = ?", (nwcservice_id,)
    )
