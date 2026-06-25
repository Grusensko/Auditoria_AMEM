---
name: ux-ui-standards
description: Directrices de diseño estético, experiencia de usuario y layouts premium para las aplicaciones del proyecto AMEM en Streamlit y web.
---

# Skill de Estándares de UX-UI: AMEM

Esta skill contiene directrices de diseño y comportamiento visual para construir aplicaciones con interfaces profesionales que "asombren" al usuario a primera vista.

## 🎨 Paleta de Colores Contables Premium

Utilizaremos un tema oscuro y claro armónico con las siguientes pautas visuales:
* **Fondo Principal (Oscuro):** `#0E1117` (Gris oscuro azulado).
* **Fondo Secundario (Tarjetas):** `#1F2937` (Gris oscuro suave).
* **Color de Éxito (Conciliado):** `#10B981` (Verde esmeralda vibrante).
* **Color de Advertencia (Pendiente):** `#F59E0B` (Ámbar cálido).
* **Color de Peligro (Discrepancia):** `#EF4444` (Rojo carmesí).
* **Acentos:** `#3B82F6` (Azul corporativo moderno).

## 🖥️ Layout e Interacción en Streamlit

1. **Estructura Limpia:**
   * Usar un sidebar oscuro para navegación de secciones (Dashboard, Clientes, Carga de Archivos, Conciliaciones).
   * Organizar los KPIs clave de la auditoría en la parte superior con tarjetas (`st.metric` o HTML personalizado con Glassmorphism).
2. **Tablas de Datos Interactivas:**
   * Utilizar `st.dataframe` con búsqueda y ordenamiento habilitados.
   * Colorear condicionalmente las filas según su estado contable (`CONCILIADO`, `PENDIENTE_COBRO`, etc.) utilizando estilos CSS personalizados inyectados o formateo de Pandas (`df.style.apply`).
3. **Cargas de Archivos (Drag & Drop):**
   * Mostrar un indicador de carga (`st.spinner`) durante el procesamiento.
   * Presentar un reporte de éxito detallando cuántas filas se cargaron de forma correcta de cada fuente (Prestaciones, AFIP, Banco).
4. **Buscador de Clientes Inteligente:**
   * Entrada de texto interactiva que busque simultáneamente por CUIT o Razón Social y autocomplete el resultado.
   * Mostrar el historial del cliente en una línea de tiempo visual (Timeline).
