import aiohttp

async def get_ton_usdt_rate():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=the-open-network%2Ctether&vs_currencies=usd"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            ton = data.get("the-open-network", {}).get("usd", None)
            usdt = data.get("tether", {}).get("usd", None)
            return ton, usdt
