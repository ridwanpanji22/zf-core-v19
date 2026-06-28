def normalize(channel: str, raw_data: dict) -> dict:
    """Normalize raw data from OKX channels into standard internal format.

    Standard format:
    {
        "symbol": str, (e.g. 'BTC-USDT-SWAP')
        "timestamp": int, (UTC epoch ms)
        "type": str, (ticker|trade|book|funding|oi|liquidation)
        "data": dict
    }
    """
    symbol = raw_data.get("arg", {}).get("instId", "UNKNOWN")
    data_list = raw_data.get("data", [])
    if not data_list:
        return {}

    first_data = data_list[0]

    if channel == "tickers":
        return {
            "symbol": symbol,
            "timestamp": int(first_data.get("ts", 0)),
            "type": "ticker",
            "data": {
                "last": first_data.get("last"),
                "volume_24h": first_data.get("vol24h"),
                "high_24h": first_data.get("high24h"),
                "low_24h": first_data.get("low24h"),
                "open_24h": first_data.get("sopen")
            }
        }

    elif channel == "trades":
        trades_normalized = []
        for item in data_list:
            trades_normalized.append({
                "tradeId": item.get("tradeId"),
                "price": item.get("px"),
                "size": item.get("sz"),
                "side": item.get("side"),
                "ts": int(item.get("ts", 0))
            })
        return {
            "symbol": symbol,
            "timestamp": int(first_data.get("ts", 0)) if data_list else 0,
            "type": "trade",
            "data": trades_normalized
        }

    elif channel.startswith("books"):
        # Normalizing orderbook depth
        bids = [[item[0], item[1]] for item in first_data.get("bids", [])] # [price, size]
        asks = [[item[0], item[1]] for item in first_data.get("asks", [])] # [price, size]
        return {
            "symbol": symbol,
            "timestamp": int(first_data.get("ts", 0)),
            "type": "book",
            "data": {
                "bids": bids,
                "asks": asks
            }
        }

    elif channel == "funding-rate":
        return {
            "symbol": symbol,
            "timestamp": int(first_data.get("fundingTime", 0)),
            "type": "funding",
            "data": {
                "funding_rate": first_data.get("fundingRate"),
                "next_funding_rate": first_data.get("nextFundingRate")
            }
        }

    elif channel == "open-interest":
        return {
            "symbol": symbol,
            "timestamp": int(first_data.get("ts", 0)),
            "type": "oi",
            "data": {
                "oi": first_data.get("oi"),
                "oi_usd": first_data.get("oiCcy")
            }
        }

    elif channel == "liquidation-orders":
        details = first_data.get("bkDetails", [])
        liquidations = []
        for det in details:
            liquidations.append({
                "price": det.get("bkPx"),
                "size": det.get("sz"),
                "side": det.get("side"), # buy/sell
                "loss": det.get("loss")
            })
        return {
            "symbol": symbol,
            "timestamp": int(first_data.get("ts", 0)),
            "type": "liquidation",
            "data": liquidations
        }

    return {}
