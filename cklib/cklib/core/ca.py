import requests
from typing import Tuple, Optional, List
from cklib.args import ArgumentParser
from cklib.utils import get_local_hostnames, get_local_ip_addresses
from cklib.x509 import (
    csr_to_bytes,
    load_cert_from_bytes,
    cert_fingerprint,
    gen_rsa_key,
    gen_csr,
)
from cklib.jwt import decode_jwt_from_headers, encode_jwt_to_headers
from cryptography.x509.base import Certificate
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey


def get_ca_cert(ckcore_uri: str = None, psk: str = None) -> Certificate:
    if ckcore_uri is None:
        ckcore_uri = getattr(ArgumentParser.args, "ckcore_uri", None)
    if psk is None:
        psk = getattr(ArgumentParser.args, "psk", None)

    r = requests.get(f"{ckcore_uri}/ca/cert", verify=False)
    ca_cert = load_cert_from_bytes(r.content)
    if psk:
        jwt = decode_jwt_from_headers(r.headers, psk)
        if jwt["sha256_fingerprint"] != cert_fingerprint(ca_cert):
            raise ValueError("Invalid Root CA certificate fingerprint")
    return ca_cert


def get_signed_cert(
    common_name: str,
    san_dns_names: Optional[List[str]] = None,
    san_ip_addresses: Optional[List[str]] = None,
    ckcore_uri: str = None,
    psk: str = None,
    ca_cert_path: str = None,
) -> Tuple[RSAPrivateKey, Certificate]:
    if san_dns_names is None:
        san_dns_names = get_local_hostnames(args=ArgumentParser.args)
    if san_ip_addresses is None:
        san_ip_addresses = get_local_ip_addresses(args=ArgumentParser.args)
    if ckcore_uri is None:
        ckcore_uri = getattr(ArgumentParser.args, "ckcore_uri", None)
    if psk is None:
        psk = getattr(ArgumentParser.args, "psk", None)

    cert_key = gen_rsa_key()
    cert_csr = gen_csr(cert_key, common_name, san_dns_names, san_ip_addresses)
    cert_csr_bytes = csr_to_bytes(cert_csr)
    headers = {}
    if psk is not None:
        encode_jwt_to_headers(headers, {}, psk)
    request_kwargs = {}
    if ca_cert_path is not None:
        request_kwargs["verify"] = ca_cert_path
    r = requests.post(
        f"{ckcore_uri}/ca/sign", cert_csr_bytes, headers=headers, **request_kwargs
    )
    cert_bytes = r.content
    cert_crt = load_cert_from_bytes(cert_bytes)
    return cert_key, cert_crt
