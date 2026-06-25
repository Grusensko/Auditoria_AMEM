# Guía de Despliegue y Arquitectura: GitHub + Streamlit Cloud

Este documento detalla la estructura, flujo de trabajo, configuraciones de seguridad y despliegue del **Sistema de Auditoría Contable AMEM**.

---

## 1. Estructura y Flujo con GitHub

El repositorio está alojado en GitHub en la URL oficial:
🔗 [https://github.com/Grusensko/Auditoria_AMEM.git](https://github.com/Grusensko/Auditoria_AMEM.git)

### 📂 Archivos en el Repositorio
* **`app.py`**: Punto de entrada de la aplicación web Streamlit (contiene la UI, lógica de ruteo y CSS personalizado).
* **`database.py`**: Definición del esquema SQLite, cifrado simétrico Fernet (AES-256) y hashing SHA-256 de CUITs.
* **`conciliador.py`**: Lógica de conciliación de tres vías (Prestaciones, Facturas AFIP y Movimientos de Banco Supervielle).
* **`loader.py`**: Procesamiento de archivos subidos (Excel de prestaciones, VENTAS.txt de AFIP y extracto bancario).
* **`excel_exporter.py`**: Generador del informe final de auditoría en Excel formateado.
* **`.streamlit/config.toml`**: Configuración de tema visual corporativo (colores Slate claro y verde esmeralda) y de servidor.

### 🔒 Seguridad y Archivos Ignorados (`.gitignore`)
Para cumplir con las reglas de privacidad de datos personales y optimizar la subida, se creó un archivo `.gitignore` que excluye de GitHub:
1. **`venv/`**: El entorno virtual de Python local (pesado e innecesario en la nube).
2. **`amem_audit.db`**: La base de datos SQLite local. Esto es crucial porque contiene los datos reales, históricos y cifrados de la auditoría. En producción, la base de datos se genera y estructura automáticamente en el servidor la primera vez que se inicia la app a través de la función `init_db()`.
3. **`temp_uploads/`**: Los archivos temporales subidos por los usuarios para auditar.
4. **`__pycache__/`**: Archivos compilados temporales de Python.

### 📦 Gestión de Dependencias (`requirements.txt`)
Streamlit Cloud lee el archivo `requirements.txt` al desplegar la app para instalar automáticamente las librerías necesarias en su servidor:
* `streamlit`: Framework de la app.
* `pandas`: Procesamiento de datos y tablas.
* `cryptography`: Encriptación AES-256 en base de datos.
* `openpyxl`: Lectura de archivos de Excel (`.xlsx`).
* `xlsxwriter`: Generación de informes exportables en Excel con formato condicional.

---

## 2. Despliegue en Streamlit Community Cloud

La aplicación está conectada directamente con tu repositorio de GitHub, lo que permite que cualquier cambio que se empuje a la rama `main` se despliegue automáticamente en vivo.

### ⚙️ Parámetros del Despliegue:
* **Repository**: `Grusensko/Auditoria_AMEM`
* **Branch**: `main`
* **Main file path**: `app.py`
* **Python version**: `3.12` (estable y totalmente compatible con las dependencias).

### 🔑 Configuración de Credenciales de Producción (Secrets)
Para evitar subir claves de encriptación al repositorio público, la clave secreta de cifrado se gestiona de forma segura en los **Advanced Settings** de Streamlit Cloud:

1. En tu panel de Streamlit Cloud, abre la configuración de la app (**Settings** -> **Secrets**).
2. Pega el secreto de producción en formato TOML:
   ```toml
   AMEM_ENCRYPTION_KEY = "PONER_AQUI_TU_CLAVE_FERNET_SECRETA"
   ```
3. Guarda los cambios. La app leerá esta variable usando `os.environ.get("AMEM_ENCRYPTION_KEY")` en caliente sin exponerla en el código de GitHub.

---

## 3. Visualización Premium sin Branding (Marca Blanca)

Para lograr una estética de software comercial (SaaS) y remover las barras superiores e inferiores por defecto de Streamlit Cloud, se combinaron dos metodologías:

### 🔗 Enlace Limpio con `?embed=true`
Cuando accedes a la URL de producción, debes utilizar el parámetro de incrustado:
👉 **[https://auditoriaamem.streamlit.app/?embed=true](https://auditoriaamem.streamlit.app/?embed=true)**

**¿Qué resuelve esto?**
1. **Oculta la cabecera padre de Streamlit Cloud:** Elimina de la vista los botones de **"Fork this app"**, el enlace al repositorio de GitHub y el menú de tres puntos.
2. **Oculta los iconos flotantes de la esquina inferior derecha:** Desactiva la corona roja y el botón del globo de Streamlit Cloud.
3. **Corrige la barra de desplazamiento:** Evita que el navegador dibuje una molesta doble barra de scroll vertical, adaptando la app perfectamente al tamaño exacto de la pantalla.

### 🎨 Inyección de CSS en `app.py`
Para reforzar la seguridad visual y hacer que la interfaz sea consistente incluso si se accede sin el parámetro `embed`, inyectamos CSS personalizado en `app.py` que:
* Remueve la marca de agua del footer (*"Made with Streamlit"*).
* Oculta los elementos de acción de la cabecera (`[data-testid="stHeaderActionElements"]`).
* Desactiva el scroll en la pantalla de Login (`overflow: hidden`) para mantener el centrado de la tarjeta y lo vuelve a habilitar tras iniciar sesión de forma dinámica para las planillas y el dashboard.
