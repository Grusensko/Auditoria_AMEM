# Contexto Unificado del Proyecto: Auditoría AMEM

Este documento sirve como "Contexto Global" para alimentar a cualquier IA (especialmente **Antigravity** o Claude) que colabore en el desarrollo, mantenimiento o análisis de datos de este proyecto de auditoría.

---

## 🌟 Resumen del Proyecto

*   **Cliente:** AMEM (Mendoza, Argentina).
*   **Objetivo:** Auditar y conciliar las cuentas contables de la empresa.
*   **Período de Auditoría:** Inicia en Enero de 2026 (fase piloto con datos de **Mayo de 2026**).
*   **Equipo de Trabajo:**
    *   **Francisco Sentinelli (Paco) & Gustavo Conti:** Socios de negocio, contacto con el cliente. Su flujo de trabajo se basa en **planillas Excel**.
    *   **Auditor Técnico (Tú):** Desarrollador del sistema, prefieres gestionar y analizar los datos a través de una **App Personalizada**.
    *   **IA (Antigravity):** Asistente de programación y análisis de datos contables.

---

## 📊 Dinámica del Negocio y Datos

### 1. Delay de la Operatoria (Crucial)
El negocio presenta un descalce financiero habitual en el cobro de prestaciones:
*   **Mes $N$ (Prestación):** Se realiza el servicio/prestación médica/social (registrado en los Excel de gestión interna).
*   **Mes $N+1$ (Facturación):** Se emite la factura (extraída de ARCA/AFIP).
*   **Mes $N+2$ (Cobro):** Se recibe el dinero en la cuenta de la empresa (extraído de movimientos bancarios).

### 2. Fuentes de Datos
El motor de auditoría consolida tres fuentes:
1.  **Informes de Gestión (Excel):** Archivos mensuales elaborados internamente donde se registran las prestaciones y datos de los clientes.
2.  **Facturación (ARCA/AFIP):** Registros oficiales de facturas emitidas por AMEM.
3.  **Movimientos Bancarios:** Extractos de cuenta que muestran los ingresos reales de dinero.

### 3. Modelo de Entidades y Estados
*   **Identificador Clave:** Los clientes se identifican unívocamente mediante su **CUIT/CUIL** (número) y tienen asociado un **Nombre/Razón Social** para legibilidad humana.
*   **Estados de Conciliación:**
    *   `PRESTADO_PENDIENTE_FACTURA`: Prestación realizada sin factura.
    *   `FACTURADO_PENDIENTE_COBRO`: Factura emitida sin depósito bancario.
    *   `CONCILIADO`: Coincidencia exitosa de Prestación + Factura + Depósito.
    *   `DISCREPANCIA`: Desajustes en montos o inconsistencias (ej: cobro sin factura o factura sin prestación).

---

## 💡 Prompt Optimizado para IAs (Copiar y Pegar)

Si necesitas iniciar una nueva conversación con cualquier IA para trabajar en este proyecto, copia y pega el siguiente bloque:

```text
Actúa como un Auditor de Datos y Desarrollador Full-Stack experto en la normativa fiscal y contable de Argentina (AFIP/ARCA). 
Estamos construyendo un sistema de auditoría contable personalizado para la empresa AMEM de Mendoza. El objetivo principal es realizar una conciliación de tres vías (Three-Way Matching) entre:
1) Prestaciones registradas internamente en planillas de Excel (organizadas mensualmente).
2) Facturas emitidas extraídas de la plataforma ARCA (AFIP).
3) Movimientos bancarios (ingresos en cuenta corriente).

Ten en cuenta que existe un delay temporal típico: la prestación ocurre en el Mes N, se factura en el Mes N+1 y se cobra en el Mes N+2. 

Requisitos de la solución:
- Base de datos en SQLite que asocie CUIT/CUIL de clientes con nombres legibles.
- Estados de seguimiento para cada ítem (Prestado pendiente factura, Facturado pendiente cobro, Conciliado, Discrepancia).
- Una aplicación web personalizada para visualizar discrepancias, realizar búsquedas de clientes y conciliar datos.
- Capacidad de exportar los resultados conciliados a planillas de Excel formateadas para mis socios que prefieren usar Excel.

Ayúdame a [insertar tarea específica, ej: diseñar el script de carga de datos / construir la interfaz / escribir el algoritmo de emparejamiento con delay] respetando esta arquitectura.
```
