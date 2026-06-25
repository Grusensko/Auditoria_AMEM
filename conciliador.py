import os
import hashlib
from database import get_db_connection

# Mapeo estático inicial de nombres cortos de Excel a CUITs de Obras Sociales en AFIP
OS_CUIT_MAP = {
    'OSPELSYM': '30661876715',
    'OSEP': '30623978164',
    'OSDE': '30546741253',
    'UNION PERSONAL': '30683032227',
    'PREVENCION': '30713045000',
    'AYE': '30657325372',          # Agua y Energía (OS del Personal de Empleados de Agua y Energía)
    'MUTUAL AGUA Y ENERGIA': '30657325372',
    'OSECAC': '30679232106',
    'OSPE': '33531576859',         # OSPE
    'PAMI': '30522763922',         # CUIT institucional INSSJP (PAMI)
    'IOSFA': '30714906948',        # Instituto de Obra Social de las FF.AA.
    'CIMESA': '30533836808',       # Círculo Médico de Mendoza (relacionado con CIMESA)
    'TV SALUD': '30516748385',
    'OSPRERA': '30547339416',
    'OSPAV': '30677896090',
    'OPSA': '30661507698',
    'INCLUIR': '30715815709',
    'PALERO': '18084418',
    'JALIF': '22392224'
}

def clean_factura_nro(fact_nro: str) -> str:
    """Extrae el número secuencial de la factura quitando prefijos de punto de venta (ej: '5-1499' -> '1499')."""
    if not fact_nro:
        return ""
    fact_str = str(fact_nro).strip()
    if not fact_str or fact_str.lower() in ['nan', 'none']:
        return ""
        
    if '-' in fact_str:
        parts = fact_str.split('-')
        digits = "".join(filter(str.isdigit, parts[-1]))
        return str(int(digits)) if digits else ""
    
    digits = "".join(filter(str.isdigit, fact_str))
    return str(int(digits)) if digits else ""

def get_cuit_for_obra_social(os_name: str) -> str:
    """Busca el CUIT correspondiente al nombre corto de la Obra Social."""
    os_name_upper = str(os_name).upper().strip()
    return OS_CUIT_MAP.get(os_name_upper, "")

def get_period_sort_value(periodo_str: str, mes_auditoria: str) -> tuple:
    """Calcula una tupla (año, mes, nombre) para ordenar cronológicamente los períodos en el contexto de un mes de auditoría."""
    periodo_str = str(periodo_str or '').upper().strip()
    
    if not mes_auditoria:
        mes_auditoria = '2026-01'
    try:
        audit_year, audit_month = map(int, mes_auditoria.split('-'))
    except Exception:
        audit_year, audit_month = 2026, 1
        
    first_part = periodo_str.split('/')[0].strip()
    
    MONTH_MAP = {
        'ENERO': 1, 'FEBRERO': 2, 'MARZO': 3, 'ABRIL': 4,
        'MAYO': 5, 'JUNIO': 6, 'JULIO': 7, 'AGOSTO': 8,
        'SEPTIEMBRE': 9, 'SETIEMBRE': 9, 'OCTUBRE': 10, 'NOVIEMBRE': 11, 'DICIEMBRE': 12
    }
    
    if first_part in MONTH_MAP:
        period_month = MONTH_MAP[first_part]
        if period_month > audit_month:
            period_year = audit_year - 1
        else:
            period_year = audit_year
    else:
        period_month = 0
        period_year = audit_year
        
    return (period_year, period_month, periodo_str)

