# Presupuesto

Presupuesto hasta el próximo cobro, con agenda y tickets leídos del móvil.

- Web: http://127.0.0.1:8767, solo desde el PC
- Móviles: https en el puerto 8768, cada uno con su llave del QR de **Móviles**
- Cobro y previstos: pestaña **Plan**, en la base de datos
- Caprichos de serie: `cuentas/clasificador.py`
- Copia de prueba con datos inventados: `docker compose -f compose.demo.yaml up -d`, en http://127.0.0.1:8777

## Docker

| Qué | Comando |
|---|---|
| Arrancar | `docker compose up -d` |
| Ver estado | `docker compose ps` |
| Ver logs | `docker compose logs -f` |
| Reiniciar | `docker compose restart` |
| Tras cambiar código | `docker compose up -d --build` |
| Parar | `docker compose down` |

- Red del PC: el cortafuegos sigue mandando
- `datos/` y `.env` van montados: base de datos, tickets y certificado
- Certificado: `despliegue/certificado.sh`
- Cortafuegos: `sudo despliegue/cortafuegos-movil.sh <MAC>`, `--nuevo`, `--lista`, `--sacar <MAC>` o `--quitar`

| Pestaña | Contenido |
|---|---|
| Calendario | agenda, gastos y previstos por día; tickets por revisar |
| Plan | cobro, fijos, ocio, comida por semanas y lo gastado por partida |
| Móviles | alta por QR y llaves de cada móvil |
