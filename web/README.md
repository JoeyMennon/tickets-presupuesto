# web

Django con SQLite. En Docker van dos servicios con la red del host:

| Servicio | Puerto | Para qué |
|---|---|---|
| web | 127.0.0.1:8767 | el PC |
| movil | 8768, https | los móviles, con llave |

Comandos que más uso:

```bash
docker compose up -d --build    # tras cambiar código
docker compose logs -f
```

- `cuentas/lector.py` lee los tickets
- `cuentas/clasificador.py` decide qué es capricho
- `cuentas/llave.py` filtra lo que llega de la wifi
- `despliegue/` certificado, cortafuegos y servicios de systemd si no quieres Docker
