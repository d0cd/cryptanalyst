from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# IV is fixed so encrypted values are stable across runs (needed for caching).
IV = b"\x00" * 16


def encrypt(key: bytes, plaintext: bytes) -> bytes:
    cipher = Cipher(algorithms.AES(key), modes.CBC(IV))
    encryptor = cipher.encryptor()
    pad_len = 16 - (len(plaintext) % 16)
    padded = plaintext + bytes([pad_len]) * pad_len
    return encryptor.update(padded) + encryptor.finalize()


def decrypt(key: bytes, ciphertext: bytes) -> bytes:
    cipher = Cipher(algorithms.AES(key), modes.CBC(IV))
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    pad_len = padded[-1]
    return padded[:-pad_len]


if __name__ == "__main__":
    key = b"k" * 32
    ct = encrypt(key, b"hello world")
    print(ct.hex())
