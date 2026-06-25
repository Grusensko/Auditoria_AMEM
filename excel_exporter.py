import sqlite3
import pandas as pd
import io
from database import get_db_connection, decrypt_data
from conciliador import get_period_sort_value

def generate_excel_report(mes_auditoria: str) -> bytes:
    """Genera un archivo Excel formateado profesionalmente con los resultados de la conciliación."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Obtener todas las prestaciones con sus datos de conciliación, facturas y movimientos asociados
    query = """
        SELECT 
            p.obra_social_nombre AS [Obra Social],
            p.paciente AS [Paciente],
            p.periodo AS [Período Prestación],
            p.monto AS [Monto Prestación],
            p.fecha_factura AS [Fecha Factura Excel],
            p.factura_nro AS [Factura Nº Excel],
            f.comprobante_id AS [Factura AFIP ID],
            f.fecha_emision AS [Fecha Emisión AFIP],
            f.monto_total AS [Monto AFIP],
            mb.fecha AS [Fecha Pago Banco],
            mb.credito AS [Monto Cobrado Banco],
            mb.concepto AS [Concepto Banco],
            c.estado_final AS [Estado Conciliación],
            c.observaciones AS [Observaciones Auditoría]
        FROM prestaciones p
        LEFT JOIN conciliaciones c ON p.id = c.prestacion_id
        LEFT JOIN facturas f ON c.factura_id = f.comprobante_id
        LEFT JOIN movimientos_banco mb ON c.movimiento_banco_id = mb.id
        WHERE p.mes_auditoria = ?
    """
    
    df = pd.read_sql_query(query, conn, params=(mes_auditoria,))
    conn.close()
    
    if not df.empty:
        # Ordenar por el orden cronológico del período
        df['_sort_key'] = df.apply(lambda row: get_period_sort_value(row['Período Prestación'], mes_auditoria), axis=1)
        df = df.sort_values('_sort_key').drop(columns=['_sort_key'])
    
    if df.empty:
        # Retornar un Excel vacío o básico
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        pd.DataFrame({"Mensaje": ["No hay datos para el mes seleccionado."]}).to_excel(writer, index=False)
        writer.close()
        return output.getvalue()
        
    # Crear un buffer en memoria
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    
    # Volcar el DataFrame al Excel
    sheet_name = f"Auditoría {mes_auditoria}"
    df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    # Obtener el libro y la hoja
    workbook  = writer.book
    worksheet = writer.sheets[sheet_name]
    
    # Definir formatos premium
    header_format = workbook.add_format({
        'bold': True,
        'text_wrap': True,
        'valign': 'top',
        'fg_color': '#1F2937', # Gris oscuro/azul
        'font_color': '#FFFFFF',
        'border': 1,
        'font_name': 'Segoe UI',
        'font_size': 11
    })
    
    # Formato numérico para montos
    currency_format = workbook.add_format({
        'num_format': '$#,##0.00',
        'font_name': 'Segoe UI',
        'font_size': 10
    })
    
    # Formato de texto normal
    normal_format = workbook.add_format({
        'font_name': 'Segoe UI',
        'font_size': 10
    })
    
    # Colores condicionales según el estado
    # Hacemos formatos con colores suaves para no sobrecargar visualmente a los socios
    fmt_conciliado = workbook.add_format({
        'fg_color': '#D1E7DD', # Verde suave
        'font_color': '#0F5132',
        'font_name': 'Segoe UI',
        'font_size': 10,
        'border': 1
    })
    
    fmt_pend_cobro = workbook.add_format({
        'fg_color': '#FFF3CD', # Amarillo/Naranja suave
        'font_color': '#664D03',
        'font_name': 'Segoe UI',
        'font_size': 10,
        'border': 1
    })
    
    fmt_pend_fact = workbook.add_format({
        'fg_color': '#E8F0FE', # Azul suave
        'font_color': '#1A73E8',
        'font_name': 'Segoe UI',
        'font_size': 10,
        'border': 1
    })
    
    fmt_discrepancia = workbook.add_format({
        'fg_color': '#F8D7DA', # Rojo suave
        'font_color': '#842029',
        'font_name': 'Segoe UI',
        'font_size': 10,
        'border': 1
    })
    
    # Escribir cabeceras con el formato
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, header_format)
        
    # Aplicar formato de datos y colores según el estado de la fila
    for row_idx in range(len(df)):
        estado = df.iloc[row_idx]['Estado Conciliación']
        
        # Elegir formato de fila según el estado
        row_format = normal_format
        if estado == 'CONCILIADO':
            row_format = fmt_conciliado
        elif estado == 'PENDIENTE_COBRO':
            row_format = fmt_pend_cobro
        elif estado == 'PENDIENTE_FACTURA':
            row_format = fmt_pend_fact
        elif estado == 'DISCREPANCIA':
            row_format = fmt_discrepancia
            
        for col_idx in range(len(df.columns)):
            val = df.iloc[row_idx, col_idx]
            
            # Chequear si es nulo
            if pd.isna(val):
                val = ""
                
            # Si es columna de moneda, aplicar formato de moneda
            col_name = df.columns[col_idx]
            if "Monto" in col_name or "Monto AFIP" in col_name:
                # Si el formato de fila es normal, usamos el formato de moneda normal.
                # Si tiene color, combinamos
                if row_format == normal_format:
                    worksheet.write_number(row_idx + 1, col_idx, float(val) if val != "" else 0.0, currency_format)
                else:
                    # Clonar formato de color para aplicar número de moneda
                    color_curr_format = workbook.add_format({
                        'num_format': '$#,##0.00',
                        'fg_color': row_format.fg_color,
                        'font_color': row_format.font_color,
                        'font_name': 'Segoe UI',
                        'font_size': 10,
                        'border': 1
                    })
                    worksheet.write_number(row_idx + 1, col_idx, float(val) if val != "" else 0.0, color_curr_format)
            else:
                worksheet.write(row_idx + 1, col_idx, val, row_format)
                
    # Autoajustar el ancho de las columnas
    for col_idx, col_name in enumerate(df.columns):
        max_len = max(
            df[col_name].apply(lambda x: len(str(x)) if pd.notna(x) else 0).max(),
            len(col_name)
        ) + 3
        worksheet.set_column(col_idx, col_idx, min(max_len, 35))
        
    writer.close()
    return output.getvalue()
