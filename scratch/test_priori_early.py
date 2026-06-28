import sys
sys.path.append('.')
from database import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

# Buscar todos los movimientos de 11:11 menores a 53
cursor.execute("""
    SELECT nro_fila, concepto, detalle, debito, credito, saldo
    FROM movimientos_banco
    WHERE fecha = '2026-05-29' AND hora = '11:11' AND nro_fila < 53
    ORDER BY nro_fila ASC
""")
print("--- MOVIMIENTOS DETALLADOS < 53 ---")
for r in cursor.fetchall():
    print(dict(r))
