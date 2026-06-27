import os
import threading
import time
import webbrowser
import uvicorn

def open_browser():
    time.sleep(1.5)
    print("Abriendo el navegador en http://127.0.0.1:8000 ...")
    webbrowser.open("http://127.0.0.1:8000")

# Leer secretos de Streamlit para cargar la clave criptográfica AMEM_ENCRYPTION_KEY
if "AMEM_ENCRYPTION_KEY" not in os.environ:
    secrets_path = os.path.join(".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        try:
            with open(secrets_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "AMEM_ENCRYPTION_KEY" in line:
                        parts = line.split("=")
                        if len(parts) == 2:
                            val = parts[1].strip().strip('"').strip("'")
                            os.environ["AMEM_ENCRYPTION_KEY"] = val
                            print("Clave de cifrado AMEM_ENCRYPTION_KEY cargada correctamente desde secrets.toml")
                            break
        except Exception as e:
            print(f"Advertencia: No se pudo leer el archivo de secretos.toml: {e}")

if __name__ == "__main__":
    print("Iniciando Servidor de Auditoría AMEM...")
    # Iniciar hilo para abrir el navegador
    threading.Thread(target=open_browser, daemon=True).start()
    # Iniciar servidor FastAPI
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
