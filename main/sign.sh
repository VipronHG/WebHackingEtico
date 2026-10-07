#!/bin/bash
#
# Firma un .exe con certificado autofirmado usando osslsigncode.
# Uso: ./sign.sh <archivo.exe> [nombre_compania]
#

set -e  # aborta si algo falla

EXE_ORIGINAL="$1"
COMPANY="${2:-Microsoft Corporation}"

if [ -z "$EXE_ORIGINAL" ]; then
    echo "❌ Uso: ./sign.sh <archivo.exe> [nombre_compania]"
    exit 1
fi

if [ ! -f "$EXE_ORIGINAL" ]; then
    echo "❌ No se encontró $EXE_ORIGINAL"
    exit 1
fi

CERT="certificado.pfx"
CERT_PASS="JKLDFjlkdjfaoed98347512rtej"
TIMESTAMP_URL="http://timestamp.digicert.com"

# --- Verificar/instalar osslsigncode ---
if ! command -v osslsigncode &> /dev/null; then
    echo "🔹 Instalando osslsigncode..."
    sudo apt update && sudo apt install -y osslsigncode
fi

# --- Crear certificado autofirmado si no existe ---
if [ ! -f "$CERT" ]; then
    echo "🔹 Creando certificado autofirmado para: $COMPANY"
    openssl req -new -x509 -days 3650 -nodes \
        -out cert.pem -keyout clave.pem \
        -subj "/CN=$COMPANY/O=$COMPANY/C=US"

    openssl pkcs12 -export \
        -out "$CERT" \
        -inkey clave.pem \
        -in cert.pem \
        -passout pass:$CERT_PASS

    echo "✅ Certificado creado: $CERT"
else
    echo "✅ Certificado ya existe: $CERT"
fi

# --- Firmar el EXE ---
echo "🔹 Firmando $EXE_ORIGINAL..."

osslsigncode sign \
    -pkcs12 "$CERT" \
    -pass "$CERT_PASS" \
    -n "Runtime Broker" \
    -i "https://www.microsoft.com" \
    -h sha256 \
    -ts "$TIMESTAMP_URL" \
    -in "$EXE_ORIGINAL" \
    -out "temp_signed.exe"

mv "temp_signed.exe" "$EXE_ORIGINAL"

# --- Verificar la firma ---
echo ""
echo "🔹 Verificando la firma..."
osslsigncode verify -in "$EXE_ORIGINAL" || true

echo ""
echo "✅ Firma completada: $EXE_ORIGINAL"
