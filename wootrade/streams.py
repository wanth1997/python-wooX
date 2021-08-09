import asyncio
import gzip
import json
import logging
import time
from enum import Enum
from random import random
from typing import Optional, List, Dict, Callable, Any

import websockets as ws
from wootrade import AsyncClient
from wootrade import signature
from .threaded_stream import ThreadedApiManager

KEEPALIVE_TIMEOUT = 5 * 60  # 5 minutes


class WSListenerState(Enum):
    INITIALISING = "Initialising"
    STREAMING = "Streaming"
    RECONNECTING = "Reconnecting"
    EXITING = "Exiting"


class ReconnectingWebsocket:
    MAX_RECONNECTS = 5
    MAX_RECONNECT_SECONDS = 60
    TIMEOUT = 60

    def __init__(
        self,
        loop,
        url: str,
        name: Optional[str] = None,
        is_binary: bool = False,
        exit_coro=None,
    ):
        self._loop = loop or asyncio.get_event_loop()
        self._log = logging.getLogger(__name__)
        self._name = name
        self._url = url
        self._exit_coro = exit_coro
        self._reconnects = 0
        self._is_binary = is_binary
        self._conn = None
        self._socket = None
        self.ws: Optional[ws.WebSocketClientProtocol] = None
        self.ws_state = WSListenerState.INITIALISING
        self._queue = asyncio.Queue(loop=self._loop)

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._exit_coro:
            await self._exit_coro(self._name)
        self.ws_state = WSListenerState.EXITING
        if self.ws:
            self.ws.fail_connection()
        if self._conn:
            await self._conn.__aexit__(exc_type, exc_val, exc_tb)
        self.ws = None

    async def connect(self):
        await self._before_connect()
        assert self._name
        self._conn = ws.connect(self._url, close_timeout=0.001)
        try:
            self.ws = await self._conn.__aenter__()
        except:  # noqa
            await self._reconnect()
            return
        self.ws_state = WSListenerState.STREAMING

        self._reconnects = 0
        await self._after_connect()
        self._loop.call_soon_threadsafe(asyncio.create_task, self._read_loop())

    async def _run(self):
        pass

    async def send_msg(self, msg):
        while not self.ws:
            time.sleep(0.1)
        await self.ws.send(json.dumps(msg))

    async def _before_connect(self):
        pass

    async def _after_connect(self):
        pass

    def _handle_message(self, evt):
        if self._is_binary:
            try:
                evt = gzip.decompress(evt)
            except (ValueError, OSError):
                return None
        try:
            return json.loads(evt)
        except ValueError:
            self._log.debug(f"error parsing evt json:{evt}")
            return None

    async def _read_loop(self):
        while True:
            res = None
            if not self.ws or self.ws_state != WSListenerState.STREAMING:
                await self._wait_for_reconnect()
                break
            if self.ws_state == WSListenerState.EXITING:
                break
            if self.ws.state == ws.protocol.State.CLOSING:
                break
            if self.ws.state == ws.protocol.State.CLOSED:
                try:
                    await self._reconnect()
                except Exception as e:
                    print(e)
                else:
                    break
            try:
                res = await asyncio.wait_for(
                    self.ws.recv(), timeout=self.TIMEOUT
                )
            except asyncio.TimeoutError:
                logging.debug(f"no message in {self.TIMEOUT} seconds")
                await self._reconnect()
            except asyncio.CancelledError as e:
                logging.debug(f"cancelled error {e}")
                break
            except asyncio.IncompleteReadError as e:
                logging.debug(f"incomplete read error {e}")
            except Exception as e:
                logging.debug(f"exception {e}")
                await self._reconnect()
                break
            else:
                if self.ws_state in (
                    WSListenerState.EXITING,
                    WSListenerState.RECONNECTING,
                ):
                    break
                res = self._handle_message(res)
                if self.ws_state in (
                    WSListenerState.EXITING,
                    WSListenerState.RECONNECTING,
                ):
                    break

            if res and self._queue.qsize() < 100:
                await self._queue.put(res)

    async def recv(self):
        res = None
        while not res:
            try:
                res = await asyncio.wait_for(
                    self._queue.get(), timeout=self.TIMEOUT
                )
            except asyncio.TimeoutError:
                logging.debug(f"no message in {self.TIMEOUT} seconds")
        return res

    async def _wait_for_reconnect(self):
        while self.ws_state == WSListenerState.RECONNECTING:
            logging.debug("reconnecting waiting for connect")
        if not self.ws:
            logging.debug("ignore message no ws")
        else:
            logging.debug(f"ignore message {self.ws_state}")

    def _get_reconnect_wait(self, attempts: int) -> int:
        expo = 2 ** attempts
        return round(random() * min(self.MAX_RECONNECT_SECONDS, expo - 1) + 1)

    async def before_reconnect(self):
        if self.ws:
            await self._conn.__aexit__(None, None, None)
            self.ws = None
        self._reconnects += 1

    def _no_message_received_reconnect(self):
        logging.debug("No message received, reconnecting")
        asyncio.create_task(self._reconnect())

    async def _reconnect(self):
        if self.ws_state == WSListenerState.RECONNECTING:
            return
        self.ws_state = WSListenerState.RECONNECTING
        await self.before_reconnect()
        if self._reconnects < self.MAX_RECONNECTS:
            reconnect_wait = self._get_reconnect_wait(self._reconnects)
            logging.debug(
                f"websocket reconnecting {self.MAX_RECONNECTS - self._reconnects} reconnects left - "
                f"waiting {reconnect_wait}"
            )
            await asyncio.sleep(reconnect_wait)
            await self.connect()
        else:
            logging.error(f"Max reconnections {self.MAX_RECONNECTS} reached:")
            raise "MaximumReconnectRetry"


