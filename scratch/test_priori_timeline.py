import sys
sys.path.append('.')
from database import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

# Buscar todos los movimientos entre el 2026-05-25 y 2026-05-30
cursor.execute("""
    SELECT fecha, hora, concepto, detalle, debito, credito, saldo, nro_fila
    FROM movimientos_banco
    WHERE fecha >= '2026-05-25' AND fecha <= '2026-05-30'
    ORDER BY fecha ASC, hora ASC, nro_fila ASC
""")
print("--- MOVIMIENTOS ALREDEDOR DEL REVERSO ---")
for r in cursor.fetchall():
    print(dict(r))
