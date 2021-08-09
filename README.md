# Package User Zone

## Installation

```bash
pip install python-wootrade
```

## Sample Code
### Restful Api
```python
from wootrade import Client
import os

API = os.getenv("API")
SECRET = os.getenv("SECRET")
APPLICATION_ID = os.getenv("APPLICATION_ID")

client = Client(API, SECRET, APPLICATION_ID, testnet=True)
info = client.get_exchange_info(symbol="SPOT_BTC_USDT")
print(info)
```

### Websocket

```python
from wootrade import ThreadedWebsocketManager

def on_read(payload):
    print(payload)

API = os.getenv("API")
SECRET = os.getenv("SECRET")
APPLICATION_ID = os.getenv("APPLICATION_ID")

wsm = ThreadedWebsocketManager(API, SECRET, APPLICATION_ID, testnet=True)
wsm.start()

# Un-auth subscribe
name = 'market_connection'
wsm.start_socket(on_read, conn_name=name, auth=False)
wsm.subscribe(name, topic="SPOT_BTC_USDT@kline_1m", id="ClientID", event="subscribe")

# Auth subscribe
name = 'private_connection'
wsm.start_socket(on_read, conn_name=name, auth=True)
wsm.authentication(conn_name=name)
wsm.subscribe(
    name,
    topic="executionreport",
    id="ClientID",
    event="subscribe",
)
```
# Developer Zone

## Lint

```bash
$ make lint
```

## Test

```bash
# Should Set up env variable API, SECRET and APPLICATION_ID in tox.ini
$ make test 
```

## Donation
**I put dontaion address here because all open source Crypto API did. It seems unprofessional if I don't**

WOO:0xB32A3CbEaD5667e026CCEC7118b132DCA349A8e6

ETH:0xB32A3CbEaD5667e026CCEC7118b132DCA349A8e6
