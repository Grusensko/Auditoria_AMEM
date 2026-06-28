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
   * Para búsquedas e índices, se guarda una columna `cuit_hash` que contiene el SHA256 del CUIT. Las búsquedas en la BD se realizan buscando el hash, evitando desencrittar registros innecesariamente.
2. **Secretos y Credenciales:**
   * Las claves criptográficas (como `AMEM_ENCRYPTION_KEY`) se guardan únicamente en variables de entorno o en los secrets de Streamlit. Nunca se suben al código de GitHub.

---

## 🎨 Estándares de UX-UI (Web HTML5 / CSS Vanilla / JS)

1. **Estética Premium (Tema Claro de Alto Contraste):**
   * **Colores Base:** Fondo principal off-white (`#F8FAFC`), tarjetas y paneles en blanco puro (`#FFFFFF`) y textos de alto contraste (`#0F172A`).
   * **Paleta Contable Pastel:** Verde esmeralda suave para Conciliados (éxitos), Ocre pastel para Pendientes de Cobro, Azul pastel para Pendientes de Factura, y Rojo carmesí pastel para Discrepancias.
   * **Listado Maestro-Detalle:** El listado maestro (28%) a la izquierda y el detalle (72%) a la derecha con scroll independiente.
2. **Interactividad y Control de Cambios:**
   * **Deshabilitado Visual:** Los botones de guardado o descarte se inician deshabilitados (opacidad al 50% y `pointer-events: none`). Se activan solo al detectar cambios.
   * **Línea de Tiempo:** Gráfico horizontal de 120 días con tooltips no desbordados (con clases `.first-event` y `.last-event` para los extremos).
   * **Trazabilidad:** Cada bloque cuenta con el icono `(i)` que despliega un tooltip con el archivo y la fila/línea de procedencia.
3. **Pautas de CSS Moderno y Estilo:**
   * Para cualquier modificación, maquetación o creación de estilos, el agente **DEBE** apegarse estrictamente a las directrices de [CSS_STANDARDS.md](file:///d:/Repositories/AMEM/CSS_STANDARDS.md).
   * Se requiere el uso de **CSS Grid** para estructuras bidimensionales (como maestro-detalle y layout principal), **Container Queries (`@container`)** y `clamp()` para responsividad fluida sin breakpoints globales, **`subgrid`** para la alineación horizontal de tarjetas/KPIs y el espacio de color **OKLCH (`oklch()`)** para control perceptual de luminosidad y estados visuales coherentes.
   * **Restricciones de Maquetación Obligatorias:**
     * **No usar `<br />`:** Queda terminantemente prohibido utilizar etiquetas `<br />` para generar espaciados o posicionar elementos; usar en su lugar márgenes, paddings o propiedades `gap` en CSS.
     * **Preferencia de CSS Grid sobre Flexbox:** Usar preferentemente Grid para estructurar layouts (tanto en 2D como en 1D). Se permite y recomienda usar Flexbox únicamente en alineaciones lineales simples, grupos de botones, o componentes inline pequeños.
     * **Unidad de Medida Preferida (`rem`):** Se utilizará `rem` de forma preferente para tipografía, paddings, márgenes y dimensionamiento de componentes, reservando los píxeles (`px`) exclusivamente para grosores de borde de `1px` o sombras específicas.

---

## 📂 Estructura del Repositorio

* `database.py`: Define el esquema SQLite, inicialización y funciones de encriptación/hashing.
* `loader.py`: Parsea e importa archivos crudos (Excel de prestaciones, VENTAS.txt de AFIP y extracto bancario de Supervielle).
* `conciliador.py`: Ejecuta el algoritmo de conciliación de tres vías.
* `excel_exporter.py`: Genera el Excel de reportes con colores suaves y formato condicional.
* `api.py`: Backend y API endpoints en FastAPI.
* `run.py`: Script lanzador que inicia Uvicorn y abre la interfaz web.
* `static/css/styles.css` y `static/js/app.js`: Estilos y lógica interactiva de la consola web.
* `templates/index.html`: Plantilla principal de la consola de auditoría.

---

## 🧠 Sincronización y Trabajo en Multi-Chat (Importante)

Dado que se trabaja con múltiples chats temáticos divididos por sección:
1. **Rastreo de Cambios Obligatorio:** Antes de modificar el código en cualquier chat, el agente **DEBE** ejecutar `git status` y `git pull` para evitar pisar commits o modificaciones de otros chats.
2. **Archivos de Planificación en el Workspace:**
   * Para trabajar en la pestaña de **Clientes** (Relaciones N-a-M, Cuenta Corriente y Conciliación por lotes), el agente debe consultar primero los archivos de diseño [plan_clientes_equilibrio.md](file:///d:/Repositories/AMEM/plan_clientes_equilibrio.md) e [informe_contexto_auditoria.md](file:///d:/Repositories/AMEM/informe_contexto_auditoria.md) creados en el directorio de la conversación para garantizar la continuidad y consistencia del diseño.
3. **Decisiones de Diseño de Clientes y Estilos (Establecidas):**
   * **Arquitectura Híbrida:** La aplicación en producción corre `app.py` en Streamlit Cloud, mientras que la consola premium HTML/CSS corre localmente en FastAPI (`run.py` / `api.py`). Los estilos premium deben programarse en FastAPI.
   * **Layout de Grid:** `.sidebar-overlay` se oculta en desktop (`display: none`) para evitar que rompa la cuadrícula de `#app-screen`.
   * **Base de Datos de Clientes:** Las conciliaciones N-a-M se implementan mediante las tablas `vinculos_prestacion_factura` e `imputaciones_factura_banco`. El saldo acumulado (Running Balance) se calcula cronológicamente mediante prestaciones (+), facturación (=) y cobros/imputaciones (-), tendiendo a cero en equilibrio contable.
   * **Visualización del CUIT:** Para cumplir con la seguridad y encriptación en reposo, en el listado maestro se utiliza el CUIT real desencriptado, y al abrir el panel de detalle **SE DEBE** mostrar el CUIT real en texto claro (desencriptado), evitando imprimir el hash SHA256 largo (`cuit_hash`) de búsqueda indexada en BD.
   * **Tags y Categorías Compactas:** Los badges de origen del cliente (`AFIP` para clientes con facturas del TXT y `Banco` para clientes identificados en Supervielle) deben alinearse horizontalmente en la misma línea del CUIT de la tarjeta del maestro para mantener la tarjeta compacta.
   * **Filtros e Indicadores Contables del Maestro:** El listado de clientes debe admitir un selector interactivo para discriminar entre clientes en equilibrio contable (`bien`) y clientes con descalces, pendientes o discrepancias (`problemas`). Al pie del listado se debe incluir un contador con el total general y el número de elementos filtrados activos.
