import os
import hashlib
import shutil
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, List

from database import (
    get_db_connection, 
    decrypt_data, 
    hash_cuit,
    hash_password,
    init_db
)
from loader import load_afip_ventas, load_excel_banco, load_excel_prestaciones
from conciliador import run_conciliacion, OS_CUIT_MAP, get_period_sort_value, get_cuit_for_obra_social
from excel_exporter import generate_excel_report

# Inicializar base de datos
init_db()

app = FastAPI(title="AMEM Auditoría API", version="2.0")

# Habilitar CORS para desarrollo local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir archivos estáticos
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Modelos Pydantic
class LoginRequest(BaseModel):
    username: str
    password: str

class ConciliarRequest(BaseModel):
    prestacion_id: int
    factura_id: Optional[str] = None
    movimiento_banco_id: Optional[int] = None
    estado_final: str
    observaciones: str
    mes_auditoria: str

class DesvincularRequest(BaseModel):
    tipo: str # "prestacion" o "banco"
    id: int

def format_period(period_str):
    meses_map = {
        "01": "Enero", "02": "Febrero", "03": "Marzo", "04": "Abril",
        "05": "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto",
        "09": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre"
    }
    try:
        if "-" in period_str:
            año, mes = period_str.split("-")
            return f"{meses_map.get(mes, mes)} {año}"
        return period_str
    except Exception:
        return period_str

# --- ENDPOINTS API ---

