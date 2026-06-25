---
name: accounting-audit
description: Skill de auditoría contable especializada para AMEM (Mendoza, Argentina) con reglas de AFIP, tratamiento de delay contable y conciliación de tres vías.
---

# Skill de Auditoría Contable: AMEM

Esta skill dota al agente de conocimientos específicos sobre las prácticas de auditoría contable en Argentina, aplicados al proyecto de AMEM.

## 📌 Principios de Conciliación Local (AFIP/ARCA)

1. **Formatos de AFIP (Libro de IVA Digital / RG 3685):**
   * **VENTAS.txt:** Registro de cabecera de facturas emitidas de ancho fijo (Anchos de campos: Fecha: 8, Tipo de Comprobante: 3, Punto de Venta: 5, Número Desde: 20, Número Hasta: 20, CUIT Comprador: 20, Razón Social: 30, Monto Total: 15, etc.).
   * **ALICUOTAS.txt:** Detalle de alícuotas por comprobante.
   * Los montos se dividen por 100 para obtener el valor flotante real (ej: `000000066362968` representa `$663629.68`).
2. **Tipos de Comprobantes AFIP Comunes:**
   * `011`: Factura C (Común en servicios exentos de IVA).
   * `012`: Nota de Débito C.
   * `013`: Nota de Crédito C.
   * `015`: Recibo C.

## 🕒 Regla de Conciliación con Delay Temporal
Las prestaciones de salud en Argentina se rigen bajo un ciclo diferido:
* **Mes N (Prestación):** Servicio de salud brindado al paciente de la Obra Social (registrado en Excel de prestaciones).
* **Mes N+1 (Facturación):** Factura emitida a la Obra Social por el total capitado o por prestación (registrada en AFIP/ARCA).
* **Mes N+2 o N+3 (Cobro):** Cobro recibido en el banco por parte de la Obra Social (registrado en extracto del Banco Supervielle).

### Algoritmo de Emparejamiento de Datos (Matching):
* **Fórmula de Tolerancia de Delay:** Buscar transacciones equivalentes (Mismo CUIT / Obra Social y Monto similar) en una ventana de:
  $$\text{Fecha de Factura} = \text{Fecha de Prestación} + [0 \text{ a } 45 \text{ días}]$$
  $$\text{Fecha de Cobro} = \text{Fecha de Factura} + [15 \text{ a } 90 \text{ días}]$$
* **Retenciones Impositivas:** Al ser AMEM una asociación sin fines de lucro, está exenta de retenciones. Por ende, no aplica cálculo de deducciones y el depósito bancario debe coincidir exactamente al centavo con el monto facturado.

## 🔒 Reglas de Seguridad de Datos
* **Claves Fiscales/Secretos:** Guardados únicamente en `secrets` de Streamlit o variables de entorno.
* **Criptografía Simétrica:** Encriptar campos que identifiquen a personas físicas (ej. CUIT, nombres de clientes) en la base de datos usando criptografía AES-256 (`cryptography.fernet`).
