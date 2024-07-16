from http import HTTPStatus
import json
from typing import List, Optional, Dict
from .models import NWCKey, NWCBudget,NWCRegistrationRequest , NWCNewBudget,NWCGetResponse
from fastapi import Depends,  Request
from loguru import logger
from lnbits.decorators import (
    WalletTypeInfo,
    get_key_type,
    require_admin_key
)
from pydantic import BaseModel,Field
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from . import nwcprovider_ext

from .crud import get_nwc, get_wallet_nwcs, get_all_config_nwc, create_nwc, delete_nwc, get_budgets_nwc, get_config_nwc,set_config_nwc


from lnbits.decorators import check_admin
from fastapi import Depends
import secp256k1
from .permission import nwc_permissions

# Get supported permissions
@nwcprovider_ext.get("/api/v1/permissions", status_code=HTTPStatus.OK)
async def api_get_permissions(
    req: Request,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> Dict:
   return nwc_permissions
    

## Get nwc keys associated with the wallet
@nwcprovider_ext.get("/api/v1/nwc", status_code=HTTPStatus.OK,  response_model=List[NWCGetResponse])
async def api_get_nwcs(
    req: Request,
    includeExpired: Optional[bool] = False,
    calculateSpendBudget: Optional[bool] = False,
    wallet: WalletTypeInfo = Depends(require_admin_key),
):
    
    wallet_id = wallet.wallet.id
    nwcs = await get_wallet_nwcs(wallet_id, includeExpired)
    out = []
    for nwc in nwcs:
        budgets = await get_budgets_nwc(nwc.pubkey, calculateSpendBudget)
        res = NWCGetResponse(
            data=nwc,
            budgets=budgets
        )
        out.append(res)
    return  out



# Get a nwc key
@nwcprovider_ext.get("/api/v1/nwc/{pubkey}", status_code=HTTPStatus.OK, response_model=NWCGetResponse)
async def api_get_nwc(
    req: Request,
    pubkey: str,
    includeExpired: Optional[bool] = False,
    wallet: WalletTypeInfo = Depends(require_admin_key)
) -> NWCGetResponse:
    wallet_id = wallet.wallet.id
    nwc = await get_nwc(pubkey, wallet_id, includeExpired)
    res = NWCGetResponse(
        data=nwc,
        budgets=await get_budgets_nwc(pubkey)
    )
    return res
 
# Get pairing url for given secret
@nwcprovider_ext.get("/api/v1/pairing/{secret}", status_code=HTTPStatus.OK, response_model=str)
async def api_get_pairing_url(
    req: Request,
    secret: str
) -> str:
    pprivkey = await get_config_nwc("provider_key")
    relay = await get_config_nwc("relay")
    relay_alias = await get_config_nwc("relay_alias")
    if relay_alias:
        relay = relay_alias
    else:
        if relay == "nostrclient":
            scheme = req.url.scheme  # http or https
            netloc = req.url.netloc  # hostname and port
            if scheme=="http":
                scheme = "ws"
            else:
                scheme = "wss"
            netloc += "/nostrclient/api/v1/relay"
            relay = f"{scheme}://{netloc}"            
    psk = secp256k1.PrivateKey(bytes.fromhex(pprivkey))
    ppk = psk.pubkey
    ppubkey = ppk.serialize().hex()[2:]
    url = "nostr+walletconnect://"
    url += ppubkey
    url += "?relay="+relay
    url += "&secret="+secret
    #lud16=?
    return url

## Register a new nwc key
@nwcprovider_ext.put("/api/v1/nwc/{pubkey}", status_code=HTTPStatus.CREATED, response_model=NWCGetResponse)
async def api_register_nwc(
    req: Request, 
    pubkey: str, 
    registration_data: NWCRegistrationRequest,  # Use the Pydantic model here
    wallet: WalletTypeInfo = Depends(require_admin_key)
):
    wallet_id = wallet.wallet.id
    nwc = await create_nwc(pubkey, wallet_id, registration_data.description, registration_data.expires_at, registration_data.permissions, registration_data.budgets)
    budgets = await get_budgets_nwc(pubkey)
    res = NWCGetResponse(
        data=nwc,
        budgets=budgets
    )
    return res


# Delete a nwc key
@nwcprovider_ext.delete("/api/v1/nwc/{pubkey}", status_code=HTTPStatus.OK)
async def api_delete_nwc(
    req: Request, 
    pubkey: str, 
    wallet: WalletTypeInfo=Depends(require_admin_key)
):
    wallet_id = wallet.wallet.id
    await delete_nwc(pubkey, wallet_id)
    return JSONResponse(content={"message": f"NWC key {pubkey} deleted successfully."})




# Get config
@nwcprovider_ext.get("/api/v1/config", status_code=HTTPStatus.OK,  dependencies=[Depends(check_admin)])
async def api_get_all_config_nwc(
    req: Request, 
):
    config = await get_all_config_nwc()
    return config


# Get config
@nwcprovider_ext.get("/api/v1/config/{key}", status_code=HTTPStatus.OK,  dependencies=[Depends(check_admin)])
async def api_get_config_nwc(
    req: Request, 
    key:str
):
    config = await get_config_nwc(key)
    out = {}
    out[key] = config
    return out



# Set config
@nwcprovider_ext.post("/api/v1/config", status_code=HTTPStatus.OK,  dependencies=[Depends(check_admin)])
async def api_set_config_nwc(
    req: Request
):
    data = await req.json()
    for key, value in data.items():
        await set_config_nwc(key, value)
    return await api_get_all_config_nwc(req)
