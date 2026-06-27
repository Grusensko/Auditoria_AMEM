# Informe de Contexto Contable y Guía de Arquitectura (Consola AMEM)

Este documento sirve como registro oficial de las decisiones arquitectónicas, de interfaz (UI/UX) y de lógica implementadas en la sección de **Conciliación**, sirviendo como base de consistencia para el resto de la aplicación y detallando la estrategia para el desarrollo de la sección de **Clientes**.

---

## ⚖️ 1. Lo Hecho en la Sección Conciliación

La sección de Conciliación se rediseñó bajo el patrón de diseño **Maestro-Detalle (Master-Detail)**, priorizando la legibilidad y la precisión de auditoría.

### A. Estructura y Distribución del Layout
* **Listado Maestro (28% de ancho):** Ubicado a la izquierda. Cuenta con barra de búsqueda rápida y selectores de estados (Conciliado 🟢, Pendiente Factura 🔵, Pendiente Cobro 🟡, Discrepancia 🔴) con scroll independiente.
* **Panel de Detalle (72% de ancho):** Ubicado a la derecha. Carga la información cruzada en tres bloques: Datos de la Prestación (Vía 1), Factura AFIP Vinculada (Vía 2) y Depósito Bancario Asociado (Vía 3).

### B. Línea de Tiempo del Ciclo Contable (delay de 90-120 días)
* Se diseñó un eje horizontal de progreso que ubica los tres hitos (Prestación, Facturación y Cobro) de forma proporcional a los días transcurridos desde el inicio del ciclo (Día 0).
* Cada hito incluye un **tooltip flotante interactivo (hover)** con el desglose de días transcurridos y el delay acumulado.
* **Solución de maquetación (Popups Cortados):** Se programó una lógica dinámica en JavaScript que detecta la cercanía a los extremos (`left < 15%` o `left > 85%`) y añade clases `.first-event` y `.last-event`, ajustando la traslación del tooltip para evitar que se desborde o se corte en los bordes de la tarjeta.

### C. Trazabilidad de Datos (Auditoría de Origen)
* Se alteraron las tablas de SQLite para agregar las columnas `archivo_origen` (TEXT) y `nro_fila` (INTEGER) en prestaciones, facturas y movimientos de banco.
* Los parsers (`loader.py`) registran el nombre del archivo y número de fila física original durante la carga.
* Cada bloque de detalle cuenta con un icono de información `(i)` que despliega un tooltip con la procedencia exacta del dato para auditoría cruzada al instante.

### D. Gestión del Estado de Cambios y UX de Botones
* **Control de Cambios:** Se implementó la función `setHasUnsavedChanges(value)` para centralizar la bandera de modificaciones pendientes.
* **Estilo Inactivo (:disabled):** Se añadió en CSS una regla que opaca al 50% los botones deshabilitados, anula hover/sombra y desactiva eventos del mouse (`pointer-events: none`). Los botones de *"Guardar"* y *"Descartar Cambios"* se inician apagados y solo se activan al realizar modificaciones.
* **Restablecer / Descartar:** El botón *"Descartar Cambios"* recarga los datos desde la base de datos local de forma asíncrona, revirtiendo el formulario y deshabilitando los botones de nuevo.
* **Advertencia de Navegación:** Si existen cambios pendientes, al intentar cambiar de período, de pestaña o de elemento maestro, se despliega un modal interactivo para Guardar, Descartar o Cancelar la acción.

---

## 📐 2. Pautas de Diseño y Consistencia para Otras Secciones

Para mantener la coherencia del software a lo largo del desarrollo del resto de los módulos (Dashboard, Clientes, Reportes), se deben respetar los siguientes estándares:

1. **Tema Claro de Alto Contraste:** 
   * Fondos de pantalla en off-white (`#F8FAFC`), tarjetas y paneles en blanco puro (`#FFFFFF`) y sombras muy tenues (`box-shadow: 0 4px 6px rgba(0,0,0,0.05)`).
   * Texto principal en gris carbón de alto contraste (`#0F172A`).
2. **Código de Colores de Estado Contable:**
   * **Verde esmeralda (`#047857` / fondo `#D1E7DD`):** Éxito, conciliado, equilibrio.
   * **Azul cobalto (`#1D4ED8` / fondo `#DBEAFE`):** Prestación facturada, trámite normal.
   * **Amarillo ocre (`#B45309` / fondo `#FEF3C7`):** Pendiente, cobro sin identificar.
   * **Rojo carmesí (`#B91C1C` / fondo `#FDE8E8`):** Discrepancias, descalces financieros, anulaciones.
3. **Bloqueo Nativo y de Clientes:**
   * Cualquier formulario de edición o panel interactivo debe heredar el comportamiento de `setHasUnsavedChanges`, mostrando los botones de acción inactivos y con cursor deshabilitado hasta que se efectúe una modificación.
4. **Trazabilidad `(i)` Obligatoria:**
   * En cualquier visor o ficha técnica donde se expongan registros contables individuales, se debe inyectar el icono `(i)` de procedencia en la esquina de la tarjeta.

---

## 🏦 3. Estrategia para la Sección de Clientes (Equilibrio de Cuenta Corriente)

La pestaña de **Clientes** se diseñará bajo la idea de un **Libro Mayor / Cuenta Corriente histórico** en lugar de listas estáticas aisladas.

### A. La Lógica Contable de Equilibrio
El ciclo de auditoría debe ser trazable partiendo del cliente. Para esto, se sumarán débitos y créditos cronológicamente:
$$\text{Saldo Acumulado} = \sum \text{Prestaciones} - \sum \text{Cobros}$$
Cuando todo el ciclo de prestaciones de una Obra Social esté facturado y cobrado al centavo, el **Saldo Acumulado** histórico del cliente debe retornar a **$0.00**. Cualquier monto residual en el balance indicará directamente la deuda pendiente de facturar o la deuda pendiente de cobrar (delay contable).

### B. Arquitectura de Base de Datos para Relaciones N-a-M
Para romper la limitación 1-a-1 actual (donde un cobro solo se asocia a una factura), se propone implementar dos tablas de relación en SQLite:
1. `vinculos_prestacion_factura`: Relaciona prestaciones con facturas de AFIP (Relación 1-a-1 o 1-a-N).
2. `imputaciones_factura_banco`: Relaciona facturas con cobros bancarios mediante un campo `monto_imputado`, permitiendo imputar partes de un cobro único a múltiples facturas, o consolidar varios cobros chicos para saldar una factura grande.

### C. Visualización de la Cuenta Corriente
Al hacer clic en una Obra Social, la interfaz renderizará:
1. **Ficha de Saldos:** Facturado histórico, Cobrado histórico y Saldo Pendiente.
2. **Historial Cronológico Compuesto:** Una grilla unificada que mezcla prestaciones, facturas e ingresos del banco ordenados por fecha, visualizando el impacto de cada hito en el Saldo Acumulado.
3. **Consola de Conciliación por Lote:** Casilleros de selección múltiple (checkboxes). El auditor podrá marcar, por ejemplo, 3 facturas pendientes de $500.000 c/u y 1 depósito de $1.500.000. El sistema calculará el equilibrio:
   $$\sum \text{Facturas Seleccionadas} = \sum \text{Depósitos Seleccionados}$$
   Si coincide, se habilita el botón de "Conciliar Lote", registrando las imputaciones correspondientes de forma automática y simplificando la tarea del auditor.
