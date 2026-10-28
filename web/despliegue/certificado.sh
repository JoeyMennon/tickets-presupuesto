#!/usr/bin/env bash
# certificado autofirmado en datos/tls
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p datos/tls
[[ -f datos/tls/cert.pem ]] && { echo "Ya hay certificado en datos/tls"; exit 0; }
openssl req -x509 -newkey rsa:2048 -nodes -days 3650 -subj "/CN=presupuesto" \
    -keyout datos/tls/clave.pem -out datos/tls/cert.pem
chmod 600 datos/tls/clave.pem
echo "Listo: datos/tls/cert.pem"
