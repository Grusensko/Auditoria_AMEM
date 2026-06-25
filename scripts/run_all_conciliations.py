import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from conciliador import run_conciliacion

def run_all():
    meses = ["2025-10", "2025-11", "2025-12", "2026-01", "2026-02", "2026-03", "2026-04", "2026-05"]
    print("Iniciando conciliación para todos los meses históricos...")
    for mes in meses:
        print(f"\n=========================================")
        print(f"CONCILIANDO MES: {mes}")
        print(f"=========================================")
        run_conciliacion(mes)
    print("\n¡Conciliación masiva completada con éxito!")

if __name__ == "__main__":
    run_all()
