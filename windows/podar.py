# deja en la carpeta solo el exe y las dll que carga, siguiendo las dependencias
import sys
from pathlib import Path

import pefile

carpeta, exe = Path(sys.argv[1]), sys.argv[2].lower()
hay = {f.name.lower(): f for f in carpeta.glob("*.dll")}
usadas, pendientes = set(), [exe]
while pendientes:
    pe = pefile.PE(str(carpeta / pendientes.pop()), fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
                                           pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"]])
    for imp in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []) + getattr(pe, "DIRECTORY_ENTRY_DELAY_IMPORT", []):
        nombre = imp.dll.decode().lower()
        if nombre in hay and nombre not in usadas:
            usadas.add(nombre)
            pendientes.append(nombre)
for nombre, f in hay.items():
    if nombre not in usadas:
        f.unlink()
print(f"{carpeta}: {len(usadas)} dll de {len(hay)}")
