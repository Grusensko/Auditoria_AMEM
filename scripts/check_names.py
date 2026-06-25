import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import sqlite3
from database import get_db_connection, decrypt_data

def check_names():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Nombres en prestaciones
    cursor.execute("SELECT DISTINCT obra_social_nombre FROM prestaciones")
    prest_os = [row[0] for row in cursor.fetchall()]
    print("Obras Sociales en Prestaciones (Excel):")
    for os_name in prest_os:
        print(f"- {os_name}")
        
    # 2. Clientes en facturas de AFIP
    print("\nClientes detectados en Facturas (AFIP):")
    cursor.execute("SELECT DISTINCT cuit_txt FROM facturas")
    cuit_list = [row[0] for row in cursor.fetchall()]
    
    for cuit in cuit_list:
        # Obtener el cliente descifrado
        import hashlib
        c_hash = hashlib.sha256(cuit.encode()).hexdigest()
        cursor.execute("SELECT cuit_encrypted, nombre_razon_social_encrypted FROM clientes WHERE cuit_hash = ?", (c_hash,))
        res = cursor.fetchone()
        if res:
            cuit_dec = decrypt_data(res[0])
            name_dec = decrypt_data(res[1])
            print(f"- CUIT: {cuit_dec} | Nombre: {name_dec}")
            
    conn.close()

if __name__ == "__main__":
    check_names()
