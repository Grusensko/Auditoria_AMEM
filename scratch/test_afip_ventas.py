path = r"d:\OneDrive\Development\AMEM\_data\Facturas\2026-05\VENTAS.txt"
with open(path, 'r', encoding='latin1') as f:
    lines = f.readlines()
    print(f"Total líneas: {len(lines)}")
    if lines:
        for idx, l in enumerate(lines[:5]):
            print(f"Línea {idx + 1} longitud: {len(l)} | Contenido: {repr(l[:40])}...")
