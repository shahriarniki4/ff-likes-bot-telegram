from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import binascii

# Free Fire encryption keys
KEY = b'Yg&tc%DEuh6%Zc^8'
IV = b'6oyZDr22E3ychjM%'

encrypted_hex = "DAA0428B16A72C0D176DDCD4AF5FFFD3C0BB2FA3BEC98DD856901612E4765059"

try:
    encrypted_data = binascii.unhexlify(encrypted_hex)
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    decrypted = unpad(cipher.decrypt(encrypted_data), AES.block_size)
    password = decrypted.decode('utf-8')
    print(f"✅ UID: 6381874102")
    print(f"✅ Password: {password}")
except Exception as e:
    print(f"❌ Error: {e}")
    print("The password might need a different decryption method")
