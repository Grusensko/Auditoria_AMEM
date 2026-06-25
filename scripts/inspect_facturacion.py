import os
import glob
import pandas as pd

def inspect_facturacion():
    data_dir = r"d:\OneDrive\Development\AMEM\_data\fwdinformesgestion"
    excel_files = glob.glob(os.path.join(data_dir, "*ABRIL 2026*.xlsx"))
    
    if not excel_files:
        print("No se encontró el informe de Abril 2026")
        return
            
    file_path = excel_files[0]
    
    try:
        xls = pd.ExcelFile(file_path)
        sheet_name = 'FACTURACIN '
        if sheet_name not in xls.sheet_names:
            # Buscar similar
            for s in xls.sheet_names:
                if 'factur' in s.lower():
                    sheet_name = s
                    break
        
        print(f"Inspeccionando hoja: '{sheet_name}'")
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        print("Dimensiones:", df.shape)
        print("Columnas:", df.columns.tolist())
        print("\nPrimeras 40 filas:")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        print(df.head(40).to_string())
        
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    inspect_facturacion()
