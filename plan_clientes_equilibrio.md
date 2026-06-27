# Plan de Diseño: Conciliación N-a-M y Cuenta Corriente (Ficha de Clientes)

Este documento detalla la propuesta técnica y visual para implementar la relación **N-a-M** (un cobro abarca varias facturas y/o una factura es saldada por varios depósitos) y visualizar el equilibrio contable histórico desde la perspectiva del **Cliente / Obra Social**.

---

## ⚖️ El Concepto de Equilibrio Contable (Cuenta Corriente)

Para auditar correctamente el flujo contable de una Obra Social (OSEP, OSDE, PAMI, etc.), no siempre es posible realizar una correspondencia 1-a-1 debido a la operatoria de las mutuales:
* **Caso 1 (Cobro consolidado):** Supervielle recibe un depósito único de $3.000.000 de OSEP que cancela 15 facturas distintas emitidas en meses anteriores.
* **Caso 2 (Factura en cuotas):** Una factura de $1.000.000 es pagada por la Obra Social en dos depósitos de $500.000 en distintas fechas.

Para resolver esto de forma intuitiva, la pestaña **Clientes** se convertirá en un **Libro Diario / Cuenta Corriente** del cliente seleccionado, ordenando todos sus hitos cronológicamente y llevando un **Saldo Acumulado (Running Balance)**. 

### El Saldo Acumulado debe comportarse así:
1. **Prestación (+):** Se genera la deuda potencial. El saldo del cliente sube (AMEM tiene saldo a favor).
2. **Facturación (=):** Hito formal en AFIP. No altera el saldo financiero real pero consolida la deuda.
3. **Cobro (-):** Acreditación en banco Supervielle. El saldo del cliente baja (se cancela la deuda).
4. **Equilibrio (➔ 0):** Una vez que todas las prestaciones se facturan y cobran, el saldo acumulado histórico debe volver exactamente a **$0.00**.

---

## 🛠️ Modificación de Base de Datos (Soporte N-a-M)

Actualmente, la tabla `conciliaciones` une de forma rígida `(prestacion_id, factura_id, movimiento_banco_id)`. Para soportar relaciones múltiples y parciales, se propone el siguiente esquema:

```sql
-- Tabla de Conciliación de Prestaciones y Facturas (Relación 1-a-1 o 1-a-N)
-- Una prestación de gestión se asocia a una factura formal de AFIP.
CREATE TABLE IF NOT EXISTS vinculos_prestacion_factura (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prestacion_id INTEGER UNIQUE, -- Una prestación se factura una sola vez
    factura_id TEXT,             -- Una factura puede agrupar N prestaciones
    fecha_vinculo TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prestacion_id) REFERENCES prestaciones(id),
    FOREIGN KEY (factura_id) REFERENCES facturas(comprobante_id)
);

-- Tabla de Imputaciones de Pagos (Relación N-a-M con montos parciales)
-- Asocia facturas AFIP con cobros bancarios, permitiendo imputar partes de un cobro a una factura.
CREATE TABLE IF NOT EXISTS imputaciones_factura_banco (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    factura_id TEXT NOT NULL,
    movimiento_banco_id INTEGER NOT NULL,
    monto_imputado REAL NOT NULL, -- Monto que este cobro aporta a esta factura
    fecha_imputacion TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (factura_id) REFERENCES facturas(comprobante_id),
    FOREIGN KEY (movimiento_banco_id) REFERENCES movimientos_banco(id)
);
```

### Flujo de Estados Automáticos:
* **Factura:** Se considera `LIQUIDADA` (Conciliada) si la suma de sus `monto_imputado` en `imputaciones_factura_banco` es igual a su `monto_total`.
* **Movimiento Banco:** Se considera `APLICADO COMPLETO` si la suma de sus `monto_imputado` es igual a su `credito`. Si es menor, queda un saldo remanente disponible para imputar a otras facturas.

---

## 🎨 Propuesta de Interfaz (Sección Clientes)

En la pestaña **Clientes**, al seleccionar una Obra Social, en lugar de mostrar tres listas estáticas aisladas, se renderizará un **Panel Unificado de Cuenta Corriente**:

### 1. Panel de Resumen de Saldos (KPIs)
```
+----------------------------+  +----------------------------+  +----------------------------+
|     Facturado Total        |  |     Cobrado Histórico      |  |      Saldo Pendiente       |
|      $ 12.450.200,00       |  |      $ 11.200.000,00       |  |       $ 1.250.200,00       |
+----------------------------+  +----------------------------+  +----------------------------+
```

### 2. Vista de Línea de Tiempo / Mayor Contable (Cronológico)
Una tabla unificada que muestra el flujo del dinero:

| Fecha | Hito / Concepto | Débito (Prestación) | Crédito (Cobro) | Saldo Acumulado | Estado / Vínculo |
| :--- | :--- | :---: | :---: | :---: | :---: |
| 10/10/2025 | **Prestación:** Paciente GOMEZ | $ 450.000,00 | — | $ 450.000,00 | 🔵 Facturado |
| 05/11/2025 | **Factura:** 00005-011-00001290 | — | — | $ 450.000,00 | vinculada a GOMEZ |
| 15/11/2025 | **Prestación:** Paciente PALACIOS | $ 800.000,00 | — | $ 1.250.200,00| 🔴 Pendiente de Factura |
| 12/12/2025 | **Cobro:** Depósito Supervielle | — | $ 450.000,00 | **$ 800.200,00** | 🟢 Conciliado (Fact. 1290) |

> **Nota Visual:** Las líneas que están conciliadas entre sí tendrán un indicador de conexión o se destacarán al pasar el cursor sobre ellas, permitiendo ver de qué cobros se nutrió una factura.

### 3. Consola de Conciliación por Lotes (Batch Reconciliation)
En la parte inferior de la ficha de cliente, un botón interactivo habilitará la **Conciliación Inteligente Multi-Item**:
1. El auditor marca con checkboxes **3 facturas pendientes** (ej: sumando $1.500.000).
2. Marca **1 depósito bancario** sin identificar (ej: de $1.500.000).
3. La aplicación muestra una alerta: `✔️ Importes en Equilibrio ($1.500.000 vs $1.500.000)`.
4. El auditor hace clic en **"Confirmar Conciliación por Lote"** y la base de datos registra las imputaciones correspondientes, dejando ambos elementos en estado `CONCILIADO` y el saldo en equilibrio.
