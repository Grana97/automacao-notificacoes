# Substitua esta linha:
BINANCE_API_URL = "https://api.binance.com/api/v3/ticker/24hr"

# Por esta:
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price"

# E troque a função `get_crypto_data()` por esta:

def get_crypto_data():
    """Obtém dados das criptomoedas pela CoinGecko"""
    try:
        # Mapeamento CoinGecko para os ativos usados
        symbol_map = {
            "BTCUSDT": "bitcoin",
            "ETHUSDT": "ethereum",
            "SOLUSDT": "solana",
            "HYPEUSDT": "hype-finance",  # Verifique se existe esse nome na CoinGecko
            "AAVEUSDT": "aave",
            "XRPUSDT": "ripple"
        }

        ids = ",".join(symbol_map.values())
        params = {
            "ids": ids,
            "vs_currencies": "usd",
            "include_24hr_change": "true"
        }

        response = requests.get(COINGECKO_API_URL, params=params, timeout=10)
        response.raise_for_status()
        prices = response.json()

        crypto_data = {}
        for symbol, coingecko_id in symbol_map.items():
            if coingecko_id in prices:
                crypto_data[symbol] = {
                    "price": prices[coingecko_id]["usd"],
                    "change_24h": prices[coingecko_id].get("usd_24h_change", 0),
                    "volume": 0  # CoinGecko no endpoint simples não traz volume
                }

        return crypto_data
    except Exception as e:
        print(f"❌ Erro ao obter dados da CoinGecko: {e}")
        return {}
