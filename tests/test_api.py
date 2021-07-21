import pytest
from wootrade.clinet import Client
import os

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
    print(API)
    assert "success" in info and info["success"] == True
    assert "info" in info

    symbol = info["info"]
    assert "symbol" in symbol and symbol["symbol"] == "SPOT_BTC_USDT"
