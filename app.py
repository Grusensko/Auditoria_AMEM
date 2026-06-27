import os
import glob
import pandas as pd
import streamlit as st
import sqlite3
import hashlib
import plotly.graph_objects as go
from database import (
    get_db_connection, 
    encrypt_data, 
    decrypt_data, 
    hash_cuit,
    hash_password,
    init_db
)
from loader import load_afip_ventas, load_excel_banco, load_excel_prestaciones
from conciliador import run_conciliacion, OS_CUIT_MAP, get_period_sort_value, get_cuit_for_obra_social
from excel_exporter import generate_excel_report

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

def get_period_display_name(periodo_str, mes_auditoria):
    year, month, name = get_period_sort_value(periodo_str, mes_auditoria)
    return f"{year}-{month:02d} - {name}"


# Asegurar que la base de datos esté creada al iniciar la app
init_db()

# Configuración de página con estética moderna
st.set_page_config(
    page_title="AMEM - Consola de Auditoría Inteligente",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inyectar CSS personalizado adaptativo para estética Premium (Glassmorphism, variables del tema de Streamlit)
st.markdown("""
<style>
    /* Ocultar el icono de cadena (ancla de encabezados) en hover */
    .element-container a.header-anchor, a.header-anchor {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
    }
    
    /* Ocultar elementos del header superior derecho (Fork, GitHub, tres puntos) */
    [data-testid="stHeaderActionElements"], 
    div[class*="stHeaderActionElements"],
    #MainMenu {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Ocultar el badge flotante inferior derecho de Streamlit Cloud (corona y logo) */
    .viewerBadge, 
    [data-testid="stViewerBadge"], 
    div[class*="viewerBadge"],
    div[class*="styles_viewerBadge"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
        height: 0px !important;
        width: 0px !important;
    }
    
    /* Ocultar el pie de página "Made with Streamlit" */
    footer {
        display: none !important;
        visibility: hidden !important;
    }

    /* Tarjetas de Métricas Adaptativas y Premium */
    .metric-card {
        background-color: var(--secondary-background-color);
        padding: 24px;
        border-radius: 12px;
        border: 1px solid rgba(128, 128, 128, 0.15);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
        border-left: 5px solid #3B82F6;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1);
    }
    
    .metric-card.success {
        border-left: 5px solid #10B981;
    }
    
    .metric-card.warning {
        border-left: 5px solid #F59E0B;
    }
    
    .metric-card.danger {
        border-left: 5px solid #EF4444;
    }
    
    .metric-title {
        font-size: 11px;
        color: var(--text-color);
        opacity: 0.6;
        text-transform: uppercase;
        font-weight: 700;
        margin-bottom: 6px;
        letter-spacing: 0.8px;
    }
    
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: var(--text-color);
        line-height: 1.1;
    }
    
    .metric-sub {
        font-size: 12px;
        margin-top: 8px;
        opacity: 0.8;
    }
</style>
""", unsafe_allow_html=True)

# Inicializar estados de sesión para el inicio de sesión
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = ""

# --- PANTALLA DE INICIO DE SESIÓN (LOGIN) ---
if not st.session_state.authenticated:
    st.markdown("""
    <style>
        /* Deshabilitar scroll únicamente en la pantalla de login */
        .main, body {
            overflow: hidden !important;
        }
        
        /* Estilos premium para el formulario de login */
        form[data-testid="stForm"] {
            border-radius: 16px !important;
            padding: 2.5rem !important;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.05) !important;
            background-color: var(--secondary-background-color) !important;
            border: 1px solid rgba(128, 128, 128, 0.15) !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<div style='margin-top: 50px;'></div>", unsafe_allow_html=True)
    
    # Limitar el ancho y centrar usando columnas responsivas de Streamlit
    col1, col2, col3 = st.columns([1.5, 1.2, 1.5])
    with col2:
        with st.form("login_form"):
            st.markdown("<h2 style='text-align: center; margin-bottom: 2px;'>📊 AMEM Mendoza</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #475569; font-size: 14px; margin-bottom: 24px;'>Consola de Auditoría Inteligente</p>", unsafe_allow_html=True)
            
            usuario_input = st.text_input("Usuario", placeholder="admin o consulta", autocomplete="off")
            password_input = st.text_input("Contraseña", type="password", placeholder="", autocomplete="new-password")
            
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            submit_btn = st.form_submit_button("Iniciar Sesión", use_container_width=True, type="primary")
        if submit_btn:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash, salt, rol FROM usuarios WHERE usuario = ?", (usuario_input,))
            user_res = cursor.fetchone()
            conn.close()
            
            if user_res:
                stored_hash = user_res['password_hash']
                salt = user_res['salt']
                role = user_res['rol']
                
                # Calcular hash para verificar
                check_hash, _ = hash_password(password_input, salt)
                
                if check_hash == stored_hash:
                    st.session_state.authenticated = True
                    st.session_state.username = usuario_input
                    st.session_state.role = role
                    st.success("¡Inicio de sesión exitoso!")
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta.")
            else:
                st.error("El usuario no existe.")
    st.stop()


# --- DEFINICIÓN DE LAS PÁGINAS DE LA APLICACIÓN ---

# PAGE 1: DASHBOARD
def show_dashboard():
    mes_trabajo = st.session_state.mes_trabajo
    
    # Si el mes global es de 2025 (ej: 2025-12), forzar visualización en Enero 2026
    # ya que la auditoría es estrictamente desde enero 2026
    if not mes_trabajo.startswith("2026"):
        mes_trabajo = "2026-01"
        
    st.subheader(f"Dashboard de Auditoría de Ingresos — {format_period(mes_trabajo)}")
    
    # Consultar datos en la base de datos
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Total Ingresado (Banco Supervielle) en el mes seleccionado
    cursor.execute("""
        SELECT SUM(credito), COUNT(*) 
        FROM movimientos_banco 
        WHERE mes_auditoria = ? AND credito > 0
    """, (mes_trabajo,))
    res_b = cursor.fetchone()
    total_ingresado = res_b[0] if res_b[0] else 0.0
    cant_ingresos = res_b[1] if res_b[1] else 0
    
    # 2. Ingresos Conciliados (Match)
    # Sumamos el crédito de los depósitos del período que estén conciliados
    cursor.execute("""
        SELECT SUM(credito), COUNT(id)
        FROM movimientos_banco
        WHERE mes_auditoria = ? AND credito > 0
          AND id IN (SELECT DISTINCT movimiento_banco_id FROM conciliaciones WHERE estado_final = 'CONCILIADO')
    """, (mes_trabajo,))
    res_c = cursor.fetchone()
    ingresos_conciliados = res_c[0] if res_c[0] else 0.0
    cant_conciliados = res_c[1] if res_c[1] else 0
    
    # 3. Ingresos con Discrepancia
    cursor.execute("""
        SELECT SUM(credito), COUNT(id)
        FROM movimientos_banco
        WHERE mes_auditoria = ? AND credito > 0
          AND id IN (SELECT DISTINCT movimiento_banco_id FROM conciliaciones WHERE estado_final = 'DISCREPANCIA')
    """, (mes_trabajo,))
    res_d = cursor.fetchone()
    ingresos_discrepantes = res_d[0] if res_d[0] else 0.0
    cant_discrepantes = res_d[1] if res_d[1] else 0
    
    # 4. Ingresos Sin Identificar (Movimientos de banco no enlazados a ninguna conciliación)
    cursor.execute("""
        SELECT SUM(credito), COUNT(*)
        FROM movimientos_banco
        WHERE mes_auditoria = ? AND credito > 0
          AND id NOT IN (SELECT DISTINCT movimiento_banco_id FROM conciliaciones WHERE movimiento_banco_id IS NOT NULL)
    """, (mes_trabajo,))
    res_s = cursor.fetchone()
    ingresos_sin_identificar = res_s[0] if res_s[0] else 0.0
    cant_sin_identificar = res_s[1] if res_s[1] else 0
    
    # 5. Prestaciones y Facturas en el mismo período (para referencia y panel de Deuda)
    # Pendientes de Facturación (en AFIP) acumulado hasta mes_trabajo
    cursor.execute("""
        SELECT SUM(monto), COUNT(*) 
        FROM prestaciones 
        WHERE mes_auditoria <= ? 
          AND estado_conciliacion = 'PENDIENTE_FACTURA'
    """, (mes_trabajo,))
    res_pf = cursor.fetchone()
    deuda_pendiente_facturar = res_pf[0] if res_pf[0] else 0.0
    cant_pendiente_facturar = res_pf[1] if res_pf[1] else 0
    
    # Pendientes de Cobro (en Banco) acumulado hasta mes_trabajo
    cursor.execute("""
        SELECT SUM(monto), COUNT(*) 
        FROM prestaciones 
        WHERE mes_auditoria <= ? 
          AND estado_conciliacion = 'PENDIENTE_COBRO'
    """, (mes_trabajo,))
    res_pc = cursor.fetchone()
    deuda_pendiente_cobrar = res_pc[0] if res_pc[0] else 0.0
    cant_pendiente_cobrar = res_pc[1] if res_pc[1] else 0

    conn.close()
    
    # Mostrar KPIs en filas con estética SaaS y efectos hover
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Total Ingresado (Banco)</div>
            <div class="metric-value">${total_ingresado:,.2f}</div>
            <div class="metric-sub" style="color: gray;">{cant_ingresos} depósitos registrados</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <div class="metric-card success">
            <div class="metric-title">Ingresos Conciliados (Match)</div>
            <div class="metric-value" style="color: #10B981;">${ingresos_conciliados:,.2f}</div>
            <div class="metric-sub" style="color: #10B981; font-weight: 600;">{cant_conciliados} cobros ok (cruce histórico)</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown(f"""
        <div class="metric-card warning">
            <div class="metric-title">Ingresos Sin Identificar</div>
            <div class="metric-value" style="color: #F59E0B;">${ingresos_sin_identificar:,.2f}</div>
            <div class="metric-sub" style="color: #F59E0B; font-weight: 600;">{cant_sin_identificar} cobros sin asociar en banco</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col4:
        st.markdown(f"""
        <div class="metric-card danger">
            <div class="metric-title">Discrepancias de Monto</div>
            <div class="metric-value" style="color: #EF4444;">${ingresos_discrepantes:,.2f}</div>
            <div class="metric-sub" style="color: #EF4444; font-weight: 600;">{cant_discrepantes} inconsistencias de pago</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    
    # Gráficos de Plotly Interactivos
    st.markdown("### Estado General de la Caja")
    
    col_chart_l, col_chart_r = st.columns([1.3, 1.7])
    
    with col_chart_l:
        # Calcular porcentaje de ingresos conciliados
        porcentaje_conciliado = (ingresos_conciliados / total_ingresado * 100) if total_ingresado > 0 else 0.0
        
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = porcentaje_conciliado,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Eficiencia de Conciliación", 'font': {'size': 15, 'weight': 'bold'}},
            number = {'suffix': "%", 'font': {'size': 32}},
            gauge = {
                'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "gray"},
                'bar': {'color': "#10B981"},
                'bgcolor': "rgba(0,0,0,0)",
                'borderwidth': 1,
                'bordercolor': "gray",
                'steps': [
                    {'range': [0, 50], 'color': 'rgba(239, 68, 68, 0.15)'},   # Rojo suave
                    {'range': [50, 85], 'color': 'rgba(245, 158, 11, 0.15)'},  # Amarillo suave
                    {'range': [85, 100], 'color': 'rgba(16, 185, 129, 0.15)'} # Verde suave
                ]
            }
        ))
        fig_gauge.update_layout(
            height=260,
            margin=dict(l=25, r=25, t=50, b=25),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font={'color': 'var(--text-color)', 'family': 'Outfit, Inter, sans-serif'}
        )
        st.plotly_chart(fig_gauge, use_container_width=True)
        
    with col_chart_r:
        # Gráfico Waterfall de desglose de Ingresos
        fig_waterfall = go.Figure(go.Waterfall(
            name = "Desglose Caja",
            orientation = "v",
            measure = ["relative", "relative", "relative", "total"],
            x = ["Total Ingresado", "Sin Identificar", "Discrepancias", "Conciliado"],
            textposition = "outside",
            text = [
                f"${total_ingresado:,.0f}", 
                f"-${ingresos_sin_identificar:,.0f}", 
                f"-${ingresos_discrepantes:,.0f}", 
                f"${ingresos_conciliados:,.0f}"
            ],
            y = [
                total_ingresado, 
                -ingresos_sin_identificar, 
                -ingresos_discrepantes, 
                ingresos_conciliados
            ],
            connector = {"line":{"color":"rgba(156, 163, 175, 0.4)", "width": 1, "dash":"dot"}},
            increasing = {"marker": {"color": "#3B82F6"}}, # Azul
            decreasing = {"marker": {"color": "#F59E0B"}}, # Ámbar/Naranja
            totals = {"marker": {"color": "#10B981"}}      # Verde esmeralda
        ))
        
        fig_waterfall.update_layout(
            title = {"text": "Flujo de Desglose de Caja ($)", "font": {"size": 15, "weight": 'bold'}, "x": 0.5},
            height = 280,
            margin = dict(l=20, r=20, t=50, b=20),
            paper_bgcolor = 'rgba(0,0,0,0)',
            plot_bgcolor = 'rgba(0,0,0,0)',
            font = {'color': 'var(--text-color)', 'family': 'Outfit, Inter, sans-serif'},
            showlegend = False,
            yaxis = dict(visible=False)
        )
        st.plotly_chart(fig_waterfall, use_container_width=True)
        
    st.markdown("---")
    
    # NUEVA SECCIÓN: Deuda Pendiente de Obras Sociales (Cuentas por Cobrar)
    st.markdown("### Deuda Pendiente y Facturación (Cuentas por Cobrar)")
    st.markdown(f"Resumen de saldos históricos pendientes acumulados hasta el cierre de **{format_period(mes_trabajo)}**:")
    
    col_deuda_l, col_deuda_r = st.columns(2)
    
    with col_deuda_l:
        st.markdown(f"""
        <div class="metric-card warning" style="border-left: 5px solid #F59E0B; padding: 15px;">
            <div class="metric-title" style="color: var(--text-color); font-weight: 700;">Pendiente de Facturación (Gestión ➔ AFIP)</div>
            <div class="metric-value" style="color: #F59E0B; font-size: 26px; font-weight: 800; margin-top: 5px;">${deuda_pendiente_facturar:,.2f}</div>
            <div class="metric-sub" style="color: gray; margin-top: 5px;">
                {cant_pendiente_facturar} prestaciones sin factura emitida en AFIP.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_deuda_r:
        st.markdown(f"""
        <div class="metric-card danger" style="border-left: 5px solid #EF4444; padding: 15px;">
            <div class="metric-title" style="color: var(--text-color); font-weight: 700;">Pendiente de Liquidación/Cobro (AFIP ➔ Banco)</div>
            <div class="metric-value" style="color: #EF4444; font-size: 26px; font-weight: 800; margin-top: 5px;">${deuda_pendiente_cobrar:,.2f}</div>
            <div class="metric-sub" style="color: gray; margin-top: 5px;">
                {cant_pendiente_cobrar} facturas emitidas sin cobro identificado en el banco.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown(
        "<p style='font-size: 12px; color: #64748B; font-style: italic; margin-top: 10px;'>"
        "* Nota: Estos saldos corresponden a prestaciones contables de meses actuales o anteriores que aún no han cerrado "
        "su ciclo administrativo debido a los plazos y demoras de facturación y acreditación de las Obras Sociales."
        "</p>",
        unsafe_allow_html=True
    )


from datetime import datetime

def format_date_readable(dt_str):
    try:
        if not dt_str:
            return "Sin Fecha"
        dt_str = dt_str.strip()
        if "-" in dt_str:
            dt = datetime.strptime(dt_str.split()[0], "%Y-%m-%d")
        else:
            dt = datetime.strptime(dt_str.split()[0], "%d/%m/%Y")
        
        meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        return f"{dt.day} {meses[dt.month - 1]} {dt.year}"
    except Exception:
        return str(dt_str)

def format_short_date(dt_str):
    try:
        if not dt_str:
            return "—"
        dt_str = dt_str.strip()
        if "-" in dt_str:
            dt = datetime.strptime(dt_str.split()[0], "%Y-%m-%d")
        else:
            dt = datetime.strptime(dt_str.split()[0], "%d/%m/%Y")
        return f"{dt.day:02d}/{dt.month:02d}"
    except Exception:
        return str(dt_str)

def parse_date(dt_str):
    if not dt_str:
        return None
    dt_str = dt_str.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            try:
                return datetime.strptime(dt_str.split()[0], fmt)
            except (ValueError, IndexError):
                continue
    return None

def day_difference(d1, d2):
    if not d1 or not d2:
        return 0
    return (d2 - d1).days

def generate_timeline_html(prest_date_str, afip_date_str, banco_date_str):
    prest_date = parse_date(prest_date_str)
    afip_date = parse_date(afip_date_str)
    banco_date = parse_date(banco_date_str)
    
    label_prest = format_date_readable(prest_date_str) if prest_date else "Sin Fecha"
    label_afip = format_date_readable(afip_date_str) if afip_date else "Pendiente"
    label_banco = format_date_readable(banco_date_str) if banco_date else "Pendiente"
    
    left_prest = 0
    left_afip = 45
    left_banco = 90
    
    status_prest = "green"
    status_afip = "blue" if afip_date else "pending"
    status_banco = "orange" if banco_date else "pending"
    
    tooltip_prest = f"Prestación Registrada: {label_prest}"
    tooltip_afip = f"Facturado en AFIP el {label_afip}" if afip_date else "Pendiente de Facturación"
    tooltip_banco = f"Acreditado en Banco el {label_banco}" if banco_date else "Pendiente de Cobro"
    
    if prest_date:
        if afip_date:
            diff_days = day_difference(prest_date, afip_date)
            left_afip = min(95, max(15, (diff_days / 120) * 100))
            tooltip_afip += f" ({diff_days} días de delay)"
        if banco_date:
            diff_days = day_difference(prest_date, banco_date)
            left_banco = min(100, max(left_afip + 15, (diff_days / 120) * 100))
            tooltip_banco += f" ({diff_days} días desde prestación)"
            if afip_date:
                diff_afip_banco = day_difference(afip_date, banco_date)
                tooltip_banco += f" / ({diff_afip_banco} días desde facturación)"
                
    progress_width = 0
    if banco_date:
        progress_width = left_banco
    elif afip_date:
        progress_width = left_afip
    else:
        progress_width = 0
        
    class_prest = "first-event" if left_prest < 15 else ("last-event" if left_prest > 85 else "")
    class_afip = "first-event" if left_afip < 15 else ("last-event" if left_afip > 85 else "")
    class_banco = "first-event" if left_banco < 15 else ("last-event" if left_banco > 85 else "")
    
    html = f"""
    <div class="timeline-container">
        <div class="timeline-line"></div>
        <div class="timeline-progress" style="width: {progress_width}%;"></div>
        
        <div class="timeline-events">
            <!-- Hito 1: Prestación -->
            <div class="timeline-event {class_prest}" style="left: {left_prest}%;" title="{tooltip_prest}">
                <div class="event-dot {status_prest}"></div>
                <div class="event-label">Prestación</div>
                <div class="event-date">{format_short_date(prest_date_str) if prest_date_str else "—"}</div>
            </div>
            
            <!-- Hito 2: Factura AFIP -->
            <div class="timeline-event {class_afip}" style="left: {left_afip}%;" title="{tooltip_afip}">
                <div class="event-dot {status_afip}"></div>
                <div class="event-label">Facturación</div>
                <div class="event-date">{format_short_date(afip_date_str) if afip_date_str else "—"}</div>
            </div>
            
            <!-- Hito 3: Cobro Banco -->
            <div class="timeline-event {class_banco}" style="left: {left_banco}%;" title="{tooltip_banco}">
                <div class="event-dot {status_banco}"></div>
                <div class="event-label">Cobro</div>
                <div class="event-date">{format_short_date(banco_date_str) if banco_date_str else "—"}</div>
            </div>
        </div>
    </div>
    """
    return html


# PAGE 2: PANEL DE CONCILIACIÓN
def show_conciliacion():
    # Tag Auditoría Conectada y Título en un flex row
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; flex-wrap: wrap; gap: 10px;">
            <h2 style="margin:0; font-weight:800; font-size:28px;">Auditoría y Conciliación de Items — {format_period(st.session_state.mes_trabajo)}</h2>
            <span style="background-color: rgba(16, 185, 129, 0.1); color: #10B981; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 700; display: inline-flex; align-items: center; gap: 6px;">
                <span style="width: 8px; height: 8px; border-radius: 50%; background-color: #10B981; display: inline-block; animation: pulse 2s infinite;"></span>
                Auditoría Conectada
            </span>
        </div>
        <style>
            @keyframes pulse {{
                0% {{ transform: scale(0.9); opacity: 1; }}
                50% {{ transform: scale(1.2); opacity: 0.5; }}
                100% {{ transform: scale(0.9); opacity: 1; }}
            }}
        </style>
        """,
        unsafe_allow_html=True
    )
    st.markdown("Revisa las prestaciones y depósitos bancarios, y realiza vinculaciones manuales maestro-detalle.")
    
    # 1. Inyectar estilos CSS avanzados adaptativos y premium (UX de tarjetas y botones maestro)
    st.markdown("""
    <style>
        /* Estilos generales del contenedor de detalle */
        .detail-card {
            background-color: var(--secondary-background-color);
            border-radius: 12px;
            padding: 22px;
            border: 1px solid rgba(128, 128, 128, 0.15);
            margin-bottom: 18px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        }
        
        .detail-header {
            font-size: 14px;
            font-weight: 700;
            margin-bottom: 14px;
            color: var(--text-color);
            border-bottom: 1px solid rgba(128, 128, 128, 0.2);
            padding-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        /* Lista Maestro a la izquierda */
        .list-master-container {
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-height: 700px;
            overflow-y: auto;
            padding-right: 5px;
        }
        
        /* Botones como tarjetas - Compatibles con la estructura de containers de Streamlit */
        div.stElementContainer:has(.selected-button-wrapper) + div.stElementContainer button,
        div.stElementContainer:has(.normal-button-wrapper) + div.stElementContainer button {
            text-align: left !important;
            display: block !important;
            width: 100% !important;
            color: var(--text-color) !important;
            border-radius: 10px !important;
            padding: 12px 14px !important;
            font-size: 13px !important;
            line-height: 1.4 !important;
            transition: all 0.2s ease-in-out !important;
            border: 1px solid rgba(128, 128, 128, 0.15) !important;
            white-space: pre-line !important;
        }
        
        div.stElementContainer:has(.normal-button-wrapper) + div.stElementContainer button {
            background-color: var(--secondary-background-color) !important;
        }
        
        div.stElementContainer:has(.normal-button-wrapper) + div.stElementContainer button:hover {
            background-color: rgba(128, 128, 128, 0.1) !important;
            border-color: #3B82F6 !important;
            transform: translateX(2px) !important;
        }
        
        div.stElementContainer:has(.selected-button-wrapper) + div.stElementContainer button {
            background-color: rgba(59, 130, 246, 0.08) !important;
            border: 1.5px solid #3B82F6 !important;
            border-left: 6px solid #3B82F6 !important;
            font-weight: 700 !important;
        }
        
        /* Estilos de la Línea de Tiempo Contable */
        .timeline-card {
            margin-bottom: 18px;
            padding: 24px 22px;
        }
        .timeline-container {
            position: relative;
            width: 90%;
            margin: 30px auto 10px auto;
            height: 60px;
        }
        .timeline-line {
            position: absolute;
            top: 8px;
            left: 0;
            width: 100%;
            height: 4px;
            background-color: #E2E8F0;
            border-radius: 2px;
            z-index: 1;
        }
        .timeline-progress {
            position: absolute;
            top: 8px;
            left: 0;
            height: 4px;
            background-color: #10B981;
            border-radius: 2px;
            z-index: 2;
            transition: width 0.3s;
        }
        .timeline-events {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 3;
        }
        .timeline-event {
            position: absolute;
            transform: translateX(-50%);
            text-align: center;
            cursor: pointer;
        }
        .event-dot {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background-color: #FFFFFF;
            border: 4px solid #94A3B8;
            margin: 0 auto;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            transition: all 0.2s;
        }
        .timeline-event:hover .event-dot {
            transform: scale(1.2);
        }
        .event-dot.green { border-color: #10B981; background-color: #10B981; }
        .event-dot.blue { border-color: #3B82F6; background-color: #3B82F6; }
        .event-dot.orange { border-color: #F59E0B; background-color: #F59E0B; }
        .event-dot.pending { border-color: #94A3B8; background-color: #FFFFFF; border-style: dashed; }
        .event-label {
            font-size: 10px;
            font-weight: 700;
            color: #64748B;
            margin-top: 6px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            white-space: nowrap;
        }
        .event-date {
            font-size: 11px;
            color: #94A3B8;
            font-weight: 600;
            margin-top: 2px;
            white-space: nowrap;
        }
        
        /* Etiquetas de ficha de detalle */
        .info-label {
            font-size: 10px;
            text-transform: uppercase;
            font-weight: 700;
            color: #64748B;
            margin-bottom: 2px;
            letter-spacing: 0.5px;
        }
        
        .info-value {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-color);
            margin-bottom: 12px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    mes_trabajo = st.session_state.mes_trabajo
    
    # Inicializar estados de la sesión para el maestro-detalle
    if "conciliacion_camino" not in st.session_state:
        st.session_state.conciliacion_camino = "A"
    if "selected_prest_id" not in st.session_state:
        st.session_state.selected_prest_id = None
    if "selected_banco_id" not in st.session_state:
        st.session_state.selected_banco_id = None
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 2. Selector de Flujo de Trabajo (Camino A o B)
    if hasattr(st, "segmented_control"):
        camino_opt = st.segmented_control(
            "Seleccionar Flujo de Conciliación",
            options=["A", "B"],
            format_func=lambda x: "⚖️ De Facturas a Cobros" if x == "A" else "🏦 De Cobros a Facturas",
            default=st.session_state.conciliacion_camino
        )
        if camino_opt and camino_opt != st.session_state.conciliacion_camino:
            st.session_state.conciliacion_camino = camino_opt
            st.session_state.selected_prest_id = None
            st.session_state.selected_banco_id = None
            st.rerun()
    else:
        camino_opt = st.radio(
            "Seleccionar Flujo de Conciliación",
            options=["A", "B"],
            format_func=lambda x: "⚖️ De Facturas a Cobros" if x == "A" else "🏦 De Cobros a Facturas",
            horizontal=True,
            index=["A", "B"].index(st.session_state.conciliacion_camino)
        )
        if camino_opt != st.session_state.conciliacion_camino:
            st.session_state.conciliacion_camino = camino_opt
            st.session_state.selected_prest_id = None
            st.session_state.selected_banco_id = None
            st.rerun()
            
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    
    # Dividir el layout en Maestro (Lista) y Detalle (Panel Derecho)
    col_maestro, col_detalle = st.columns([1.6, 2.4])
    
    # ----------------------------------------------------
    # CAMINO A: PRESTACIONES/FACTURAS ➔ BANCO
    # ----------------------------------------------------
    if st.session_state.conciliacion_camino == "A":
        with col_maestro:
            st.markdown("#### 📄 Facturas y Prestaciones")
            search_query = st.text_input("Buscar...", placeholder="Buscar...", key="search_prest_master", label_visibility="collapsed")
            
            # Filtros de estado directos (sin expander)
            st.markdown("<div style='font-size: 10px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;'>ESTADOS:</div>", unsafe_allow_html=True)
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            with col_f1:
                filtro_conc = st.checkbox("🟢 Concil.", value=False, key="maestro_f_conc")
            with col_f2:
                filtro_fact = st.checkbox("🔵 Pend. Fact", value=True, key="maestro_f_fact")
            with col_f3:
                filtro_cobro = st.checkbox("🟡 Pend. Cob", value=True, key="maestro_f_cobro")
            with col_f4:
                filtro_disc = st.checkbox("🔴 Disc.", value=True, key="maestro_f_disc")
                    
            est_filter = []
            if filtro_conc: est_filter.append("🟢 CONCILIADO")
            if filtro_fact: est_filter.append("🔵 PENDIENTE FACTURA")
            if filtro_cobro: est_filter.append("🟡 PENDIENTE COBRO")
            if filtro_disc: est_filter.append("🔴 DISCREPANCIA")
            
            # Cargar prestaciones del periodo
            query_prest_master = """
                SELECT 
                    p.id AS prest_id,
                    p.obra_social_nombre AS os,
                    p.paciente AS paciente,
                    p.periodo AS periodo,
                    p.monto AS monto,
                    p.factura_nro AS factura_nro,
                    c.estado_final AS estado,
                    c.observaciones AS obs,
                    c.factura_id AS fact_afip_id,
                    c.movimiento_banco_id AS banco_id
                FROM prestaciones p
                LEFT JOIN conciliaciones c ON p.id = c.prestacion_id
                WHERE p.mes_auditoria = ?
            """
            df_prest = pd.read_sql_query(query_prest_master, conn, params=(mes_trabajo,))
            
            if not df_prest.empty:
                status_map = {
                    'CONCILIADO': '🟢 CONCILIADO',
                    'PENDIENTE_FACTURA': '🔵 PENDIENTE FACTURA',
                    'PENDIENTE_COBRO': '🟡 PENDIENTE COBRO',
                    'DISCREPANCIA': '🔴 DISCREPANCIA'
                }
                df_prest['estado_raw'] = df_prest['estado']
                df_prest['estado'] = df_prest['estado'].map(lambda x: status_map.get(x, str(x)))
                
                # Aplicar filtros
                filtered_df = df_prest
                if est_filter:
                    filtered_df = filtered_df[filtered_df['estado'].isin(est_filter)]
                if search_query:
                    sq_lower = search_query.lower()
                    filtered_df = filtered_df[
                        filtered_df['os'].str.lower().str.contains(sq_lower) |
                        filtered_df['paciente'].str.lower().str.contains(sq_lower)
                    ]
                    
                filtered_df = filtered_df.sort_values('prest_id', ascending=False)
                
                if not filtered_df.empty:
                    # Inicializar seleccion por defecto si no hay o si la anterior no está en los filtrados
                    valid_ids = filtered_df['prest_id'].tolist()
                    if st.session_state.selected_prest_id not in valid_ids:
                        st.session_state.selected_prest_id = int(valid_ids[0])
                        
                    st.markdown('<div class="list-master-container">', unsafe_allow_html=True)
                    for _, row in filtered_df.iterrows():
                        p_id = int(row['prest_id'])
                        is_selected = (st.session_state.selected_prest_id == p_id)
                        
                        # Determinar emoji de estado
                        st_emoji = "🟢"
                        if "PENDIENTE FACTURA" in row['estado']: st_emoji = "🔵"
                        elif "PENDIENTE COBRO" in row['estado']: st_emoji = "🟡"
                        elif "DISCREPANCIA" in row['estado']: st_emoji = "🔴"
                        
                        btn_lbl = f"{st_emoji} {row['os']} — ${row['monto']:,.2f}\n👤 Paciente: {row['paciente']}"
                        
                        wrapper_class = "selected-button-wrapper" if is_selected else "normal-button-wrapper"
                        st.markdown(f'<div class="{wrapper_class}">', unsafe_allow_html=True)
                        if st.button(btn_lbl, key=f"p_btn_{p_id}"):
                            st.session_state.selected_prest_id = p_id
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.info("No hay items que coincidan con los filtros.")
            else:
                st.info("No hay prestaciones cargadas para este período.")
                
        with col_detalle:
            st.markdown("#### 🔬 Ficha de Análisis y Conciliación")
            if st.session_state.selected_prest_id:
                # Cargar datos actuales del item seleccionado con fechas para la línea de tiempo
                cursor.execute("""
                    SELECT 
                        p.id AS prest_id,
                        p.obra_social_nombre AS os,
                        p.paciente AS paciente,
                        p.periodo AS periodo,
                        p.monto AS monto,
                        p.factura_nro AS factura_nro,
                        p.fecha_factura AS fecha_factura,
                        c.estado_final AS estado,
                        c.observaciones AS obs,
                        c.factura_id AS fact_afip_id,
                        c.movimiento_banco_id AS banco_id,
                        f.fecha_emision AS afip_fecha,
                        mb.fecha AS banco_fecha
                    FROM prestaciones p
                    LEFT JOIN conciliaciones c ON p.id = c.prestacion_id
                    LEFT JOIN facturas f ON c.factura_id = f.comprobante_id
                    LEFT JOIN movimientos_banco mb ON c.movimiento_banco_id = mb.id
                    WHERE p.id = ?
                """, (st.session_state.selected_prest_id,))
                row_item = cursor.fetchone()
                
                if row_item:
                    # Tarjeta 1: Datos Principales de la Prestación
                    st.markdown('<div class="detail-card">', unsafe_allow_html=True)
                    st.markdown('<div class="detail-header">📊 Datos de la Prestación (Gestión)</div>', unsafe_allow_html=True)
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        st.markdown('<div class="info-label">Obra Social</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="info-value">{row_item["os"]}</div>', unsafe_allow_html=True)
                        st.markdown('<div class="info-label">Paciente</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="info-value">{row_item["paciente"]}</div>', unsafe_allow_html=True)
                    with col_d2:
                        st.markdown('<div class="info-label">Monto de la Prestación</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="info-value" style="font-size: 16px; color: #10B981; font-weight: 700;">${row_item["monto"]:,.2f}</div>', unsafe_allow_html=True)
                        st.markdown('<div class="info-label">Período de Prestación</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="info-value">{format_period(row_item["periodo"])}</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Tarjeta Timeline: Línea de Tiempo del Ciclo Contable
                    timeline_html = generate_timeline_html(
                        row_item['fecha_factura'],
                        row_item['afip_fecha'],
                        row_item['banco_fecha']
                    )
                    st.markdown('<div class="detail-card timeline-card">', unsafe_allow_html=True)
                    st.markdown('<div class="detail-header">📅 Línea de Tiempo del Ciclo Contable (Escala 120 días)</div>', unsafe_allow_html=True)
                    st.markdown(timeline_html, unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Tarjeta 2: Vínculo Factura AFIP (Vía 2)
                    st.markdown('<div class="detail-card">', unsafe_allow_html=True)
                    st.markdown('<div class="detail-header">📄 Factura de AFIP / ARCA (Vía 2)</div>', unsafe_allow_html=True)
                    
                    factura_vinculo_id = row_item['fact_afip_id']
                    if factura_vinculo_id:
                        cursor.execute("SELECT fecha_emision, monto_total, cuit_txt, tipo_comprobante FROM facturas WHERE comprobante_id = ?", (factura_vinculo_id,))
                        f_res = cursor.fetchone()
                        if f_res:
                            col_f1, col_f2 = st.columns(2)
                            with col_f1:
                                st.markdown('<div class="info-label">Comprobante ID</div>', unsafe_allow_html=True)
                                st.markdown(f'<div class="info-value">{factura_vinculo_id}</div>', unsafe_allow_html=True)
                                st.markdown('<div class="info-label">Fecha Emisión</div>', unsafe_allow_html=True)
                                st.markdown(f'<div class="info-value">{f_res["fecha_emision"]}</div>', unsafe_allow_html=True)
                            with col_f2:
                                st.markdown('<div class="info-label">Monto Facturado</div>', unsafe_allow_html=True)
                                st.markdown(f'<div class="info-value">${f_res["monto_total"]:,.2f}</div>', unsafe_allow_html=True)
                                st.markdown('<div class="info-label">CUIT & Tipo</div>', unsafe_allow_html=True)
                                st.markdown(f'<div class="info-value">{f_res["cuit_txt"]} (Tipo: {f_res["tipo_comprobante"]})</div>', unsafe_allow_html=True)
                    else:
                        st.warning("⚠️ Sin Factura de AFIP asociada")
                        
                    # Selector Factura AFIP
                    cuit = get_cuit_for_obra_social(row_item['os'])
                    c_hash = hash_cuit(cuit) if cuit else ""
                    
                    cursor.execute("""
                        SELECT comprobante_id, monto_total, fecha_emision, cuit_txt, tipo_comprobante
                        FROM facturas
                        WHERE (cuit_hash = ? OR cuit_hash IS NULL OR ? = '')
                          AND (comprobante_id NOT IN (SELECT factura_id FROM conciliaciones WHERE prestacion_id != ? AND factura_id IS NOT NULL)
                               OR comprobante_id = ?)
                        ORDER BY ABS(monto_total - ?) ASC, fecha_emision DESC
                        LIMIT 50
                    """, (c_hash, c_hash, row_item['prest_id'], factura_vinculo_id, row_item['monto']))
                    
                    facturas_cands = cursor.fetchall()
                    if not facturas_cands:
                        cursor.execute("""
                            SELECT comprobante_id, monto_total, fecha_emision, cuit_txt, tipo_comprobante
                            FROM facturas
                            WHERE comprobante_id NOT IN (SELECT factura_id FROM conciliaciones WHERE prestacion_id != ? AND factura_id IS NOT NULL)
                               OR comprobante_id = ?
                            ORDER BY ABS(monto_total - ?) ASC, fecha_emision DESC
                            LIMIT 50
                        """, (row_item['prest_id'], factura_vinculo_id, row_item['monto']))
                        facturas_cands = cursor.fetchall()
                        
                    facturas_options = { "Ninguna / Desvincular": None }
                    default_factura_key = "Ninguna / Desvincular"
                    
                    for f in facturas_cands:
                        f_id = f['comprobante_id']
                        f_text = f"Factura Nº {f_id} | Emisión: {f['fecha_emision']} | Monto: ${f['monto_total']:,.2f} | CUIT: {f['cuit_txt']} (Tipo: {f['tipo_comprobante']})"
                        facturas_options[f_text] = f_id
                        if factura_vinculo_id == f_id:
                            default_factura_key = f_text
                            
                    if factura_vinculo_id and default_factura_key == "Ninguna / Desvincular":
                        f_text = f"Factura Nº {factura_vinculo_id} (Vinculada actualmente)"
                        facturas_options[f_text] = factura_vinculo_id
                        default_factura_key = f_text
                        
                    selected_factura_text = st.selectbox(
                        "Asociar Factura AFIP", 
                        list(facturas_options.keys()), 
                        index=list(facturas_options.keys()).index(default_factura_key),
                        key="sel_factura_vinculo_a"
                    )
                    factura_vinculo_id = facturas_options[selected_factura_text]
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Tarjeta 3: Vínculo Depósito Bancario (Vía 3)
                    st.markdown('<div class="detail-card">', unsafe_allow_html=True)
                    st.markdown('<div class="detail-header">🏦 Depósito Bancario / Cobro (Vía 3)</div>', unsafe_allow_html=True)
                    
                    banco_vinculo_id = row_item['banco_id']
                    if banco_vinculo_id:
                        cursor.execute("SELECT fecha, concepto, detalle, credito FROM movimientos_banco WHERE id = ?", (banco_vinculo_id,))
                        b_res = cursor.fetchone()
                        if b_res:
                            col_b1, col_b2 = st.columns(2)
                            with col_b1:
                                st.markdown('<div class="info-label">Movimiento ID</div>', unsafe_allow_html=True)
                                st.markdown(f'<div class="info-value">{banco_vinculo_id}</div>', unsafe_allow_html=True)
                                st.markdown('<div class="info-label">Fecha de Cobro</div>', unsafe_allow_html=True)
                                st.markdown(f'<div class="info-value">{b_res["fecha"]}</div>', unsafe_allow_html=True)
                            with col_b2:
                                st.markdown('<div class="info-label">Monto Acreditado</div>', unsafe_allow_html=True)
                                st.markdown(f'<div class="info-value" style="font-size: 15px; color: #10B981; font-weight: 700;">${b_res["credito"]:,.2f}</div>', unsafe_allow_html=True)
                                st.markdown('<div class="info-label">Concepto Bancario</div>', unsafe_allow_html=True)
                                conc_str = b_res['concepto'] if b_res['concepto'] else ""
                                det_str = f" — {b_res['detalle']}" if b_res['detalle'] else ""
                                st.markdown(f'<div class="info-value">{conc_str}{det_str}</div>', unsafe_allow_html=True)
                    else:
                        st.warning("⚠️ Sin Depósito Bancario identificado")
                        
                    # Buscador de Banco
                    st.markdown("##### 🔍 Buscar Depósito en Banco")
                    col_fb1, col_fb2 = st.columns(2)
                    with col_fb1:
                        buscar_texto_banco = st.text_input("Concepto o Detalle (Ej: OSDE, OSEP, CUIT)", value="", placeholder="Filtrar movimientos...", key="search_banco_text_a")
                    with col_fb2:
                        filtrar_por_monto = st.checkbox("Filtrar por Importe Similar (±5%)", value=True, key="chk_filtrar_monto_a")
                        
                    query_banco = """
                        SELECT id, fecha, concepto, detalle, credito
                        FROM movimientos_banco
                        WHERE credito > 0 AND debito = 0.0
                          AND (id NOT IN (SELECT movimiento_banco_id FROM conciliaciones WHERE prestacion_id != ? AND movimiento_banco_id IS NOT NULL)
                               OR id = ?)
                    """
                    params_banco = [row_item['prest_id'], banco_vinculo_id]
                    
                    if buscar_texto_banco:
                        query_banco += " AND (concepto LIKE ? OR detalle LIKE ?)"
                        params_banco.extend([f"%{buscar_texto_banco}%", f"%{buscar_texto_banco}%"])
                    if filtrar_por_monto:
                        monto_min = row_item['monto'] * 0.95
                        monto_max = row_item['monto'] * 1.05
                        query_banco += " AND credito BETWEEN ? AND ?"
                        params_banco.extend([monto_min, monto_max])
                        
                    query_banco += " ORDER BY ABS(credito - ?) ASC, fecha DESC LIMIT 100"
                    params_banco.append(row_item['monto'])
                    
                    cursor.execute(query_banco, tuple(params_banco))
                    banco_cands = cursor.fetchall()
                    
                    banco_options = { "Ninguno / Desvincular": None }
                    default_banco_key = "Ninguno / Desvincular"
                    
                    for b in banco_cands:
                        b_id = b['id']
                        c_str = b['concepto'] if b['concepto'] else ""
                        d_str = f" ({b['detalle']})" if b['detalle'] else ""
                        b_text = f"ID: {b_id} | Fecha: {b['fecha']} | Monto: ${b['credito']:,.2f} | {c_str}{d_str}"
                        banco_options[b_text] = b_id
                        if banco_vinculo_id == b_id:
                            default_banco_key = b_text
                            
                    if banco_vinculo_id and default_banco_key == "Ninguno / Desvincular":
                        cursor.execute("SELECT id, fecha, concepto, detalle, credito FROM movimientos_banco WHERE id = ?", (banco_vinculo_id,))
                        curr_b = cursor.fetchone()
                        if curr_b:
                            b_id = curr_b['id']
                            c_str = curr_b['concepto'] if curr_b['concepto'] else ""
                            d_str = f" ({curr_b['detalle']})" if curr_b['detalle'] else ""
                            b_text = f"ID: {b_id} | Fecha: {curr_b['fecha']} | Monto: ${curr_b['credito']:,.2f} | {c_str}{d_str} (Vinculado actualmente)"
                            banco_options[b_text] = b_id
                            default_banco_key = b_text
                            
                    selected_banco_text = st.selectbox(
                        "Asociar Depósito Bancario", 
                        list(banco_options.keys()), 
                        index=list(banco_options.keys()).index(default_banco_key),
                        key="sel_banco_vinculo_a"
                    )
                    banco_vinculo_id = banco_options[selected_banco_text]
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Tarjeta 4: Estado y Guardar
                    st.markdown('<div class="detail-card">', unsafe_allow_html=True)
                    st.markdown('<div class="detail-header">⚙️ Conciliación y Acciones</div>', unsafe_allow_html=True)
                    
                    # Calcular montos elegidos
                    monto_fact_sel = None
                    if factura_vinculo_id:
                        cursor.execute("SELECT monto_total FROM facturas WHERE comprobante_id = ?", (factura_vinculo_id,))
                        res_mf = cursor.fetchone()
                        monto_fact_sel = res_mf['monto_total'] if res_mf else None
                        
                    monto_banc_sel = None
                    if banco_vinculo_id:
                        cursor.execute("SELECT credito FROM movimientos_banco WHERE id = ?", (banco_vinculo_id,))
                        res_mb = cursor.fetchone()
                        monto_banc_sel = res_mb['credito'] if res_mb else None
                        
                    estado_sugerido = "PENDIENTE_FACTURA"
                    recomendacion_msg = ""
                    
                    if factura_vinculo_id and banco_vinculo_id:
                        diff_f = abs(row_item['monto'] - monto_fact_sel)
                        diff_b = abs(row_item['monto'] - monto_banc_sel)
                        if diff_f < 0.01 and diff_b < 0.01:
                            estado_sugerido = "CONCILIADO"
                            recomendacion_msg = "🟢 Conciliación completa: Prestación, Factura y Depósito coinciden exactamente en monto."
                        else:
                            estado_sugerido = "DISCREPANCIA"
                            recomendacion_msg = f"🔴 Discrepancia de montos: Prestación (${row_item['monto']:,.2f}) vs Factura (${monto_fact_sel:,.2f}) vs Banco (${monto_banc_sel:,.2f})."
                    elif factura_vinculo_id and not banco_vinculo_id:
                        estado_sugerido = "PENDIENTE_COBRO"
                        recomendacion_msg = "🟡 Factura vinculada pero sin depósito bancario identificado (Pendiente de Cobro)."
                    elif not factura_vinculo_id and banco_vinculo_id:
                        estado_sugerido = "DISCREPANCIA"
                        recomendacion_msg = "🔴 Pago recibido en banco pero sin factura de AFIP asociada (Discrepancia)."
                    else:
                        estado_sugerido = "PENDIENTE_FACTURA"
                        recomendacion_msg = "🔵 Sin factura de AFIP ni depósito en banco (Pendiente de Factura)."
                        
                    st.info(recomendacion_msg)
                    
                    estados_lista = ["CONCILIADO", "PENDIENTE_FACTURA", "PENDIENTE_COBRO", "DISCREPANCIA"]
                    idx_sugerido = estados_lista.index(estado_sugerido)
                    
                    col_e1, col_e2 = st.columns([1.2, 2.8])
                    with col_e1:
                        estado_final_guardar = st.selectbox(
                            "Estado de Conciliación",
                            estados_lista,
                            index=idx_sugerido,
                            key="sel_estado_final_guardar_a"
                        )
                    with col_e2:
                        obs_guardar = st.text_area(
                            "Observaciones",
                            value=row_item['obs'] if row_item['obs'] else f"Ajuste manual: {recomendacion_msg}",
                            key="txt_observaciones_guardar_a"
                        )
                        
                    # Determine changes and links
                    original_fact_id = row_item['fact_afip_id']
                    original_banco_id = row_item['banco_id']
                    original_estado = row_item['estado'] if row_item['estado'] else estado_sugerido
                    original_obs = row_item['obs'] if row_item['obs'] else f"Ajuste manual: {recomendacion_msg}"
                    
                    has_changes_a = (
                        factura_vinculo_id != original_fact_id or
                        banco_vinculo_id != original_banco_id or
                        estado_final_guardar != original_estado or
                        obs_guardar != original_obs
                    )
                    has_links_a = (original_fact_id is not None or original_banco_id is not None)
                    
                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    with col_btn1:
                        if st.button("Guardar", type="primary", use_container_width=True, key="btn_save_a", disabled=not has_changes_a):
                            cursor.execute("SELECT id FROM conciliaciones WHERE prestacion_id = ?", (row_item['prest_id'],))
                            conc_res = cursor.fetchone()
                            
                            if conc_res:
                                cursor.execute("""
                                    UPDATE conciliaciones 
                                    SET factura_id = ?, movimiento_banco_id = ?, estado_final = ?, observaciones = ? 
                                    WHERE prestacion_id = ?
                                """, (factura_vinculo_id, banco_vinculo_id, estado_final_guardar, obs_guardar, row_item['prest_id']))
                            else:
                                cursor.execute("""
                                    INSERT INTO conciliaciones (prestacion_id, factura_id, movimiento_banco_id, estado_final, observaciones, mes_auditoria)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                """, (row_item['prest_id'], factura_vinculo_id, banco_vinculo_id, estado_final_guardar, obs_guardar, mes_trabajo))
                                
                            cursor.execute("UPDATE prestaciones SET estado_conciliacion = ? WHERE id = ?", (estado_final_guardar, row_item['prest_id']))
                            
                            # Retroalimentación inteligente de CUIT
                            if banco_vinculo_id and cuit:
                                cursor.execute("""
                                    UPDATE movimientos_banco
                                    SET cuit_hash_asociado = ?, cuit_txt_asociado = ?
                                    WHERE id = ? AND (cuit_hash_asociado IS NULL OR cuit_hash_asociado = '')
                                """, (c_hash, cuit, banco_vinculo_id))
                                
                            conn.commit()
                            st.success("¡Conciliación manual guardada con éxito!")
                            st.rerun()
                            
                    with col_btn2:
                        if st.button("Descartar cambios", type="secondary", use_container_width=True, key="btn_discard_a", disabled=not has_changes_a):
                            st.info("Cambios descartados.")
                            st.rerun()
                            
                    with col_btn3:
                        if st.button("Desvincular por completo", type="secondary", use_container_width=True, key="btn_unlink_a", disabled=not has_links_a):
                            cursor.execute("DELETE FROM conciliaciones WHERE prestacion_id = ?", (row_item['prest_id'],))
                            cursor.execute("UPDATE prestaciones SET estado_conciliacion = 'PENDIENTE_FACTURA' WHERE id = ?", (row_item['prest_id'],))
                            conn.commit()
                            st.success("¡Vínculos eliminados!")
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("👈 Selecciona una prestación válida en el listado izquierdo.")

    # ----------------------------------------------------
    # CAMINO B: COBROS BANCARIOS ➔ PRESTACIONES/FACTURAS
    # ----------------------------------------------------
    else:
        with col_maestro:
            st.markdown("#### 🏦 Depósitos del Banco")
            search_query = st.text_input("Buscar...", placeholder="Buscar...", key="search_banco_master", label_visibility="collapsed")
            
            # Filtros de estado directos (sin expander)
            st.markdown("<div style='font-size: 10px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;'>ESTADOS:</div>", unsafe_allow_html=True)
            col_fb1, col_fb2, col_fb3 = st.columns(3)
            with col_fb1:
                filtro_conc_b = st.checkbox("🟢 Concil.", value=False, key="maestro_fb_conc")
            with col_fb2:
                filtro_sin_id_b = st.checkbox("🟡 Sin Ident.", value=True, key="maestro_fb_sin_id")
            with col_fb3:
                filtro_disc_b = st.checkbox("🔴 Disc.", value=True, key="maestro_fb_disc")
                    
            est_filter = []
            if filtro_conc_b: est_filter.append("🟢 CONCILIADO")
            if filtro_sin_id_b: est_filter.append("🟡 SIN IDENTIFICAR")
            if filtro_disc_b: est_filter.append("🔴 DISCREPANCIA")
            
            # Cargar depósitos bancarios del periodo
            query_banco_master = """
                SELECT 
                    mb.id AS banco_id,
                    mb.fecha AS fecha,
                    mb.concepto AS concepto,
                    mb.detalle AS detalle,
                    mb.credito AS credito,
                    mb.cuit_txt_asociado AS cuit_txt,
                    mb.cuit_hash_asociado AS cuit_hash,
                    c.prestacion_id AS prest_id,
                    c.estado_final AS estado,
                    c.observaciones AS obs,
                    p.obra_social_nombre AS os,
                    p.paciente AS paciente
                FROM movimientos_banco mb
                LEFT JOIN conciliaciones c ON mb.id = c.movimiento_banco_id
                LEFT JOIN prestaciones p ON c.prestacion_id = p.id
                WHERE mb.mes_auditoria = ? AND mb.credito > 0 AND mb.debito = 0.0
            """
            df_banco = pd.read_sql_query(query_banco_master, conn, params=(mes_trabajo,))
            
            if not df_banco.empty:
                # Determinar estado
                def map_banco_state(row):
                    if pd.isna(row['prest_id']) or not row['estado']:
                        return '🟡 SIN IDENTIFICAR'
                    elif row['estado'] == 'CONCILIADO':
                        return '🟢 CONCILIADO'
                    elif row['estado'] == 'DISCREPANCIA':
                        return '🔴 DISCREPANCIA'
                    else:
                        return f"⚪ {row['estado']}"
                        
                df_banco['estado_display'] = df_banco.apply(map_banco_state, axis=1)
                
                # Filtrar
                filtered_df = df_banco
                if est_filter:
                    filtered_df = filtered_df[filtered_df['estado_display'].isin(est_filter)]
                if search_query:
                    sq_lower = search_query.lower()
                    filtered_df = filtered_df[
                        filtered_df['concepto'].str.lower().str.contains(sq_lower) |
                        filtered_df['detalle'].str.lower().str.contains(sq_lower) |
                        filtered_df['cuit_txt'].str.lower().str.contains(sq_lower)
                    ]
                    
                filtered_df = filtered_df.sort_values('banco_id', ascending=False)
                
                if not filtered_df.empty:
                    valid_ids = filtered_df['banco_id'].tolist()
                    if st.session_state.selected_banco_id not in valid_ids:
                        st.session_state.selected_banco_id = int(valid_ids[0])
                        
                    st.markdown('<div class="list-master-container">', unsafe_allow_html=True)
                    for _, row in filtered_df.iterrows():
                        b_id = int(row['banco_id'])
                        is_selected = (st.session_state.selected_banco_id == b_id)
                        
                        st_emoji = "🟢"
                        if "SIN IDENTIFICAR" in row['estado_display']: st_emoji = "🟡"
                        elif "DISCREPANCIA" in row['estado_display']: st_emoji = "🔴"
                        
                        concepto_str = row['concepto'] if row['concepto'] else ""
                        cuit_lbl = f" | CUIT: {row['cuit_txt']}" if row['cuit_txt'] else ""
                        btn_lbl = f"{st_emoji} {row['fecha']} — ${row['credito']:,.2f}\n🏦 {concepto_str}{cuit_lbl}"
                        
                        wrapper_class = "selected-button-wrapper" if is_selected else "normal-button-wrapper"
                        st.markdown(f'<div class="{wrapper_class}">', unsafe_allow_html=True)
                        if st.button(btn_lbl, key=f"b_btn_{b_id}"):
                            st.session_state.selected_banco_id = b_id
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.info("No hay items bancarios que coincidan con los filtros.")
            else:
                st.info("No hay depósitos bancarios para este período.")
                
        with col_detalle:
            st.markdown("#### 🔬 Ficha de Análisis y Conciliación")
            if st.session_state.selected_banco_id:
                # Cargar datos del depósito seleccionado con fechas para la línea de tiempo
                cursor.execute("""
                    SELECT 
                        mb.id AS banco_id,
                        mb.fecha AS fecha,
                        mb.concepto AS concepto,
                        mb.detalle AS detalle,
                        mb.credito AS credito,
                        mb.cuit_txt_asociado AS cuit_txt,
                        mb.cuit_hash_asociado AS cuit_hash,
                        c.prestacion_id AS prest_id,
                        c.estado_final AS estado,
                        c.observaciones AS obs,
                        p.obra_social_nombre AS os,
                        p.paciente AS paciente,
                        p.fecha_factura AS fecha_factura,
                        c.factura_id AS fact_afip_id,
                        f.fecha_emision AS afip_fecha
                    FROM movimientos_banco mb
                    LEFT JOIN conciliaciones c ON mb.id = c.movimiento_banco_id
                    LEFT JOIN prestaciones p ON c.prestacion_id = p.id
                    LEFT JOIN facturas f ON c.factura_id = f.comprobante_id
                    WHERE mb.id = ?
                """, (st.session_state.selected_banco_id,))
                row_banco = cursor.fetchone()
                
                if row_banco:
                    # Tarjeta 1: Detalles del Depósito Bancario
                    st.markdown('<div class="detail-card">', unsafe_allow_html=True)
                    st.markdown('<div class="detail-header">🏦 Detalles del Depósito Bancario</div>', unsafe_allow_html=True)
                    col_db1, col_db2 = st.columns(2)
                    with col_db1:
                        st.markdown('<div class="info-label">Fecha de Depósito</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="info-value">{row_banco["fecha"]}</div>', unsafe_allow_html=True)
                        st.markdown('<div class="info-label">Monto Acreditado</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="info-value" style="font-size: 16px; color: #10B981; font-weight: 700;">${row_banco["credito"]:,.2f}</div>', unsafe_allow_html=True)
                    with col_db2:
                        st.markdown('<div class="info-label">Concepto Bancario</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="info-value">{row_banco["concepto"]}</div>', unsafe_allow_html=True)
                        st.markdown('<div class="info-label">Detalle Extracto</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="info-value">{row_banco["detalle"] if row_banco["detalle"] else "Sin detalles"}</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Tarjeta Timeline: Línea de Tiempo del Ciclo Contable
                    timeline_html = generate_timeline_html(
                        row_banco['fecha_factura'] if row_banco['prest_id'] else None,
                        row_banco['afip_fecha'] if row_banco['prest_id'] else None,
                        row_banco['fecha']
                    )
                    st.markdown('<div class="detail-card timeline-card">', unsafe_allow_html=True)
                    st.markdown('<div class="detail-header">📅 Línea de Tiempo del Ciclo Contable (Escala 120 días)</div>', unsafe_allow_html=True)
                    st.markdown(timeline_html, unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Tarjeta 2: Detalles de la Prestación Asociada
                    st.markdown('<div class="detail-card">', unsafe_allow_html=True)
                    st.markdown('<div class="detail-header">📊 Prestación de Gestión Asociada (Vía 1)</div>', unsafe_allow_html=True)
                    
                    prestacion_vinculo_id = row_banco['prest_id']
                    if prestacion_vinculo_id:
                        col_p1, col_p2 = st.columns(2)
                        with col_p1:
                            st.markdown('<div class="info-label">ID Prestación</div>', unsafe_allow_html=True)
                            st.markdown(f'<div class="info-value">{prestacion_vinculo_id}</div>', unsafe_allow_html=True)
                            st.markdown('<div class="info-label">Obra Social</div>', unsafe_allow_html=True)
                            st.markdown(f'<div class="info-value">{row_banco["os"]}</div>', unsafe_allow_html=True)
                        with col_p2:
                            st.markdown('<div class="info-label">Paciente</div>', unsafe_allow_html=True)
                            st.markdown(f'<div class="info-value">{row_banco["paciente"]}</div>', unsafe_allow_html=True)
                            st.markdown('<div class="info-label">Factura AFIP Vinculada</div>', unsafe_allow_html=True)
                            st.markdown(f'<div class="info-value">{row_banco["fact_afip_id"] if row_banco["fact_afip_id"] else "Sin Factura AFIP"}</div>', unsafe_allow_html=True)
                    else:
                        st.warning("⚠️ Sin prestación ni factura asociada a este cobro.")
                        
                    # Buscador de Prestación
                    st.markdown("##### 🔍 Buscar Prestación / Factura en Gestión")
                    col_fp1, col_fp2 = st.columns(2)
                    with col_fp1:
                        buscar_texto_prest = st.text_input("Obra Social o Paciente (Ej: OSDE, Perez)", value="", placeholder="Filtrar prestaciones...", key="search_prest_text_b")
                    with col_fp2:
                        filtrar_por_monto_prest = st.checkbox("Filtrar por Importe Similar (±5%)", value=True, key="chk_filtrar_monto_prest_b")
                        
                    query_prest = """
                        SELECT p.id, p.obra_social_nombre, p.paciente, p.monto, p.periodo, p.factura_nro,
                               c.factura_id
                        FROM prestaciones p
                        LEFT JOIN conciliaciones c ON p.id = c.prestacion_id
                        WHERE (p.id NOT IN (SELECT prestacion_id FROM conciliaciones WHERE movimiento_banco_id != ? AND prestacion_id IS NOT NULL)
                               OR p.id = ?)
                    """
                    params_prest = [row_banco['banco_id'], prestacion_vinculo_id]
                    
                    if buscar_texto_prest:
                        query_prest += " AND (p.obra_social_nombre LIKE ? OR p.paciente LIKE ?)"
                        params_prest.extend([f"%{buscar_texto_prest}%", f"%{buscar_texto_prest}%"])
                    if filtrar_por_monto_prest:
                        monto_min = row_banco['credito'] * 0.95
                        monto_max = row_banco['credito'] * 1.05
                        query_prest += " AND p.monto BETWEEN ? AND ?"
                        params_prest.extend([monto_min, monto_max])
                        
                    query_prest += " ORDER BY ABS(p.monto - ?) ASC, p.periodo DESC LIMIT 100"
                    params_prest.append(row_banco['credito'])
                    
                    cursor.execute(query_prest, tuple(params_prest))
                    prest_cands = cursor.fetchall()
                    
                    prest_options = { "Ninguna / Desvincular": None }
                    default_prest_key = "Ninguna / Desvincular"
                    
                    for p in prest_cands:
                        p_id = p['id']
                        f_nro_str = f" | Factura AFIP: {p['factura_id']}" if p['factura_id'] else " | Sin Factura AFIP"
                        p_text = f"ID: {p_id} | {p['obra_social_nombre']} | Paciente: {p['paciente']} | Monto: ${p['monto']:,.2f} | Período: {p['periodo']}{f_nro_str}"
                        prest_options[p_text] = p_id
                        if prestacion_vinculo_id == p_id:
                            default_prest_key = p_text
                            
                    if prestacion_vinculo_id and default_prest_key == "Ninguna / Desvincular":
                        # Forzar la prestación actual
                        cursor.execute("SELECT id, obra_social_nombre, paciente, monto, periodo FROM prestaciones WHERE id = ?", (prestacion_vinculo_id,))
                        curr_p = cursor.fetchone()
                        if curr_p:
                            p_text = f"ID: {curr_p['id']} | {curr_p['obra_social_nombre']} | Paciente: {curr_p['paciente']} | Monto: ${curr_p['monto']:,.2f} | Período: {curr_p['periodo']} (Vinculado actualmente)"
                            prest_options[p_text] = prestacion_vinculo_id
                            default_prest_key = p_text
                            
                    selected_prest_text = st.selectbox(
                        "Asociar Prestación", 
                        list(prest_options.keys()), 
                        index=list(prest_options.keys()).index(default_prest_key),
                        key="sel_prest_vinculo_b"
                    )
                    prestacion_vinculo_id = prest_options[selected_prest_text]
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Tarjeta 3: Estado y Guardar
                    st.markdown('<div class="detail-card">', unsafe_allow_html=True)
                    st.markdown('<div class="detail-header">⚙️ Conciliación y Acciones</div>', unsafe_allow_html=True)
                    
                    factura_de_prestacion = None
                    monto_prestacion_elegida = None
                    obra_social_nombre_elegido = None
                    if prestacion_vinculo_id:
                        cursor.execute("SELECT obra_social_nombre, monto FROM prestaciones WHERE id = ?", (prestacion_vinculo_id,))
                        res_p_info = cursor.fetchone()
                        monto_prestacion_elegida = res_p_info['monto'] if res_p_info else None
                        obra_social_nombre_elegido = res_p_info['obra_social_nombre'] if res_p_info else None
                        
                        cursor.execute("SELECT factura_id FROM conciliaciones WHERE prestacion_id = ?", (prestacion_vinculo_id,))
                        res_p_conc = cursor.fetchone()
                        factura_de_prestacion = res_p_conc['factura_id'] if res_p_conc else None
                        
                    estado_sugerido = "PENDIENTE_COBRO"
                    recomendacion_msg = ""
                    
                    if prestacion_vinculo_id:
                        if factura_de_prestacion:
                            cursor.execute("SELECT monto_total FROM facturas WHERE comprobante_id = ?", (factura_de_prestacion,))
                            res_f_info = cursor.fetchone()
                            monto_factura = res_f_info['monto_total'] if res_f_info else None
                            
                            if abs(row_banco['credito'] - monto_prestacion_elegida) < 0.01 and abs(row_banco['credito'] - monto_factura) < 0.01:
                                estado_sugerido = "CONCILIADO"
                                recomendacion_msg = "🟢 Conciliación completa: Prestación, Factura de AFIP y Depósito coinciden exactamente."
                            else:
                                estado_sugerido = "DISCREPANCIA"
                                recomendacion_msg = f"🔴 Discrepancia de montos: Prestación (${monto_prestacion_elegida:,.2f}) vs Factura (${monto_factura:,.2f}) vs Banco (${row_banco['credito']:,.2f})."
                        else:
                            estado_sugerido = "DISCREPANCIA"
                            recomendacion_msg = "🔴 Depósito bancario vinculado a una prestación que no posee factura emitida en AFIP (Discrepancia de facturación)."
                    else:
                        estado_sugerido = "PENDIENTE_COBRO"
                        recomendacion_msg = "🟡 Depósito bancario sin identificar. No se ha asociado ninguna prestación de gestión."
                        
                    st.info(recomendacion_msg)
                    
                    estados_lista = ["CONCILIADO", "PENDIENTE_FACTURA", "PENDIENTE_COBRO", "DISCREPANCIA"]
                    idx_sugerido = estados_lista.index(estado_sugerido)
                    
                    col_e1, col_e2 = st.columns([1.2, 2.8])
                    with col_e1:
                        estado_final_guardar = st.selectbox(
                            "Estado de Conciliación",
                            estados_lista,
                            index=idx_sugerido,
                            key="sel_estado_final_guardar_b"
                        )
                    with col_e2:
                        obs_guardar = st.text_area(
                            "Observaciones",
                            value=row_banco['obs'] if row_banco['obs'] else f"Ajuste manual: {recomendacion_msg}",
                            key="txt_observaciones_guardar_b"
                        )
                        
                    # Determine changes and links
                    original_prest_id = row_banco['prest_id']
                    original_estado = row_banco['estado'] if row_banco['estado'] else estado_sugerido
                    original_obs = row_banco['obs'] if row_banco['obs'] else f"Ajuste manual: {recomendacion_msg}"
                    
                    has_changes_b = (
                        prestacion_vinculo_id != original_prest_id or
                        estado_final_guardar != original_estado or
                        obs_guardar != original_obs
                    )
                    has_links_b = (original_prest_id is not None)
                    
                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    with col_btn1:
                        if st.button("Guardar", type="primary", use_container_width=True, key="btn_save_b", disabled=not has_changes_b):
                            if prestacion_vinculo_id:
                                # Buscar si ya existe la conciliación
                                cursor.execute("SELECT id FROM conciliaciones WHERE prestacion_id = ?", (prestacion_vinculo_id,))
                                conc_res = cursor.fetchone()
                                
                                # Obtener factura vinculada actual si ya estaba
                                cursor.execute("SELECT factura_id FROM conciliaciones WHERE prestacion_id = ?", (prestacion_vinculo_id,))
                                f_res = cursor.fetchone()
                                fact_id_save = f_res['factura_id'] if f_res else None
                                
                                if conc_res:
                                    cursor.execute("""
                                        UPDATE conciliaciones 
                                        SET movimiento_banco_id = ?, estado_final = ?, observaciones = ? 
                                        WHERE prestacion_id = ?
                                    """, (row_banco['banco_id'], estado_final_guardar, obs_guardar, prestacion_vinculo_id))
                                else:
                                    cursor.execute("""
                                        INSERT INTO conciliaciones (prestacion_id, factura_id, movimiento_banco_id, estado_final, observaciones, mes_auditoria)
                                        VALUES (?, ?, ?, ?, ?, ?)
                                    """, (prestacion_vinculo_id, fact_id_save, row_banco['banco_id'], estado_final_guardar, obs_guardar, mes_trabajo))
                                    
                                cursor.execute("UPDATE prestaciones SET estado_conciliacion = ? WHERE id = ?", (estado_final_guardar, prestacion_vinculo_id))
                                
                                # Retroalimentación de CUIT
                                if obra_social_nombre_elegido:
                                    cuit_dest = get_cuit_for_obra_social(obra_social_nombre_elegido)
                                    if cuit_dest:
                                        c_hash_dest = hash_cuit(cuit_dest)
                                        cursor.execute("""
                                            UPDATE movimientos_banco
                                            SET cuit_hash_asociado = ?, cuit_txt_asociado = ?
                                            WHERE id = ? AND (cuit_hash_asociado IS NULL OR cuit_hash_asociado = '')
                                        """, (c_hash_dest, cuit_dest, row_banco['banco_id']))
                                        
                                # Limpiar el vínculo de banco en cualquier otra conciliación que lo tuviera (para asegurar unicidad)
                                cursor.execute("""
                                    UPDATE conciliaciones
                                    SET movimiento_banco_id = NULL, estado_final = 'PENDIENTE_COBRO'
                                    WHERE movimiento_banco_id = ? AND prestacion_id != ?
                                """, (row_banco['banco_id'], prestacion_vinculo_id))
                            else:
                                # Desasociar el banco de la conciliación anterior
                                cursor.execute("""
                                    UPDATE conciliaciones
                                    SET movimiento_banco_id = NULL, estado_final = 'PENDIENTE_COBRO'
                                    WHERE movimiento_banco_id = ?
                                """, (row_banco['banco_id'],))
                                
                            conn.commit()
                            st.success("¡Vinculación bancaria guardada con éxito!")
                            st.rerun()
                            
                    with col_btn2:
                        if st.button("Descartar cambios", type="secondary", use_container_width=True, key="btn_discard_b", disabled=not has_changes_b):
                            st.info("Cambios descartados.")
                            st.rerun()
                            
                    with col_btn3:
                        if st.button("Desvincular por completo", type="secondary", use_container_width=True, key="btn_unlink_b", disabled=not has_links_b):
                            cursor.execute("""
                                UPDATE conciliaciones
                                SET movimiento_banco_id = NULL, estado_final = 'PENDIENTE_COBRO'
                                WHERE movimiento_banco_id = ?
                            """, (row_banco['banco_id'],))
                            conn.commit()
                            st.success("¡Vínculos eliminados!")
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("👈 Selecciona un depósito bancario válido en el listado izquierdo.")
                
    conn.close()


# PAGE 3: BUSCADOR DE CLIENTES
def show_buscador():
    st.subheader("Buscador e Historial de Clientes")
    st.markdown("Consulta la ficha histórica y los movimientos consolidados de cada cliente o de una Obra Social.")
    
    # 1. Inyectar estilos CSS avanzados para maestro-detalle de Clientes
    st.markdown("""
    <style>
        .list-master-container {
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-height: 700px;
            overflow-y: auto;
            padding-right: 5px;
        }
        /* Botones como tarjetas - Compatibles con la estructura de containers de Streamlit */
        div.stElementContainer:has(.selected-button-wrapper) + div.stElementContainer button,
        div.stElementContainer:has(.normal-button-wrapper) + div.stElementContainer button {
            text-align: left !important;
            display: block !important;
            width: 100% !important;
            color: var(--text-color) !important;
            border-radius: 10px !important;
            padding: 12px 14px !important;
            font-size: 13px !important;
            line-height: 1.4 !important;
            transition: all 0.2s ease-in-out !important;
            border: 1px solid rgba(128, 128, 128, 0.15) !important;
            white-space: pre-line !important;
        }
        
        div.stElementContainer:has(.normal-button-wrapper) + div.stElementContainer button {
            background-color: var(--secondary-background-color) !important;
        }
        
        div.stElementContainer:has(.normal-button-wrapper) + div.stElementContainer button:hover {
            background-color: rgba(128, 128, 128, 0.1) !important;
            border-color: #3B82F6 !important;
            transform: translateX(2px) !important;
        }
        
        div.stElementContainer:has(.selected-button-wrapper) + div.stElementContainer button {
            background-color: rgba(59, 130, 246, 0.08) !important;
            border: 1.5px solid #3B82F6 !important;
            border-left: 6px solid #3B82F6 !important;
            font-weight: 700 !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Usaremos una interfaz maestro/detalle con dos columnas principales
    col_master, col_detail = st.columns([1.5, 2.5], gap="large")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Cargar todos los clientes para mostrar en el maestro
    cursor.execute("SELECT cuit_hash, cuit_encrypted, nombre_razon_social_encrypted, categoria FROM clientes")
    clientes_raw = cursor.fetchall()
    
    clientes_list = []
    for c in clientes_raw:
        cuit = decrypt_data(c['cuit_encrypted'])
        nombre = decrypt_data(c['nombre_razon_social_encrypted'])
        
        # Mapear nombre corto legible si es genérico o 'Cliente Identificado Banco'
        cuit_clean = "".join(filter(str.isdigit, cuit))
        display_name = nombre
        if not nombre or nombre.strip() == "" or nombre == "Cliente Identificado Banco":
            for k, v in OS_CUIT_MAP.items():
                if v == cuit_clean:
                    display_name = k
                    break
                    
        clientes_list.append({
            'Hash': c['cuit_hash'],
            'CUIT/CUIL': cuit,
            'Cliente / Obra Social': display_name,
            'Categoría': c['categoria'] or "Sin Categoría"
        })
        
    # Columna 1: Maestro (Buscador y Selección de Clientes)
    with col_master:
        st.markdown("### 🏢 Maestro de Clientes")
        
        # Filtro de búsqueda
        search_query = st.text_input("🔍 Buscar por Nombre o CUIT", key="master_search_input", placeholder="Escriba para filtrar...")
        
        # Filtrar la lista en base a la búsqueda
        filtered_list = []
        for c in clientes_list:
            if not search_query or search_query.lower() in c['CUIT/CUIL'] or search_query.lower() in c['Cliente / Obra Social'].lower():
                filtered_list.append(c)
                
        # Inicializar seleccion por defecto en la sesión si no está establecida o si el cliente seleccionado ya no está en los resultados filtrados
        valid_hashes = [c['Hash'] for c in filtered_list]
        if "selected_client_hash" not in st.session_state or st.session_state.selected_client_hash not in valid_hashes:
            if valid_hashes:
                st.session_state.selected_client_hash = valid_hashes[0]
            else:
                st.session_state.selected_client_hash = None
                
        if filtered_list:
            with st.container(height=650):
                for c in filtered_list:
                    c_hash = c['Hash']
                    is_selected = (st.session_state.selected_client_hash == c_hash)
                    
                    # Tag de categoría dinámico y emoji
                    cat_emoji = "🟢" if "Obra Social" in c['Categoría'] else "🔵"
                    btn_lbl = f"🏢 {c['Cliente / Obra Social']}\nCUIT: {c['CUIT/CUIL']} | {cat_emoji} {c['Categoría']}"
                    
                    wrapper_class = "selected-button-wrapper" if is_selected else "normal-button-wrapper"
                    st.markdown(f'<div class="{wrapper_class}">', unsafe_allow_html=True)
                    if st.button(btn_lbl, key=f"c_btn_{c_hash}"):
                        st.session_state.selected_client_hash = c_hash
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("No se encontraron clientes.")
            
    # Columna 2: Detalle (Ficha detallada, Gráfico de descalce temporal y tres columnas de datos)
    with col_detail:
        if st.session_state.selected_client_hash and filtered_list:
            client_info_list = [c for c in filtered_list if c['Hash'] == st.session_state.selected_client_hash]
            if client_info_list:
                client_info = client_info_list[0]
                selected_name = client_info['Cliente / Obra Social']
                selected_hash = client_info['Hash']
                selected_cuit = client_info['CUIT/CUIL']
                selected_categoria = client_info['Categoría']
            
            # Encabezado Premium de la Ficha del Cliente
            tag_color = "#10B981" if "Obra Social" in selected_categoria else "#3B82F6"
            st.markdown(
                f"""
                <div style="background-color: var(--secondary-background-color); padding: 18px 24px; border-radius: 12px; border: 1px solid rgba(128,128,128,0.15); margin-bottom: 20px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                        <h2 style="margin: 0; color: var(--text-color); font-weight: 800; font-size: 24px;">{selected_name}</h2>
                        <span style="background-color: {tag_color}; color: white; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">
                            {selected_categoria}
                        </span>
                    </div>
                    <div style="margin-top: 10px; font-size: 14px; color: var(--text-color); opacity: 0.8; display: flex; gap: 20px;">
                        <div><strong>CUIT/CUIL:</strong> {selected_cuit}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # --- BUSCAR PRESTACIONES ASOCIADAS (cruce por CUIT y nombre aproximado) ---
            # 1. Buscar nombres cortos de la obra social mapeados al CUIT
            matching_os_names = [k for k, v in OS_CUIT_MAP.items() if v == selected_cuit]
            all_search_terms = {selected_name.upper()}
            for name in matching_os_names:
                all_search_terms.add(name.upper())
                
            conditions = []
            params = []
            for term in all_search_terms:
                conditions.append("UPPER(obra_social_nombre) = ?")
                params.append(term)
                conditions.append("obra_social_nombre LIKE ?")
                params.append(f"%{term}%")
                conditions.append("? LIKE '%' || obra_social_nombre || '%'")
                params.append(term)
                
            # Agregar el fallback original por las primeras 5 letras del nombre
            conditions.append("obra_social_nombre LIKE ?")
            params.append(f"%{selected_name[:5]}%")
            
            sql_prest = """
                SELECT id, paciente, fecha_factura, periodo, monto, factura_nro, estado_conciliacion, mes_auditoria
                FROM prestaciones
                WHERE """ + " OR ".join(conditions)
                
            cursor.execute(sql_prest, tuple(params))
            prest_raw = cursor.fetchall()
            
            # Deduplicar en Python
            seen_ids = set()
            prest_asoc = []
            for p in prest_raw:
                if p['id'] not in seen_ids:
                    seen_ids.add(p['id'])
                    prest_asoc.append(p)
            
            # --- BUSCAR FACTURAS Y BANCO ---
            cursor.execute("""
                SELECT comprobante_id, fecha_emision, monto_total, tipo_comprobante, estado, mes_auditoria
                FROM facturas
                WHERE cuit_hash = ?
            """, (selected_hash,))
            fact_asoc = cursor.fetchall()
            
            cursor.execute("""
                SELECT id, fecha, concepto, detalle, credito, mes_auditoria
                FROM movimientos_banco
                WHERE cuit_hash_asociado = ?
            """, (selected_hash,))
            banco_asoc = cursor.fetchall()
            
            # Buscar asociaciones en conciliaciones para relacionar qué cierra con qué
            prest_ids = [p['id'] for p in prest_asoc]
            fact_links = {}
            banco_links = {}
            if prest_ids:
                placeholders = ",".join("?" for _ in prest_ids)
                cursor.execute(f"""
                    SELECT prestacion_id, factura_id, movimiento_banco_id, estado_final
                    FROM conciliaciones
                    WHERE prestacion_id IN ({placeholders})
                """, tuple(prest_ids))
                concil_rows = cursor.fetchall()
                
                for r in concil_rows:
                    p_id = r['prestacion_id']
                    f_id = r['factura_id']
                    b_id = r['movimiento_banco_id']
                    
                    p_item = next((x for x in prest_asoc if x['id'] == p_id), None)
                    p_desc = f"{p_item['paciente']} (${p_item['monto']:,.2f})" if p_item else f"ID: {p_id}"
                    
                    if f_id:
                        if f_id not in fact_links:
                            fact_links[f_id] = []
                        if p_desc not in fact_links[f_id]:
                            fact_links[f_id].append(p_desc)
                    if b_id:
                        if b_id not in banco_links:
                            banco_links[b_id] = []
                        if p_desc not in banco_links[b_id]:
                            banco_links[b_id].append(p_desc)

            # --- CÁLCULO DE MÉTRICAS Y DELAY ---
            total_monto = 0.0
            conciliado_monto = 0.0
            faltante_normal = 0.0
            faltante_atrasado = 0.0
            
            def get_month_difference(mes_auditoria_prest, mes_auditoria_actual):
                try:
                    y_p, m_p = map(int, mes_auditoria_prest.split('-'))
                    y_a, m_a = map(int, mes_auditoria_actual.split('-'))
                    return (y_a - y_p) * 12 + (m_a - m_p)
                except Exception:
                    return 0
            
            for p in prest_asoc:
                monto = p['monto']
                total_monto += monto
                if p['estado_conciliacion'] == 'CONCILIADO':
                    conciliado_monto += monto
                else:
                    diff_meses = get_month_difference(p['mes_auditoria'], st.session_state.mes_trabajo)
                    if diff_meses <= 3:
                        # Dentro de lo normal (menor o igual a 90 días)
                        faltante_normal += monto
                    else:
                        # Fuera de lo normal (atraso crítico)
                        faltante_atrasado += monto
                        
            # Mostrar Tarjetas de KPIs Premium (Visualización del descalce)
            st.markdown(
                f"""
                <div style="display: flex; gap: 15px; margin-bottom: 25px; flex-wrap: wrap; justify-content: space-between;">
                    <div class="metric-card" style="flex: 1; min-width: 180px; margin-bottom: 0px; border-left: 5px solid #475569; padding: 18px 20px;">
                        <div class="metric-title">Total Prestado</div>
                        <div class="metric-value" style="font-size: 24px;">${total_monto:,.2f}</div>
                        <div class="metric-sub" style="color: gray; font-size: 11px;">100% prestaciones</div>
                    </div>
                    <div class="metric-card success" style="flex: 1; min-width: 180px; margin-bottom: 0px; padding: 18px 20px;">
                        <div class="metric-title">Conciliado (OK)</div>
                        <div class="metric-value" style="color: #10B981; font-size: 24px;">${conciliado_monto:,.2f}</div>
                        <div class="metric-sub" style="color: #10B981; font-weight: 600; font-size: 11px;">{(conciliado_monto/total_monto*100) if total_monto else 0:.1f}% del total</div>
                    </div>
                    <div class="metric-card warning" style="flex: 1; min-width: 180px; margin-bottom: 0px; padding: 18px 20px;">
                        <div class="metric-title">Faltante Normal</div>
                        <div class="metric-value" style="color: #F59E0B; font-size: 24px;">${faltante_normal:,.2f}</div>
                        <div class="metric-sub" style="color: #F59E0B; font-weight: 600; font-size: 11px;">{(faltante_normal/total_monto*100) if total_monto else 0:.1f}% (&le; 90 días)</div>
                    </div>
                    <div class="metric-card danger" style="flex: 1; min-width: 180px; margin-bottom: 0px; padding: 18px 20px;">
                        <div class="metric-title">Atraso Fuera Rango</div>
                        <div class="metric-value" style="color: #EF4444; font-size: 24px;">${faltante_atrasado:,.2f}</div>
                        <div class="metric-sub" style="color: #EF4444; font-weight: 600; font-size: 11px;">{(faltante_atrasado/total_monto*100) if total_monto else 0:.1f}% (&gt; 90 días)</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # --- GRÁFICO DE ANÁLISIS DE CONCILIACIÓN ---
            if total_monto > 0:
                st.markdown("#### 📊 Distribución de Cobro y Delay Temporal")
                
                # Precomputar porcentajes y formatear strings en Python para evitar KeyErrors
                conciliado_pct = (conciliado_monto / total_monto * 100)
                faltante_normal_pct = (faltante_normal / total_monto * 100)
                faltante_atrasado_pct = (faltante_atrasado / total_monto * 100)
                
                fig = go.Figure()
                
                # Barra 1: Total Prestado (100%)
                fig.add_trace(go.Bar(
                    y=['Total Prestado'],
                    x=[total_monto],
                    name='Total Prestado (100%)',
                    orientation='h',
                    marker=dict(color='#475569'),
                    hovertemplate=f'Total: ${total_monto:,.2f} (100%)<extra></extra>'
                ))
                
                # Barra 2: Conciliado (OK)
                fig.add_trace(go.Bar(
                    y=['Conciliado'],
                    x=[conciliado_monto],
                    name='Conciliado (OK)',
                    orientation='h',
                    marker=dict(color='#10B981'),
                    hovertemplate=f'Conciliado: ${conciliado_monto:,.2f} ({conciliado_pct:.1f}%)<extra></extra>'
                ))
                
                # Barra 3: Faltante Stacked (Normal + Atrasado)
                fig.add_trace(go.Bar(
                    y=['Faltante'],
                    x=[faltante_normal],
                    name='Faltante (Delay Normal <= 90d)',
                    orientation='h',
                    marker=dict(color='#F59E0B'),
                    hovertemplate=f'Faltante Normal: ${faltante_normal:,.2f} ({faltante_normal_pct:.1f}%)<extra></extra>'
                ))
                
                fig.add_trace(go.Bar(
                    y=['Faltante'],
                    x=[faltante_atrasado],
                    name='Atraso Crítico (> 90d)',
                    orientation='h',
                    marker=dict(color='#EF4444'),
                    hovertemplate=f'Atraso Crítico: ${faltante_atrasado:,.2f} ({faltante_atrasado_pct:.1f}%)<extra></extra>'
                ))
                
                fig.update_layout(
                    barmode='stack',
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(
                        showgrid=True,
                        gridcolor='rgba(128,128,128,0.15)',
                        title="Monto ($)",
                        tickformat="$,.2f"
                    ),
                    yaxis=dict(autorange="reversed"),
                    margin=dict(l=140, r=20, t=10, b=10),
                    height=180,
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.1,
                        xanchor="center",
                        x=0.5
                    )
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            else:
                st.info("ℹ️ No hay prestaciones registradas para este cliente. No se puede generar el gráfico de delay temporal.")
                
            # --- BALANZA DE SALDOS (EQUILIBRIO DE CUENTAS) ---
            st.markdown("<hr style='margin-top: 15px; margin-bottom: 20px; border: 0; border-top: 1px solid rgba(128,128,128,0.15);'>", unsafe_allow_html=True)
            st.markdown("#### ⚖️ Balance del Ciclo de Cuentas (Equilibrio)")
            
            total_prestado = total_monto
            total_facturado = sum(f['monto_total'] for f in fact_asoc if str(f['estado']).upper() == 'ACTIVO')
            total_cobrado = sum(b['credito'] for b in banco_asoc)
            
            facturado_vs_prestado = total_facturado - total_prestado
            cobrado_vs_facturado = total_cobrado - total_facturado
            descalce_total = total_cobrado - total_prestado
            
            bal_col1, bal_col2, bal_col3 = st.columns(3)
            with bal_col1:
                st.markdown(f"""
                <div style="background-color: var(--secondary-background-color); padding: 15px; border-radius: 8px; border: 1px solid rgba(128,128,128,0.15); text-align: center;">
                    <div style="font-size: 11px; opacity: 0.6; font-weight: 700; text-transform: uppercase;">1. Prestado vs Facturado</div>
                    <div style="font-size: 20px; font-weight: 800; color: {'#10B981' if abs(facturado_vs_prestado) < 0.01 else '#EF4444' if facturado_vs_prestado < 0 else '#F59E0B'};">
                        ${facturado_vs_prestado:+,.2f}
                    </div>
                    <div style="font-size: 11px; color: gray; margin-top: 5px;">
                        { 'Facturación al día' if abs(facturado_vs_prestado) < 0.01 else 'Falta facturar' if facturado_vs_prestado < 0 else 'Sobrefacturación / NC pendiente' }
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            with bal_col2:
                st.markdown(f"""
                <div style="background-color: var(--secondary-background-color); padding: 15px; border-radius: 8px; border: 1px solid rgba(128,128,128,0.15); text-align: center;">
                    <div style="font-size: 11px; opacity: 0.6; font-weight: 700; text-transform: uppercase;">2. Facturado vs Cobrado</div>
                    <div style="font-size: 20px; font-weight: 800; color: {'#10B981' if abs(cobrado_vs_facturado) < 0.01 else '#EF4444' if cobrado_vs_facturado < 0 else '#F59E0B'};">
                        ${cobrado_vs_facturado:+,.2f}
                    </div>
                    <div style="font-size: 11px; color: gray; margin-top: 5px;">
                        { 'Cobros al día' if abs(cobrado_vs_facturado) < 0.01 else 'Pendiente de cobro' if cobrado_vs_facturado < 0 else 'Cobros sin facturar / Anticipos' }
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            with bal_col3:
                st.markdown(f"""
                <div style="background-color: var(--secondary-background-color); padding: 15px; border-radius: 8px; border: 1px solid rgba(128,128,128,0.15); text-align: center;">
                    <div style="font-size: 11px; opacity: 0.6; font-weight: 700; text-transform: uppercase;">3. Descalce General (Banco vs Excel)</div>
                    <div style="font-size: 20px; font-weight: 800; color: {'#10B981' if abs(descalce_total) < 0.01 else '#EF4444' if descalce_total < 0 else '#F59E0B'};">
                        ${descalce_total:+,.2f}
                    </div>
                    <div style="font-size: 11px; color: gray; margin-top: 5px;">
                        { 'Ciclo cerrado' if abs(descalce_total) < 0.01 else 'Pendiente general' if descalce_total < 0 else 'Excedente de cobro' }
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # --- DETALLE DE TRES COLUMNAS (Prestaciones, Facturas, Banco) ---
            st.markdown("<hr style='margin-top: 15px; margin-bottom: 20px; border: 0; border-top: 1px solid rgba(128,128,128,0.15);'>", unsafe_allow_html=True)
            
            col_a, col_b, col_c = st.columns(3)
            
            status_map = {
                'CONCILIADO': '🟢 CONCILIADO',
                'PENDIENTE_FACTURA': '🔵 PENDIENTE FACTURA',
                'PENDIENTE_COBRO': '🟡 PENDIENTE COBRO',
                'DISCREPANCIA': '🔴 DISCREPANCIA'
            }
            
            with col_a:
                st.markdown("#### 📋 Prestaciones de Gestión")
                if prest_asoc:
                    p_data = [{
                        'Paciente': p['paciente'],
                        'Periodo': get_period_display_name(p['periodo'], p['mes_auditoria']),
                        'Monto': p['monto'],
                        'Factura': p['factura_nro'] if p['factura_nro'] else "-",
                        'Estado': status_map.get(p['estado_conciliacion'], p['estado_conciliacion'])
                    } for p in prest_asoc]
                    df_p = pd.DataFrame(p_data)
                    df_p = df_p.sort_values('Periodo')
                    
                    st.dataframe(
                        df_p,
                        column_config={
                            "Monto": st.column_config.NumberColumn("Monto", format="$%,.2f")
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("Sin prestaciones registradas.")
                    
            with col_b:
                st.markdown("#### 📄 Facturas Emitidas (AFIP)")
                if fact_asoc:
                    f_data = []
                    for f in fact_asoc:
                        f_id = f['comprobante_id']
                        asoc_list = fact_links.get(f_id, [])
                        f_data.append({
                            'Comprobante': f_id,
                            'Fecha': f['fecha_emision'],
                            'Monto': f['monto_total'],
                            'Estado': f"🟢 {str(f['estado']).upper()}" if str(f['estado']).upper() == 'ACTIVO' else f"🔴 {str(f['estado']).upper()}",
                            'Vinculado a': ", ".join(asoc_list) if asoc_list else "Sin vincular"
                        })
                    df_f = pd.DataFrame(f_data)
                    df_f = df_f.sort_values('Fecha', ascending=False)
                    
                    st.dataframe(
                        df_f,
                        column_config={
                            "Monto": st.column_config.NumberColumn("Monto", format="$%,.2f")
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("Sin facturas registradas en AFIP.")
                    
            with col_c:
                st.markdown("#### 🏦 Depósitos Recibidos (Banco)")
                if banco_asoc:
                    b_data = []
                    for b in banco_asoc:
                        b_id = b['id']
                        asoc_list = banco_links.get(b_id, [])
                        b_data.append({
                            'Fecha': b['fecha'],
                            'Detalle': b['concepto'] if b['concepto'] else b['detalle'],
                            'Monto': b['credito'],
                            'Vinculado a': ", ".join(asoc_list) if asoc_list else "Sin vincular"
                        })
                    df_b = pd.DataFrame(b_data)
                    df_b = df_b.sort_values('Fecha', ascending=False)
                    
                    st.dataframe(
                        df_b,
                        column_config={
                            "Monto": st.column_config.NumberColumn("Monto", format="$%,.2f")
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("Sin depósitos bancarios identificados.")
        else:
            st.info("Seleccione un cliente en el panel izquierdo para ver su historial detallado.")
            
    conn.close()


# PAGE 4: CARGA E IMPORTACIÓN
def show_importacion():
    if st.session_state.role != 'auditor':
        st.error("Acceso denegado. Esta página es exclusiva para Auditores.")
        st.stop()
    st.subheader(f"Carga e Importación de Archivos — {format_period(st.session_state.mes_trabajo)}")
    st.markdown("Sube los archivos correspondientes al período seleccionado para ejecutar el motor de conciliación.")
    
    mes_trabajo = st.session_state.mes_trabajo
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 1. Planilla de Prestaciones (Excel)")
        file_prest = st.file_uploader("Subir Excel de Prestaciones", type=["xlsx", "xls"], key="prest")
        
    with col2:
        st.markdown("#### 2. Facturación AFIP (VENTAS.txt)")
        file_afip = st.file_uploader("Subir archivo VENTAS.txt de AFIP/ARCA", type=["txt"], key="afip")
        
    with col3:
        st.markdown("#### 3. Extracto Bancario (Excel)")
        file_banco = st.file_uploader("Subir Excel de Movimientos de Banco Supervielle", type=["xlsx", "xls"], key="banco")
        
    st.markdown("---")
    
    if st.button("Procesar Archivos Subidos", use_container_width=True, type="primary"):
        temp_dir = "temp_uploads"
        os.makedirs(temp_dir, exist_ok=True)
        
        has_processed = False
        
        # 1. Cargar Prestaciones
        if file_prest:
            p_path = os.path.join(temp_dir, f"prest_{mes_trabajo}.xlsx")
            with open(p_path, "wb") as f:
                f.write(file_prest.getvalue())
            count_p = load_excel_prestaciones(p_path, mes_trabajo)
            st.success(f"Cargadas {count_p} prestaciones de gestión.")
            has_processed = True
            
        # 2. Cargar Facturas AFIP
        if file_afip:
            a_path = os.path.join(temp_dir, f"ventas_{mes_trabajo}.txt")
            with open(a_path, "wb") as f:
                f.write(file_afip.getvalue())
            count_a = load_afip_ventas(a_path, mes_trabajo)
            st.success(f"Cargadas {count_a} facturas de AFIP.")
            has_processed = True
            
        # 3. Cargar Banco
        if file_banco:
            b_path = os.path.join(temp_dir, f"banco_{mes_trabajo}.xlsx")
            with open(b_path, "wb") as f:
                f.write(file_banco.getvalue())
            count_b = load_excel_banco(b_path, mes_trabajo)
            st.success(f"Cargados {count_b} movimientos bancarios.")
            has_processed = True
            
        if has_processed:
            with st.spinner("Ejecutando algoritmo de conciliación de tres vías para el período y meses previos..."):
                # Obtener los 3 meses anteriores para re-evaluar la conciliación
                year, month = map(int, mes_trabajo.split('-'))
                meses_a_conciliar = []
                for i in range(3, -1, -1):
                    m = month - i
                    y = year
                    if m <= 0:
                        m += 12
                        y -= 1
                    meses_a_conciliar.append(f"{y:04d}-{m:02d}")
                
                # Ejecutar en orden cronológico para propagar los cobros
                for m in meses_a_conciliar:
                    res_c = run_conciliacion(m)
                    
            st.success(f"¡Procesamiento masivo completado! Para {format_period(mes_trabajo)}: Conciliados: {res_c['conciliados']} | Pendientes de Factura: {res_c['pendientes_factura']} | Pendientes de Cobro: {res_c['pendientes_cobro']} | Discrepancias: {res_c['discrepancias']}")
        else:
            st.warning("Sube al menos un archivo para poder procesar.")


# PAGE 5: REPORTES & EXPORTAR
def show_reportes():
    st.subheader(f"Exportar Reportes Contables — {format_period(st.session_state.mes_trabajo)}")
    st.markdown("Genera el reporte consolidado de conciliación de tres vías con colores suaves y formato condicional.")
    
    mes_trabajo = st.session_state.mes_trabajo
    
    with st.container(border=True):
        st.markdown(f"#### Resumen de Exportación: {mes_trabajo}")
        st.markdown("Al hacer clic en generar, compilaremos todas las prestaciones conciliadas y descalces detectados del período y daremos un enlace de descarga en Excel.")
        
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        if st.button("Generar Reporte Excel", type="primary", use_container_width=True):
            with st.spinner("Compilando datos y aplicando formatos..."):
                excel_data = generate_excel_report(mes_trabajo)
            
            st.success("¡Reporte Excel compilado y formateado con éxito!")
            st.download_button(
                label="📥 Descargar Reporte Excel",
                data=excel_data,
                file_name=f"Auditoria_AMEM_{mes_trabajo}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )


# --- NAVEGACIÓN Y CONFIGURACIÓN GLOBAL ---

# 1. Registrar las páginas con la navegación nativa de Streamlit 1.58+
page_dashboard = st.Page(show_dashboard, title="Dashboard", icon="📊")
page_reconcile = st.Page(show_conciliacion, title="Conciliación", icon="⚖️")
page_search = st.Page(show_buscador, title="Clientes", icon="🔍")
page_import = st.Page(show_importacion, title="Cargar Datos", icon="📂")
page_export = st.Page(show_reportes, title="Exportar", icon="📥")

# Navegación plana sin secciones colapsables según el rol del usuario
if st.session_state.role == 'auditor':
    pg = st.navigation([page_dashboard, page_reconcile, page_search, page_import, page_export])
else:
    pg = st.navigation([page_dashboard, page_reconcile, page_search, page_export])

# 2. Barra superior en la zona de contenido (estética SaaS - Logo izquierda, Selector/Header centro, Usuario/Logout derecha)
col_title, col_period, col_user = st.columns([1.2, 2.6, 1.2], vertical_alignment="center")

with col_title:
    st.markdown("<h3 style='margin:0; padding:0; font-weight:800; color: #10B981;'>📊 AMEM</h3>", unsafe_allow_html=True)

with col_period:
    if "mes_trabajo" not in st.session_state:
        st.session_state.mes_trabajo = "2026-05"
        
    opciones_meses = ["2026-05", "2026-04", "2026-03", "2026-02", "2026-01"]
    opciones_formateadas = {m: format_period(m) for m in opciones_meses}
    idx_default = opciones_meses.index(st.session_state.mes_trabajo) if st.session_state.mes_trabajo in opciones_meses else 0
    
    st.markdown(
        f"""
        <div style='text-align: center; margin-bottom: 4px;'>
            <span style='font-size: 11px; font-weight: 700; color: #64748B; letter-spacing: 1.5px; text-transform: uppercase;'>Período de Auditoría</span>
            <h1 style='margin: 0; padding: 0; font-size: 28px; font-weight: 800; color: var(--text-color);'>
                {format_period(st.session_state.mes_trabajo)}
            </h1>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    col_sel_left, col_sel_mid, col_sel_right = st.columns([1, 1.5, 1])
    with col_sel_mid:
        mes_trabajo = st.selectbox(
            "Seleccionar Período",
            opciones_meses,
            format_func=lambda x: opciones_formateadas.get(x, x),
            index=idx_default,
            label_visibility="collapsed",
            key="global_period_selector"
        )
        if mes_trabajo != st.session_state.mes_trabajo:
            st.session_state.mes_trabajo = mes_trabajo
            st.rerun()

with col_user:
    st.markdown(
        f"""
        <div style='display: flex; align-items: center; justify-content: flex-end; gap: 10px; margin-bottom: 5px;'>
            <div style='text-align: right; line-height: 1.2;'>
                <div style='font-size: 11px; color: #64748B;'>Bienvenido,</div>
                <div style='font-size: 13px; font-weight: 700; color: var(--text-color);'>{st.session_state.username.capitalize()}</div>
                <div style='font-size: 9px; font-weight: 600; color: #10B981; text-transform: uppercase;'>{st.session_state.role}</div>
            </div>
            <div style='width: 36px; height: 36px; border-radius: 50%; background-color: #10B981; color: white; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border: 2px solid white;'>
                {st.session_state.username[0].upper()}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    col_exit_l, col_exit_r = st.columns([1.2, 1])
    with col_exit_r:
        if st.button("Salir", key="logout_btn", type="secondary", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.username = ""
            st.session_state.role = ""
            st.rerun()

st.markdown("<hr style='margin-top: 10px; margin-bottom: 25px; border: 0; border-top: 1px solid rgba(128,128,128,0.15);'>", unsafe_allow_html=True)

# Ejecutar el ruteo de la página seleccionada
pg.run()
