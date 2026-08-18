# Protective Source License v1.0 (PSL-1.0)
# Copyright (c) 2025 Kaif
# Unauthorized removal of credits or use for abusive/illegal purposes
# will terminate all rights granted under this license.

import httpx
import asyncio
import json
import base64
import sys
from typing import Tuple
from google.protobuf import json_format
from Crypto.Cipher import AES
from ff_proto import freefire_pb2

MAIN_KEY = base64.b64decode('WWcmdGMlREV1aDYlWmNeOA==')
MAIN_IV = base64.b64decode('Nm95WkRyMjJFM3ljaGpNJQ==')
RELEASEVERSION = "OB50"
USERAGENT = "Dalvik/2.1.0 (Linux; U; Android 13; CPH2095 Build/RKQ1.211119.001)"

def _pad(plaintext: bytes) -> bytes:
    padding_length = AES.block_size - (len(plaintext) % AES.block_size)
    return plaintext + bytes([padding_length] * padding_length)

def _aes_cbc_encrypt(plaintext: bytes) -> bytes:
    cipher = AES.new(MAIN_KEY, AES.MODE_CBC, MAIN_IV)
    return cipher.encrypt(_pad(plaintext))

async def getAccess_Token(uid: str, password: str):
    url = "https://ffmconnect.live.gop.garenanow.com/oauth/guest/token/grant"
    payload = {
        "uid": str(uid),
        "password": password,
        "response_type": "token",
        "client_type": "2",
        "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
        "client_id": "100067",
    }
    headers = {
        'User-Agent': USERAGENT,
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/x-www-form-urlencoded"
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(url, data=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    access_token = data.get("access_token")
    open_id = data.get("open_id")
    if not access_token or not open_id:
        raise ValueError("Guest login response did not contain an access token.")
    return access_token, open_id

async def create_jwt(uid: str, password: str) -> Tuple[str, str, str]:
    access_token, open_id = await getAccess_Token(str(uid), password)

    request = freefire_pb2.LoginReq(
        open_id=open_id,
        open_id_type="4",
        login_token=access_token,
        orign_platform_type="4",
    )
    payload = _aes_cbc_encrypt(request.SerializeToString())
    headers = {
        "User-Agent": USERAGENT,
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
        "Content-Type": "application/octet-stream",
        "Expect": "100-continue",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": RELEASEVERSION,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            "https://loginbp.ggblueshark.com/MajorLogin",
            data=payload,
            headers=headers,
        )
        response.raise_for_status()

    login_response = freefire_pb2.LoginRes()
    login_response.ParseFromString(response.content)
    token = login_response.token
    region = login_response.lock_region
    server_url = login_response.server_url
    if not token:
        raise ValueError("Free Fire login response did not contain a JWT.")
    return token, region, server_url

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
