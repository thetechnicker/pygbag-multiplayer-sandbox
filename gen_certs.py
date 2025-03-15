import datetime
import ipaddress
import requests
import json
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization


def get_location_info():
    try:
        response = requests.get("https://ipinfo.io")
        if response.status_code == 200:
            data = response.json()
            return {
                "country": data.get("country", ""),
                "region": data.get("region", ""),
                "city": data.get("city", ""),
            }
    except Exception as e:
        print(f"Error fetching location info: {e}")
    return None


def generate_self_signed_cert(
    common_name, country, state, city, output_key="key.pem", output_cert="cert.pem"
):
    # Generate a private key
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Create a self-signed certificate
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, country),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, state),
            x509.NameAttribute(NameOID.LOCALITY_NAME, city),
            x509.NameAttribute(
                NameOID.ORGANIZATION_NAME,
                "Self-Signed (im a hacker and im going to steal your data lol. no im not but maybe, im just trolling dont think about it. or do, i dont care, its your life)",
            ),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ]
    )

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
        )
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName(common_name),
                    x509.DNSName("localhost"),
                    x509.DNSName("localhost.localdomain"),
                    x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                    x509.IPAddress(ipaddress.IPv6Address("::1")),
                ]
            ),
            critical=False,
        )
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    # Save the private key
    with open(output_key, "wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    # Save the certificate
    with open(output_cert, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f"Self-signed certificate generated for {common_name}")
    print(f"Private key saved to: {output_key}")
    print(f"Certificate saved to: {output_cert}")


if __name__ == "__main__":
    location_info = get_location_info()
    if location_info:
        print("Location information retrieved:")
        print(f"Country: {location_info['country']}")
        print(f"Region: {location_info['region']}")
        print(f"City: {location_info['city']}")

        common_name = input(
            "Enter the common name for the certificate (e.g., localhost): "
        )
        generate_self_signed_cert(
            common_name,
            location_info["country"],
            location_info["region"],
            location_info["city"],
        )
