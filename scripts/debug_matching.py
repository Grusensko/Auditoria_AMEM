import os
import sys
import hashlib
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import get_db_connection, decrypt_data
from conciliador import clean_factura_nro, get_cuit_for_obra_social

def debug_matching():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Ver algunas prestaciones reales cargadas
    print("Muestra de Prestaciones en la BD (primeras 5):")
    cursor.execute("SELECT id, obra_social_nombre, monto, factura_nro, mes_auditoria FROM prestaciones LIMIT 5")
    for row in cursor.fetchall():
        print(f"ID: {row[0]} | OS: {row[1]} | Monto: {row[2]} | Factura Excel: {row[3]} | Mes Aud: {row[4]}")
        
    # 2. Ver algunas facturas reales de AFIP cargadas
    print("\nMuestra de Facturas de AFIP en la BD (primeras 5):")
    cursor.execute("SELECT comprobante_id, cuit_txt, monto_total, fecha_emision, mes_auditoria FROM facturas LIMIT 5")
    for row in cursor.fetchall():
        print(f"CompID: {row[0]} | CUIT: {row[1]} | Monto: {row[2]} | Fecha Emisión: {row[3]} | Mes Aud: {row[4]}")
        
    # 3. Intentemos buscar una coincidencia manual para una prestación
    cursor.execute("SELECT obra_social_nombre, monto, factura_nro, id FROM prestaciones WHERE factura_nro != '' LIMIT 3")
    sample_prests = cursor.fetchall()
    
    for prest in sample_prests:
        os_nombre = prest['obra_social_nombre']
        monto = prest['monto']
        fact_nro = prest['factura_nro']
        p_id = prest['id']
        
        cuit = get_cuit_for_obra_social(os_nombre)
        c_hash = hashlib.sha256(cuit.encode()).hexdigest() if cuit else None
        fact_nro_clean = clean_factura_nro(fact_nro)
        
        print(f"\nIntentando emparejar Prestación ID {p_id}:")
        print(f"- OS: {os_nombre} (CUIT: {cuit})")
        print(f"- Factura Nº Excel: {fact_nro} (Limpia: {fact_nro_clean})")
        print(f"- Monto: {monto}")
        
        # Buscar por CUIT y número de factura aproximado
        if cuit:
            cursor.execute("""
                SELECT comprobante_id, cuit_txt, monto_total, fecha_emision
                FROM facturas
                WHERE cuit_hash = ?
            """, (c_hash,))
            all_cuit_facts = cursor.fetchall()
            print(f"- Facturas de este CUIT encontradas en AFIP: {len(all_cuit_facts)}")
            for f in all_cuit_facts[:5]:
                print(f"  * CompID: {f['comprobante_id']} | Monto AFIP: {f['monto_total']} | Fecha Emisión: {f['fecha_emision']}")
                
            # Buscar coincidencia exacta
            cursor.execute("""
                SELECT comprobante_id, monto_total, fecha_emision
                FROM facturas
                WHERE cuit_hash = ? AND CAST(comprobante_id AS TEXT) LIKE ?
            """, (c_hash, f"%{fact_nro_clean}"))
            match = cursor.fetchone()
            if match:
                print(f"  => ¡COINCIDENCIA ENCONTRADA POR NÚMERO! CompID: {match[0]} | Monto AFIP: {match[1]}")
            else:
                print("  => Sin coincidencia por número.")
                
    # 4. Búsqueda libre de facturas específicas por número
    print("\n--- Búsqueda de Facturas Específicas por Número (sin filtrar CUIT) ---")
    cursor.execute("""
        SELECT comprobante_id, cuit_txt, monto_total, fecha_emision 
        FROM facturas 
        WHERE comprobante_id LIKE '%1928%' OR comprobante_id LIKE '%1930%' OR comprobante_id LIKE '%1932%'
    """)
    libre_facts = cursor.fetchall()
    print(f"Facturas en AFIP con números 1928, 1930 o 1932: {len(libre_facts)}")
    for lf in libre_facts:
        # Buscar el nombre descifrado del CUIT
        cuit = lf['cuit_txt']
        c_hash = hashlib.sha256(cuit.encode()).hexdigest()
        cursor.execute("SELECT nombre_razon_social_encrypted FROM clientes WHERE cuit_hash = ?", (c_hash,))
        res = cursor.fetchone()
        nombre_cli = decrypt_data(res[0]) if res else "Desconocido"
        print(f"- CompID: {lf['comprobante_id']} | CUIT: {cuit} ({nombre_cli}) | Monto AFIP: {lf['monto_total']}")
                
    conn.close()

if __name__ == "__main__":
    debug_matching()
