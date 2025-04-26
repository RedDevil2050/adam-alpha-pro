
from cryptography.fernet import Fernet

def generate_key():
    return Fernet.generate_key()

def encrypt_data(data: str, key: bytes) -> bytes:
    f = Fernet(key)
    return f.encrypt(data.encode())

def decrypt_data(token: bytes, key: bytes) -> str:
    f = Fernet(key)
    return f.decrypt(token).decode()
