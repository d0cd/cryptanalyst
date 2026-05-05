from __future__ import annotations

import hashlib
from dataclasses import dataclass


def _hash(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


@dataclass
class MerkleProof:
    leaf_data: bytes
    siblings: list[tuple[bytes, str]]  # (hash, "L" | "R")
    root: bytes


def build_tree(items: list[bytes]) -> tuple[bytes, list[list[bytes]]]:
    """Build a Merkle tree from *items*.

    Returns (root_hash, layers) where layers[0] is the leaf hashes
    and layers[-1] is [root_hash].
    """
    if not items:
        raise ValueError("cannot build tree from empty list")

    layer = [_hash(item) for item in items]
    layers = [layer]

    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer.append(layer[-1])  # duplicate last node for odd count
        next_layer = []
        for i in range(0, len(layer), 2):
            next_layer.append(_hash(layer[i] + layer[i + 1]))
        layer = next_layer
        layers.append(layer)

    return layer[0], layers


def make_proof(items: list[bytes], index: int) -> MerkleProof:
    """Generate an inclusion proof for items[index]."""
    root, layers = build_tree(items)
    siblings: list[tuple[bytes, str]] = []
    idx = index

    for layer in layers[:-1]:
        if idx % 2 == 0:
            sibling_idx = idx + 1
            direction = "R"
        else:
            sibling_idx = idx - 1
            direction = "L"
        if sibling_idx < len(layer):
            siblings.append((layer[sibling_idx], direction))
        else:
            siblings.append((layer[idx], direction))
        idx //= 2

    return MerkleProof(leaf_data=items[index], siblings=siblings, root=root)


def verify_proof(proof: MerkleProof) -> bool:
    """Verify that *proof.leaf_data* is included in the tree with *proof.root*."""
    current = _hash(proof.leaf_data)

    for sibling_hash, direction in proof.siblings:
        if direction == "L":
            current = _hash(sibling_hash + current)
        else:
            current = _hash(current + sibling_hash)

    return current == proof.root


if __name__ == "__main__":
    items = [f"item-{i}".encode() for i in range(8)]
    root, _ = build_tree(items)

    # Valid proof
    proof = make_proof(items, 3)
    assert verify_proof(proof), "valid proof rejected"

    # Tampered leaf
    forged = MerkleProof(leaf_data=b"not-in-tree", siblings=proof.siblings, root=proof.root)
    assert not verify_proof(forged), "forged proof accepted"

    print(f"OK: root={root.hex()[:16]}... proof verified, tamper rejected")
