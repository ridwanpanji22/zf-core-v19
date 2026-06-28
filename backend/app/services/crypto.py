import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
from app.config import settings

def get_encryption_key() -> bytes:
    # Derive a 32-byte key from API_KEY_ENCRYPTION_SECRET env variable using SHA-256
    return hashlib.sha256(settings.API_KEY_ENCRYPTION_SECRET.encode()).digest()

def encrypt(plaintext: str) -> tuple[bytes, bytes]:
    """Encrypt plaintext using AES-256-GCM.

    Returns: (ciphertext, nonce)
    """
    key = get_encryption_key()
    nonce = os.urandom(12) # 96-bit nonce
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return ciphertext, nonce

def decrypt(ciphertext: bytes, nonce: bytes) -> str:
    """Decrypt ciphertext using AES-256-GCM."""
    key = get_encryption_key()
    aesgcm = AESGCM(key)
    decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
    return decrypted_bytes.decode()
