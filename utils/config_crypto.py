"""Encrypted config blobs: PBKDF2-HMAC-SHA256 + Fernet (authenticated encryption)."""
import base64
import os
import struct

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

MAGIC = b"CODYENC1"
VERSION = 1
DEFAULT_ITERATIONS = 480_000

_HEADER = struct.Struct("!8s B I H")


def derive_fernet_key(password: bytes, salt: bytes, iterations: int) -> bytes:
  kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=salt,
    iterations=iterations,
  )
  return base64.urlsafe_b64encode(kdf.derive(password))


def encrypt_json_bytes(
  plaintext: bytes,
  password: str,
  *,
  salt: bytes | None = None,
  iterations: int = DEFAULT_ITERATIONS,
) -> bytes:
  if salt is None:
    salt = os.urandom(16)
  key = derive_fernet_key(password.encode("utf-8"), salt, iterations)
  token = Fernet(key).encrypt(plaintext)
  header = _HEADER.pack(MAGIC, VERSION, iterations, len(salt))
  return header + salt + token


def decrypt_json_bytes(blob: bytes, password: str) -> tuple[bytes, bytes, int]:
  """
  Returns (plaintext, salt, iterations) for re-encrypting with the same salt.
  """
  min_len = _HEADER.size + 1 + 1
  if len(blob) < min_len:
    raise ValueError("config blob too short")
  magic, version, iterations, salt_len = _HEADER.unpack_from(blob, 0)
  if magic != MAGIC:
    raise ValueError("not a Cody encrypted config file")
  if version != VERSION:
    raise ValueError(f"unsupported encrypted config version {version}")
  if salt_len < 16 or salt_len > 64:
    raise ValueError("invalid salt length")
  off = _HEADER.size
  salt = blob[off : off + salt_len]
  off += salt_len
  token = blob[off:]
  if not token:
    raise ValueError("missing ciphertext")
  key = derive_fernet_key(password.encode("utf-8"), salt, iterations)
  try:
    plain = Fernet(key).decrypt(token)
  except InvalidToken as e:
    raise ValueError("wrong password or corrupted config") from e
  return plain, salt, iterations
