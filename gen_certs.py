import datetime
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization


def generate_self_signed_cert(
    common_name, output_key="key.pem", output_cert="cert.pem"
):
    # Generate a private key
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Create a self-signed certificate
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "My Organization"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ]
    )

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName(common_name)]),
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
    common_name = input("Enter the common name for the certificate (e.g., localhost): ")
    generate_self_signed_cert(common_name)
