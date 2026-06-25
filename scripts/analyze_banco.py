import os
import glob
import pandas as pd

def analyze_banco():
    # Ruta de la información bancaria
    data_dir = r"d:\OneDrive\Development\AMEM\_data\Información Bancaria"
    
    # Buscar archivos xlsx en la carpeta de bancos
    excel_files = glob.glob(os.path.join(data_dir, "*.xlsx"))
    
    if not excel_files:
        print(f"No se encontraron archivos de movimientos bancarios en {data_dir}")
        return
            
    file_path = excel_files[0]
    print(f"Analizando archivo de banco: {os.path.basename(file_path)}")
    
    try:
        # Cargar las hojas disponibles en el Excel
        xls = pd.ExcelFile(file_path)
        print("Hojas encontradas:", xls.sheet_names)
        
        # Cargar la primera hoja
        df = pd.read_excel(file_path, sheet_name=0)
        
        print("\n--- Dimensiones ---")
        print(f"Filas: {df.shape[0]}, Columnas: {df.shape[1]}")
        
        print("\n--- Columnas Encontradas ---")
        for col in df.columns:
            non_null = df[col].count()
            print(f"- {col} (Tipo: {df[col].dtype}, No nulos: {non_null}/{df.shape[0]})")
            
        print("\n--- Primeras 5 Filas ---")
        print(df.head(5).to_string())
        
        print("\n--- Resumen estadístico de importes ---")
        # Buscar columnas relacionadas con importes (crédito, débito, importe)
        for col in df.columns:
            col_lower = str(col).lower()
            if any(term in col_lower for term in ['importe', 'credito', 'cred', 'deposito', 'ingreso', 'monto']):
                print(f"\nColumna de Importe detectada '{col}':")
                print(df[col].describe())
                
    except Exception as e:
        print(f"Error al analizar el archivo: {e}")

if __name__ == "__main__":
    analyze_banco()
