import os
import sys
import glob
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from loader import load_afip_ventas, load_excel_banco, load_excel_prestaciones
from database import init_db, get_db_connection

def load_historical_data():
    print("Inicializando base de datos...")
    init_db()
    
    # 1. Cargar todas las facturas de AFIP (Enero a Mayo 2026)
    facturas_dir = r"d:\OneDrive\Development\AMEM\_data\Facturas"
    print("\n--- Cargando Historial de Facturas AFIP ---")
    for mes_folder in sorted(os.listdir(facturas_dir)):
        folder_path = os.path.join(facturas_dir, mes_folder)
        if os.path.isdir(folder_path):
            # mes_folder es tipo '2026-01', '2026-02', etc.
            ventas_txt = os.path.join(folder_path, "VENTAS.txt")
            if os.path.exists(ventas_txt):
                print(f"Cargando facturas para {mes_folder}...")
                load_afip_ventas(ventas_txt, mes_folder)
                
    # 2. Cargar todo el historial de Movimientos Bancarios (Supervielle)
    print("\n--- Cargando Historial de Movimientos Bancarios ---")
    banco_dir = r"d:\OneDrive\Development\AMEM\_data\Información Bancaria"
    banco_files = glob.glob(os.path.join(banco_dir, "Movimientos_Supervielle_*.xlsx"))
    if banco_files:
        banco_file = banco_files[0]
        print(f"Cargando movimientos desde: {os.path.basename(banco_file)}")
        # Los cargamos bajo el período '2026-05' que consolida el primer análisis
        # En la realidad, el cargador mapea las fechas internas reales de cada movimiento
        load_excel_banco(banco_file, "2026-05")
    else:
        print("No se encontró el archivo de movimientos del banco Supervielle.")
        
    # 3. Cargar Prestaciones de Gestión (Histórico 2025 y 2026)
    print("\n--- Cargando Historial de Prestaciones de Gestión ---")
    prest_dir = r"d:\OneDrive\Development\AMEM\_data\fwdinformesgestion"
    
    # Mapear los archivos de prestaciones para cada mes correspondiente
    prest_mappings = {
        "2025-10": "INFORME OCTUBRE 2025.xlsx",
        "2025-11": "INFORME NOVIEMBRE 2025 (1).xlsx",
        "2025-12": "INFORME DICIEMBRE 2025 (1).xlsx",
        "2026-01": "INFORME ENERO 2026.xlsx",
        "2026-02": "INFORME FEBRERO 2026.xlsx",
        "2026-03": "INFORME MARZO 2026 (1).xlsx",
        "2026-04": "INFORME ABRIL 2026.xlsx"
    }
    
    for mes, file_name in prest_mappings.items():
        file_path = os.path.join(prest_dir, file_name)
        if os.path.exists(file_path):
            print(f"Cargando prestaciones para {mes} desde {file_name}...")
            load_excel_prestaciones(file_path, mes)
        else:
            print(f"No se encontró el archivo para {mes}: {file_name}")
            
    print("\n¡Carga de datos históricos completada con éxito!")

if __name__ == "__main__":
    load_historical_data()
