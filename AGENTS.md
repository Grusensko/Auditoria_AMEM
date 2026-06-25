# Reglas del Agente: Auditoría AMEM (Mendoza)

Este archivo define los comportamientos, reglas del negocio y pautas técnicas que debe seguir cualquier IA que colabore en este proyecto.

---

## 💼 Reglas del Negocio y Operatoria

1. **El Ciclo de Facturación y Delay (Crítico):**
   * **Mes N (Prestación):** El servicio se presta y se registra internamente en Excel.
   * **Mes N+1 (Facturación):** Se emite la factura en AFIP/ARCA.
   * **Mes N+2 o N+3 (Cobro):** El dinero se recibe en el Banco Supervielle.
   * *Regla para la IA:* Al buscar conciliaciones, la IA debe buscar depósitos bancarios de un CUIT/Monto hasta 90 días después de la fecha de la prestación.
   * *Retenciones:* AMEM es una asociación sin fines de lucro exenta de retenciones impositivas, por lo que el monto facturado y el cobro bancario correspondiente deben coincidir exactamente al centavo.
2. **Identificación de Clientes:**
   * Los clientes (en su mayoría Obras Sociales como OSEP, OSDE, OSECAC, PAMI, etc.) se identifican únicamente por su **CUIT/CUIL**.
   * Debe existir siempre una correspondencia legible para humanos (Nombre/Razón Social).
   * La IA debe usar el archivo `OS_CUIT_MAP` en `conciliador.py` para mapear los nombres cortos del Excel de prestaciones con los CUITs oficiales de AFIP.

---

## 🔒 Reglas de Seguridad y Cifrado de Datos

1. **Cifrado en Reposo:**
   * Todos los datos personales identificables de clientes (CUIT, Nombre/Razón Social) se deben encriptar antes de guardarse en la base de datos SQLite.
   * Se utiliza criptografía simétrica AES-256 (`cryptography.fernet`).
   * Para búsquedas e índices, se guarda una columna `cuit_hash` que contiene el SHA256 del CUIT. Las búsquedas en la BD se realizan buscando el hash, evitando desencriptar registros innecesariamente.
2. **Secretos y Credenciales:**
   * Las claves criptográficas (como `AMEM_ENCRYPTION_KEY`) se guardan únicamente en variables de entorno o en los secrets de Streamlit. Nunca se suben al código de GitHub.

---

## 🎨 Estándares de UX-UI (App Streamlit)

1. **Estética Premium:**
   * Usar diseño moderno con paleta oscura/gris azulado y acentos vibrantes (Verde esmeralda para éxitos/conciliados, Amarillo/Ámbar para pendientes, Rojo carmesí para discrepancias).
   * Interfaces limpias con tarjetas de KPIs y tablas interactivas.
2. **Acceso de Roles:**
   * **Auditor (`admin`):** Acceso total. Puede cargar datos, ejecutar la conciliación automática, editar manualmente los estados y observaciones de cada ítem, y exportar reportes.
   * **Consulta (`consulta`):** Acceso de solo lectura al panel de conciliación y visor de clientes. Puede descargar los reportes consolidados en Excel.

---

## 📂 Estructura del Repositorio

* `database.py`: Define el esquema SQLite, inicialización y funciones de encriptación/hashing.
* `loader.py`: Parsea e importa archivos crudos (Excel de prestaciones, VENTAS.txt de AFIP y extracto bancario de Supervielle).
* `conciliador.py`: Ejecuta el algoritmo de conciliación de tres vías.
* `excel_exporter.py`: Genera el Excel de reportes con colores suaves y formato condicional para los socios.
* `app.py`: Interfaz web interactiva en Streamlit.
