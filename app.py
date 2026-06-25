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
from conciliador import run_conciliacion, OS_CUIT_MAP, get_period_sort_value
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


# PAGE 2: PANEL DE CONCILIACIÓN
def show_conciliacion():
    st.subheader(f"Auditoría y Conciliación de Items — {format_period(st.session_state.mes_trabajo)}")
    st.markdown("Revisa las prestaciones del mes y edita manualmente los estados de conciliación si detectas errores.")
    
    mes_trabajo = st.session_state.mes_trabajo
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Cargar las prestaciones del mes seleccionado con sus conciliaciones
    query = """
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
    
    df_items = pd.read_sql_query(query, conn, params=(mes_trabajo,))
    
    if not df_items.empty:
        status_map = {
            'CONCILIADO': '🟢 CONCILIADO',
            'PENDIENTE_FACTURA': '🔵 PENDIENTE FACTURA',
            'PENDIENTE_COBRO': '🟡 PENDIENTE COBRO',
            'DISCREPANCIA': '🔴 DISCREPANCIA'
        }
        
        # Guardamos el estado original para poder filtrar y modificar
        df_items['estado_raw'] = df_items['estado']
        df_items['estado'] = df_items['estado'].map(lambda x: status_map.get(x, str(x)))
        
        # Ordenar los períodos cronológicamente y convertirlos a Categorical para sorting correcto
        unique_periods = [p for p in df_items['periodo'].unique() if pd.notna(p)]
        sorted_unique_periods = sorted(unique_periods, key=lambda x: get_period_sort_value(x, mes_trabajo))
        df_items['periodo'] = pd.Categorical(df_items['periodo'], categories=sorted_unique_periods, ordered=True)
        df_items = df_items.sort_values('periodo')
        
        # Filtro de Estado
        est_filter_display = st.multiselect(
            "Filtrar por Estado", 
            ["🟢 CONCILIADO", "🔵 PENDIENTE FACTURA", "🟡 PENDIENTE COBRO", "🔴 DISCREPANCIA"], 
            default=["🔵 PENDIENTE FACTURA", "🟡 PENDIENTE COBRO", "🔴 DISCREPANCIA"]
        )
        
        filtered_df = df_items[df_items['estado'].isin(est_filter_display)] if est_filter_display else df_items
        
        # Mostrar grilla elegante
        df_display = filtered_df.rename(columns={
            'os': 'Obra Social',
            'paciente': 'Paciente',
            'periodo': 'Período',
            'monto': 'Monto',
            'factura_nro': 'Factura Nº',
            'estado': 'Estado Conciliación',
            'obs': 'Observaciones'
        })
        
        st.dataframe(
            df_display[['Obra Social', 'Paciente', 'Período', 'Monto', 'Factura Nº', 'Estado Conciliación', 'Observaciones']], 
            column_config={
                "Monto": st.column_config.NumberColumn("Monto", format="$%,.2f")
            },
            use_container_width=True
        )
        
        # Módulo de ajuste manual para el Auditor
        if st.session_state.role == 'auditor':
            st.markdown("### Ajuste Manual de Conciliación")
            
            # Crear una lista de opciones descriptivas para el selectbox
            options_dict = {}
            for _, row_item in filtered_df.iterrows():
                opt_str = f"ID {row_item['prest_id']} - {row_item['os']} (${row_item['monto']:,.2f}) - {row_item['paciente']}"
                options_dict[opt_str] = row_item['prest_id']
                
            if options_dict:
                selected_opt = st.selectbox("Seleccione Prestación a modificar", list(options_dict.keys()))
                
                if selected_opt:
                    selected_prest_id = options_dict[selected_opt]
                    row_item = filtered_df[filtered_df['prest_id'] == selected_prest_id].iloc[0]
                    
                    nuevo_estado = st.selectbox(
                        "Nuevo Estado", 
                        ["CONCILIADO", "PENDIENTE_FACTURA", "PENDIENTE_COBRO", "DISCREPANCIA"], 
                        index=["CONCILIADO", "PENDIENTE_FACTURA", "PENDIENTE_COBRO", "DISCREPANCIA"].index(row_item['estado_raw']) if row_item['estado_raw'] in ["CONCILIADO", "PENDIENTE_FACTURA", "PENDIENTE_COBRO", "DISCREPANCIA"] else 0
                    )
                    nuevas_obs = st.text_area("Observaciones del Auditor", value=row_item['obs'] if row_item['obs'] else "")
                    
                    if st.button("Guardar Ajuste Manual", type="primary"):
                        cursor.execute("""
                            UPDATE conciliaciones 
                            SET estado_final = ?, observaciones = ? 
                            WHERE prestacion_id = ?
                        """, (nuevo_estado, nuevas_obs, selected_prest_id))
                        
                        cursor.execute("""
                            UPDATE prestaciones 
                            SET estado_conciliacion = ? 
                            WHERE id = ?
                        """, (nuevo_estado, selected_prest_id))
                        
                        conn.commit()
                        st.success("¡Ajuste manual guardado con éxito!")
                        st.rerun()
            else:
                st.info("No hay items que coincidan con los filtros seleccionados.")
        else:
            st.info("Los usuarios con rol Consulta tienen acceso de solo lectura al ajuste manual. Solo los Auditores pueden editar.")
    else:
        st.info(
            "💡 **¡Comencemos con la auditoría!**\n\n"
            "El período seleccionado actualmente no cuenta con prestaciones cargadas en el sistema.\n\n"
            "**¿Qué puedes hacer?**\n"
            "* **Seleccionar otro período:** Elige un mes con información registrada desde el selector superior (como *Enero 2026* o *Febrero 2026*).\n"
            "* **Cargar datos nuevos:** Si eres Administrador/Auditor, puedes subir la planilla del mes desde la pestaña **Carga e Importación** para iniciar el proceso de conciliación."
        )
        
    conn.close()


# PAGE 3: BUSCADOR DE CLIENTES
def show_buscador():
    st.subheader("Buscador e Historial de Clientes")
    st.markdown("Consulta la ficha histórica y los movimientos consolidados de cada cliente o de una Obra Social.")
    
    # Input de búsqueda
    search_query = st.text_input("Buscar por CUIT/CUIL o Nombre de la Obra Social/Cliente")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Cargar todos los clientes para mostrar una lista
    cursor.execute("SELECT cuit_hash, cuit_encrypted, nombre_razon_social_encrypted, categoria FROM clientes")
    clientes_raw = cursor.fetchall()
    
    clientes_list = []
    for c in clientes_raw:
        cuit = decrypt_data(c['cuit_encrypted'])
        nombre = decrypt_data(c['nombre_razon_social_encrypted'])
        # Aplicar filtro de búsqueda
        if not search_query or search_query.lower() in cuit or search_query.lower() in nombre.lower():
            clientes_list.append({
                'Hash': c['cuit_hash'],
                'CUIT/CUIL': cuit,
                'Cliente / Obra Social': nombre,
                'Categoría': c['categoria']
            })
            
    if clientes_list:
        df_cli = pd.DataFrame(clientes_list)
        st.dataframe(
            df_cli[['CUIT/CUIL', 'Cliente / Obra Social', 'Categoría']], 
            use_container_width=True
        )
        
        # Selección del cliente para ver historial
        selected_name = st.selectbox("Seleccione un cliente para ver su ficha histórica detallada", df_cli['Cliente / Obra Social'].tolist())
        
        if selected_name:
            selected_hash = df_cli[df_cli['Cliente / Obra Social'] == selected_name]['Hash'].values[0]
            selected_cuit = df_cli[df_cli['Cliente / Obra Social'] == selected_name]['CUIT/CUIL'].values[0]
            
            st.markdown("---")
            st.markdown(f"### Ficha Detallada: {selected_name}")
            st.markdown(f"**CUIT/CUIL:** {selected_cuit} | **Categoría:** {df_cli[df_cli['Cliente / Obra Social'] == selected_name]['Categoría'].values[0]}")
            
            # Buscar prestaciones asociadas (haciendo cruce por nombre aproximado)
            cursor.execute("""
                SELECT id, paciente, fecha_factura, periodo, monto, factura_nro, estado_conciliacion, mes_auditoria
                FROM prestaciones
                WHERE obra_social_nombre LIKE ? OR ? LIKE '%' || obra_social_nombre || '%'
            """, (f"%{selected_name[:5]}%", selected_name))
            
            prest_asoc = cursor.fetchall()
            
            # Buscar facturas emitidas asociadas por cuit_hash
            cursor.execute("""
                SELECT comprobante_id, fecha_emision, monto_total, tipo_comprobante, estado, mes_auditoria
                FROM facturas
                WHERE cuit_hash = ?
            """, (selected_hash,))
            
            fact_asoc = cursor.fetchall()
            
            # Buscar depósitos bancarios asociados por cuit_hash
            cursor.execute("""
                SELECT fecha, concepto, detalle, credito, mes_auditoria
                FROM movimientos_banco
                WHERE cuit_hash_asociado = ?
            """, (selected_hash,))
            
            banco_asoc = cursor.fetchall()
            
            col_a, col_b, col_c = st.columns(3)
            
            status_map = {
                'CONCILIADO': '🟢 CONCILIADO',
                'PENDIENTE_FACTURA': '🔵 PENDIENTE FACTURA',
                'PENDIENTE_COBRO': '🟡 PENDIENTE COBRO',
                'DISCREPANCIA': '🔴 DISCREPANCIA'
            }
            
            with col_a:
                st.markdown("#### Prestaciones de Gestión")
                if prest_asoc:
                    p_data = [{
                        'Paciente': p['paciente'],
                        'Periodo': str(p['periodo']).upper().strip(),
                        'Monto': p['monto'],
                        'Factura': p['factura_nro'],
                        'Estado': status_map.get(p['estado_conciliacion'], p['estado_conciliacion']),
                        '_sort_key': get_period_sort_value(p['periodo'], p['mes_auditoria'])
                    } for p in prest_asoc]
                    
                    # Ordenar la lista base por la clave de ordenamiento
                    p_data = sorted(p_data, key=lambda x: x['_sort_key'])
                    
                    # Extraer el orden único obtenido para definir la categoría
                    unique_periods = []
                    for item in p_data:
                        p_val = item['Periodo']
                        if p_val not in unique_periods:
                            unique_periods.append(p_val)
                            
                    df_p = pd.DataFrame(p_data)
                    df_p['Periodo'] = pd.Categorical(df_p['Periodo'], categories=unique_periods, ordered=True)
                    df_p = df_p.drop(columns=['_sort_key']).sort_values('Periodo')
                    
                    st.dataframe(
                        df_p,
                        column_config={
                            "Monto": st.column_config.NumberColumn("Monto", format="$%,.2f")
                        },
                        use_container_width=True
                    )
                else:
                    st.info("Sin prestaciones registradas.")
                    
            with col_b:
                st.markdown("#### Facturas Emitidas (AFIP)")
                if fact_asoc:
                    f_data = [{
                        'Factura ID': f['comprobante_id'],
                        'Fecha': f['fecha_emision'],
                        'Monto': f['monto_total'],
                        'Tipo': f['tipo_comprobante'],
                        'Estado': f"🟢 {str(f['estado']).upper()}" if str(f['estado']).upper() == 'ACTIVO' else f"🔴 {str(f['estado']).upper()}"
                    } for f in fact_asoc]
                    
                    st.dataframe(
                        pd.DataFrame(f_data),
                        column_config={
                            "Monto": st.column_config.NumberColumn("Monto", format="$%,.2f")
                        },
                        use_container_width=True
                    )
                else:
                    st.info("Sin facturas registradas en AFIP.")
                    
            with col_c:
                st.markdown("#### Depósitos Recibidos (Banco)")
                if banco_asoc:
                    b_data = [{
                        'Fecha': b['fecha'],
                        'Detalle': b['concepto'] if b['concepto'] else b['detalle'],
                        'Monto': b['credito']
                    } for b in banco_asoc]
                    
                    st.dataframe(
                        pd.DataFrame(b_data),
                        column_config={
                            "Monto": st.column_config.NumberColumn("Monto", format="$%,.2f")
                        },
                        use_container_width=True
                    )
                else:
                    st.info("Sin depósitos bancarios identificados.")
    else:
        st.warning("No se encontraron clientes con el criterio de búsqueda.")
        
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
page_dashboard = st.Page(show_dashboard, title="Dashboard General", icon="📊")
page_reconcile = st.Page(show_conciliacion, title="Panel de Conciliación", icon="⚖️")
page_search = st.Page(show_buscador, title="Buscador de Clientes", icon="🔍")
page_import = st.Page(show_importacion, title="Carga e Importación", icon="📂")
page_export = st.Page(show_reportes, title="Reportes & Exportar", icon="📥")

# Organizar páginas en secciones colapsables en la barra lateral según el rol del usuario
if st.session_state.role == 'auditor':
    pg = st.navigation({
        "Auditoría": [page_dashboard, page_reconcile, page_search],
        "Datos y Reportes": [page_import, page_export]
    })
else:
    pg = st.navigation({
        "Auditoría": [page_dashboard, page_reconcile, page_search],
        "Datos y Reportes": [page_export]
    })

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