class WootradeSocketManager:
    STREAM_URL = "wss://wss.woo.network/ws/stream/{}"
    STREAM_TESTNET_URL = "wss://wss.staging.woo.network/ws/stream/{}"
    PSTREAM_URL = "wss://wss.woo.network/v2/ws/private/stream/{}"
    PSTREAM_TESTNET_URL = (
        "wss://wss.staging.woo.network/v2/ws/private/stream/{}"
    )

    def __init__(
        self,
        client: AsyncClient,
        loop=None,
    ):
        self._conns = {}
        self._loop = loop or asyncio.get_event_loop()
        self._client = client
        self.testnet = self._client.testnet
        self._log = logging.getLogger("WootradeSocketManager")
        self._init_stream_url(client.application_id)

    def _init_stream_url(self, app_id):
        self.STREAM_URL = self.STREAM_URL.format(app_id)
        self.STREAM_TESTNET_URL = self.STREAM_TESTNET_URL.format(app_id)
        self.PSTREAM_URL = self.PSTREAM_URL.format(app_id)
        self.PSTREAM_TESTNET_URL = self.PSTREAM_TESTNET_URL.format(app_id)

        self.ws_url = self.STREAM_URL
        self.private_ws_url = self.PSTREAM_URL
        if self.testnet:
            self.ws_url = self.STREAM_TESTNET_URL
            self.private_ws_url = self.PSTREAM_TESTNET_URL

    def _get_socket(
        self, socket_name: str, is_binary: bool = False, auth: bool = False
    ) -> str:
        conn_id = f"{socket_name}"
        if auth:
            url = self.private_ws_url
        else:
            url = self.ws_url
        if conn_id not in self._conns:
            self._conns[conn_id] = ReconnectingWebsocket(
                loop=self._loop,
                name=socket_name,
                url=url,
                exit_coro=self._exit_socket,
                is_binary=is_binary,
            )

        return self._conns[conn_id]

    async def subscribe(self, conn_name: str, **params):
        try:
            await self._conns[conn_name].send_msg(params)
        except KeyError:
            self._log.warning(
                f"Connection name: <{conn_name}> not create and start!"
            )

    async def _exit_socket(self, name: str):
        await self._stop_socket(name)

    def get_socket(self, socket_name, auth: bool = False):
        return self._get_socket(socket_name, auth=auth)

    async def _stop_socket(self, conn_key):
        if conn_key not in self._conns:
            return

        del self._conns[conn_key]


class ThreadedWebsocketManager(ThreadedApiManager):
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        application_id: str = "",
        testnet: bool = False,
    ):
        super().__init__(api_key, api_secret, application_id, testnet)
        self._bsm: Optional[WootradeSocketManager] = None
        self.api = api_key
        self.secret = api_secret

    async def _before_socket_listener_start(self):
        assert self._client
        self._bsm = WootradeSocketManager(client=self._client, loop=self._loop)

    def _start_socket(
        self,
        callback: Callable,
        socket_name: str,
        auth: bool = False,
    ) -> str:
        while not self._bsm:
            time.sleep(0.1)

        socket = getattr(self._bsm, "get_socket")(socket_name, auth=auth)
        name = socket._name
        self._socket_running[name] = True
        self._loop.call_soon_threadsafe(
            asyncio.create_task,
            self.start_listener(socket, socket._name, callback, self.ping),
        )

        return socket

    def start_socket(
        self,
        callback: Callable,
        socket_name: str,
        auth: bool = False,
    ) -> str:
        return self._start_socket(
            callback=callback,
            socket_name=socket_name,
            auth=auth,
        )

    def subscribe(self, conn_name: str, **params):
        while not self._bsm:
            time.sleep(0.1)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            loop.create_task(self._bsm.subscribe(conn_name, **params))
        else:
            asyncio.run(self._bsm.subscribe(conn_name, **params))

    def authentication(self, conn_name="private_connection"):
        ts = str(int(time.time() * 1000))
        sign = signature(ts, self.secret)
        params = {}
        params["apikey"] = self.api
        params["sign"] = sign
        params["timestamp"] = ts
        self.subscribe(
            conn_name=conn_name, id=conn_name, event="auth", params=params
        )

    def ping(self, name):
        self.subscribe(name, event="pong")
