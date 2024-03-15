import argparse
import asyncio
import httpx
import sys
import time
import json
import hmac
import hashlib

API_BASE_URL = 'https://api.bringin.xyz'
BRINGIN_ENDPOINT_KEY = '/api/v0/application/api-key'
BRINGIN_ENDPOINT_OFFRAMP = '/api/v0/offramp/order'

# Setup command-line arguments
parser = argparse.ArgumentParser(description="Request an offramp at Bringin.")
parser.add_argument("--api_key", type=str, required=True, help="API key for Bringin")
parser.add_argument("--secret_key", type=str, required=True, help="Secret key for HMAC generation")
parser.add_argument("--lightning_address", type=str, required=True, help="Lightning address for the transaction")
parser.add_argument("--amount_sats", type=str, required=True, help="Amount in satoshis to offramp as a string")
args = parser.parse_args()

# Function to generate HMAC authorization header
def generate_hmac_authorization(api_secret, http_method, path, body):
    # 1. Fetch the current UNIX timestamp in milliseconds
    current_time = str(int(time.time() * 1000))
    
    # 2. Stringify the body of your request
    body_string = json.dumps(body, separators=(',', ':')) if body else '{}'
    
    # 3. Calculate the hex encoded MD5 digest of your request body
    md5_hasher = hashlib.md5()
    md5_hasher.update(body_string.encode())
    request_content_hex_string = md5_hasher.hexdigest()
    
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
        response = await client.get("https://api.ipify.org?format=json")
        if response.status_code == 200:
            return response.json()["ip"]
        else:
            raise Exception("Failed to fetch public IP address")

async def fetch_users_api_key(api_key, secret_key, lightning_address):
    body = {
        "lightningAddress": lightning_address
    }
    headers = {
        'authorization': generate_hmac_authorization(secret_key, "POST", BRINGIN_ENDPOINT_KEY, body),
        'api-key': api_key,
        'Content-Type': 'application/json',
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(API_BASE_URL + BRINGIN_ENDPOINT_KEY, json=body, headers=headers)
        if response.status_code == 200:
            response_data = response.json()  # Parse the JSON response
            user_api_key = response_data.get("apikey")  # Extract the API key
            if user_api_key:
                print("Success fetching user's API key:", user_api_key)
                return user_api_key
            else:
                print("API key not found in the response.")
                return None
        else:
            print("Failed to fetch user's API key:", response.status_code, response.text)
            return None


async def create_offramp_order(user_api_key, lightning_address, amount_sats, ip_address, label="OPAGO offramp", payment_method="LIGHTNING", source_id=None):
    body = {
        "sourceAmount": amount_sats,  
        "ipAddress": ip_address,  
        "label": label,  
        "paymentMethod": payment_method  
    }
    # Include sourceId if provided
    if source_id:
        body["sourceId"] = source_id

    headers = {
        'api-key': user_api_key,
        'Content-Type': 'application/json',
    }
    print(f"Headers: {headers}")
    print(f"Body: {json.dumps(body, indent=4)}")
    async with httpx.AsyncClient() as client:
        response = await client.post(API_BASE_URL + BRINGIN_ENDPOINT_OFFRAMP, json=body, headers=headers)
        if response.status_code == 200:
            response_data = response.json()  # Parse the JSON response
            invoice = response_data.get("invoice")  # Extract the invoice text
            if invoice:
                print("Offramp order created successfully. Invoice:", invoice)
                return invoice  # Return the invoice text
            else:
                print("Invoice not found in the response.")
                return None
        else:
            print("Failed to create offramp order. Error code:", response.status_code)
            return response.status_code  # Return the error code

# Main function to trigger the offramp order creation
async def main():
    # Example placeholders - replace with actual values or logic to obtain them
    ip_address = await fetch_public_ip()

    user_api_key = await fetch_users_api_key(args.api_key, args.secret_key, args.lightning_address)
    if user_api_key:
        await create_offramp_order(user_api_key, args.lightning_address, args.amount_sats, ip_address)

if __name__ == "__main__":
    asyncio.run(main())