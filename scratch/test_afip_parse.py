import sys
sys.path.append('.')
from database import get_db_connection
from loader import clean_cuit, hash_cuit, encrypt_data
from datetime import datetime

path = r"d:\OneDrive\Development\AMEM\_data\Facturas\2026-05\VENTAS.txt"
mes_auditoria = "2026-05"

with open(path, 'r', encoding='latin1') as f:
    for line_idx, line in enumerate(f, 1):
        if len(line) < 123:
            print(f"Línea {line_idx} ignorada por longitud: {len(line)}")
            continue
            
        fecha_raw = line[0:8].strip()
        tipo_comp = line[8:11].strip()
        pto_venta = line[11:16].strip()
        nro_comp = line[16:36].strip()
        cuit_clean = clean_cuit(line[58:78].strip())
        razon_social = line[78:108].strip()
        monto_raw = line[108:123].strip()
        
        try:
            fecha = datetime.strptime(fecha_raw, "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            fecha = fecha_raw
            
        try:
            monto = float(monto_raw) / 100.0
        except Exception as e:
            print(f"Error parseando monto en línea {line_idx}: {e}")
            continue
            
        comprobante_id = f"{pto_venta}-{tipo_comp}-{nro_comp}"
        print(f"Línea {line_idx} procesada: id={comprobante_id} | fecha={fecha} | cuit={cuit_clean} | monto={monto}")
