import sys
sys.path.append('.')
from database import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

# Buscar todos los movimientos que tengan montos de $495313.00 o $184369.72
cursor.execute("""
    SELECT fecha, hora, concepto, detalle, debito, credito, saldo
    FROM movimientos_banco
    WHERE debito = 495313.00 OR credito = 495313.00
       OR debito = 184369.72 OR credito = 184369.72
""")
print("--- MOVIMIENTOS POR MONTOS EXACTOS ---")
for r in cursor.fetchall():
    print(dict(r))

# Buscar todos los movimientos que contengan "GIMENA" o "PRIOR" o "VERONICA" sin límites de columnas
cursor.execute("""
    SELECT fecha, hora, concepto, detalle, debito, credito, saldo
    FROM movimientos_banco
    WHERE detalle LIKE '%PRIOR%' OR detalle LIKE '%VERONICA%'
    ORDER BY fecha ASC, hora ASC
""")
print("\n--- TODOS LOS MOVIMIENTOS DE PRIORI / PRIOR / VERONICA ---")
for r in cursor.fetchall():
    print(dict(r))
