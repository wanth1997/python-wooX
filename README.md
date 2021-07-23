# python-wootrade

## Lint

```bash
$ make lint
```

## Test

```bash
$ make test #need to set up API and SECRET and application id
```

## Sample Code

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