@app.post("/api/login")
def login(req: LoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash, salt, rol FROM usuarios WHERE usuario = ?", (req.username,))
    user_res = cursor.fetchone()
    conn.close()
    
    if user_res:
        stored_hash = user_res['password_hash']
        salt = user_res['salt']
        role = user_res['rol']
        
        check_hash, _ = hash_password(req.password, salt)
        if check_hash == stored_hash:
            return {
                "authenticated": True,
                "username": req.username,
                "role": role
            }
    
    raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")


@app.get("/api/periods")
def get_periods():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT mes_auditoria FROM prestaciones
        UNION
        SELECT DISTINCT mes_auditoria FROM facturas
        UNION
        SELECT DISTINCT mes_auditoria FROM movimientos_banco
        ORDER BY mes_auditoria DESC
    """)
    periods = [row['mes_auditoria'] for row in cursor.fetchall() if row['mes_auditoria']]
    conn.close()
    
    if not periods:
        periods = ["2026-05", "2026-04", "2026-03", "2026-02", "2026-01"]
    return periods


@app.get("/api/dashboard")
def get_dashboard(periodo: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Total Banco
    cursor.execute("""
        SELECT SUM(credito), COUNT(*) 
        FROM movimientos_banco 
        WHERE mes_auditoria = ? AND credito > 0
    """, (periodo,))
    res_b = cursor.fetchone()
    total_ingresado = res_b[0] if res_b[0] else 0.0
    cant_ingresos = res_b[1] if res_b[1] else 0
    
    # 2. Conciliados
    cursor.execute("""
        SELECT SUM(credito), COUNT(id)
        FROM movimientos_banco
        WHERE mes_auditoria = ? AND credito > 0
          AND id IN (SELECT DISTINCT movimiento_banco_id FROM conciliaciones WHERE estado_final = 'CONCILIADO')
    """, (periodo,))
    res_c = cursor.fetchone()
    ingresos_conciliados = res_c[0] if res_c[0] else 0.0
    cant_conciliados = res_c[1] if res_c[1] else 0
    
    # 3. Discrepantes
    cursor.execute("""
        SELECT SUM(credito), COUNT(id)
        FROM movimientos_banco
        WHERE mes_auditoria = ? AND credito > 0
          AND id IN (SELECT DISTINCT movimiento_banco_id FROM conciliaciones WHERE estado_final = 'DISCREPANCIA')
    """, (periodo,))
    res_d = cursor.fetchone()
    ingresos_discrepantes = res_d[0] if res_d[0] else 0.0
    cant_discrepantes = res_d[1] if res_d[1] else 0
    
    # 4. Sin Identificar
    cursor.execute("""
        SELECT SUM(credito), COUNT(*)
        FROM movimientos_banco
        WHERE mes_auditoria = ? AND credito > 0
          AND id NOT IN (SELECT DISTINCT movimiento_banco_id FROM conciliaciones WHERE movimiento_banco_id IS NOT NULL)
    """, (periodo,))
    res_s = cursor.fetchone()
    ingresos_sin_identificar = res_s[0] if res_s[0] else 0.0
    cant_sin_identificar = res_s[1] if res_s[1] else 0
    
    # 5. Deuda Pendiente de Facturar
    cursor.execute("""
        SELECT SUM(monto), COUNT(*) 
        FROM prestaciones 
        WHERE mes_auditoria <= ? 
          AND estado_conciliacion = 'PENDIENTE_FACTURA'
    """, (periodo,))
    res_pf = cursor.fetchone()
    deuda_pendiente_facturar = res_pf[0] if res_pf[0] else 0.0
    cant_pendiente_facturar = res_pf[1] if res_pf[1] else 0
    
    # 6. Deuda Pendiente de Cobro
    cursor.execute("""
        SELECT SUM(monto), COUNT(*) 
        FROM prestaciones 
        WHERE mes_auditoria <= ? 
          AND estado_conciliacion = 'PENDIENTE_COBRO'
    """, (periodo,))
    res_pc = cursor.fetchone()
    deuda_pendiente_cobrar = res_pc[0] if res_pc[0] else 0.0
    cant_pendiente_cobrar = res_pc[1] if res_pc[1] else 0
    
    conn.close()
    
    return {
        "periodo_formateado": format_period(periodo),
        "total_ingresado": total_ingresado,
        "cant_ingresos": cant_ingresos,
        "ingresos_conciliados": ingresos_conciliados,
        "cant_conciliados": cant_conciliados,
        "ingresos_sin_identificar": ingresos_sin_identificar,
        "cant_sin_identificar": cant_sin_identificar,
        "ingresos_discrepantes": ingresos_discrepantes,
        "cant_discrepantes": cant_discrepantes,
        "deuda_pendiente_facturar": deuda_pendiente_facturar,
        "cant_pendiente_facturar": cant_pendiente_facturar,
        "deuda_pendiente_cobrar": deuda_pendiente_cobrar,
        "cant_pendiente_cobrar": cant_pendiente_cobrar
    }


@app.get("/api/prestaciones")
def get_prestaciones(periodo: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT 
            p.id AS prest_id,
            p.obra_social_nombre AS os,
            p.paciente AS paciente,
            p.periodo AS periodo,
            p.monto AS monto,
            p.factura_nro AS factura_nro,
            p.fecha_factura AS fecha_factura,
            p.archivo_origen AS archivo_origen,
            p.nro_fila AS nro_fila,
            COALESCE(c.estado_final, 'PENDIENTE_FACTURA') AS estado,
            c.observaciones AS obs,
            c.factura_id AS fact_afip_id,
            c.movimiento_banco_id AS banco_id,
            mb.fecha AS banco_fecha,
            mb.credito AS banco_monto,
            f.fecha_emision AS afip_fecha,
            f.monto_total AS afip_monto,
            f.archivo_origen AS afip_archivo,
            f.nro_fila AS afip_fila,
            mb.archivo_origen AS banco_archivo,
            mb.nro_fila AS banco_fila
        FROM prestaciones p
        LEFT JOIN conciliaciones c ON p.id = c.prestacion_id
        LEFT JOIN movimientos_banco mb ON c.movimiento_banco_id = mb.id
        LEFT JOIN facturas f ON c.factura_id = f.comprobante_id
        WHERE p.mes_auditoria = ?
    """
    cursor.execute(query, (periodo,))
    prestaciones = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return prestaciones


@app.get("/api/banco")
def get_banco(periodo: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener todos los movimientos bancarios para el mes
    cursor.execute("""
        SELECT id AS banco_id, fecha, concepto, detalle, credito, cuit_txt_asociado AS cuit_txt, cuit_hash_asociado AS cuit_hash, archivo_origen, nro_fila
        FROM movimientos_banco
        WHERE mes_auditoria = ? AND credito > 0 AND debito = 0.0
    """, (periodo,))
    movs = [dict(row) for row in cursor.fetchall()]
    
    # Para cada movimiento, buscar todas sus prestaciones asociadas
    for m in movs:
        cursor.execute("""
            SELECT c.prestacion_id, c.factura_id, c.estado_final, c.observaciones AS obs,
                   p.obra_social_nombre AS os, p.paciente, p.monto, p.periodo, p.fecha_factura,
                   p.archivo_origen AS prest_archivo, p.nro_fila AS prest_fila,
                   f.fecha_emision AS afip_fecha, f.monto_total AS afip_monto,
                   f.archivo_origen AS afip_archivo, f.nro_fila AS afip_fila
            FROM conciliaciones c
            LEFT JOIN prestaciones p ON c.prestacion_id = p.id
            LEFT JOIN facturas f ON c.factura_id = f.comprobante_id
            WHERE c.movimiento_banco_id = ?
        """, (m['banco_id'],))
        asocs = [dict(row) for row in cursor.fetchall()]
        
        m['asociaciones'] = asocs
        
        # Determinar estado consolidado
        if not asocs:
            m['estado_display'] = 'SIN IDENTIFICAR'
            m['estado'] = 'PENDIENTE_COBRO'
        else:
            # Si hay alguna discrepancia, ese es el estado general, de lo contrario conciliado
            non_conc = [a for a in asocs if a['estado_final'] != 'CONCILIADO']
            if not non_conc:
                m['estado_display'] = 'CONCILIADO'
                m['estado'] = 'CONCILIADO'
            else:
                m['estado_display'] = non_conc[0]['estado_final']
                m['estado'] = non_conc[0]['estado_final']
                
    conn.close()
    return movs


@app.get("/api/candidatos/facturas")
def get_candidatos_facturas(prest_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener detalles de la prestacion
    cursor.execute("SELECT obra_social_nombre, monto, factura_nro FROM prestaciones WHERE id = ?", (prest_id,))
    prest = cursor.fetchone()
    if not prest:
        conn.close()
        raise HTTPException(status_code=404, detail="Prestación no encontrada")
        
    os_nombre = prest['obra_social_nombre']
    monto_prest = prest['monto']
    
    # Obtener CUIT y hash
    cuit = get_cuit_for_obra_social(os_nombre)
    c_hash = hash_cuit(cuit) if cuit else ""
    
    # Obtener factura vinculada actual si la hay
    cursor.execute("SELECT factura_id FROM conciliaciones WHERE prestacion_id = ?", (prest_id,))
    conc_res = cursor.fetchone()
    fact_actual_id = conc_res['factura_id'] if conc_res else None
    
    cursor.execute("""
        SELECT comprobante_id, monto_total, fecha_emision, cuit_txt, tipo_comprobante, archivo_origen, nro_fila
        FROM facturas
        WHERE (cuit_hash = ? OR cuit_hash IS NULL OR ? = '')
          AND (comprobante_id NOT IN (SELECT factura_id FROM conciliaciones WHERE prestacion_id != ? AND factura_id IS NOT NULL)
               OR comprobante_id = ?)
        ORDER BY ABS(monto_total - ?) ASC, fecha_emision DESC
        LIMIT 50
    """, (c_hash, c_hash, prest_id, fact_actual_id, monto_prest))
    
    facturas_cands = [dict(row) for row in cursor.fetchall()]
    
    # Si no hay facturas específicas de este CUIT, traer de forma general
    if not facturas_cands:
        cursor.execute("""
            SELECT comprobante_id, monto_total, fecha_emision, cuit_txt, tipo_comprobante, archivo_origen, nro_fila
            FROM facturas
            WHERE comprobante_id NOT IN (SELECT factura_id FROM conciliaciones WHERE prestacion_id != ? AND factura_id IS NOT NULL)
               OR comprobante_id = ?
            ORDER BY ABS(monto_total - ?) ASC, fecha_emision DESC
            LIMIT 50
        """, (prest_id, fact_actual_id, monto_prest))
        facturas_cands = [dict(row) for row in cursor.fetchall()]
        
    conn.close()
    return facturas_cands


@app.get("/api/candidatos/banco")
def get_candidatos_banco(
    prest_id: int,
    buscar_texto: Optional[str] = Query(None),
    filtrar_monto: bool = Query(True)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener monto de la prestacion
    cursor.execute("SELECT monto, obra_social_nombre FROM prestaciones WHERE id = ?", (prest_id,))
    prest = cursor.fetchone()
    if not prest:
        conn.close()
        raise HTTPException(status_code=404, detail="Prestación no encontrada")
        
    monto_prest = prest['monto']
    
    # Obtener banco vinculado actual
    cursor.execute("SELECT movimiento_banco_id FROM conciliaciones WHERE prestacion_id = ?", (prest_id,))
    conc_res = cursor.fetchone()
    banco_actual_id = conc_res['movimiento_banco_id'] if conc_res else None
    
    query_banco = """
        SELECT id, fecha, concepto, detalle, credito, archivo_origen, nro_fila
        FROM movimientos_banco
        WHERE credito > 0 AND debito = 0.0
          AND (id NOT IN (SELECT movimiento_banco_id FROM conciliaciones WHERE prestacion_id != ? AND movimiento_banco_id IS NOT NULL)
               OR id = ?)
    """
    params_banco = [prest_id, banco_actual_id]
    
    if buscar_texto:
        query_banco += " AND (concepto LIKE ? OR detalle LIKE ?)"
        params_banco.extend([f"%{buscar_texto}%", f"%{buscar_texto}%"])
        
    if filtrar_monto:
        monto_min = monto_prest * 0.95
        monto_max = monto_prest * 1.05
        query_banco += " AND credito BETWEEN ? AND ?"
        params_banco.extend([monto_min, monto_max])
        
    query_banco += " ORDER BY ABS(credito - ?) ASC, fecha DESC LIMIT 100"
    params_banco.append(monto_prest)
    
    cursor.execute(query_banco, tuple(params_banco))
    banco_cands = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return banco_cands


@app.get("/api/candidatos/prestaciones")
def get_candidatos_prestaciones(
    banco_id: int,
    buscar_texto: Optional[str] = Query(None),
    filtrar_monto: bool = Query(True)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener datos del banco
    cursor.execute("SELECT credito FROM movimientos_banco WHERE id = ?", (banco_id,))
    banco_mov = cursor.fetchone()
    if not banco_mov:
        conn.close()
        raise HTTPException(status_code=404, detail="Movimiento de banco no encontrado")
        
    credito = banco_mov['credito']
    
    # Obtener prestacion vinculada actual
    cursor.execute("SELECT prestacion_id FROM conciliaciones WHERE movimiento_banco_id = ?", (banco_id,))
    conc_res = cursor.fetchone()
    prest_actual_id = conc_res['prestacion_id'] if conc_res else None
    
    query_prest = """
        SELECT p.id, p.obra_social_nombre, p.paciente, p.monto, p.periodo, p.factura_nro, p.archivo_origen, p.nro_fila,
               c.factura_id
        FROM prestaciones p
        LEFT JOIN conciliaciones c ON p.id = c.prestacion_id
        WHERE (p.id NOT IN (SELECT prestacion_id FROM conciliaciones WHERE movimiento_banco_id != ? AND prestacion_id IS NOT NULL)
               OR p.id = ?)
    """
    params_prest = [banco_id, prest_actual_id]
    
    if buscar_texto:
        query_prest += " AND (p.obra_social_nombre LIKE ? OR p.paciente LIKE ?)"
        params_prest.extend([f"%{buscar_texto}%", f"%{buscar_texto}%"])
        
    if filtrar_monto:
        monto_min = credito * 0.95
        monto_max = credito * 1.05
        query_prest += " AND p.monto BETWEEN ? AND ?"
        params_prest.extend([monto_min, monto_max])
        
    query_prest += " ORDER BY ABS(p.monto - ?) ASC, p.periodo DESC LIMIT 100"
    params_prest.append(credito)
    
    cursor.execute(query_prest, tuple(params_prest))
    prest_cands = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return prest_cands


@app.post("/api/conciliar")
def post_conciliar(req: ConciliarRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Buscar si ya existe la conciliación
    cursor.execute("SELECT id FROM conciliaciones WHERE prestacion_id = ?", (req.prestacion_id,))
    conc_res = cursor.fetchone()
    
    if conc_res:
        cursor.execute("""
            UPDATE conciliaciones 
            SET factura_id = ?, movimiento_banco_id = ?, estado_final = ?, observaciones = ? 
            WHERE prestacion_id = ?
        """, (req.factura_id, req.movimiento_banco_id, req.estado_final, req.observaciones, req.prestacion_id))
    else:
        cursor.execute("""
            INSERT INTO conciliaciones (prestacion_id, factura_id, movimiento_banco_id, estado_final, observaciones, mes_auditoria)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (req.prestacion_id, req.factura_id, req.movimiento_banco_id, req.estado_final, req.observaciones, req.mes_auditoria))
        
    # Actualizar tabla de prestaciones
    cursor.execute("UPDATE prestaciones SET estado_conciliacion = ? WHERE id = ?", (req.estado_final, req.prestacion_id))
    
    # Retroalimentación inteligente de CUIT
    if req.movimiento_banco_id:
        cursor.execute("SELECT obra_social_nombre FROM prestaciones WHERE id = ?", (req.prestacion_id,))
        prest_res = cursor.fetchone()
        if prest_res:
            cuit = get_cuit_for_obra_social(prest_res['obra_social_nombre'])
            if cuit:
                c_hash = hash_cuit(cuit)
                cursor.execute("""
                    UPDATE movimientos_banco
                    SET cuit_hash_asociado = ?, cuit_txt_asociado = ?
                    WHERE id = ? AND (cuit_hash_asociado IS NULL OR cuit_hash_asociado = '')
                """, (c_hash, cuit, req.movimiento_banco_id))
                
        # Limpiar el vínculo bancario en otras conciliaciones para asegurar unicidad
        cursor.execute("""
            UPDATE conciliaciones
            SET movimiento_banco_id = NULL, estado_final = 'PENDIENTE_COBRO'
            WHERE movimiento_banco_id = ? AND prestacion_id != ?
        """, (req.movimiento_banco_id, req.prestacion_id))
        
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Conciliación guardada exitosamente"}


@app.post("/api/desvincular")
def post_desvincular(req: DesvincularRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if req.tipo == "prestacion":
        cursor.execute("DELETE FROM conciliaciones WHERE prestacion_id = ?", (req.id,))
        cursor.execute("UPDATE prestaciones SET estado_conciliacion = 'PENDIENTE_FACTURA' WHERE id = ?", (req.id,))
    elif req.tipo == "banco":
        # Desvincular el banco de cualquier conciliación
        cursor.execute("""
            UPDATE conciliaciones
            SET movimiento_banco_id = NULL, estado_final = 'PENDIENTE_COBRO'
            WHERE movimiento_banco_id = ?
        """, (req.id,))
        
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Vínculo deshecho exitosamente"}


@app.post("/api/importar")
def post_importar(
    periodo: str = Form(...),
    file_prest: Optional[UploadFile] = File(None),
    file_afip: Optional[UploadFile] = File(None),
    file_banco: Optional[UploadFile] = File(None)
):
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    
    results = {}
    
    # 1. Cargar Prestaciones
    if file_prest:
        p_path = os.path.join(temp_dir, f"prest_{periodo}_{file_prest.filename}")
        with open(p_path, "wb") as f:
            shutil.copyfileobj(file_prest.file, f)
        count_p = load_excel_prestaciones(p_path, periodo)
        results["prestaciones"] = count_p
        
    # 2. Cargar Facturas AFIP
    if file_afip:
        a_path = os.path.join(temp_dir, f"ventas_{periodo}_{file_afip.filename}")
        with open(a_path, "wb") as f:
            shutil.copyfileobj(file_afip.file, f)
        count_a = load_afip_ventas(a_path, periodo)
        results["afip"] = count_a
        
    # 3. Cargar Banco
    if file_banco:
        b_path = os.path.join(temp_dir, f"banco_{periodo}_{file_banco.filename}")
        with open(b_path, "wb") as f:
            shutil.copyfileobj(file_banco.file, f)
        count_b = load_excel_banco(b_path, periodo)
        results["banco"] = count_b
        
    if results:
        # Ejecutar algoritmo de conciliación en lote para el mes y los 3 anteriores
        year, month = map(int, periodo.split('-'))
        meses_a_conciliar = []
        for i in range(3, -1, -1):
            m = month - i
            y = year
            if m <= 0:
                m += 12
                y -= 1
            meses_a_conciliar.append(f"{y:04d}-{m:02d}")
            
        final_stats = {}
        for m in meses_a_conciliar:
            final_stats = run_conciliacion(m)
            
        return {
            "status": "success",
            "imported": results,
            "conciliados": final_stats.get("conciliados", 0),
            "pendientes_factura": final_stats.get("pendientes_factura", 0),
            "pendientes_cobro": final_stats.get("pendientes_cobro", 0),
            "discrepancias": final_stats.get("discrepancias", 0)
        }
        
    raise HTTPException(status_code=400, detail="Debe subir al menos un archivo para procesar")


@app.get("/api/exportar")
def get_exportar(periodo: str):
    try:
        excel_data = generate_excel_report(periodo)
        temp_file = f"temp_report_{periodo}.xlsx"
        with open(temp_file, "wb") as f:
            f.write(excel_data)
        return FileResponse(
            path=temp_file,
            filename=f"Auditoria_AMEM_{periodo}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar reporte: {str(e)}")


@app.get("/api/clientes")
def get_clientes(query: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT cuit_hash, cuit_encrypted, nombre_razon_social_encrypted, categoria FROM clientes")
    clientes_raw = cursor.fetchall()
    
    clientes_list = []
    for c in clientes_raw:
        cuit = decrypt_data(c['cuit_encrypted'])
        nombre = decrypt_data(c['nombre_razon_social_encrypted'])
        c_hash = c['cuit_hash']
        
        if query and not (query.lower() in cuit or query.lower() in nombre.lower()):
            continue
            
        # 1. Buscar prestaciones asociadas al cliente por nombre
        cursor.execute("""
            SELECT estado_conciliacion, monto
            FROM prestaciones
            WHERE obra_social_nombre LIKE ? OR ? LIKE '%' || obra_social_nombre || '%'
        """, (f"%{nombre[:5]}%", nombre))
        prests = cursor.fetchall()
        
        # 2. Buscar facturas asociadas
        cursor.execute("""
            SELECT monto_total, estado
            FROM facturas
            WHERE cuit_hash = ?
        """, (c_hash,))
        facts = cursor.fetchall()
        
        # 3. Buscar movimientos del banco
        cursor.execute("""
            SELECT credito
            FROM movimientos_banco
            WHERE cuit_hash_asociado = ?
        """, (c_hash,))
        bancos = cursor.fetchall()
        
        # Lógica contable de estado para filtros
        tiene_discrepancias = any(p['estado_conciliacion'] == 'DISCREPANCIA' for p in prests)
        
        total_prestaciones = sum(p['monto'] for p in prests)
        total_facturas = sum(f['monto_total'] for f in facts if f['estado'].upper() == 'ACTIVO')
        total_banco = sum(b['credito'] for b in bancos)
        
        tiene_descalces = False
        # Si la suma de prestaciones o facturas no coincide con lo cobrado en banco
        if len(prests) > 0 or len(facts) > 0 or len(bancos) > 0:
            referencia = total_prestaciones if total_prestaciones > 0 else total_facturas
            if abs(referencia - total_banco) > 0.05:
                tiene_descalces = True
                
        # Si hay depósitos huérfanos sin prestaciones ni facturas
        deposito_huerfano = len(prests) == 0 and len(facts) == 0 and len(bancos) > 0
        
        # Si hay prestaciones sin conciliar (pendientes)
        tiene_pendientes = any(p['estado_conciliacion'] != 'CONCILIADO' for p in prests)
        
        estado_filtro = "bien"
        # Si tiene discrepancias, descuadres financieros o depósitos sin registrar es "problemas"
        if tiene_discrepancias or tiene_descalces or deposito_huerfano or tiene_pendientes:
            estado_filtro = "problemas"
            
        clientes_list.append({
            "cuit_hash": c_hash,
            "cuit": cuit,
            "nombre": nombre,
            "categoria": c['categoria'],
            "estado_filtro": estado_filtro,
            "total_prestado": total_prestaciones,
            "total_facturado": total_facturas,
            "total_cobrado": total_banco
        })
        
    conn.close()
    return clientes_list


@app.get("/api/cliente/ficha")
def get_cliente_ficha(cuit_hash: str, nombre: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Prestaciones
    cursor.execute("""
        SELECT id, paciente, fecha_factura, periodo, monto, factura_nro, estado_conciliacion, mes_auditoria, archivo_origen, nro_fila
        FROM prestaciones
        WHERE obra_social_nombre LIKE ? OR ? LIKE '%' || obra_social_nombre || '%'
        ORDER BY fecha_factura ASC
    """, (f"%{nombre[:5]}%", nombre))
    prest_asoc = [dict(row) for row in cursor.fetchall()]
    
    # 2. Facturas AFIP
    cursor.execute("""
        SELECT comprobante_id, fecha_emision, monto_total, tipo_comprobante, estado, mes_auditoria, archivo_origen, nro_fila
        FROM facturas
        WHERE cuit_hash = ?
        ORDER BY fecha_emision ASC
    """, (cuit_hash,))
    fact_asoc = [dict(row) for row in cursor.fetchall()]
    
    # 3. Depósitos Banco
    cursor.execute("""
        SELECT id, fecha, concepto, detalle, credito, mes_auditoria, archivo_origen, nro_fila
        FROM movimientos_banco
        WHERE cuit_hash_asociado = ?
        ORDER BY fecha ASC
    """, (cuit_hash,))
    banco_asoc = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        "prestaciones": prest_asoc,
        "facturas": fact_asoc,
        "banco": banco_asoc
    }


# Serve index.html SPA
@app.get("/")
def read_root():
    index_path = "templates/index.html"
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>AMEM Backend Activo</h1><p>El frontend se está construyendo...</p>")

# Mount static folder
app.mount("/static", StaticFiles(directory="static"), name="static")
