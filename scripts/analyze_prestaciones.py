import os
import glob
import pandas as pd

def analyze_prestaciones():
    data_dir = r"d:\OneDrive\Development\AMEM\_data\fwdinformesgestion"
    excel_files = glob.glob(os.path.join(data_dir, "*ABRIL 2026*.xlsx"))
    
    if not excel_files:
        print("No se encontró el informe de Abril 2026")
        return
            
    file_path = excel_files[0]
    print(f"Analizando archivo: {os.path.basename(file_path)}")
    
    try:
        xls = pd.ExcelFile(file_path)
        print("Hojas disponibles:", xls.sheet_names)
        
        for sheet_name in xls.sheet_names:
            print(f"\n==================================================")
            print(f"HOJA: {sheet_name}")
            print(f"==================================================")
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            print(f"Dimensiones: {df.shape[0]} filas, {df.shape[1]} columnas")
            print("Columnas:", list(df.columns))
            print("\nPrimeras 5 filas:")
            print(df.head(5).to_string())
            print("\nÚltimas 5 filas:")
            print(df.tail(5).to_string())
            
    except Exception as e:
        print(f"Error al analizar el archivo: {e}")

if __name__ == "__main__":
    analyze_prestaciones()
