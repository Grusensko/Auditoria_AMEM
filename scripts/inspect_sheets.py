import os
import glob
import pandas as pd

def inspect_sheets():
    data_dir = r"d:\OneDrive\Development\AMEM\_data\fwdinformesgestion"
    excel_files = glob.glob(os.path.join(data_dir, "*ABRIL 2026*.xlsx"))
    
    if not excel_files:
        print("No se encontró el informe de Abril 2026")
        return
            
    file_path = excel_files[0]
    
    try:
        xls = pd.ExcelFile(file_path)
        
        target_sheets = ['FACTURACIN ', 'FACTURACIÓN ', 'INGRESOS OBRAS SOCIALES']
        # Buscar coincidencias aproximadas
        found_sheets = []
        for s in xls.sheet_names:
            if 'factur' in s.lower() or 'obras' in s.lower():
                found_sheets.append(s)
                
        print("Hojas de interés encontradas:", found_sheets)
        
        for sheet in found_sheets:
            print(f"\n==================================================")
            print(f"MOSTRANDO PRIMERAS 40 FILAS DE LA HOJA: {sheet}")
            print(f"==================================================")
            df = pd.read_excel(file_path, sheet_name=sheet)
            print(f"Columnas detectadas en pandas: {df.columns.tolist()}")
            
            # Imprimir las filas
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', 1000)
            print(df.head(40).to_string())
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_sheets()