def run_conciliacion(mes_auditoria: str):
    """Ejecuta la conciliación de tres vías para un mes de auditoría específico."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Limpiar conciliaciones previas del mismo mes de auditoría para evitar duplicados
    cursor.execute("DELETE FROM conciliaciones WHERE mes_auditoria = ?", (mes_auditoria,))
    
    # 2. Obtener todas las prestaciones del mes
    cursor.execute("""
        SELECT id, obra_social_nombre, paciente, fecha_factura, periodo, monto, factura_nro, fecha_pago, forma_pago
        FROM prestaciones 
        WHERE mes_auditoria = ?
    """, (mes_auditoria,))
    
    prestaciones = cursor.fetchall()
    print(f"Iniciando conciliación para {len(prestaciones)} prestaciones del mes {mes_auditoria}...")
    
    conciliados_count = 0
    pend_factura_count = 0
    pend_cobro_count = 0
    discrepancias_count = 0
    
    for prest in prestaciones:
        p_id = prest['id']
        os_nombre = prest['obra_social_nombre']
        monto_prest = prest['monto']
        fact_nro_excel = prest['factura_nro']
        fecha_pago_excel = prest['fecha_pago']
        
        # Buscar CUIT asociado
        cuit = get_cuit_for_obra_social(os_nombre)
        c_hash = hashlib.sha256(cuit.encode()).hexdigest() if cuit else None
        
        # 1. Buscar la Factura en AFIP (Vía 2)
        factura_id = None
        factura_encontrada = None
        cuit_hash_final = c_hash
        
        # Intentar buscar por número de factura limpio
        if fact_nro_excel:
            fact_nro_clean = clean_factura_nro(fact_nro_excel)
            if fact_nro_clean:
                # Primero, intentar buscar con CUIT hash y número de factura
                if c_hash:
                    cursor.execute("""
                        SELECT comprobante_id, monto_total, fecha_emision, cuit_hash
                        FROM facturas
                        WHERE cuit_hash = ? AND CAST(comprobante_id AS TEXT) LIKE ?
                    """, (c_hash, f"%{fact_nro_clean}"))
                    factura_encontrada = cursor.fetchone()
                
                # Segundo, si no se encuentra (por ej. por discrepancia de nombre/CUIT en Excel),
                # buscar únicamente por número de factura (dado que el número de factura en AFIP es único por punto de venta)
                if not factura_encontrada:
                    cursor.execute("""
                        SELECT comprobante_id, monto_total, fecha_emision, cuit_hash
                        FROM facturas
                        WHERE CAST(comprobante_id AS TEXT) LIKE ?
                    """, (f"%{fact_nro_clean}",))
                    coincidencias = cursor.fetchall()
                    if len(coincidencias) == 1:
                        factura_encontrada = coincidencias[0]
                    elif len(coincidencias) > 1:
                        # Si hay varias (por ej. distintas notas de crédito/débito o comprobantes),
                        # buscar la que coincida en monto exacto
                        for c in coincidencias:
                            if abs(c['monto_total'] - monto_prest) < 0.01:
                                factura_encontrada = c
                                break
                        if not factura_encontrada:
                            factura_encontrada = coincidencias[0]
                
                if factura_encontrada:
                    factura_id = factura_encontrada['comprobante_id']
                    # Usar el cuit_hash real de la factura de AFIP para buscar el movimiento en el banco
                    cuit_hash_final = factura_encontrada['cuit_hash']
                
        # 2. Buscar el Cobro en Banco (Vía 3)
        movimiento_id = None
        movimiento_encontrado = None
        
        # Coincidencia de monto exacta (sin retenciones por ser entidad sin fines de lucro)
        monto_exacto = monto_prest
        
        if cuit_hash_final:
            # Buscar en movimientos bancarios con el CUIT real/asociado
            # que coincidan exactamente en el monto y sean de crédito
            cursor.execute("""
                SELECT id, fecha, credito, concepto
                FROM movimientos_banco
                WHERE cuit_hash_asociado = ? 
                  AND credito = ?
                  AND debito = 0.0
            """, (cuit_hash_final, monto_exacto))
            
            movimiento_encontrado = cursor.fetchone()
            if movimiento_encontrado:
                movimiento_id = movimiento_encontrado['id']
        
        # Si no encontramos por CUIT en el banco (las transferencias a veces no traen el CUIT en el detalle),
        # podemos intentar buscar por el nombre de la obra social en el detalle del movimiento bancario
        if not movimiento_id:
            cursor.execute("""
                SELECT id, fecha, credito, concepto, detalle
                FROM movimientos_banco
                WHERE credito = ?
                  AND debito = 0.0
            """, (monto_exacto,))
            
            todos_movimientos = cursor.fetchall()
            for mov in todos_movimientos:
                detalle_upper = str(mov['detalle']).upper()
                concepto_upper = str(mov['concepto']).upper()
                # Verificar si contiene el nombre de la obra social
                if os_nombre.upper() in detalle_upper or os_nombre.upper() in concepto_upper:
                    movimiento_id = mov['id']
                    movimiento_encontrado = mov
                    break
                    
        # 3. Determinar el Estado Final de la Conciliación
        estado_final = 'DISCREPANCIA'
        observaciones = ""
        
        if factura_id and movimiento_id:
            estado_final = 'CONCILIADO'
            observaciones = "Matching de tres vías exitoso."
            conciliados_count += 1
        elif factura_id and not movimiento_id:
            estado_final = 'PENDIENTE_COBRO'
            observaciones = f"Factura {fact_nro_excel} emitida en AFIP. Sin depósito bancario identificado."
            pend_cobro_count += 1
        elif not factura_id and movimiento_id:
            estado_final = 'DISCREPANCIA'
            observaciones = "Pago recibido en banco pero factura no encontrada en AFIP."
            discrepancias_count += 1
        else:
            estado_final = 'PENDIENTE_FACTURA'
            observaciones = "Prestación registrada. Sin factura en AFIP ni depósito en banco."
            pend_factura_count += 1
            
        # 4. Insertar la conciliación
        cursor.execute("""
            INSERT INTO conciliaciones (prestacion_id, factura_id, movimiento_banco_id, estado_final, observaciones, mes_auditoria)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (p_id, factura_id, movimiento_id, estado_final, observaciones, mes_auditoria))
        
        # 5. Actualizar el estado en la tabla de prestaciones
        cursor.execute("""
            UPDATE prestaciones 
            SET estado_conciliacion = ? 
            WHERE id = ?
        """, (estado_final, p_id))
        
    conn.commit()
    conn.close()
    
    print("\n--- Resultados de la Conciliación ---")
    print(f"Conciliados (Match Completo): {conciliados_count}")
    print(f"Pendientes de Factura: {pend_factura_count}")
    print(f"Pendientes de Cobro: {pend_cobro_count}")
    print(f"Discrepancias: {discrepancias_count}")
    print("--------------------------------------")
    return {
        'conciliados': conciliados_count,
        'pendientes_factura': pend_factura_count,
        'pendientes_cobro': pend_cobro_count,
        'discrepancias': discrepancias_count
    }

if __name__ == "__main__":
    run_conciliacion("2026-05")
