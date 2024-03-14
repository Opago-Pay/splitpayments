import argparse
import httpx
import sys
import time
import hmac
import hashlib

# Setup command-line arguments
parser = argparse.ArgumentParser(description="Request an offramp at Bringin.")
parser.add_argument("--api_key", type=str, required=True, help="API key for Bringin")
parser.add_argument("--secret_key", type=str, required=True, help="Secret key for HMAC generation")
parser.add_argument("--lightning_address", type=str, required=True, help="Lightning address for the transaction")
parser.add_argument("--amount_sats", type=int, required=True, help="Amount in satoshis to offramp")
args = parser.parse_args()

# Function to generate HMAC authorization header
def generate_hmac_authorization(api_key, secret_key):
    timestamp = str(int(time.time() * 1000))
    message = timestamp + api_key
    signature = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()
    return f"HMAC {timestamp}:{signature}"

# API URLs
GET_API_KEY_URL = "https://api.bringin.xyz/api/v0/application/api-key"
GET_EURO_TO_BTC_URL = "https://api.bringin.xyz/api/v0/market/euro-to-btc"
CREATE_OFFRAMP_ORDER_URL = "https://api.bringin.xyz/api/v0/offramp/order"  # Assuming this is the endpoint

async def get_api_key():
    hmac_authorization = generate_hmac_authorization(args.api_key, args.secret_key)
    headers_for_api_key = {
        "api-key": args.api_key,
        "authorization": hmac_authorization,
        "Content-Type": "application/json"
    }
    data_for_api_key = {
        "lightningAddress": args.lightning_address
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(GET_API_KEY_URL, json=data_for_api_key, headers=headers_for_api_key)
        if response.status_code == 200:
            return response.json().get("apikey")
        else:
            print("Failed to retrieve API key:", response.text)
            sys.exit(1)

async def get_euro_to_btc_rate():
    async with httpx.AsyncClient() as client:
        response = await client.get(GET_EURO_TO_BTC_URL)
        if response.status_code == 200:
            return response.json().get("rate")
        else:
            print("Failed to retrieve Euro to BTC rate:", response.text)
            sys.exit(1)

async def create_offramp_order(api_key, amount_eur, lightning_address):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "userId": lightning_address,
        "amountEur": amount_eur
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(CREATE_OFFRAMP_ORDER_URL, json=data, headers=headers)
        if response.status_code == 200:
            print("Offramp order created successfully:", response.json())
            return response.json()  # Return the response JSON on success
        else:
            print("Failed to create offramp order:", response.text)
            return response.text  # Return the error text on failure

async def main():
    api_key = await get_api_key()
    euro_to_btc_rate = await get_euro_to_btc_rate()
    amount_eur = (args.amount_sats / 1e8) / euro_to_btc_rate  # Convert satoshis to BTC and then to Euros
    await create_offramp_order(api_key, amount_eur, args.lightning_address)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())