import sys
sys.path.append('.')
from database import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

# Buscar todos los movimientos del 2026-05-29 a las 11:11
cursor.execute("""
    SELECT nro_fila, concepto, detalle, debito, credito, saldo
    FROM movimientos_banco
    WHERE fecha = '2026-05-29' AND hora = '11:11'
    ORDER BY nro_fila ASC
""")
print("--- MOVIMIENTOS DETALLADOS DEL 29-05-2026 11:11 ---")
for r in cursor.fetchall():
    print(dict(r))
