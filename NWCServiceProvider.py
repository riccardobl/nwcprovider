import asyncio
import hashlib
import json
from typing import Dict
import secp256k1
from loguru import logger
from lnbits.settings import settings
import time
import websockets
from Cryptodome import Random
from Cryptodome.Cipher import AES
import base64
import random
from typing import Union, List, Callable, Tuple
from lnbits.app import settings
from lnbits.helpers import encrypt_internal_message
from urllib.parse import quote

class MainSubscription:
    def __init__(self):
        self.requests_sub_id = None
        self.responses_sub_id = None
        self.requests_eose = False
        self.responses_eose = False
        self.events:Dict[str, Dict] = {}
        self.responses:List[str] = []
    
    def getStale(self) -> List[Dict]:
        pending_events = []
        for [id, event] in self.events.items():
            if not id in self.responses:
                pending_events.append(event)
        return pending_events
    
    def registerResponse(self, event_id:str):
        if not event_id in self.responses:
            self.responses.append(event_id)


class NWCServiceProvider:
    def __init__(self, private_key:str=None, relay:str=None):
        if not relay: # Connect to nostrclient
            relay = "nostrclient"
        if relay == "nostrclient":
            relay=f"ws://localhost:{settings.port}/nostrclient/api/v1/relay"
        elif relay == "nostrclient:private":
            relay_endpoint = encrypt_internal_message("relay")
            relay=f"ws://localhost:{settings.port}/nostrclient/api/v1/{relay_endpoint}"
        self.relay = relay

        if not private_key: # Create random key
            private_key = bytes.hex(secp256k1._gen_private_key())
        
        self.private_key = secp256k1.PrivateKey(bytes.fromhex(private_key))
        self.private_key_hex = private_key
        self.public_key = self.private_key.pubkey
        self.public_key_hex = self.public_key.serialize().hex()[2:]

        self.supported_methods = []
        
        self.subscriptions_count = 0

        self.request_listeners = {}

        self.reconnect_task = None

        self.sub = None

        # websocket connection
        self.ws = None
        # if True the websocket is connected
        self.connected = False
        # if True the wallet is shutting down
        self.shutdown = False

        logger.info("NWC Service is ready. relay: "+str(self.relay)+" pubkey: " +
                    self.public_key_hex)
        
    def getSupportedMethods(self):
        return self.supported_methods

    def addRequestListener(self, method: str, l: Callable[["NWCConnector", str, Dict], List[Tuple[Dict, Dict]]]):
        if not method in self.supported_methods:
            self.supported_methods.append(method)
        self.request_listeners[method] = l

    async def start(self):
        """
        Starts the NWC service connection.
        """
        self.reconnect_task = asyncio.create_task(self._connect_to_relay())


    def _json_dumps(self, data: Union[Dict, list]) -> str:
        """
        Converts a Python dictionary to a JSON string with compact encoding.

        Args:
            data (Dict): The dictionary to be converted.
        
        Returns:
            str: The compact JSON string.
        """
        if isinstance(data, Dict):
            data = {k: v for k, v in data.items() if v is not None}
        return json.dumps(data, separators=(',', ':'), ensure_ascii=False)

    def _is_shutting_down(self) -> bool:
        """
        Returns True if the wallet is shutting down.
        """
        return self.shutdown or not settings.lnbits_running

    async def _send(self, data: Dict):
        """
        Sends data to the NWC relay.

        Args:
            data (Dict): The data to be sent.
        """
        if self._is_shutting_down():
            logger.warning("Trying to send data while shutting down")
            return
        await self._wait_for_connection()  # ensure the connection is established
        tx = self._json_dumps(data)
        await self.ws.send(tx)

    def _get_new_subid(self) -> str:
        """
        Generates a unique subscription id.

        Returns:
            str: The generated 64 characters long subscription id (eg. lnbits0abc...)
        """
        subid = "lnbitsnwcs"+str(self.subscriptions_count)
        self.subscriptions_count += 1
        maxLength = 64
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        n = maxLength - len(subid)
        if n > 0:
            for i in range(n):
                subid += chars[random.randint(0, len(chars) - 1)]
        return subid


    async def _wait_for_connection(self):
        """
        Waits until the wallet is connected to the relay.
        """
        while not self.connected:
            if self._is_shutting_down():
                raise Exception("Connection is closing")
            logger.debug("Waiting for connection...")
            await asyncio.sleep(1)


    async def _subscribe(self):
        """
        [Re]Subscribe to receive nip 47 requests and responses from the relay
        """
        self.sub = MainSubscription()
        
        # Create requests subscription
        req_filter = {
            "kinds": [23194],
            "#p": [self.public_key_hex],
            # Since the last 3 hours (handles reboots)
            "since": int(time.time()) - 3*60*60
        }
        self.sub.requests_sub_id = self._get_new_subid()
        # Create responses subscription (needed to track previosly responded requests)
        res_filter = {
            "kinds": [23195],
            "authors": [self.public_key_hex],
            "since": int(time.time()) - 3*60*60
        }
        self.sub.responses_sub_id = self._get_new_subid()
        # Subscribe
        await self._send(["REQ", self.sub.requests_sub_id, req_filter])
        await self._send(["REQ", self.sub.responses_sub_id, res_filter])

    async def _on_connection(self,ws):
        """
        On connection callback, announce the service provider methods and subscribe to nip67 events.
        """
        # Send info event
        event = {
            "kind": 13194,
            "content": " ".join(self.supported_methods),
            "created_at": int(time.time()),
            "tags": [
                ["p", self.public_key_hex]
            ]
        }
        self._sign_event(event)
        await self._send(["EVENT", event])
        # Resubscribe to nwc events
        await self._subscribe()
    

    async def _handle_request(self, event):
        """
        Handle a nwc request
        """
        nwc_pubkey = event["pubkey"]        
        content = event["content"]
        # Decrypt the content
        content = self._decrypt_content(content, nwc_pubkey)
        # Deserialize content
        content = json.loads(content)
        # Handle request
        method = content["method"]
        l = self.request_listeners.get(method, None)
        outs = []
        if not l:
            outs.append({
                "error": {
                    "code": "NOT_IMPLEMENTED",
                    "message": "Method "+method+" is not implemented by this service provider"
                }
            })
        else:
            try:
                results = await l(self, nwc_pubkey, content)
                for result in results:
                    r = result[0]
                    e = result[1]
                    t = result[2] if len(result) > 2 else None
                    out = {}
                    if r: out["result"] = r
                    if e: out["error"] = e
                    if t: out["tags"] = t
                    outs.append(out)
            except Exception as e:
                outs.append({
                    "code": "INTERNAL",
                    "message": str(e)
                })
        for out in outs:
            # Finalize output
            out["result_type"] = method
            # Prepare response event
            res = {
                "kind": 23195,
                "created_at": int(time.time()),
                "tags": out.get("tags", []),
                "content": self._json_dumps(out),
            }
            # Reference request
            res["tags"].append(["e", event["id"]])
            # Reference user
            res["tags"].append(["p", nwc_pubkey])
            # Finalize response event
            res["content"] = self._encrypt_content(res["content"], nwc_pubkey)
            self._sign_event(res)
            # Register response for this request, so we knows it is not stale
            self.sub.registerResponse(event["id"])
            # Send response event

            await self._send(["EVENT", res])
        
 
 
    async def _on_message(self, ws, message: str):
        """
        Handle incoming messages from the relay.
        """
        try:
            msg = json.loads(message)
            if msg[0] == "EVENT":  # Event message
                sub_id = msg[1]
                event = msg[2]
                # Ensure the event is valid (do not trust relays)
                if not self._verify_event(event):
                    raise Exception("Invalid event signature")                                
                tags = event["tags"]          
                expiration = -1
                for tag in tags:
                    if tag[0] == "expiration":
                        expiration = int(tag[1])
                        break
                # Handle event expiration if the relay doesn't support nip 40
                if expiration > 0 and expiration < int(time.time()):
                    logger.debug("Event expired")      
                    return 
                if event["kind"] == 23194 and sub_id == self.sub.requests_sub_id:
                    # Ensure the request is for this service provider
                    valid_p = False
                    for tag in tags:
                        if tag[0] == "p" and tag[1] == self.public_key_hex:
                            valid_p = True
                            break
                    if not valid_p:
                        raise Exception("Unexpected request from another service")
                    # Track request
                    self.sub.events[event["id"]] = event
                    # if eose was received for both subscriptions, we handle the request in realtime
                    # if not, we do nothing since the request may be already handled or stale,
                    # all stale requests will be handled later when eose is received
                    if self.sub.requests_eose and self.sub.responses_eose:
                        await self._handle_request(event)
                elif event["kind"] == 23195 and sub_id == self.sub.responses_sub_id:
                    # Ensure the response is from this service provider
                    if event["pubkey"] != self.public_key_hex:
                        raise Exception("Unexpected response from another service")
                    # Register as response for each e tag (request event id)
                    # Note: usually we expect only one "e" tag, but we are handling multiple "e" tags just in case
                    for tag in tags:
                        if tag[0] == "e":
                            self.sub.registerResponse(tag[1])
            elif msg[0] == "EOSE":            
                sub_id = msg[1]
                # Track EOSE                
                if sub_id == self.sub.requests_sub_id:
                    self.sub.requests_eose = True
                elif sub_id == self.sub.responses_sub_id:
                    self.sub.responses_eose = True
                # When both EOSE are receives, handle all the stale requests
                #   Note: All the requests that were received prior to the service connection
                #   and do not have a response yet, are considered stale, we will process them now
                if self.sub.requests_eose and self.sub.responses_eose:
                    stales = self.sub.getStale()
                    for stale in stales:
                        await self._handle_request(stale)
            elif msg[0] == "CLOSED":
                # Subscription was closed remotely.
                sub_id = msg[1]
                info = msg[2] or "" if len(msg) > 2 else ""
                # Resubscribe if one of the main subscriptions was closed
                if sub_id == self.sub.requests_sub_id or sub_id == self.sub.responses_sub_id:
                    logger.warning("Subscription "+sub_id+" was closed remotely: "+info+" ... resubscribing...")
                    self._subscribe()
            elif msg[0] == "NOTICE":
                # A message from the relay, mostly useless, but we log it anyway
                logger.info("Notice from relay "+self.relay+": "+str(msg[1]))
            elif msg[0] == "OK":
                pass
            else:
                raise Exception("Unknown message type")
        except Exception as e:
            logger.error("Error parsing event: "+str(e))

    async def _connect_to_relay(self):
        """
        Initiate websocket connection to the relay.
        """
        await asyncio.sleep(1)  
        logger.debug("Connecting to NWC relay "+self.relay)
        while not self._is_shutting_down():  # Reconnect until the wallet is shutting down
            logger.debug('Creating new connection...')
            try:
                async with websockets.connect(self.relay) as ws:
                    self.ws = ws
                    self.connected = True
                    await self._on_connection(ws)
                    while not self._is_shutting_down():  # receive messages until the wallet is shutting down
                        try:
                            reply = await ws.recv()
                            await self._on_message(ws, reply)
                        except Exception as e:
                            logger.debug("Error receiving message: " + str(e))
                            break
                logger.debug("Connection to NWC relay closed")
            except Exception as e:
                logger.error("Error connecting to NWC relay: "+str(e))
                await asyncio.sleep(5)
            # the connection was closed, so we set the connected flag to False
            # this will make the methods calling _wait_for_connection() to wait until the connection is re-established
            self.connected = False
            if not self._is_shutting_down():
                # Wait some time before reconnecting
                logger.debug("Reconnecting to NWC relay in 5 seconds...")
                await asyncio.sleep(5)

    def _encrypt_content(self, content: str, pubkey_hex:str) -> str:
        """
        Encrypts the content to be sent to the service.

        Args:
            content (str): The content to be encrypted.

        Returns:
            str: The encrypted content.
        """
        pubkey = secp256k1.PublicKey(
            bytes.fromhex("02" + pubkey_hex), True)
        
        shared = pubkey.tweak_mul(bytes.fromhex(
            self.private_key_hex)).serialize()[1:]
        # random iv (16B)
        iv = Random.new().read(AES.block_size)
        aes = AES.new(shared, AES.MODE_CBC, iv)
        # padding
        def pad(s): return s + (16 - len(s) % 16) * chr(16 - len(s) % 16)
        content = pad(content).encode("utf-8")
        # Encrypt
        encryptedB64 = base64.b64encode(aes.encrypt(content)).decode("ascii")
        ivB64 = base64.b64encode(iv).decode("ascii")
        encryptedContent = encryptedB64 + "?iv=" + ivB64
        return encryptedContent

    def _decrypt_content(self, content: str , pubkey_hex:str) -> str:
        """
        Decrypts the content coming from the service.

        Args:
            content (str): The encrypted content.

        Returns:
            str: The decrypted content.
        """
        pubkey = secp256k1.PublicKey(
            bytes.fromhex("02" + pubkey_hex), True)

        shared = pubkey.tweak_mul(bytes.fromhex(
            self.private_key_hex)).serialize()[1:]
        # extract iv and content
        (encryptedContentB64, ivB64) = content.split("?iv=")
        encryptedContent = base64.b64decode(
            encryptedContentB64.encode("ascii"))
        iv = base64.b64decode(ivB64.encode("ascii"))
        # Decrypt
        aes = AES.new(shared, AES.MODE_CBC, iv)
        decrypted = aes.decrypt(encryptedContent).decode("utf-8")
        def unpad(s): return s[:-ord(s[len(s)-1:])]
        return unpad(decrypted)

    def _verify_event(self, event: Dict) -> bool:
        """
        Signs the event (in place) with the service secret

        Args:
            event (Dict): The event to be signed.

        Returns:
            Dict: The input event with the signature added.
        """
        signature_data = self._json_dumps([
            0,
            event["pubkey"],
            event["created_at"],
            event["kind"],
            event["tags"],
            event["content"]
        ])
        event_id = hashlib.sha256(signature_data.encode()).hexdigest()
        if event_id != event["id"]:  # Invalid event id
            return False
        pubkeyHex = event["pubkey"]
        pubkey = secp256k1.PublicKey(bytes.fromhex("02" + pubkeyHex), True)
        if not pubkey.schnorr_verify(bytes.fromhex(event_id), bytes.fromhex(event["sig"]), None, raw=True):
            return False
        return True

    def _sign_event(self, event: Dict) -> Dict:
        """
        Signs the event (in place) with the service secret

        Args:
            event (Dict): The event to be signed.

        Returns:
            Dict: The input event with the signature added.
        """
        signature_data = self._json_dumps([
            0,
            self.public_key_hex,
            event["created_at"],
            event["kind"],
            event["tags"],
            event["content"]
        ])

        event_id = hashlib.sha256(signature_data.encode()).hexdigest()
        event["id"] = event_id
        event["pubkey"] = self.public_key_hex

        signature = (self.private_key.schnorr_sign(
            bytes.fromhex(event_id), None, raw=True)).hex()
        event["sig"] = signature
        return event

    async def cleanup(self):
        logger.debug("Closing NWC Service Provider connection")
        self.shutdown = True  # Mark for shutdown
        # close tasks
        try:
            if self.reconnect_task:
                self.reconnect_task.cancel()
        except Exception as e:
            logger.warning("Error closing reconnection task: "+str(e))
        # close the websocket
        try:
            if self.ws:
                await self.ws.close()
        except Exception as e:
            logger.warning("Error closing websocket connection: "+str(e))
