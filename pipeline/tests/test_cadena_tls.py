"""Un certificado intermedio descargado por HTTP solo se acepta si su cadena termina en una raíz conocida."""
import datetime
import sys
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # catalogo_fuentes.py está en la raíz
from catalogo_fuentes import cadena_confiable  # noqa: E402


def _cert(nombre, clave, emisor_nombre, clave_emisor, ca=True):
    ahora = datetime.datetime(2026, 1, 1)
    return (x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, nombre)]))
            .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, emisor_nombre)]))
            .public_key(clave.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(ahora).not_valid_after(ahora + datetime.timedelta(days=3650))
            .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True)
            .sign(clave_emisor, hashes.SHA256()))


def _cadena():
    k_raiz, k_int, k_falsa = (ec.generate_private_key(ec.SECP256R1()) for _ in range(3))
    raiz = _cert("Raiz", k_raiz, "Raiz", k_raiz)
    intermedio = _cert("Intermedio", k_int, "Raiz", k_raiz)
    falso = _cert("Intermedio", k_falsa, "Raiz", k_falsa)  # mismo nombre, firmado por otra clave
    return raiz, intermedio, falso


def test_intermedio_firmado_por_una_raiz_conocida():
    raiz, intermedio, _ = _cadena()
    assert cadena_confiable([intermedio], [raiz])


def test_intermedio_falso_con_el_mismo_nombre_se_rechaza():
    raiz, _, falso = _cadena()
    assert not cadena_confiable([falso], [raiz])


def test_sin_raiz_conocida_o_sin_intermedios():
    _, intermedio, _ = _cadena()
    assert not cadena_confiable([intermedio], [])
    assert not cadena_confiable([], [intermedio])
