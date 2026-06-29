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

OFFICIAL_NAMES_MAP = {
    "30623978164": "OSEP (Obra Social de los Empleados Públicos de Mendoza)",
    "30546741253": "OSDE (Organización de Servicios Directos Empresarios)",
    "30683032227": "Unión Personal (Obra Social de la Unión del Personal Civil de la Nación)",
    "30713045000": "Prevención Salud (Sancor Seguros)",
    "30679232106": "OSECAC (Obra Social de los Empleados de Comercio y Actividades Afines)",
    "30661876715": "OSPE (Obra Social de Petroleros)",
    "30657325372": "OSPELSYM (Obra Social del Personal de Estaciones de Servicio)",
    "30522763922": "PAMI (Instituto Nacional de Servicios Sociales para Jubilados y Pensionados)",
    "30714906948": "IOSFA (Instituto de Obra Social de las Fuerzas Armadas)",
    "30533836808": "CIMESA (Círculo Médico de Mendoza)",
    "30680620713": "AYE (Obra Social del Personal Jerárquico del Agua y la Energía)",
    "30546101890": "Mutual del Personal de Agua y Energía Eléctrica",
    "30516748385": "TV Salud (Obra Social del Personal de Televisión)",
    "30547339416": "OSPRERA (Obra Social del Personal Rural y Estibadores)",
    "33531576859": "OSPAV (Obra Social del Personal de la Actividad Vitivinícola)",
    "30715815709": "Incluir Salud (Programa Federal Incluir Salud)",
    "30300000000": "Sancor Salud",
    "30678138300": "Swiss Medical",
    "30536481747": "Galeno",
    "30685871239": "OMINT",
    "18084418": "Palero",
    "22392224": "Jalif"
}

def get_official_name(cuit: str, default_name: str) -> str:
    if not cuit:
        return default_name
    clean = str(cuit).strip().replace("-", "")
    return OFFICIAL_NAMES_MAP.get(clean, default_name)

app = FastAPI(title="AMEM Auditoría API", version="2.0")

# Habilitar CORS para desarrollo local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

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
    periods = [row['mes_auditoria'] for row in cursor.fetchall() if row['mes_auditoria'] and row['mes_auditoria'] >= '2026-01']
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


