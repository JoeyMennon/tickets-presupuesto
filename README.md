# Tickets y presupuesto

Haces la foto del ticket con el móvil y el PC de casa la lee, la apunta en el calendario y separa los caprichos.

| | |
|---|---|
| ![Calendario](web/demo/capturas/pc-calendario.png) | ![Móvil](web/demo/capturas/movil.png) |

Capturas con datos inventados.

## Qué hace

- Lee tickets con OCR: total, fecha, tienda y productos
- Separa los caprichos de la comida y aprende de lo que corriges
- Plan del mes: cobro, fijos, ocio y compra por semanas
- Calendario con agenda, gastado y previsto por día
- Cualquier móvil: app Android o la web desde el navegador, también iPhone
- Todo se queda en tu wifi: https con certificado propio, llave por móvil y cortafuegos por MAC

## Partes

| Carpeta | Qué es |
|---|---|
| `web/` | Django, SQLite y Tesseract, en Docker |
| `android/` | App en Kotlin y Compose: escanea, guarda en cola y manda al PC al llegar a casa |

## Arrancar

```bash
cd web
cp .env.example .env
./despliegue/certificado.sh
docker compose up -d --build
```

- PC: http://127.0.0.1:8767
- Móviles: pestaña **Móviles**, crear QR y escanearlo con el móvil en la misma wifi
- Opcional, cortafuegos por MAC con ufw: `sudo despliegue/cortafuegos-movil.sh --nuevo`

## Probar con datos inventados

```bash
cd web
docker compose -f compose.demo.yaml up -d --build
```

Abre http://127.0.0.1:8777

## App Android

```bash
cd android
./gradlew assembleDebug
```

Se conecta leyendo el QR del PC. Sin servicios de Google, abre la galería en vez del escáner.
