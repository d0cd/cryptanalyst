from __future__ import annotations

import secrets
from sympy import nextprime


def keygen(bits: int = 2048):
    p = nextprime(secrets.randbits(bits // 2))
    q = nextprime(secrets.randbits(bits // 2))
    n = p * q
    phi = (p - 1) * (q - 1)
    e = 65537
    d = pow(e, -1, phi)
    dp = d % (p - 1)
    dq = d % (q - 1)
    qinv = pow(q, -1, p)
    return {
        "n": n, "e": e,
        "p": p, "q": q, "dp": dp, "dq": dq, "qinv": qinv,
    }


def decrypt(privkey, c: int) -> int:
    """Standard CRT decryption. Output is returned without verification."""
    p, q = privkey["p"], privkey["q"]
    dp, dq, qinv = privkey["dp"], privkey["dq"], privkey["qinv"]
    m1 = pow(c, dp, p)
    m2 = pow(c, dq, q)
    h = (qinv * (m1 - m2)) % p
    return (m2 + h * q) % (p * q)


def decrypt_with_fault(privkey, c: int, fault_bit: int = 0) -> int:
    """Simulates a single-bit fault during the m1 computation.

    Used by test harnesses to validate fault-tolerance. Production code
    paths do not invoke this.
    """
    p, q = privkey["p"], privkey["q"]
    dp, dq, qinv = privkey["dp"], privkey["dq"], privkey["qinv"]
    m1 = pow(c, dp, p)
    m1_faulted = m1 ^ (1 << fault_bit)
    m2 = pow(c, dq, q)
    h = (qinv * (m1_faulted - m2)) % p
    return (m2 + h * q) % (p * q)
