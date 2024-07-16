# Data models for your extension

from sqlite3 import Row
from typing import Optional, List
from pydantic import BaseModel
from fastapi import Request

from lnbits.lnurl import encode as lnurl_encode
from urllib.parse import urlparse


class CreateNWCServiceData(BaseModel):
    wallet: Optional[str]
    name: Optional[str]
    total: Optional[int]
    lnurlpayamount: Optional[int]
    lnurlwithdrawamount: Optional[int]
    ticker: Optional[int]


class NWCService(BaseModel):
    id: str
    wallet: Optional[str]
    name: Optional[str]
    total: Optional[int]
    lnurlpayamount: Optional[int]
    lnurlwithdrawamount: Optional[int]
    lnurlpay: Optional[str]
    lnurlwithdraw: Optional[str]
    ticker: Optional[int]

    @classmethod
    def from_row(cls, row: Row) -> "NWCService":
        return cls(**dict(row))
