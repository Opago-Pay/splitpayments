import argparse
import httpx
import sys
import time
import json
import hmac
import hashlib

# Setup command-line arguments
parser = argparse.ArgumentParser(description="Request an offramp at Bringin.")
parser.add_argument("--api_key", type=str, required=True, help="API key for Bringin")
parser.add_argument("--secret_key", type=str, required=True, help="Secret key for HMAC generation")
parser.add_argument("--lightning_address", type=str, required=True, help="Lightning address for the transaction")
parser.add_argument("--amount_sats", type=str, required=True, help="Amount in satoshis to offramp as a string")
args = parser.parse_args()

# Function to generate HMAC authorization header
def generate_hmac_authorization(api_secret, http_method, path, body):
    # 1. Fetch the current UNIX timestamp
    current_time = str(int(time.time() * 1000))
    
    # 2. Stringify the body of your request
    body_string = json.dumps(body)
    
    # 3. Calculate the hex encoded MD5 digest of your request body
    if body:
        md5_hasher = hashlib.md5()
        md5_hasher.update(body_string.encode())
        request_content_hex_string = md5_hasher.hexdigest()
    else:  # For GET requests or empty bodies
        request_content_hex_string = '99914b932bd37a50b983c5e7c90ae93b'
    
    # 4. Concatenate the UNIX timestamp with the request verb, path, and the requestContentHexString
    signature_raw_data = current_time + http_method + path + request_content_hex_string
    
    # 5. Use your API Secret to create a SHA256 HMAC digest in hex
    signature = hmac.new(api_secret.encode(), signature_raw_data.encode(), hashlib.sha256).hexdigest()
    
    # 6. Finally, create your authorization header
    authorization_header = f"HMAC {current_time}:{signature}"
    
    return authorization_header

# Function to fetch the host's public IP address
async def fetch_public_ip():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://httpbin.org/ip")
        if response.status_code == 200:
            return response.json()["origin"]
        else:
            print("Failed to fetch public IP address:", response.text)
            sys.exit(1)

# API URL for creating offramp order
CREATE_OFFRAMP_ORDER_URL = "https://api.bringin.xyz/api/v0/offramp/order"

async def create_offramp_order(api_key, amount_sats):
    # Define the HTTP method and API endpoint path
    http_method = "POST"
    path = "/api/v0/offramp/order"  # Adjust this path as per the actual API endpoint

    # Construct the request body
    body = {
        "sourceAmount": amount_sats,
        "ipAddress": await fetch_public_ip(),  # Assuming fetch_public_ip() fetches the host's IP
        "label": "OPAGO offramp",
        "paymentMethod": "LIGHTNING"
    }

    # Generate the HMAC authorization header
    hmac_authorization = generate_hmac_authorization(args.secret_key, http_method, path, body)

    # Include the HMAC authorization in the request headers
    headers = {
        "api-key": api_key,
        "authorization": hmac_authorization,
        "Content-Type": "application/json"
    }

    # Make the HTTP request
    async with httpx.AsyncClient() as client:
        response = await client.post("https://api.bringin.xyz" + path, json=body, headers=headers)
        if response.status_code == 200:
            print("Offramp order created successfully:", response.json())
        else:
            print("Failed to create offramp order:", response.text)

async def main():
    await create_offramp_order(args.api_key, args.amount_sats)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())