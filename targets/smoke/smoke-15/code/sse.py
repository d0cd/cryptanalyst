from __future__ import annotations

import os
from dataclasses import dataclass, field

from .crypto_utils import (
    prf,
    encrypt_aead,
    decrypt_aead,
    deterministic_encrypt,
    deterministic_decrypt,
)


@dataclass
class ClientKeys:
    search_key: bytes = field(default_factory=lambda: os.urandom(32))
    enc_key: bytes = field(default_factory=lambda: os.urandom(32))
    doc_id_key: bytes = field(default_factory=lambda: os.urandom(32))


@dataclass
class EncryptedIndex:
    """Server-side encrypted index."""
    index: dict[bytes, list[bytes]] = field(default_factory=dict)
    documents: dict[bytes, bytes] = field(default_factory=dict)


def build_index(
    keys: ClientKeys,
    corpus: dict[str, dict[str, list[str]]],
) -> EncryptedIndex:
    """Build an encrypted search index from a plaintext corpus.

    *corpus* maps doc_id -> {"keywords": [keyword, ...], "content": "..."}
    """
    ei = EncryptedIndex()

    # Invert: keyword -> [doc_id, ...]
    keyword_to_docs: dict[str, list[str]] = {}
    for doc_id, doc in corpus.items():
        for kw in doc.get("keywords", []):
            keyword_to_docs.setdefault(kw, []).append(doc_id)

    # Build encrypted index
    for keyword, doc_ids in keyword_to_docs.items():
        token = prf(keys.search_key, keyword.encode())
        enc_doc_ids = []
        for did in doc_ids:
            # Deterministic encryption ensures deduplication if the same
            # doc_id appears under multiple keywords.
            enc_did = deterministic_encrypt(keys.doc_id_key, did.encode())
            enc_doc_ids.append(enc_did)
        ei.index[token] = enc_doc_ids

    # Encrypt documents
    for doc_id, doc in corpus.items():
        content = doc.get("content", "")
        enc_did = deterministic_encrypt(keys.doc_id_key, doc_id.encode())
        ei.documents[enc_did] = encrypt_aead(keys.enc_key, content.encode())

    return ei


def search_token(keys: ClientKeys, keyword: str) -> bytes:
    """Compute a search token for *keyword*."""
    return prf(keys.search_key, keyword.encode())


def server_search(index: EncryptedIndex, token: bytes) -> list[bytes]:
    """Server-side search: return encrypted doc IDs matching *token*."""
    return index.index.get(token, [])


def client_decrypt_results(
    keys: ClientKeys,
    index: EncryptedIndex,
    enc_doc_ids: list[bytes],
) -> list[tuple[str, str]]:
    """Client-side: decrypt doc IDs and retrieve + decrypt documents."""
    results = []
    for enc_did in enc_doc_ids:
        doc_id = deterministic_decrypt(keys.doc_id_key, enc_did).decode()
        enc_content = index.documents.get(enc_did)
        if enc_content:
            content = decrypt_aead(keys.enc_key, enc_content).decode()
            results.append((doc_id, content))
    return results


if __name__ == "__main__":
    corpus = {
        "doc1": {"keywords": ["crypto", "aes"], "content": "AES encryption details"},
        "doc2": {"keywords": ["crypto", "rsa"], "content": "RSA key generation"},
        "doc3": {"keywords": ["network", "tls"], "content": "TLS handshake protocol"},
        "doc4": {"keywords": ["crypto", "hash"], "content": "SHA-256 internals"},
    }

    keys = ClientKeys()
    index = build_index(keys, corpus)

    # Search for "crypto" — should return doc1, doc2, doc4
    token = search_token(keys, "crypto")
    enc_results = server_search(index, token)
    results = client_decrypt_results(keys, index, enc_results)

    found_ids = {r[0] for r in results}
    assert found_ids == {"doc1", "doc2", "doc4"}, f"unexpected results: {found_ids}"

    # Search for "tls" — should return doc3
    token2 = search_token(keys, "tls")
    enc_results2 = server_search(index, token2)
    results2 = client_decrypt_results(keys, index, enc_results2)
    assert {r[0] for r in results2} == {"doc3"}

    # Unknown keyword — empty
    token3 = search_token(keys, "quantum")
    assert server_search(index, token3) == []

    print(f"OK: indexed {len(corpus)} docs, searches returned correct results")
