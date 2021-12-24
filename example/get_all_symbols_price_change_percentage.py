from wootrade import Client

api = ""  # Fill your api key
secret = ""  # Fill your secret key
a_id = ""  # FIll your application id

client = Client(api, secret, a_id, testnet=False)
info = client.get_available_symbol()  # Get klines raw data

for data in info["rows"]:  # Parse raw data, check data format on WooX document
    symbol = data["symbol"]
    klines = client.get_klines(
        symbol=symbol, type="1d", limit=8
    )  # get the latest 8 kline
    before = klines["rows"][0]["open"]  # Kline data 7 days before
    tdy = klines["rows"][-1]["open"]  # Today kline data
    change = (tdy - before) / before * 100  # Get change percentage
    print(
        f"{symbol} 7 days before: {before}, today: {tdy}. Change %: {change}"
    )
