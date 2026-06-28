import pandas as pd
import glob

banco_files = glob.glob(r"d:\OneDrive\Development\AMEM\_data\*Bancaria\*Movimientos_Supervielle_*.xlsx")
print(f"Archivos encontrados: {banco_files}")

if banco_files:
    excel_path = banco_files[0]
    df = pd.read_excel(excel_path)
    print("Columnas originales del Excel:")
    print(df.columns.tolist())
    print("\nPrimeras 3 filas:")
    print(df.head(3).to_dict(orient='records'))
