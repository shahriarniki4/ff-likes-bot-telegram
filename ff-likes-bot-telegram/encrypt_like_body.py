# Protective Source License v1.0 (PSL-1.0)
import binascii
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

MAIN_KEY = b'Yg&tc%DEuh6%Zc^8'
MAIN_IV = b'6oyZDr22E3ychjM%'

def aes_cbc_encrypt(key: bytes, iv: bytes, plaintext: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded = pad(plaintext, AES.block_size)
    return cipher.encrypt(padded)

def create_like_payload(uid: int, region: str) -> bytes:
    # Create simple payload
    payload_str = f"{uid}:{region}"
    plaintext = payload_str.encode('utf-8')
    encrypted_bytes = aes_cbc_encrypt(MAIN_KEY, MAIN_IV, plaintext)
    return encrypted_bytes

if __name__ == "__main__":
    uid_to_like = 111119900
    region = "IND"
    payload = create_like_payload(uid_to_like, region)
    print("--- /LikeProfile Payload ---")
    print("Raw bytes:", payload)
    print("Hex string:", binascii.hexlify(payload).upper().decode())
