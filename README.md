# tickets-presupuesto

Me lo hice para llegar a fin de mes sin apuntar los gastos a mano. Hago la foto del ticket con el móvil y el PC de casa la lee, la apunta en el calendario y separa lo que es capricho.

Todo va dentro de la wifi de casa, no hay servidor fuera.

![Calendario](web/demo/capturas/pc-calendario.png)

<img src="web/demo/capturas/movil.png" width="300" alt="Ticket leído en el móvil">

Las capturas son de la demo, con datos inventados.

## Lo que hace

- Lee el ticket con Tesseract: total, fecha, tienda y productos
- Marca los caprichos con una lista y se acuerda de lo que le corriges
- Plan del mes: lo que cobras, fijos, ocio y la compra de cada semana
- App Android que guarda los tickets si estás fuera y los manda al llegar a casa
- Desde iPhone o cualquier otro móvil va por el navegador

## Montarlo

```bash
cd web
cp .env.example .env    # cambia SECRET_KEY
./despliegue/certificado.sh
docker compose up -d --build
```

La web queda en http://127.0.0.1:8767. Para añadir un móvil, pestaña Móviles, creas un QR y lo escaneas con el móvil en la misma wifi. El navegador se queja del certificado porque es autofirmado, es normal.

Si usas ufw, `sudo despliegue/cortafuegos-movil.sh --nuevo` deja entrar solo a los móviles que des de alta.

Para verlo con datos de mentira: `docker compose -f compose.demo.yaml up -d --build` y abrir http://127.0.0.1:8777

## App

```bash
cd android
./gradlew assembleDebug
```

Se configura leyendo el QR del PC. Si el móvil no tiene servicios de Google, abre la galería en vez del escáner.

## Pendiente

- Solo lo he probado con un Redmi y con capturas de Google Wallet
- Con fotos torcidas o con poca luz el OCR falla bastante
- En iPhone hay que poner la dirección privada de la wifi en fija, si no cambia la MAC y el cortafuegos lo deja fuera
- Tests
