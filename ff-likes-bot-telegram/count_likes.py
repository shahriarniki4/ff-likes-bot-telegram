import httpx
import asyncio

async def GetAccountInformation(uid: str, token: str, server: str, endpoint: str):
    base_url = f"https://client.{server.lower()}.freefiremobile.com"
    headers = {
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 14; Pixel 8 Build/UP1A.231005.007)",
        "Authorization": f"Bearer {token}"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}{endpoint}", params={"uid": uid}, headers=headers)
            return response.json()
    except Exception as e:
        return {"error": True, "message": str(e)}

if __name__ == "__main__":
    asyncio.run(GetAccountInformation("123456789", "token", "IND", "/GetPlayerPersonalShow"))
