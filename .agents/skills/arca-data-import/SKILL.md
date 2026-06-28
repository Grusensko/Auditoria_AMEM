---
name: arca-data-import
description: Skill especializada en parsear TXT de posiciones fijas de ARCA (Ventas y Alícuotas) y combinar con XLSX para armar bases de datos en Python.
---

# Instrucciones de Importación y Análisis ARCA

## 1. Parseo de Archivos TXT (Posiciones Fijas)
- Al procesar el archivo de **Ventas.txt**, recordá que no viene separado por comas ni pestañas. Utilizá substrings indexados o `pandas.read_fwf()`.
- Validaciones clave de campos ARCA:
  - Fecha: posiciones 0 a 8 (YYYYMMDD).
  - Tipo de Comprobante: posiciones 8 a 11.
  - CUIT Comprador: posiciones 13 a 24.
- Al procesar **Alicuotas.txt**, vinculá cada registro mediante los campos compuestos obligatorios: Tipo de Comprobante + Punto de Venta + Número de Comprobante + CUIT del Emisor.

## 2. Consolidación con XLSX
- Leé los archivos `.xlsx` usando `pandas.read_excel()` con el motor `openpyxl`.
- Realizá un proceso de ETL para limpiar nombres de columnas duplicados, valores nulos y asegurar que los tipos de datos coincidan (ej. pasar CUITs y números de comprobante estrictamente a texto/string para evitar pérdidas de ceros a la izquierda).
- Generá un merge de tipo `left` o `inner` según corresponda para estructurar el esquema relacional final de la base de datos.

## 3. Arquitectura del Proyecto (Backend Antigravity)
- La lógica de negocio debe residir en scripts de Python independientes (ej. `controllers/importador.py`).
- El frontend (HTML/CSS/JS) consumirá estos datos mediante endpoints limpios de la API REST que expone tu backend.
