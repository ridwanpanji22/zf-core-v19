from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
import os
from app.config import settings

def get_encryption_key() -> bytes:
    """Derive a 32-byte AES key from API_KEY_ENCRYPTION_SECRET using HKDF."""
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"zfcore-api-key-encryption",
    ).derive(settings.API_KEY_ENCRYPTION_SECRET.encode())

def encrypt(plaintext: str) -> tuple[bytes, bytes]:
    """Encrypt plaintext using AES-256-GCM.

    Returns: (ciphertext, nonce) — caller MUST store nonce per-field.
    """
    key = get_encryption_key()
    nonce = os.urandom(12) # 96-bit nonce, unique per encryption call
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return ciphertext, nonce

def decrypt(ciphertext: bytes, nonce: bytes) -> str:
    """Decrypt ciphertext using AES-256-GCM."""
    key = get_encryption_key()
    aesgcm = AESGCM(key)
    decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
    return decrypted_bytes.decode()
