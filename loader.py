import os
import re
import glob
import pandas as pd
from datetime import datetime
from database import (
    get_db_connection, 
    encrypt_data, 
    hash_cuit, 
    decrypt_data
)

def clean_cuit(cuit_val) -> str:
    if pd.isna(cuit_val):
        return ""
    # Dejar solo dígitos y quitar ceros a la izquierda
    digits = "".join(filter(str.isdigit, str(cuit_val)))
    return digits.lstrip('0')

def extract_cuit_and_name_from_bank_detail(detail: str) -> tuple[str, str]:
    """
    Intenta extraer el CUIT/DNI y Razón Social/Nombre del detalle del movimiento bancario.
    Ejemplo: DOCUMENTO: 20420101490 NOMBRE: ALOSI SEBASTIAN FEDERICO CBU:...
    Ejemplo 2: BENEF:  0-27413687840 REF:VAR-...
    """
    if not detail or pd.isna(detail):
        return "", ""
    
    cuit = ""
    name = ""
    
    # Buscar patrón de DOCUMENTO / CUIT / DNI
    doc_match = re.search(r'DOCUMENTO:\s*(\d+)', detail, re.IGNORECASE)
    if doc_match:
        cuit = doc_match.group(1)
        
    # Buscar patrón de BENEF: 0-27413687840
    benef_match = re.search(r'BENEF:\s*\d*-(\d+)', detail, re.IGNORECASE)
    if benef_match:
        cuit = benef_match.group(1)
        
    # Buscar patrón de NOMBRE
    name_match = re.search(r'NOMBRE:\s*([^CBU:]+)', detail, re.IGNORECASE)
    if name_match:
        name = name_match.group(1).strip()
        
    return clean_cuit(cuit), name

