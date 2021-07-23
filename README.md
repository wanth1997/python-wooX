# python-wootrade

## Package User Zone

### Pre-request

```bash
pip install python-wootrade # Not Done yet
```

### Sample Code
#### Restful Api
```python
from wootrade.clinet import Client
import os

API = os.getenv("API")
SECRET = os.getenv("SECRET")
APPLICATION_ID = os.getenv("APPLICATION_ID")

client = Client(API, SECRET, APPLICATION_ID, testnet=True)
info = client.get_exchange_info(symbol="SPOT_BTC_USDT")
print(info)
```

#### Websocket

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
wsm.start_socket(on_read, conn_name="market_connection", auth=False)
wsm.subscribe("market_connection", topic="SPOT_BTC_USDT@kline_1m", id="ClientID", event="subscribe")

# Auth subscribe
wsm.start_socket(on_read, conn_name="private_connection", auth=True)
wsm.authentication(conn_name="private_connection")
wsm.subscribe(
    "private_connection",
    topic="executionreport",
    id="ClientID",
    event="subscribe",
)
```

## Developer Zone

### Lint

```bash
$ make lint
```

### Test

```bash
# Should Set up env variable API, SECRET and APPLICATION_ID in tox.ini
$ make test 
```

