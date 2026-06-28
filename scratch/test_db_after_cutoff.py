import sys
sys.path.append('.')
from database import get_db_connection, decrypt_data

conn = get_db_connection()
cursor = conn.cursor()

# Ver clientes
cursor.execute("SELECT cuit_hash, cuit_encrypted, nombre_razon_social_encrypted FROM clientes LIMIT 5")
print("--- CLIENTES EN BD ---")
for r in cursor.fetchall():
    cuit = decrypt_data(r[1])
    nombre = decrypt_data(r[2])
    print(f"CUIT: {cuit} | Nombre: {nombre}")

# Ver facturas
cursor.execute("SELECT COUNT(*) FROM facturas")
print(f"\nTotal Facturas: {cursor.fetchone()[0]}")

# Ver movimientos banco
cursor.execute("SELECT COUNT(*) FROM movimientos_banco")
print(f"Total Movimientos Banco: {cursor.fetchone()[0]}")

# Ver facturas de Petroleros (30661876715)
cuit_petroleros = "30661876715"
import hashlib
hash_pet = hashlib.sha256(cuit_petroleros.encode()).hexdigest()

cursor.execute("SELECT COUNT(*) FROM facturas WHERE cuit_hash = ?", (hash_pet,))
print(f"\nFacturas de Petroleros: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM movimientos_banco WHERE cuit_hash_asociado = ?", (hash_pet,))
print(f"Movimientos Banco de Petroleros: {cursor.fetchone()[0]}")

# Detalles de movimientos de Petroleros
cursor.execute("SELECT fecha, concepto, credito, debito, mes_auditoria FROM movimientos_banco WHERE cuit_hash_asociado = ? LIMIT 5", (hash_pet,))
print("\nMovimientos de Petroleros:")
for r in cursor.fetchall():
    print(dict(r))