def load_afip_ventas(ventas_txt_path: str, mes_auditoria: str) -> int:
    """Parsea el archivo VENTAS.txt de AFIP y carga las facturas y clientes en la BD."""
    if not os.path.exists(ventas_txt_path):
        print(f"El archivo {ventas_txt_path} no existe.")
        return 0
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    count = 0
    with open(ventas_txt_path, 'r', encoding='latin1') as f:
        for line in f:
            if len(line) < 123:
                continue
                
            # Parsing del registro de ventas de AFIP (RG 3685)
            fecha_raw = line[0:8].strip()     # YYYYMMDD
            tipo_comp = line[8:11].strip()    # Código tipo comprobante
            pto_venta = line[11:16].strip()   # Punto de venta
            nro_comp = line[16:36].strip()    # Nro comprobante desde
            cuit_clean = clean_cuit(line[58:78].strip()) # CUIT del comprador
            razon_social = line[78:108].strip()          # Razón social
            monto_raw = line[108:123].strip() # Monto total (multiplicado por 100)
            
            # Formatear datos
            try:
                fecha = datetime.strptime(fecha_raw, "%Y%m%d").strftime("%Y-%m-%d")
            except ValueError:
                fecha = fecha_raw
                
            monto = float(monto_raw) / 100.0
            comprobante_id = f"{pto_venta}-{tipo_comp}-{nro_comp}"
            
            # 1. Guardar o actualizar el cliente en la tabla clientes (encriptado)
            c_hash = hash_cuit(cuit_clean)
            if cuit_clean:
                cursor.execute("SELECT cuit_hash FROM clientes WHERE cuit_hash = ?", (c_hash,))
                if not cursor.fetchone():
                    cuit_enc = encrypt_data(cuit_clean)
                    razon_enc = encrypt_data(razon_social)
                    cursor.execute("""
                    INSERT INTO clientes (cuit_hash, cuit_encrypted, nombre_razon_social_encrypted, categoria)
                    VALUES (?, ?, ?, ?)
                    """, (c_hash, cuit_enc, razon_enc, 'Obra Social / Empresa'))
            
            # 2. Insertar la factura
            cursor.execute("SELECT comprobante_id FROM facturas WHERE comprobante_id = ?", (comprobante_id,))
            if not cursor.fetchone():
                cursor.execute("""
                INSERT INTO facturas (comprobante_id, cuit_hash, cuit_txt, fecha_emision, monto_total, tipo_comprobante, mes_auditoria)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (comprobante_id, c_hash, cuit_clean, fecha, monto, tipo_comp, mes_auditoria))
                count += 1
                
    conn.commit()
    conn.close()
    print(f"Cargadas {count} facturas desde AFIP Ventas para el mes {mes_auditoria}.")
    return count

def load_excel_prestaciones(excel_path: str, mes_auditoria: str) -> int:
    """Parsea la hoja de INGRESOS OBRAS SOCIALES del Excel e importa a la BD."""
    if not os.path.exists(excel_path):
        print(f"El archivo {excel_path} no existe.")
        return 0
        
    xls = pd.ExcelFile(excel_path)
    sheet_name = None
    for s in xls.sheet_names:
        if 'obras' in s.lower() and 'ingreso' in s.lower():
            sheet_name = s
            break
            
    if not sheet_name:
        print("No se encontró la hoja de ingresos de obras sociales en el Excel de prestaciones.")
        return 0
        
    df = pd.read_excel(excel_path, sheet_name=sheet_name)
    
    # Buscar dinámicamente la fila de encabezado
    header_idx = None
    for idx, row in df.iterrows():
        row_vals = [str(val).upper().strip() for val in row.values if pd.notna(val)]
        if any('OBRA' in val or 'SOCIAL' in val for val in row_vals) and any('MONTO' in val or 'IMPORTE' in val for val in row_vals):
            header_idx = idx
            break
            
    if header_idx is not None:
        print(f"Cabecera detectada en la fila {header_idx} de la hoja {sheet_name}")
        df.columns = [str(df.iloc[header_idx, col_idx]).strip() for col_idx in range(df.shape[1])]
        df = df.iloc[header_idx + 1:].reset_index(drop=True)
    else:
        print("Detección dinámica fallida. Intentando normalización estándar...")
        
    # Normalizar nombres de columnas
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    # Buscar columnas de forma robusta e inteligente
    col_mapping = {}
    for col in df.columns:
        col_clean = str(col).upper().strip()
        if 'TIPO' in col_clean and 'OBRA' not in col_clean:
            col_mapping['TIPO'] = col
        elif any(term in col_clean for term in ['FACT', 'NRO', 'NUM', 'N°', 'Nº']) or col_clean == 'N':
            col_mapping['FACTURA Nº'] = col
        elif 'FECHA' in col_clean and 'PAGO' not in col_clean:
            col_mapping['FECHA'] = col
        elif 'OBRA' in col_clean or 'SOCIAL' in col_clean:
            col_mapping['TIPO DE OBRA SOCIAL'] = col
        elif 'MONTO' in col_clean or 'IMPORTE' in col_clean or 'VALOR' in col_clean:
            col_mapping['MONTO'] = col
            
    # Verificar si encontramos al menos las columnas clave para continuar
    required_keys = ['TIPO DE OBRA SOCIAL', 'MONTO']
    missing = [k for k in required_keys if k not in col_mapping]
    if missing:
        print("El Excel no posee las columnas de prestaciones requeridas:", missing)
        print("Columnas encontradas en el Excel:", list(df.columns))
        return 0
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Hacer la carga de prestaciones de gestión de este período limpia/idempotente
    cursor.execute("DELETE FROM prestaciones WHERE mes_auditoria = ?", (mes_auditoria,))
    
    count = 0
    for idx, row in df.iterrows():
        # Saltar si no hay un monto válido o tipo
        monto_col = col_mapping.get('MONTO')
        tipo_col = col_mapping.get('TIPO')
        os_col = col_mapping.get('TIPO DE OBRA SOCIAL')
        fact_col = col_mapping.get('FACTURA Nº')
        fecha_col = col_mapping.get('FECHA')
        
        if pd.isna(row.get(monto_col)) or pd.isna(row.get(os_col)):
            continue
            
        obra_social = str(row.get(os_col)).strip()
        if "total" in obra_social.lower():
            # Saltar fila de totales
            continue
            
        monto = float(row.get(monto_col))
        tipo = str(row.get(tipo_col)) if not pd.isna(row.get(tipo_col)) else ""
        factura_nro = str(row.get(fact_col)).strip() if not pd.isna(row.get(fact_col)) else ""
        
        # Procesar fechas
        fecha_raw = row.get(fecha_col)
        fecha_prestacion = ""
        if isinstance(fecha_raw, datetime):
            fecha_prestacion = fecha_raw.strftime("%Y-%m-%d")
        elif pd.notna(fecha_raw):
            fecha_prestacion = str(fecha_raw).split(" ")[0]
            
        # Período y Paciente (si existen)
        paciente = str(row.get('PACIENTE')).strip() if 'PACIENTE' in df.columns and pd.notna(row.get('PACIENTE')) else ""
        periodo = str(row.get('PERIODO')).strip() if 'PERIODO' in df.columns and pd.notna(row.get('PERIODO')) else ""
        
        # Fecha de cobro registrada en Excel
        fecha_pago = ""
        fecha_pago_raw = row.get('FECHA DE PAGO') if 'FECHA DE PAGO' in df.columns else None
        if isinstance(fecha_pago_raw, datetime):
            fecha_pago = fecha_pago_raw.strftime("%Y-%m-%d")
        elif pd.notna(fecha_pago_raw):
            fecha_pago = str(fecha_pago_raw).split(" ")[0]
            
        forma_pago = str(row.get('FORMA DE PAGO')).strip() if 'FORMA DE PAGO' in df.columns and pd.notna(row.get('FORMA DE PAGO')) else ""
        
        # Insertar prestación
        cursor.execute("""
        INSERT INTO prestaciones (
            obra_social_nombre, paciente, fecha_factura, periodo, monto, 
            factura_nro, forma_pago, fecha_pago, mes_auditoria
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (obra_social, paciente, fecha_prestacion, periodo, monto, factura_nro, forma_pago, fecha_pago, mes_auditoria))
        count += 1
        
    conn.commit()
    conn.close()
    print(f"Cargadas {count} prestaciones de gestión para el mes {mes_auditoria}.")
    return count

def load_excel_banco(excel_path: str, mes_auditoria: str) -> int:
    """Parsea el Excel de movimientos de Supervielle y carga a la BD."""
    if not os.path.exists(excel_path):
        print(f"El archivo {excel_path} no existe.")
        return 0
        
    df = pd.read_excel(excel_path)
    
    # Normalizar columnas
    df.columns = [str(c).strip().title() for c in df.columns]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    count = 0
    for idx, row in df.iterrows():
        fecha_raw = row.get('Fecha')
        concepto = str(row.get('Concepto')).strip() if pd.notna(row.get('Concepto')) else ""
        detalle = str(row.get('Detalle')).strip() if pd.notna(row.get('Detalle')) else ""
        debito = float(row.get('Díbito')) if pd.notna(row.get('Díbito')) else 0.0
        credito = float(row.get('Crédito')) if pd.notna(row.get('Crédito')) else 0.0
        saldo = float(row.get('Saldo')) if pd.notna(row.get('Saldo')) else 0.0
        hora = str(row.get('Hora')).strip() if pd.notna(row.get('Hora')) else ""
        
        if pd.isna(fecha_raw) or not concepto:
            continue
            
        # Formatear Fecha (DD/MM/YYYY a YYYY-MM-DD)
        fecha = ""
        if isinstance(fecha_raw, datetime):
            fecha = fecha_raw.strftime("%Y-%m-%d")
        else:
            try:
                fecha = datetime.strptime(str(fecha_raw).strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
            except ValueError:
                fecha = str(fecha_raw)
                
        # Limpiar floats con representación nula rara
        if debito < 1e-10: debito = 0.0
        if credito < 1e-10: credito = 0.0
        
        # Extraer CUIT y Nombre del detalle del movimiento
        cuit_asociado, nombre_asociado = extract_cuit_and_name_from_bank_detail(detalle)
        c_hash = hash_cuit(cuit_asociado) if cuit_asociado else None
        
        # Si detectamos un nuevo cliente en el banco, guardarlo
        if cuit_asociado and c_hash:
            cursor.execute("SELECT cuit_hash FROM clientes WHERE cuit_hash = ?", (c_hash,))
            if not cursor.fetchone():
                cuit_enc = encrypt_data(cuit_asociado)
                nombre_enc = encrypt_data(nombre_asociado if nombre_asociado else "Cliente Identificado Banco")
                cursor.execute("""
                INSERT INTO clientes (cuit_hash, cuit_encrypted, nombre_razon_social_encrypted, categoria)
                VALUES (?, ?, ?, ?)
                """, (c_hash, cuit_enc, nombre_enc, 'Identificado por Banco'))
                
        # Verificar duplicados del movimiento exacto
        cursor.execute("""
        SELECT id FROM movimientos_banco 
        WHERE fecha = ? AND hora = ? AND concepto = ? AND detalle = ? AND debito = ? AND credito = ? AND saldo = ?
        """, (fecha, hora, concepto, detalle, debito, credito, saldo))
        
        if not cursor.fetchone():
            cursor.execute("""
            INSERT INTO movimientos_banco (
                fecha, hora, concepto, detalle, debito, credito, saldo, 
                cuit_hash_asociado, cuit_txt_asociado, mes_auditoria
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (fecha, hora, concepto, detalle, debito, credito, saldo, c_hash, cuit_asociado if cuit_asociado else None, mes_auditoria))
            count += 1
        
    conn.commit()
    conn.close()
    print(f"Cargados {count} movimientos bancarios para el mes {mes_auditoria}.")
    return count

if __name__ == "__main__":
    # Test de carga con la información de Mayo 2026
    print("Iniciando carga de prueba de Mayo 2026...")
    
    afip_file = r"d:\OneDrive\Development\AMEM\_data\2026-05\RESULTADOS_BUSQUEDA\VENTAS.txt"
    banco_file = glob.glob(r"d:\OneDrive\Development\AMEM\_data\Información Bancaria\Movimientos_Supervielle_*.xlsx")[0]
    prestaciones_file = r"d:\OneDrive\Development\AMEM\_data\fwdinformesgestion\INFORME ABRIL 2026.xlsx" # Usaremos Abril como prueba
    
    load_afip_ventas(afip_file, "2026-05")
    load_excel_banco(banco_file, "2026-05")
    load_excel_prestaciones(prestaciones_file, "2026-05")
