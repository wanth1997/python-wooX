import asyncio
import threading
from typing import Callable, Optional, Dict
from woox import AsyncClient


class ThreadedApiManager(threading.Thread):
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        application_id: str = "",
        testnet: bool = False,
    ):
        """Initialise the wooxSocketManager"""
        super().__init__()
        self._loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
        self._client: Optional[AsyncClient] = None
        self._running: bool = True
        self._socket_running: Dict[str, bool] = {}
        self._client_params = {
            "api": api_key,
            "secret": api_secret,
            "application_id": application_id,
            "testnet": testnet,
        }

    async def _before_socket_listener_start(self):
        ...

    async def socket_listener(self):
        self._client = await AsyncClient.create(
            loop=self._loop, **self._client_params
        )
        await self._before_socket_listener_start()
        while self._running:
            await asyncio.sleep(0.2)
        while self._socket_running:
            await asyncio.sleep(0.2)

    async def start_listener(
        self, socket, name: str, callback, ping: Optional[Callable] = None
    ):
        async with socket as s:
            while self._socket_running[name]:
                try:
                    msg = await asyncio.wait_for(s.recv(), 3)
                except asyncio.TimeoutError:
                    ...
                    continue
                if not msg:
                    continue
                if "event" in msg and msg["event"] == "ping":
                    ping(name)
                callback(msg)
        del self._socket_running[name]

    def run(self):
        self._loop.run_until_complete(self.socket_listener())

    def stop_socket(self, socket_name):
        if socket_name in self._socket_running:
            self._socket_running[socket_name] = False

    async def stop_client(self):
        await self._client.close_connection()

    def stop(self):
        if not self._running:
            return
        self._running = False
        self._loop.call_soon(asyncio.create_task, self.stop_client())
        for socket_name in self._socket_running.keys():
            self._socket_running[socket_name] = False
