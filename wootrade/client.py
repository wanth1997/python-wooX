from typing import Dict, Optional, List, Tuple

import aiohttp
import asyncio
import hashlib
import hmac
import requests
import time
from urllib.parse import urlencode
from wootrade import WootradeAPIException, WootradeValueError
from wootrade import signature


class BaseClient:
    API_URL = "http://api.woo.network"
    API_TESTNET_URL = "http://api.staging.woo.network"
    WS_URL = "wss://wss.woo.network/ws/stream/{}"
    WS_TESTNET_URL = "wss://wss.staging.woo.network/ws/stream/{}"
    API_VERSION = "v1"

    def __init__(
        self,
        api: Optional[str] = None,
        secret: Optional[str] = None,
        application_id: str = "",
        testnet: bool = False,
    ):
        self.API_KEY = api
        self.API_SECRET = secret
        if not application_id:
            raise Exception("NoApplicationIdError")
        self.application_id = application_id
        self.testnet = testnet
        self.session = self._init_session()
        self.header = {}
        self._init_url(application_id)

    def _get_header(self) -> Dict:
        header = {
            "Content-Type": "application/x-www-form-urlencoded",
            "x-api-key": "",
            "x-api-signature": "",
            "x-api-timestamp": "",
        }
        if self.API_KEY:
            assert self.API_KEY
            header["x-api-key"] = self.API_KEY
        return header

    def _init_session(self):
        raise NotImplementedError

    def _init_url(self, application_id: str):
        self.api_url = self.API_URL
        self.ws_url = self.WS_URL

        if self.testnet:
            self.api_url = self.API_TESTNET_URL
            self.ws_url = self.WS_TESTNET_URL

        self.ws_url.format(application_id)

    def _handle_response(self, response: requests.Response):
        code = response.status_code
        if code == 200:
            return response.json()
        else:
            try:
                resp_json = response.json()
                raise WootradeAPIException(resp_json, code)
            except ValueError:
                raise WootradeValueError(response)


class Client(BaseClient):
    def __init__(
        self,
        api: Optional[str],
        secret: Optional[str],
        application_id: str,
        testnet: bool,
    ):
        super().__init__(
            api=api,
            secret=secret,
            application_id=application_id,
            testnet=testnet,
        )

    def _init_session(self) -> requests.Session:
        self.header = self._get_header()
        session = requests.session()
        session.headers.update(self.header)
        return session

    def _create_api_uri(self, ep: str, v: str = ""):
        if not v:
            v = self.API_VERSION
        else:
            v = v
        return self.api_url + "/" + v + "/" + ep

    def _request_api(
        self, method, ep: str, signed: bool, v: str = "", **kwargs
    ):
        uri = self._create_api_uri(ep, v)
        return self._request(method, uri, signed, **kwargs)

    def _get(self, ep, signed=False, v: str = "", **kwargs):
        return self._request_api("get", ep, signed, v, **kwargs)

    def _post(self, ep, signed=False, v: str = "", **kwargs) -> Dict:
        return self._request_api("post", ep, signed, v, **kwargs)

    def _put(self, ep, signed=False, v: str = "", **kwargs) -> Dict:
        return self._request_api("put", ep, signed, v, **kwargs)

    def _delete(self, ep, signed=False, v: str = "", **kwargs) -> Dict:
        return self._request_api("delete", ep, signed, v, **kwargs)

    def _request(self, method, uri: str, signed: bool, **kwargs):
        sorted_arg = {key: value for key, value in sorted(kwargs.items())}
        if signed:
            ts = str(int(time.time() * 1000))
            sig = signature(ts, self.API_SECRET, **sorted_arg)
            self.header["x-api-signature"] = sig
            self.header["x-api-timestamp"] = ts
            self.session.headers.update(self.header)

        self.response = getattr(self.session, method)(uri, params=sorted_arg)
        return self._handle_response(self.response)

    def get_exchange_info(self, symbol: str) -> Dict:
        return self._get(f"public/info/{symbol}")

    def get_available_symbol(self) -> Dict:
        return self._get("public/info")

    def get_market_trades(self, **params) -> Dict:
        return self._get("public/market_trades", **params)

    def get_available_token(self) -> Dict:
        return self._get("public/token")

    def send_order(self, **params) -> Dict:
        return self._post("order", True, **params)

    def cancel_order(self, **params) -> Dict:
        return self._delete("order", True, **params)

    def cancel_orders(self, **params) -> Dict:
        return self._delete("orders", True, **params)

    def cancel_order_by_client_order_id(self, **params) -> Dict:
        return self._delete("client/order", True, **params)

    def get_order(self, oid) -> Dict:
        return self._get(f"order/{oid}", True)

    def get_order_by_client_order_id(self, oid) -> Dict:
        return self._get("client/order/{oid}", True)

    def get_orders(self, **params) -> Dict:
        return self._get("orders", True, **params)

    def get_current_holding(self, **params) -> Dict:
        return self._get("client/holding", True, "v2", **params)

    def get_account_info(self) -> Dict:
        return self._get("client/info", True)

    def get_market_trades(self, **params) -> Dict:
        return self._get("public/market_trades", **params)

class AsyncClient(BaseClient):
    def __init__(
        self,
        api: Optional[str],
        secret: Optional[str],
        application_id: str,
        testnet: bool,
        loop=None,
    ):
        self.loop = loop or asyncio.get_event_loop()
        super().__init__(
            api=api,
            secret=secret,
            application_id=application_id,
            testnet=testnet,
        )

    @classmethod
    async def create(
        cls,
        api: Optional[str],
        secret: Optional[str],
        application_id: str,
        testnet: bool,
        loop=None,
    ):
        self = cls(api, secret, application_id, testnet, loop)
        return self

    def _init_session(self) -> aiohttp.ClientSession:
        session = aiohttp.ClientSession(
            loop=self.loop, headers=self._get_header()
        )
        return session

    async def close_connection(self):
        if self.session:
            assert self.session
            await self.session.close()

    async def _request(self, method, uri: str, signed: bool, **kwargs):
        sorted_arg = {key: value for key, value in sorted(kwargs.items())}
        if signed:
            ts = str(int(time.time() * 1000))
            sig = signature(ts, self.API_SECRET, **sorted_arg)
            self.header["x-api-signature"] = sig
            self.header["x-api-timestamp"] = ts
            self.session.headers.update(self.header)

        async with getattr(self.session, method)(
            uri, params=sorted_arg
        ) as response:
            self.response = response
            return await self._handle_response(response)

    async def _handle_response(self, response: requests.Response):
        code = response.status_code
        if code == 200:
            return response.json()
        else:
            try:
                resp_json = response.json()
                raise WootradeAPIException(resp_json, code)
            except ValueError:
                raise WootradeValueError(response)

    async def _request_api(
        self, method, ep: str, signed: bool, v: str = "", **kwargs
    ):
        uri = self._create_api_uri(ep, v)
        return self._request(method, uri, signed, **kwargs)

    async def _get(self, ep, signed=False, v: str = "", **kwargs):
        return await self._request_api("get", ep, signed, v, **kwargs)

    async def _post(self, ep, signed=False, v: str = "", **kwargs) -> Dict:
        return await self._request_api("post", ep, signed, v, **kwargs)

    async def _put(self, ep, signed=False, v: str = "", **kwargs) -> Dict:
        return await self._request_api("put", ep, signed, v, **kwargs)

    async def _delete(self, ep, signed=False, v: str = "", **kwargs) -> Dict:
        return await self._request_api("delete", ep, signed, v, **kwargs)

    async def get_available_symbol(self):
        return await self._get("public/info")
