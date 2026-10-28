#!/usr/bin/env bash
# Al puerto 8768 solo entran los móviles de la lista, por su MAC.
# Uso con sudo:
#   cortafuegos-movil.sh AA:BB:CC:DD:EE:FF    añade ese móvil
#   cortafuegos-movil.sh --nuevo              busca el móvil que acaba de intentar entrar y lo añade
#   cortafuegos-movil.sh --lista              enseña los que hay
#   cortafuegos-movil.sh --sacar MAC          quita uno
#   cortafuegos-movil.sh --quitar             quita todas las reglas del móvil
set -euo pipefail
REGLAS=/etc/ufw/before.rules
COPIA=/etc/ufw/before.rules.antes-presupuesto
ETIQUETA=presupuesto-movil
AVISO="presupuesto-movil-fuera: "
PATRON_MAC='^([0-9a-f]{2}:){5}[0-9a-f]{2}$'

[[ $EUID -eq 0 ]] || { echo "Hay que ejecutarlo con sudo"; exit 1; }

actuales() {
    grep -- "--comment $ETIQUETA" "$REGLAS" | grep -o -- "--mac-source [0-9A-Fa-f:]*" | awk '{print tolower($2)}' || true
}

ORDEN="${1:-}"
case "$ORDEN" in
    --lista)
        actuales
        exit 0 ;;
    --nuevo)
        # La regla de aviso deja en el registro del kernel quién intentó entrar sin estar en la lista
        mapfile -t VISTOS < <(journalctl -k --since "-15min" --no-pager 2>/dev/null | grep -- "$AVISO" \
            | grep -o "MAC=[0-9a-f:]*" | cut -c5- | cut -d: -f7-12 | sort -u)
        CONOCIDOS=$(actuales)
        NUEVOS=()
        for m in "${VISTOS[@]}"; do grep -qx "$m" <<<"$CONOCIDOS" || NUEVOS+=("$m"); done
        if [[ ${#NUEVOS[@]} -eq 0 ]]; then
            echo "Nadie ha intentado entrar en los últimos 15 minutos."
            echo "Abre el enlace del QR en el móvil y vuelve a ejecutarlo."
            exit 1
        fi
        echo "Han intentado entrar:"
        for i in "${!NUEVOS[@]}"; do echo "  $((i + 1)). ${NUEVOS[$i]}"; done
        read -rp "¿Cuál añado? Pon el número: " N
        [[ "$N" =~ ^[0-9]+$ && $N -ge 1 && $N -le ${#NUEVOS[@]} ]] || { echo "Número no válido"; exit 1; }
        LISTA=$( (actuales; echo "${NUEVOS[$((N - 1))]}") | sort -u) ;;
    --sacar)
        QUITA=$(tr 'A-F' 'a-f' <<<"${2:-}")
        [[ "$QUITA" =~ $PATRON_MAC ]] || { echo "Pon la MAC que quitar"; exit 1; }
        LISTA=$(actuales | grep -vx "$QUITA" || true) ;;
    --quitar)
        LISTA="" ;;
    *)
        NUEVA=$(tr 'A-F' 'a-f' <<<"$ORDEN")
        [[ "$NUEVA" =~ $PATRON_MAC ]] || { echo "Pon la MAC del móvil, por ejemplo AA:BB:CC:DD:EE:FF, o --nuevo"; exit 1; }
        LISTA=$( (actuales; echo "$NUEVA") | sort -u) ;;
esac

ESTABA_ACTIVO=no
ufw status | grep -q "^Status: active" && ESTABA_ACTIVO=si
[[ -f "$COPIA" ]] || cp "$REGLAS" "$COPIA"
ANTES=$(mktemp)
cp "$REGLAS" "$ANTES"

volver_atras() {
    echo "Algo falló: vuelvo a las reglas de antes"
    cp "$ANTES" "$REGLAS"
    if [[ $ESTABA_ACTIVO == si ]]; then ufw reload; else ufw --force disable; fi
    exit 1
}

NUEVO=$(mktemp)
trap 'rm -f "$NUEVO" "$ANTES"' EXIT
# Parte siempre de las reglas sin nada de este script
grep -v -- "--comment $ETIQUETA" "$REGLAS" > "$NUEVO"

if [[ "$ORDEN" != "--quitar" ]]; then
    python3 - "$NUEVO" "$ETIQUETA" "$AVISO" $LISTA <<'PY'
import sys
ruta, etiqueta, aviso, *macs = sys.argv[1:]
lineas = open(ruta).read().split("\n")
pos = max(i for i, l in enumerate(lineas) if l.strip() == "COMMIT")
nuevas = [f"-A ufw-before-input -p tcp --dport 8768 -m mac --mac-source {m} -m comment --comment {etiqueta} -j ACCEPT"
          for m in macs]
nuevas += [
    f'-A ufw-before-input -p tcp --dport 8768 -m conntrack --ctstate NEW -m limit --limit 6/min -m comment --comment {etiqueta} -j LOG --log-prefix "{aviso}"',
    f"-A ufw-before-input -p tcp --dport 8768 -m comment --comment {etiqueta} -j DROP",
]
lineas[pos:pos] = nuevas
open(ruta, "w").write("\n".join(lineas))
PY
fi

# Prueba el fichero sin aplicarlo
iptables-restore --test --noflush < "$NUEVO" || { echo "Las reglas nuevas no valen, no toco nada"; exit 1; }

cp "$NUEVO" "$REGLAS"
chmod 644 "$REGLAS"
if [[ $ESTABA_ACTIVO == si ]]; then ufw reload || volver_atras; else ufw --force enable || volver_atras; fi
sleep 2
ping -c 1 -W 3 1.1.1.1 >/dev/null || volver_atras

if [[ "$ORDEN" == "--quitar" ]]; then
    echo "Quitadas las reglas del móvil"
else
    echo "Listo. Al 8768 entran:"
    actuales | sed 's/^/  /'
fi
ufw status | head -1
