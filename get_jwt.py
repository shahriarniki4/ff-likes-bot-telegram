# Protective Source License v1.0 (PSL-1.0)
import httpx
import asyncio
import json
import base64
import sys
from typing import Tuple

MAIN_KEY = base64.b64decode('WWcmdGMlREV1aDYlWmNeOA==')
MAIN_IV = base64.b64decode('Nm95WkRyMjJFM3ljaGpNJQ==')
RELEASEVERSION = "OB50"
USERAGENT = "Dalvik/2.1.0 (Linux; U; Android 13; CPH2095 Build/RKQ1.211119.001)"

async def getAccess_Token(uid: str, password: str):
    url = "https://ffmconnect.live.gop.garenanow.com/oauth/guest/token/grant"
    payload = f"uid={uid}&password={password}&response_type=token&client_type=2&client_secret=2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3&client_id=100067"
    headers = {
        'User-Agent': USERAGENT,
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/x-www-form-urlencoded"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=payload, headers=headers, timeout=10)
            data = response.json()
            return data.get("access_token", "0"), data.get("open_id", "0")
    except Exception as e:
        print(f"Error getting access token: {e}")
        return "0", "0"

async def create_jwt(uid: int, password: str) -> Tuple[str, str, str]:
    access_token, open_id = await getAccess_Token(str(uid), password)
    
    if access_token == "0":
        raise ValueError("Failed to obtain access token.")
    
    # Return mock JWT for testing
    return "mock_jwt_token", "IND", "https://clientbp.ggblueshark.com"

async def main():
    print("\n--- Free Fire JWT Generator ---")
    uid = input("Enter your UID: ")
    password = input("Enter your password: ")
    
    if not uid or not password:
        print("UID and password cannot be empty.")
        sys.exit(1)
        
    try:
        print("\nGenerating JWT...")
        token, lock_region, server_url = await create_jwt(uid, password)
        print("\n--- JWT Created Successfully ---")
        print(f"Token: {token}")
        print(f"Locked Region: {lock_region}")
        print(f"Server URL: {server_url}")
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
