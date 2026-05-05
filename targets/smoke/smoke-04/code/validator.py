from __future__ import annotations

import datetime
from typing import Sequence

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding


def _check_validity(cert: x509.Certificate, now: datetime.datetime) -> None:
    """Raise if *cert* is outside its validity period."""
    if now < cert.not_valid_before_utc:
        raise ValueError(
            f"certificate {cert.subject} is not yet valid "
            f"(not before {cert.not_valid_before_utc})"
        )
    if now > cert.not_valid_after_utc:
        raise ValueError(
            f"certificate {cert.subject} has expired "
            f"(not after {cert.not_valid_after_utc})"
        )


def _check_ca(cert: x509.Certificate) -> None:
    """Raise if *cert* lacks the CA basic-constraint."""
    try:
        bc = cert.extensions.get_extension_for_class(x509.BasicConstraints)
        if not bc.value.ca:
            raise ValueError(f"certificate {cert.subject} is not a CA")
    except x509.ExtensionNotFound:
        raise ValueError(f"certificate {cert.subject} has no BasicConstraints")


def _verify_signature(subject_cert: x509.Certificate,
                      issuer_cert: x509.Certificate) -> None:
    """Verify that *issuer_cert* signed *subject_cert*.

    Raises ValueError if the signature does not match.
    """
    pub = issuer_cert.public_key()
    try:
        if isinstance(pub, ec.EllipticCurvePublicKey):
            pub.verify(
                subject_cert.signature,
                subject_cert.tbs_certificate_bytes,
                ec.ECDSA(subject_cert.signature_hash_algorithm),
            )
        else:
            pub.verify(
                subject_cert.signature,
                subject_cert.tbs_certificate_bytes,
                padding.PKCS1v15(),
                subject_cert.signature_hash_algorithm,
            )
    except InvalidSignature:
        raise ValueError(
            f"signature on {subject_cert.subject} not valid "
            f"under issuer {issuer_cert.subject}"
        )


def validate_chain(
    chain: Sequence[x509.Certificate],
    trusted_root: x509.Certificate,
    now: datetime.datetime | None = None,
) -> bool:
    """Validate *chain* (leaf-first) against *trusted_root*.

    Returns True if the full chain is valid.
    Raises ValueError with a description on the first failure.
    """
    if now is None:
        now = datetime.datetime.now(datetime.timezone.utc)

    _check_validity(trusted_root, now)

    full_chain = list(chain) + [trusted_root]

    # Check validity and CA constraints for every certificate
    for i, cert in enumerate(full_chain[:-1]):
        _check_validity(cert, now)
        issuer = full_chain[i + 1]
        if i < len(full_chain) - 2:
            _check_ca(issuer)

    # Verify signatures up the chain from intermediates to root
    for i in range(1, len(full_chain) - 1):
        _verify_signature(full_chain[i], full_chain[i + 1])

    # Root must be self-signed
    _verify_signature(trusted_root, trusted_root)

    return True


if __name__ == "__main__":
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    def _make_cert(subject_name, issuer_name, signing_key, subject_key, is_ca=False):
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, subject_name)])
        issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, issuer_name)])
        builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(subject_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc))
            .not_valid_after(datetime.datetime(2028, 1, 1, tzinfo=datetime.timezone.utc))
        )
        if is_ca:
            builder = builder.add_extension(
                x509.BasicConstraints(ca=True, path_length=None), critical=True,
            )
        return builder.sign(signing_key, hashes.SHA256())

    root_key = ec.generate_private_key(ec.SECP256R1())
    inter_key = ec.generate_private_key(ec.SECP256R1())
    leaf_key = ec.generate_private_key(ec.SECP256R1())

    root_cert = _make_cert("Root CA", "Root CA", root_key, root_key, is_ca=True)
    inter_cert = _make_cert("Intermediate", "Root CA", root_key, inter_key, is_ca=True)
    leaf_cert = _make_cert("leaf.example.com", "Intermediate", inter_key, leaf_key)

    assert validate_chain([leaf_cert, inter_cert], root_cert)
    print("OK: valid 3-cert chain accepted")
