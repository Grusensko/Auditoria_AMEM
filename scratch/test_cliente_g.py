import sys
import sqlite3
sys.path.append('.')
from database import get_db_connection, decrypt_data

conn = get_db_connection()
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# CUIT de "G"
cuit = "27257827890"
import hashlib
cuit_hash = hashlib.sha256(cuit.encode('utf-8')).hexdigest()

print(f"--- ANALIZANDO CLIENTE CUIT {cuit} (HASH: {cuit_hash}) ---")

# 1. Ver en tabla clientes
cursor.execute("SELECT * FROM clientes WHERE cuit_hash = ?", (cuit_hash,))
row = cursor.fetchone()
if row:
    print("Encontrado en tabla CLIENTES:")
    print(f"  Categoría: {row['categoria']}")
    print(f"  Nombre Desencriptado: {decrypt_data(row['cuit_encrypted'])}")
else:
    print("No encontrado en tabla clientes.")

# 2. Ver movimientos de banco asociados
cursor.execute("SELECT fecha, concepto, detalle, debito, credito, saldo FROM movimientos_banco WHERE cuit_hash_asociado = ?", (cuit_hash,))
rows = cursor.fetchall()
print(f"\nEncontrados {len(rows)} movimientos bancarios:")
for r in rows:
    print(f"  Fecha: {r['fecha']} | Concepto: {r['concepto']} | Detalle: {r['detalle']} | Débito: {r['debito']} | Crédito: {r['credito']}")

conn.close()
