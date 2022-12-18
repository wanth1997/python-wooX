import pytest
from wootrade import Client
import os
import datetime
from datetime import timezone
import pprint

API = os.getenv("API")
SECRET = os.getenv("SECRET")
APPLICATION_ID = os.getenv("APPLICATION_ID")


def test_create_client():
    try:
        client = Client(API, SECRET, APPLICATION_ID, testnet=True)
    except Exception as e:
        pytest.fail(e)


def test_get_exchange_info():
    client = Client(API, SECRET, APPLICATION_ID, testnet=True)
    info = client.get_exchange_info(symbol="SPOT_BTC_USDT")
    assert "success" in info and info["success"] == True
    assert "info" in info

    symbol = info["info"]
    assert "symbol" in symbol and symbol["symbol"] == "SPOT_BTC_USDT"


def test_funding_history():
    client = Client(API, SECRET, APPLICATION_ID, testnet=True)
    dt = datetime.datetime(2022, 12, 14)
    start_time = dt.replace(tzinfo=timezone.utc).timestamp()
    edt = datetime.datetime(2022, 12, 16)
    end_time = edt.replace(tzinfo=timezone.utc).timestamp()
    info = client.get_funding_rate_history(
        symbol="PERP_BTC_USDT", start_t=start_time, end_t=end_time
    )
    pprint.pprint(info)
    assert "success" in info and info["success"] == True