@app.get("/api/dashboard/sin_identificar")
def get_dashboard_sin_identificar(periodo: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, fecha, concepto, detalle, credito AS monto, archivo_origen, nro_fila
        FROM movimientos_banco
        WHERE mes_auditoria = ? AND credito > 0
          AND id NOT IN (SELECT DISTINCT movimiento_banco_id FROM conciliaciones WHERE movimiento_banco_id IS NOT NULL)
        ORDER BY fecha DESC, id DESC
    """, (periodo,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


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
        nombre_original = decrypt_data(c['nombre_razon_social_encrypted'])
        nombre = get_official_name(cuit, nombre_original)
        c_hash = c['cuit_hash']
        
        if query and not (query.lower() in cuit or query.lower() in nombre.lower()):
            continue
            
        # Obtener todos los identificadores unificados asociados a este cliente principal
        cursor.execute("SELECT cuit_hash FROM cliente_identificadores WHERE cliente_cuit_principal_hash = ?", (c_hash,))
        hashes_asoc = [r['cuit_hash'] for r in cursor.fetchall()]
        if not hashes_asoc:
            hashes_asoc = [c_hash]
            
        # 1. Buscar prestaciones asociadas al cliente por nombre
        cursor.execute("""
            SELECT estado_conciliacion, monto
            FROM prestaciones
            WHERE obra_social_nombre LIKE ? OR ? LIKE '%' || obra_social_nombre || '%'
        """, (f"%{nombre[:5]}%", nombre))
        prests = cursor.fetchall()
        
        # 2. Buscar facturas asociadas a cualquiera de los CUITs unificados
        placeholders = ','.join('?' for _ in hashes_asoc)
        cursor.execute(f"""
            SELECT monto_total, estado
            FROM facturas
            WHERE cuit_hash IN ({placeholders})
        """, hashes_asoc)
        facts = cursor.fetchall()
        
        # 3. Buscar movimientos del banco asociados a cualquiera de los CUITs unificados
        cursor.execute(f"""
            SELECT credito
            FROM movimientos_banco
            WHERE cuit_hash_asociado IN ({placeholders})
        """, hashes_asoc)
        bancos = cursor.fetchall()
        
        # Lógica contable de estado para filtros
        tiene_discrepancias = any(p['estado_conciliacion'] == 'DISCREPANCIA' for p in prests)
        
        total_prestaciones = sum(p['monto'] for p in prests)
        total_facturas = sum(f['monto_total'] for f in facts if f['estado'].upper() == 'ACTIVO')
        total_banco = sum(b['credito'] for b in bancos)
        
        tiene_descalces = False
        if len(prests) > 0 or len(facts) > 0 or len(bancos) > 0:
            referencia = total_prestaciones if total_prestaciones > 0 else total_facturas
            if abs(referencia - total_banco) > 0.05:
                tiene_descalces = True
                
        deposito_huerfano = len(prests) == 0 and len(facts) == 0 and len(bancos) > 0
        tiene_pendientes = any(p['estado_conciliacion'] != 'CONCILIADO' for p in prests)
        
        estado_filtro = "bien"
        if tiene_discrepancias or tiene_descalces or deposito_huerfano or tiene_pendientes:
            estado_filtro = "problemas"
            
        # Lógica tipo_cliente
        tipo_cliente = "OS"
        if not cuit or cuit.strip() == "":
            tipo_cliente = "PARTICULAR"
        else:
            c_clean = cuit.replace("-", "").strip()
            if c_clean.startswith("20") or c_clean.startswith("23") or c_clean.startswith("24") or c_clean.startswith("27"):
                tipo_cliente = "PARTICULAR"
            elif len(c_clean) < 11:
                tipo_cliente = "PARTICULAR"
            elif c['categoria'] == "Obra Social" or c['categoria'] == "Banco":
                tipo_cliente = "OS"
            
        clientes_list.append({
            "cuit_hash": c_hash,
            "cuit": cuit,
            "nombre": nombre,
            "categoria": c['categoria'],
            "tipo_cliente": tipo_cliente,
            "estado_filtro": estado_filtro,
            "total_prestado": total_prestaciones,
            "total_facturado": total_facturas,
            "total_cobrado": total_banco
        })
        
    conn.close()
    return clientes_list


@app.get("/api/cliente/ficha")
def get_cliente_ficha(cuit_hash: str, nombre: str):
    import hashlib
    hash_sim = hashlib.sha256(b"27223922244").hexdigest()
    if cuit_hash == hash_sim:
        return {
            "prestaciones": [],
            "facturas": [
                {
                    "comprobante_id": "00005-011-00000000000000009999",
                    "fecha_emision": "2026-05-04",
                    "monto_total": 450000.00,
                    "tipo_comprobante": "011",
                    "estado": "ACTIVO",
                    "mes_auditoria": "2026-05",
                    "archivo_origen": "VENTAS.txt (Simulado)",
                    "nro_fila": 99,
                    "cuit_txt": "27223922244",
                    "cuit_hash": cuit_hash,
                    "diferencia_cuit": False,
                    "cuit_factura": "27223922244"
                }
            ],
            "banco": []
        }

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener todos los identificadores unificados asociados a este cliente
    cursor.execute("SELECT cuit_hash FROM cliente_identificadores WHERE cliente_cuit_principal_hash = ?", (cuit_hash,))
    hashes_asoc = [r['cuit_hash'] for r in cursor.fetchall()]
    if not hashes_asoc:
        hashes_asoc = [cuit_hash]
        
    # 1. Prestaciones
    if len(nombre.strip()) <= 3:
        cursor.execute("""
            SELECT id, paciente, fecha_factura, periodo, monto, factura_nro, estado_conciliacion, mes_auditoria, archivo_origen, nro_fila
            FROM prestaciones
            WHERE obra_social_nombre = ?
            ORDER BY fecha_factura ASC
        """, (nombre.strip(),))
    else:
        cursor.execute("""
            SELECT id, paciente, fecha_factura, periodo, monto, factura_nro, estado_conciliacion, mes_auditoria, archivo_origen, nro_fila
            FROM prestaciones
            WHERE obra_social_nombre LIKE ? OR ? LIKE '%' || obra_social_nombre || '%'
            ORDER BY fecha_factura ASC
        """, (f"%{nombre.strip()[:5]}%", nombre.strip()))
    prest_asoc = [dict(row) for row in cursor.fetchall()]
    
    # 2. Facturas AFIP asociadas a cualquiera de los identificadores
    placeholders = ','.join('?' for _ in hashes_asoc)
    cursor.execute(f"""
        SELECT comprobante_id, fecha_emision, monto_total, tipo_comprobante, estado, mes_auditoria, archivo_origen, nro_fila, cuit_txt, cuit_hash
        FROM facturas
        WHERE cuit_hash IN ({placeholders})
        ORDER BY fecha_emision ASC
    """, hashes_asoc)
    fact_asoc = [dict(row) for row in cursor.fetchall()]
    for f in fact_asoc:
        f['diferencia_cuit'] = (f['cuit_hash'] != cuit_hash)
        f['cuit_factura'] = f['cuit_txt']

    # Buscar también facturas asociadas indirectamente por la conciliación de prestaciones de este cliente
    prest_ids = [p['id'] for p in prest_asoc]
    if prest_ids:
        p_placeholders = ','.join('?' for _ in prest_ids)
        cursor.execute(f"""
            SELECT f.comprobante_id, f.fecha_emision, f.monto_total, f.tipo_comprobante, f.estado, 
                   f.mes_auditoria, f.archivo_origen, f.nro_fila, f.cuit_txt, f.cuit_hash
            FROM conciliaciones c
            JOIN facturas f ON c.factura_id = f.comprobante_id
            WHERE c.prestacion_id IN ({p_placeholders})
        """, prest_ids)
        facturas_indirectas = cursor.fetchall()
        
        fact_ids_existentes = {f['comprobante_id'] for f in fact_asoc}
        for f_ind in facturas_indirectas:
            f_dict = dict(f_ind)
            if f_dict['comprobante_id'] not in fact_ids_existentes:
                f_dict['diferencia_cuit'] = (f_dict['cuit_hash'] != cuit_hash)
                f_dict['cuit_factura'] = f_dict['cuit_txt']
                fact_asoc.append(f_dict)
                fact_ids_existentes.add(f_dict['comprobante_id'])
                
        fact_asoc.sort(key=lambda x: x['fecha_emision'] or '')
    
    # 3. Depósitos Banco asociados a cualquiera de los identificadores
    cursor.execute(f"""
        SELECT id, fecha, concepto, detalle, credito, mes_auditoria, archivo_origen, nro_fila
        FROM movimientos_banco
        WHERE cuit_hash_asociado IN ({placeholders})
        ORDER BY fecha ASC
    """, hashes_asoc)
    banco_asoc = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    # Agrupar prestaciones por paciente
    pacientes_map = {}
    for p in prest_asoc:
        pac = p['paciente']
        if not pac: pac = "DESCONOCIDO"
        if pac not in pacientes_map:
            pacientes_map[pac] = {
                "paciente": pac,
                "total_monto": 0.0,
                "prestaciones": []
            }
        pacientes_map[pac]['prestaciones'].append(p)
        pacientes_map[pac]['total_monto'] += float(p['monto'] or 0.0)
        
    pacientes_list = list(pacientes_map.values())
    pacientes_list.sort(key=lambda x: x['paciente'])
    
    return {
        "pacientes": pacientes_list,
        "prestaciones": prest_asoc, # Mantenemos la lista plana por si se necesita
        "facturas": fact_asoc,
        "banco": banco_asoc
    }


class CatalogarRequest(BaseModel):
    id_movimiento: int
    categoria: str
    comentario: Optional[str] = ""

@app.get("/api/alertas")
def get_alertas():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Buscaremos transacciones sospechosas:
    # 1. Concepto contiene 'Reverso' (rebotes de transferencia)
    # 2. CUIT asociado es el de Veronica Priori (27174412702) que es empleada
    # 3. Transacciones de débito > 100.000 con detalle genérico o 'Referencia: |'
    # 4. Cualquier movimiento que ya esté catalogado
    cursor.execute("""
        SELECT id, fecha, hora, concepto, detalle, debito, credito, saldo, 
               cuit_txt_asociado, mes_auditoria, archivo_origen, nro_fila,
               categoria_auditoria, comentario_auditoria
        FROM movimientos_banco
        WHERE concepto LIKE '%Reverso%'
           OR cuit_txt_asociado = '27174412702'
           OR (debito > 100000.0 AND (detalle = '' OR detalle IS NULL OR detalle LIKE '%Referencia:%'))
           OR (categoria_auditoria IS NOT NULL AND categoria_auditoria != '')
        ORDER BY fecha DESC, hora DESC, id DESC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

@app.post("/api/movimiento/catalogar")
def catalogar_movimiento(req: CatalogarRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM movimientos_banco WHERE id = ?", (req.id_movimiento,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
        
    cursor.execute("""
        UPDATE movimientos_banco
        SET categoria_auditoria = ?, comentario_auditoria = ?
        WHERE id = ?
    """, (req.categoria, req.comentario, req.id_movimiento))
    
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Movimiento catalogado correctamente"}


# --- SUGERENCIAS Y FUSIÓN DE DUPLICADOS ---
STOPWORDS = {
    "OBRA", "SOCIAL", "DEL", "PERSONAL", "DE", "LA", "EL", "LOS", "LAS", 
    "ASOCIACION", "MUTUAL", "SINDICATO", "UNION", "NACION", "PROVINCIA", 
    "Y", "DEPARTAMENTO", "MINISTERIO", "OS", "PARA", "CON", "POR",
    "CLIENTE", "IDENTIFICADO", "BANCO"
}

def obtener_trazabilidad_cliente(cursor, cuit_hash, nombre):
    """Busca en transacciones (facturas, banco) el archivo de origen y número de fila de procedencia."""
    cursor.execute("SELECT cuit_hash FROM cliente_identificadores WHERE cliente_cuit_principal_hash = ?", (cuit_hash,))
    hashes = [r['cuit_hash'] for r in cursor.fetchall()]
    if not hashes:
        hashes = [cuit_hash]
        
    procedencias = []
    
    # 1. Buscar en facturas
    placeholders = ','.join('?' for _ in hashes)
    cursor.execute(f"SELECT archivo_origen, nro_fila FROM facturas WHERE cuit_hash IN ({placeholders}) AND archivo_origen IS NOT NULL LIMIT 2", hashes)
    for r in cursor.fetchall():
        fn = os.path.basename(r['archivo_origen'])
        procedencias.append(f"📄 AFIP (Fila {r['nro_fila']}): {fn}")
        
    # 2. Buscar en movimientos de banco
    cursor.execute(f"SELECT archivo_origen, nro_fila FROM movimientos_banco WHERE cuit_hash_asociado IN ({placeholders}) AND archivo_origen IS NOT NULL LIMIT 2", hashes)
    for r in cursor.fetchall():
        fn = os.path.basename(r['archivo_origen'])
        procedencias.append(f"🏦 Banco (Fila {r['nro_fila']}): {fn}")
        
    # 3. Buscar en prestaciones (por coincidencia de nombre)
    cursor.execute("SELECT archivo_origen, nro_fila FROM prestaciones WHERE obra_social_nombre LIKE ? OR ? LIKE '%' || obra_social_nombre || '%' LIMIT 2", (f"%{nombre[:5]}%", nombre))
    for r in cursor.fetchall():
        fn = os.path.basename(r['archivo_origen'])
        procedencias.append(f"📋 Excel Prestaciones (Fila {r['nro_fila']}): {fn}")
        
    return list(set(procedencias))[:3]

def detectar_posibles_duplicados(cursor):
    """Busca en la base de datos parejas de clientes sospechosos de ser duplicados (ej: DNI vs CUIT, nombres similares)."""
    # Leer descartados de la base de datos
    cursor.execute("SELECT cuit_hash_a, cuit_hash_b FROM clientes_descartados_duplicados")
    descartados = set()
    for r in cursor.fetchall():
        descartados.add(tuple(sorted([r['cuit_hash_a'], r['cuit_hash_b']])))

    cursor.execute("SELECT cuit_hash, cuit_encrypted, nombre_razon_social_encrypted, categoria FROM clientes")
    rows = cursor.fetchall()
    
    clientes = []
    for r in rows:
        cuit = decrypt_data(r['cuit_encrypted'])
        nombre = decrypt_data(r['nombre_razon_social_encrypted'])
        clientes.append({
            'cuit_hash': r['cuit_hash'],
            'cuit': cuit,
            'nombre': nombre,
            'categoria': r['categoria']
        })
        
    sugerencias = []
    processed_pairs = set()
    
    # 1. Detección por CUIT 11 vs DNI 8
    for c1 in clientes:
        cuit1 = c1['cuit']
        if len(cuit1) == 11:
            dni = cuit1[2:10] # Extraer el DNI
            for c2 in clientes:
                cuit2 = c2['cuit']
                if len(cuit2) == 8 and cuit2 == dni:
                    pair_key = tuple(sorted([c1['cuit_hash'], c2['cuit_hash']]))
                    if pair_key not in processed_pairs and pair_key not in descartados:
                        processed_pairs.add(pair_key)
                        
                        proc_a = obtener_trazabilidad_cliente(cursor, c1['cuit_hash'], c1['nombre'])
                        proc_b = obtener_trazabilidad_cliente(cursor, c2['cuit_hash'], c2['nombre'])
                        
                        sugerencias.append({
                            'cuit_hash_a': c1['cuit_hash'],
                            'nombre_a': c1['nombre'],
                            'cuit_a': cuit1,
                            'categoria_a': c1['categoria'],
                            'procedencia_a': proc_a,
                            'cuit_hash_b': c2['cuit_hash'],
                            'nombre_b': c2['nombre'],
                            'cuit_b': cuit2,
                            'categoria_b': c2['categoria'],
                            'procedencia_b': proc_b,
                            'razon': 'Relación CUIT ➔ DNI.',
                            'razon_detallada': f"Relación directa CUIT ➔ DNI. El CUIT de 11 dígitos ({cuit1}) de {c1['nombre']} contiene exactamente el DNI de 8 dígitos ({cuit2}) de {c2['nombre']}.",
                            'tipo': 'cuit_dni'
                        })
                        
    # 2. Detección por similitud de nombres clave (excluyendo stopwords y descartando CUITs de 11 dígitos diferentes)
    for i, c1 in enumerate(clientes):
        n1_clean = c1['nombre'].strip().upper().replace(",", " ").replace(".", " ")
        n1_words = set(w for w in n1_clean.split() if len(w) > 2 and w not in STOPWORDS)
        if not n1_words:
            continue
            
        for c2 in clientes[i+1:]:
            # REGLA DE EXCLUSIÓN: Si ambos tienen CUIT de 11 dígitos válidos y son distintos, NO son la misma persona contablemente
            if len(c1['cuit']) == 11 and len(c2['cuit']) == 11 and c1['cuit'] != c2['cuit']:
                continue
                
            n2_clean = c2['nombre'].strip().upper().replace(",", " ").replace(".", " ")
            n2_words = set(w for w in n2_clean.split() if len(w) > 2 and w not in STOPWORDS)
            if not n2_words:
                continue
            
            common = n1_words.intersection(n2_words)
            if len(common) >= 2 or (len(n1_words) == 1 and len(n2_words) == 1 and common):
                if c1['cuit'] != c2['cuit']:
                    pair_key = tuple(sorted([c1['cuit_hash'], c2['cuit_hash']]))
                    if pair_key not in processed_pairs and pair_key not in descartados:
                        processed_pairs.add(pair_key)
                        coincidencias = ", ".join(common)
                        
                        proc_a = obtener_trazabilidad_cliente(cursor, c1['cuit_hash'], c1['nombre'])
                        proc_b = obtener_trazabilidad_cliente(cursor, c2['cuit_hash'], c2['nombre'])
                        
                        sugerencias.append({
                            'cuit_hash_a': c1['cuit_hash'],
                            'nombre_a': c1['nombre'],
                            'cuit_a': c1['cuit'],
                            'categoria_a': c1['categoria'],
                            'procedencia_a': proc_a,
                            'cuit_hash_b': c2['cuit_hash'],
                            'nombre_b': c2['nombre'],
                            'cuit_b': c2['cuit'],
                            'categoria_b': c2['categoria'],
                            'procedencia_b': proc_b,
                            'razon': 'Coincidencia de nombre.',
                            'razon_detallada': f"Nombres similares. Ambos clientes comparten las palabras clave significativas: '{coincidencias}'.",
                            'tipo': 'nombre_similar'
                        })
                        
    # 3. MOCK SIMULADO DE SEGURIDAD (Si no hay duplicados reales activos en la BD)
    if not sugerencias:
        jalif = next((c for c in clientes if "JALIF" in c['nombre'].upper()), None)
        if jalif:
            cuit_sim = "27223922244"
            import hashlib
            hash_sim = hashlib.sha256(cuit_sim.encode()).hexdigest()
            proc_b = obtener_trazabilidad_cliente(cursor, jalif['cuit_hash'], jalif['nombre'])
            sugerencias.append({
                'cuit_hash_a': hash_sim,
                'nombre_a': "JALIF LUCILA SILVINA (Simulado de Demostración)",
                'cuit_a': cuit_sim,
                'categoria_a': "Obra Social",
                'procedencia_a': ["📄 AFIP (Fila 88): VENTAS.txt (Simulado)"],
                'cuit_hash_b': jalif['cuit_hash'],
                'nombre_b': jalif['nombre'],
                'cuit_b': jalif['cuit'],
                'categoria_b': jalif['categoria'],
                'procedencia_b': proc_b,
                'razon': 'Simulación: Relación CUIT ➔ DNI.',
                'razon_detallada': f"[SIMULACIÓN DE DEMOSTRACIÓN] Relación directa CUIT ➔ DNI. El CUIT de 11 dígitos ({cuit_sim}) contiene el DNI de 8 dígitos ({jalif['cuit']}) de JALIF.",
                'tipo': 'cuit_dni',
                'is_simulated': True
            })
            
    return sugerencias

@app.get("/api/duplicados/sugerencias")
def get_duplicados_sugerencias():
    conn = get_db_connection()
    cursor = conn.cursor()
    sugs = detectar_posibles_duplicados(cursor)
    conn.close()
    return sugs

class FusionRequest(BaseModel):
    cuit_hash_principal: str
    cuit_hash_duplicado: str

@app.post("/api/clientes/fusionar")
def post_clientes_fusionar(req: FusionRequest):
    import hashlib
    hash_sim = hashlib.sha256(b"27223922244").hexdigest()
    if req.cuit_hash_principal == hash_sim or req.cuit_hash_duplicado == hash_sim:
        return {"status": "success", "message": "[SIMULACIÓN] Clientes fusionados con éxito de demostración."}

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT cuit_encrypted FROM clientes WHERE cuit_hash = ?", (req.cuit_hash_principal,))
        c_principal = cursor.fetchone()
        cursor.execute("SELECT cuit_encrypted FROM clientes WHERE cuit_hash = ?", (req.cuit_hash_duplicado,))
        c_duplicado = cursor.fetchone()
        
        if not c_principal or not c_duplicado:
            raise HTTPException(status_code=404, detail="Uno o ambos clientes no existen.")
            
        # Actualizar todos los identificadores que apuntaban al duplicado para que ahora apunten al principal
        cursor.execute("""
            UPDATE cliente_identificadores 
            SET cliente_cuit_principal_hash = ? 
            WHERE cliente_cuit_principal_hash = ?
        """, (req.cuit_hash_principal, req.cuit_hash_duplicado))
        
        # Insertar el identificador propio del duplicado apuntando al principal (si no estaba ya)
        cursor.execute("""
            INSERT OR IGNORE INTO cliente_identificadores (cuit_hash, cuit_encrypted, cliente_cuit_principal_hash)
            VALUES (?, ?, ?)
        """, (req.cuit_hash_duplicado, c_duplicado['cuit_encrypted'], req.cuit_hash_principal))
        
        # Eliminar el registro duplicado de la tabla clientes
        cursor.execute("DELETE FROM clientes WHERE cuit_hash = ?", (req.cuit_hash_duplicado,))
        
        conn.commit()
        return {"status": "success", "message": "Clientes fusionados con éxito."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

class DescarteRequest(BaseModel):
    cuit_hash_a: str
    cuit_hash_b: str

@app.post("/api/clientes/descartar-duplicado")
def post_descartar_duplicado(req: DescarteRequest):
    import hashlib
    hash_sim = hashlib.sha256(b"27223922244").hexdigest()
    if req.cuit_hash_a == hash_sim or req.cuit_hash_b == hash_sim:
        return {"status": "success", "message": "[SIMULACIÓN] Sugerencia descartada con éxito de demostración."}
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO clientes_descartados_duplicados (cuit_hash_a, cuit_hash_b)
            VALUES (?, ?)
        """, (req.cuit_hash_a, req.cuit_hash_b))
        conn.commit()
        return {"status": "success", "message": "Pareja de duplicados descartada permanentemente."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# -------------------------------------------------------------------
# DATA LAKE ENDPOINTS
# -------------------------------------------------------------------

@app.get("/api/data/prestaciones")
def get_all_prestaciones():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, obra_social_nombre, paciente, fecha_factura, periodo, monto, factura_nro, forma_pago, fecha_pago, estado_conciliacion, mes_auditoria 
        FROM prestaciones
        ORDER BY id DESC
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

@app.get("/api/data/facturas")
def get_all_facturas():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT comprobante_id, cuit_txt, fecha_emision, monto_total, tipo_comprobante, estado, mes_auditoria 
        FROM facturas
        ORDER BY fecha_emision DESC
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

@app.get("/api/data/banco")
def get_all_banco():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, fecha, hora, concepto, detalle, debito, credito, saldo, cuit_txt_asociado, mes_auditoria, categoria_auditoria, comentario_auditoria 
        FROM movimientos_banco
        ORDER BY fecha DESC
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

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
