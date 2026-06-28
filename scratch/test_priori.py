import sys
sys.path.append('.')
from database import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

# Buscar en movimientos de banco
cursor.execute("""
    SELECT fecha, hora, concepto, detalle, debito, credito, saldo, archivo_origen, nro_fila
    FROM movimientos_banco
    WHERE detalle LIKE '%PRIORI%' OR detalle LIKE '%GIMENA%' OR detalle LIKE '%VERONICA%'
       OR concepto LIKE '%PRIORI%' OR concepto LIKE '%GIMENA%' OR concepto LIKE '%VERONICA%'
    ORDER BY fecha ASC, hora ASC
""")

print("--- MOVIMIENTOS ENCONTRADOS ---")
rows = cursor.fetchall()
for r in rows:
    print(dict(r))
