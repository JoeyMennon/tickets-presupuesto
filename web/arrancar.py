# arranca todo sin docker: python arrancar.py
# lo usa el zip de windows, pero vale en cualquier sistema
import os
import secrets
import shutil
import sys
import threading
import time
import urllib.request
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
PUERTO_PC = 8767
PUERTO_MOVIL = 8768
WEB = f"http://127.0.0.1:{PUERTO_PC}"


def carpeta_datos():
    if os.environ.get("DATOS_DIR"):
        return Path(os.environ["DATOS_DIR"])
    # en windows fuera del zip, para no perderlos al actualizar
    if os.name == "nt":
        return Path(os.environ["LOCALAPPDATA"]) / "TicketsPresupuesto"
    return AQUI / "datos"


def programas():
    # tesseract y poppler que trae el zip de windows
    for sub in ("tesseract", "poppler"):
        if (RAIZ / sub).is_dir():
            os.environ["PATH"] = str(RAIZ / sub) + os.pathsep + os.environ.get("PATH", "")
    if (RAIZ / "tesseract" / "tessdata").is_dir():
        os.environ["TESSDATA_PREFIX"] = str(RAIZ / "tesseract" / "tessdata")
        # con varios hilos en windows va muchísimo más lento
        os.environ.setdefault("OMP_THREAD_LIMIT", "1")


def clave(datos):
    ruta = datos / "clave.txt"
    if not ruta.exists():
        ruta.write_text(secrets.token_urlsafe(50))
    return ruta.read_text().strip()


def certificado(datos):
    tls = datos / "tls"
    if (tls / "cert.pem").exists():
        return
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    tls.mkdir(parents=True, exist_ok=True)
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nombre = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "presupuesto")])
    ahora = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(nombre).issuer_name(nombre)
            .public_key(k.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(ahora - timedelta(days=1)).not_valid_after(ahora + timedelta(days=3650))
            .sign(k, hashes.SHA256()))
    (tls / "clave.pem").write_bytes(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                    serialization.NoEncryption()))
    (tls / "cert.pem").write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def ya_abierto():
    try:
        urllib.request.urlopen(f"{WEB}/api/ping/", timeout=2)
        return True
    except OSError:
        return False


def abrir():
    if not os.environ.get("SIN_NAVEGADOR"):
        webbrowser.open(WEB)


def main():
    if ya_abierto():
        print("Ya estaba abierto.")
        abrir()
        return

    datos = carpeta_datos()
    datos.mkdir(parents=True, exist_ok=True)
    os.environ["DATOS_DIR"] = str(datos)
    os.environ.setdefault("SECRET_KEY", clave(datos))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    programas()
    certificado(datos)
    # la apk que trae el zip, para bajarla desde el móvil
    apk = RAIZ / "tickets.apk"
    if apk.exists():
        (datos / "app").mkdir(exist_ok=True)
        shutil.copyfile(apk, datos / "app" / "tickets.apk")

    sys.path.insert(0, str(AQUI))
    import django
    from django.core.management import call_command
    django.setup()
    from django.conf import settings
    if not Path(settings.STATIC_ROOT).is_dir():
        call_command("collectstatic", interactive=False, verbosity=0)
    call_command("migrate", interactive=False, verbosity=0)

    from cheroot import wsgi
    from cheroot.ssl.builtin import BuiltinSSLAdapter
    from django.core.wsgi import get_wsgi_application

    app = get_wsgi_application()
    pc = wsgi.Server(("127.0.0.1", PUERTO_PC), app, numthreads=4)
    movil = wsgi.Server(("0.0.0.0", PUERTO_MOVIL), app, numthreads=4, timeout=120)
    movil.ssl_adapter = BuiltinSSLAdapter(str(datos / "tls" / "cert.pem"), str(datos / "tls" / "clave.pem"))
    for s in (pc, movil):
        s.prepare()
        threading.Thread(target=s.serve, daemon=True).start()

    print(f"Abierto en {WEB}")
    print(f"Tus datos están en {datos}")
    print("No cierres esta ventana mientras lo uses. Para pararlo, ciérrala o pulsa Ctrl+C.")
    abrir()
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        pc.stop()
        movil.stop()


if __name__ == "__main__":
    main()
