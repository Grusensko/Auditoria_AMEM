// ==========================================================================
// LOGICA DE FRONTEND SPA - AMEM AUDITORÍA
// ==========================================================================

document.addEventListener("DOMContentLoaded", () => {
    // --- ESTADO GLOBAL ---
    let session = {
        authenticated: false,
        username: "",
        role: ""
    };
    
    let currentPeriod = "2026-05";
    let periods = [];
    let conciliacionCamino = "A"; // "A" = Facturas -> Bancos, "B" = Bancos -> Facturas
    
    // Almacenamiento local de datos del periodo activo para filtrado rápido en cliente
    let rawPrestaciones = [];
    let rawMovimientosBanco = [];
    
    let selectedPrestId = null;
    let selectedBancoId = null;
    let selectedClienteHash = null;
    
    let hasUnsavedChanges = false;
    let pendingAction = null;
    
    function setHasUnsavedChanges(value) {
        hasUnsavedChanges = value;
        const btnSaveA = document.getElementById("btn-save-manual-a");
        const btnResetA = document.getElementById("btn-reset-a");
        if (btnSaveA) btnSaveA.disabled = !value;
        if (btnResetA) btnResetA.disabled = !value;
        
        const btnSaveB = document.getElementById("btn-save-manual-b");
        const btnResetB = document.getElementById("btn-reset-b");
        if (btnSaveB) btnSaveB.disabled = !value;
        if (btnResetB) btnResetB.disabled = !value;
    }
    
    let currentPrestCands = [];
    let currentFacturasCands = [];
    let currentBancoCands = [];
    
    // Instancias de Gráficos Chart.js para destruirlas/actualizarlas
    let chartPie = null;
    let chartBar = null;
    let chartCliente = null;
    
    let sugerenciasDuplicados = [];
    let sugerenciaActiva = null;

    // --- ELEMENTOS DEL DOM ---
    const loginScreen = document.getElementById("login-screen");
    const appScreen = document.getElementById("app-screen");
    const loginForm = document.getElementById("login-form");
    const loginError = document.getElementById("login-error");
    
    const menuItems = document.querySelectorAll(".menu-item");
    const viewPanes = document.querySelectorAll(".view-pane");
    
    const globalPeriodSelectors = document.querySelectorAll(".period-select-sync");
    const headerPeriodTitle = document.getElementById("header-period-title");
    
    const logoutBtn = document.getElementById("logout-btn");
    
    // Elementos del menú responsive en móviles
    const menuToggleBtn = document.getElementById("menu-toggle-btn");
    const appSidebar = document.getElementById("app-sidebar");
    const sidebarOverlay = document.getElementById("sidebar-overlay");
    
    // Grid.js Instancias globales
    let gridPrestacionesInstance = null;
    let gridFacturasInstance = null;
    let gridBancoInstance = null;
    
    let rawPrestacionesData = [];
    let rawFacturasData = [];
    let rawBancoData = [];

    // Inicializar autenticación desde SessionStorage si existe
    const cachedUser = sessionStorage.getItem("amem_user");
    if (cachedUser) {
        session = JSON.parse(cachedUser);
        if (session.authenticated) {
            showAppScreen();
        }
    }

    // --- MANEJO DE INICIO DE SESIÓN ---
    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const usernameInput = document.getElementById("username").value.trim();
        const passwordInput = document.getElementById("password").value;
        
        try {
            const res = await fetch("/api/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username: usernameInput, password: passwordInput })
            });
            
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Error de inicio de sesión");
            }
            
            const data = await res.json();
            session.authenticated = true;
            session.username = data.username;
            session.role = data.role;
            
            sessionStorage.setItem("amem_user", JSON.stringify(session));
            loginError.textContent = "";
            showAppScreen();
        } catch (err) {
            loginError.textContent = err.message;
        }
    });

    logoutBtn.addEventListener("click", () => {
        sessionStorage.removeItem("amem_user");
        session = { authenticated: false, username: "", role: "" };
        appScreen.classList.remove("active");
        loginScreen.classList.add("active");
        document.body.classList.remove("logged-in");
    });

    function showAppScreen() {
        loginScreen.classList.remove("active");
        appScreen.classList.add("active");
        
        // Configurar UI de usuario
        document.getElementById("user-name-display").textContent = session.username.toUpperCase();
        document.getElementById("user-role-display").textContent = session.role;
        document.getElementById("user-avatar").textContent = session.username[0].toUpperCase();
        
        // Restricción de rol para carga de datos
        const navImportar = document.getElementById("nav-importar");
        if (session.role !== "auditor") {
            navImportar.classList.add("hidden");
        } else {
            navImportar.classList.remove("hidden");
        }
        
        // Inicializar períodos y datos
        loadPeriods();
    }

    // --- NAVEGACIÓN Y VISTAS ---
    menuItems.forEach(item => {
        item.addEventListener("click", () => {
            const target = item.getAttribute("data-target");
            const action = () => {
                menuItems.forEach(i => i.classList.remove("active"));
                item.classList.add("active");
                
                viewPanes.forEach(pane => {
                    pane.classList.remove("active");
                    if (pane.id === target) {
                        pane.classList.add("active");
                    }
                });
                
                setHasUnsavedChanges(false);
                
                // Recargar datos específicos de la pestaña
                if (target === "view-dashboard") {
                    loadDashboardData();
                } else if (target === "view-conciliacion") {
                    loadConciliacionData();
                } else if (target === "view-clientes") {
                    loadClientes();
                } else if (target === "view-alertas") {
                    loadAlertasData();
                } else if (target === "view-reportes") {
                    const reportElem = document.getElementById("report-period-confirm");
                    if (reportElem) {
                        reportElem.textContent = formatPeriod(currentPeriod);
                    }
                } else if (target === "view-data-prestaciones") {
                    loadDataLakePrestaciones();
                } else if (target === "view-data-facturas") {
                    loadDataLakeFacturas();
                } else if (target === "view-data-banco") {
                    loadDataLakeBanco();
                }

                // Cerrar sidebar en móviles al navegar
                if (appSidebar && appSidebar.classList.contains("active")) {
                    appSidebar.classList.remove("active");
                    if (menuToggleBtn) menuToggleBtn.classList.remove("active");
                    if (sidebarOverlay) sidebarOverlay.classList.remove("active");
                }
            };
            
            if (hasUnsavedChanges) {
                pendingAction = action;
                showUnsavedModal();
            } else {
                action();
            }
        });
    });

    // Control de apertura/cierre de sidebar (Drawer en mobile, colapso manual en desktop)
    if (menuToggleBtn && appSidebar && sidebarOverlay) {
        menuToggleBtn.addEventListener("click", () => {
            if (window.innerWidth > 1200) {
                const appScreen = document.getElementById("app-screen");
                if (appScreen) {
                    appScreen.classList.toggle("sidebar-collapsed");
                }
            } else {
                const isOpened = menuToggleBtn.classList.contains("active");
                if (isOpened) {
                    menuToggleBtn.classList.remove("active");
                    appSidebar.classList.remove("active");
                    sidebarOverlay.classList.remove("active");
                    menuToggleBtn.setAttribute("aria-expanded", "false");
                } else {
                    menuToggleBtn.classList.add("active");
                    appSidebar.classList.add("active");
                    sidebarOverlay.classList.add("active");
                    menuToggleBtn.setAttribute("aria-expanded", "true");
                }
            }
        });

        sidebarOverlay.addEventListener("click", () => {
            menuToggleBtn.classList.remove("active");
            appSidebar.classList.remove("active");
            sidebarOverlay.classList.remove("active");
            menuToggleBtn.setAttribute("aria-expanded", "false");
        });
    }

    // --- CARGAR PERÍODOS DE AUDITORÍA ---
    async function loadPeriods() {
        try {
            const res = await fetch("/api/periods");
            periods = await res.json();
            
            globalPeriodSelectors.forEach(select => {
                select.innerHTML = "";
                periods.forEach(p => {
                    const opt = document.createElement("option");
                    opt.value = p;
                    opt.textContent = formatPeriod(p);
                    select.appendChild(opt);
                });
            });
            
            if (periods.length > 0) {
                currentPeriod = periods[0];
                globalPeriodSelectors.forEach(select => {
                    select.value = currentPeriod;
                });
            }
            if (headerPeriodTitle) {
                headerPeriodTitle.textContent = formatPeriod(currentPeriod);
            }
            
            // Cargar dashboard inicial
            loadDashboardData();
        } catch (err) {
            console.error("Error al cargar períodos:", err);
        }
    }

    globalPeriodSelectors.forEach(select => {
        select.addEventListener("change", (e) => {
            const newPeriod = e.target.value;
            
            const changeAction = () => {
                currentPeriod = newPeriod;
                globalPeriodSelectors.forEach(s => {
                    s.value = currentPeriod;
                });
                if (headerPeriodTitle) {
                    headerPeriodTitle.textContent = formatPeriod(currentPeriod);
                }
                
                // Forzar limpieza de selecciones locales
                selectedPrestId = null;
                selectedBancoId = null;
                
                // Recargar vista activa
                const activePane = document.querySelector(".view-pane.active");
                if (activePane.id === "view-dashboard") {
                    loadDashboardData();
                } else if (activePane.id === "view-conciliacion") {
                    loadConciliacionData();
                } else if (activePane.id === "view-reportes") {
                    const reportConfirm = document.getElementById("report-period-confirm");
                    if (reportConfirm) {
                        reportConfirm.textContent = formatPeriod(currentPeriod);
                    }
                }
            };
            
            if (hasUnsavedChanges) {
                pendingAction = changeAction;
                // Revert target value back to currentPeriod visually
                e.target.value = currentPeriod;
                showUnsavedModal();
            } else {
                changeAction();
            }
        });
    });

    function formatPeriod(pStr) {
        const meses = {
            "01": "Enero", "02": "Febrero", "03": "Marzo", "04": "Abril",
            "05": "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto",
            "09": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre"
        };
        if (pStr.includes("-")) {
            const [y, m] = pStr.split("-");
            return `${meses[m] || m} ${y}`;
        }
        return pStr;
    }

    // --- CARGAR DATOS DEL DASHBOARD & DIBUJAR GRÁFICOS ---
    async function loadDashboardData() {
        try {
            const res = await fetch(`/api/dashboard?periodo=${currentPeriod}`);
            const data = await res.json();
            
            // Llenar KPIs
            document.getElementById("kpi-total-banco").textContent = formatCurrency(data.total_ingresado);
            document.getElementById("kpi-cant-banco").textContent = `${data.cant_ingresos} depósitos registrados`;
            
            document.getElementById("kpi-conciliado").textContent = formatCurrency(data.ingresos_conciliados);
            document.getElementById("kpi-cant-conciliado").textContent = `${data.cant_conciliados} cobros ok (match completo)`;
            
            document.getElementById("kpi-sin-id").textContent = formatCurrency(data.ingresos_sin_identificar);
            document.getElementById("kpi-cant-sin-id").textContent = `${data.cant_sin_identificar} cobros sin asociar en banco`;
            
            document.getElementById("kpi-discrepante").textContent = formatCurrency(data.ingresos_discrepantes);
            document.getElementById("kpi-cant-discrepante").textContent = `${data.cant_discrepantes} inconsistencias de pago`;
            
            document.getElementById("kpi-deuda-facturar").textContent = formatCurrency(data.deuda_pendiente_facturar);
            document.getElementById("kpi-cant-deuda-facturar").textContent = `${data.cant_pendiente_facturar} prestaciones sin factura`;
            
            document.getElementById("kpi-deuda-cobrar").textContent = formatCurrency(data.deuda_pendiente_cobrar);
            document.getElementById("kpi-cant-deuda-cobrar").textContent = `${data.cant_pendiente_cobrar} facturas emitidas sin cobro`;
            
            // Destruir gráficos anteriores si existen
            if (chartPie) chartPie.destroy();
            if (chartBar) chartBar.destroy();
            
            // Dibujar Circular Efficiency
            const ctxPie = document.getElementById("chart-pie-efficiency").getContext("2d");
            chartPie = new Chart(ctxPie, {
                type: 'doughnut',
                data: {
                    labels: ['Conciliado', 'Sin Identificar', 'Discrepancias'],
                    datasets: [{
                        data: [data.ingresos_conciliados, data.ingresos_sin_identificar, data.ingresos_discrepantes],
                        backgroundColor: ['#047857', '#B45309', '#B91C1C'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom', labels: { color: '#0F172A' } }
                    }
                }
            });
            
            // Dibujar Bar Desglose
            const ctxBar = document.getElementById("chart-bar-waterfall").getContext("2d");
            chartBar = new Chart(ctxBar, {
                type: 'bar',
                data: {
                    labels: ['Total Ingresado', 'Conciliado', 'Sin Identificar', 'Discrepancias'],
                    datasets: [{
                        label: 'Importe ($)',
                        data: [data.total_ingresado, data.ingresos_conciliados, data.ingresos_sin_identificar, data.ingresos_discrepantes],
                        backgroundColor: ['#1D4ED8', '#047857', '#B45309', '#B91C1C'],
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: { grid: { color: 'rgba(0,0,0,0.06)' }, ticks: { color: '#475569' } },
                        x: { ticks: { color: '#475569' } }
                    }
                }
            });
            
            // Cargar sugerencias de duplicados y transacciones de control en el Header
            try {
                const resDup = await fetch('/api/duplicados/sugerencias');
                sugerenciasDuplicados = await resDup.json();
                
                const resAlerts = await fetch('/api/alertas');
                const alertasContables = await resAlerts.json();
                const alertasSinCatalogar = alertasContables.filter(a => !a.categoria_auditoria);
                
                const headerNotifList = document.getElementById("header-notif-list");
                const headerNotifBadge = document.getElementById("header-notif-badge");
                const headerNotifCount = document.getElementById("header-notif-count");
                
                const totalNotifs = sugerenciasDuplicados.length + (alertasSinCatalogar.length > 0 ? 1 : 0);
                
                if (headerNotifCount) headerNotifCount.textContent = totalNotifs;
                if (headerNotifBadge) {
                    headerNotifBadge.style.display = totalNotifs > 0 ? "block" : "none";
                }
                
                if (headerNotifList) {
                    headerNotifList.innerHTML = "";
                    let itemsHtml = "";
                    
                    // 1. Agregar duplicados detectados
                    sugerenciasDuplicados.forEach((sug, index) => {
                        const styleBg = sug.is_simulated ? "#eff6ff" : "#fff7ed";
                        const styleBorder = sug.is_simulated ? "var(--color-blue)" : "var(--color-orange)";
                        const styleColor = sug.is_simulated ? "#1d4ed8" : "#b45309";
                        const labelSim = sug.is_simulated ? "🤖 [SIMULADO] " : "⚠️ ";
                        
                        itemsHtml += `
                            <div class="notification-item" style="display: flex; flex-direction: column; padding: 10px 12px; border-radius: 8px; background: ${styleBg}; border-left: 4px solid ${styleBorder}; font-size: 11.5px; color: ${styleColor}; box-shadow: 0 1px 2px rgba(0,0,0,0.01); text-align: left;">
                                <div style="display: flex; align-items: flex-start; gap: 8px;">
                                    <span style="font-size: 14px; margin-top: 1px;">${sug.is_simulated ? '💡' : '⚠️'}</span>
                                    <div>
                                        <strong>${labelSim}Posible duplicado:</strong>
                                        <div style="font-weight: 600; margin-top: 2px;">${sug.nombre_a}</div>
                                        <div style="opacity: 0.8; font-size: 10.5px;">con ${sug.nombre_b}</div>
                                        <div style="font-size: 10.5px; opacity: 0.85; margin-top: 4px; line-height: 1.25;">Motivo: ${sug.razon_detallada}</div>
                                    </div>
                                </div>
                                <div style="display: flex; justify-content: flex-end; margin-top: 8px; gap: 6px;">
                                    <button class="btn-primary btn-notif-unificar" data-index="${index}" style="padding: 4px 10px; font-size: 10px; font-weight: 700; background: ${sug.is_simulated ? '#2563eb' : '#ea580c'}; border: none; border-radius: 4px; cursor: pointer; color: white;">🔗 Unificar</button>
                                </div>
                            </div>
                        `;
                    });
                    
                    // 2. Agregar alertas de transacciones bancarias sospechosas sin catalogar
                    if (alertasSinCatalogar.length > 0) {
                        itemsHtml += `
                            <div class="notification-item" style="display: flex; flex-direction: column; padding: 10px 12px; border-radius: 8px; background: #fef2f2; border-left: 4px solid var(--color-red); font-size: 11.5px; color: #b91c1c; box-shadow: 0 1px 2px rgba(0,0,0,0.01); text-align: left;">
                                <div style="display: flex; align-items: flex-start; gap: 8px;">
                                    <span style="font-size: 14px; margin-top: 1px;">🚨</span>
                                    <div>
                                        <strong>Control Interno:</strong>
                                        <div style="margin-top: 2px;">Se detectaron ${alertasSinCatalogar.length} movimientos inusuales sin catalogar.</div>
                                    </div>
                                </div>
                                <div style="display: flex; justify-content: flex-end; margin-top: 8px;">
                                    <button class="btn-secondary btn-notif-revisar-alertas" style="padding: 4px 10px; font-size: 10px; font-weight: 700; border-color: #fca5a5; color: #b91c1c; background: #fff; border-radius: 4px; cursor: pointer;">🛡️ Catalogar</button>
                                </div>
                            </div>
                        `;
                    }
                    
                    if (itemsHtml) {
                        headerNotifList.innerHTML = itemsHtml;
                        
                        // Enlazar eventos click de botones en notificaciones
                        headerNotifList.querySelectorAll(".btn-notif-unificar").forEach(btn => {
                            btn.addEventListener("click", (e) => {
                                e.stopPropagation();
                                const idx = parseInt(btn.getAttribute("data-index"));
                                sugerenciaActiva = sugerenciasDuplicados[idx];
                                abrirModalFusion(sugerenciaActiva);
                                // Cerrar dropdown flotante al hacer click en la acción
                                document.getElementById("header-notif-dropdown").classList.add("hidden");
                            });
                        });
                        
                        const btnRevAlerts = headerNotifList.querySelector(".btn-notif-revisar-alertas");
                        if (btnRevAlerts) {
                            btnRevAlerts.addEventListener("click", (e) => {
                                e.stopPropagation();
                                const menuAlertas = Array.from(document.querySelectorAll(".menu-item")).find(i => i.getAttribute("data-target") === "view-alertas");
                                if (menuAlertas) menuAlertas.click();
                                document.getElementById("header-notif-dropdown").classList.add("hidden");
                            });
                        }
                    } else {
                        headerNotifList.innerHTML = `<div class="list-empty-state" style="padding: 15px; font-size: 11.5px; text-align: center; color: var(--text-secondary);">Sin notificaciones pendientes. Todo en orden. ✅</div>`;
                    }
                }
            } catch (dupErr) {
                console.error("Error al cargar sugerencias de duplicados:", dupErr);
            }
        } catch (err) {
            console.error("Error al cargar KPIs del dashboard:", err);
        }
    }

    function formatCurrency(val) {
        return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(val);
    }

    // --- NAVEGACIÓN Y LOGICA DE CONCILIACIÓN MAESTRO-DETALLE ---
    const flowBtnA = document.getElementById("flow-btn-a");
    const flowBtnB = document.getElementById("flow-btn-b");
    const masterSearchInput = document.getElementById("master-search-input");
    
    // Checkboxes filtros maestro
    const chkConc = document.getElementById("chk-master-conciliado");
    const chkPend = document.getElementById("chk-master-pendiente");
    const chkCobro = document.getElementById("chk-master-cobro");
    const chkDisc = document.getElementById("chk-master-discrepancia");

    flowBtnA.addEventListener("click", () => {
        const action = () => {
            flowBtnB.classList.remove("active");
            flowBtnA.classList.add("active");
            conciliacionCamino = "A";
            selectedPrestId = null;
            setHasUnsavedChanges(false);
            loadConciliacionData();
        };
        
        if (hasUnsavedChanges) {
            pendingAction = action;
            showUnsavedModal();
        } else {
            action();
        }
    });

    flowBtnB.addEventListener("click", () => {
        const action = () => {
            flowBtnA.classList.remove("active");
            flowBtnB.classList.add("active");
            conciliacionCamino = "B";
            selectedBancoId = null;
            setHasUnsavedChanges(false);
            loadConciliacionData();
        };
        
        if (hasUnsavedChanges) {
            pendingAction = action;
            showUnsavedModal();
        } else {
            action();
        }
    });

    // Escuchar eventos en filtros locales
    masterSearchInput.addEventListener("input", filterMasterList);
    [chkConc, chkPend, chkCobro, chkDisc].forEach(chk => {
        chk.addEventListener("change", filterMasterList);
    });

    async function loadConciliacionData() {
        if (conciliacionCamino === "A") {
            try {
                const res = await fetch(`/api/prestaciones?periodo=${currentPeriod}`);
                rawPrestaciones = await res.json();
                filterMasterList();
            } catch (err) {
                console.error("Error cargando prestaciones:", err);
            }
        } else {
            try {
                const res = await fetch(`/api/banco?periodo=${currentPeriod}`);
                rawMovimientosBanco = await res.json();
                filterMasterList();
            } catch (err) {
                console.error("Error cargando banco:", err);
            }
        }
    }

    function selectPrestacion(id) {
        const action = () => {
            selectedPrestId = id;
            setHasUnsavedChanges(false);
            filterMasterList();
        };
        if (hasUnsavedChanges) {
            pendingAction = action;
            showUnsavedModal();
        } else {
            action();
        }
    }
    
    function selectBanco(id) {
        const action = () => {
            selectedBancoId = id;
            setHasUnsavedChanges(false);
            filterMasterList();
        };
        if (hasUnsavedChanges) {
            pendingAction = action;
            showUnsavedModal();
        } else {
            action();
        }
    }

    function filterMasterList() {
        const query = masterSearchInput.value.toLowerCase().trim();
        
        // Obtener estados marcados
        const showConc = chkConc.checked;
        const showPend = chkPend.checked;
        const showCobro = chkCobro.checked;
        const showDisc = chkDisc.checked;
        
        const container = document.getElementById("master-list-container");
        container.innerHTML = "";
        
        if (conciliacionCamino === "A") {
            // Filtrar prestaciones
            let filtered = rawPrestaciones;
            
            // Filtro de estados
            filtered = filtered.filter(p => {
                if (p.estado === "CONCILIADO") return showConc;
                if (p.estado === "PENDIENTE_FACTURA") return showPend;
                if (p.estado === "PENDIENTE_COBRO") return showCobro;
                if (p.estado === "DISCREPANCIA") return showDisc;
                return true;
            });
            
            // Filtro de búsqueda texto
            if (query) {
                filtered = filtered.filter(p => 
                    p.os.toLowerCase().includes(query) || 
                    p.paciente.toLowerCase().includes(query)
                );
            }
            
            // Renderizar tarjetas
            if (filtered.length > 0) {
                // Seleccionar primero si no hay ninguno seleccionado o no está en la lista activa
                const validIds = filtered.map(p => p.prest_id);
                if (!selectedPrestId || !validIds.includes(selectedPrestId)) {
                    selectedPrestId = filtered[0].prest_id;
                }
                
                filtered.forEach(p => {
                    const card = document.createElement("div");
                    const isSelected = p.prest_id === selectedPrestId;
                    card.className = isSelected ? "selected-button-wrapper" : "normal-button-wrapper";
                    
                    let statusEmoji = "🟢";
                    if (p.estado === "PENDIENTE_FACTURA") statusEmoji = "🔵";
                    else if (p.estado === "PENDIENTE_COBRO") statusEmoji = "🟡";
                    else if (p.estado === "DISCREPANCIA") statusEmoji = "🔴";
                    
                    const btn = document.createElement("button");
                    btn.innerHTML = `<strong>${statusEmoji} ${p.os}</strong> — ${formatCurrency(p.monto)}<br><span class="search-item-meta">👤 Paciente: ${p.paciente}</span>`;
                    
                    btn.addEventListener("click", () => {
                        selectPrestacion(p.prest_id);
                    });
                    
                    card.appendChild(btn);
                    container.appendChild(card);
                });
                
                // Cargar detalles en panel derecho
                renderDetailPane();
            } else {
                container.innerHTML = `<div class="list-empty-state">Sin resultados</div>`;
                showDetailPlaceholder("No hay facturas o prestaciones que coincidan con la búsqueda.");
            }
        } else {
            // Filtrar banco
            let filtered = rawMovimientosBanco;
            
            // Filtro de estados
            filtered = filtered.filter(b => {
                if (b.estado_display === "CONCILIADO") return showConc;
                if (b.estado_display === "SIN IDENTIFICAR") return showCobro; // Cobro pendiente de identificar
                if (b.estado_display === "DISCREPANCIA") return showDisc;
                return true;
            });
            
            // Filtro de búsqueda texto
            if (query) {
                filtered = filtered.filter(b => 
                    b.concepto.toLowerCase().includes(query) || 
                    (b.detalle && b.detalle.toLowerCase().includes(query)) ||
                    (b.cuit_txt && b.cuit_txt.toLowerCase().includes(query))
                );
            }
            
            if (filtered.length > 0) {
                const validIds = filtered.map(b => b.banco_id);
                if (!selectedBancoId || !validIds.includes(selectedBancoId)) {
                    selectedBancoId = filtered[0].banco_id;
                }
                
                filtered.forEach(b => {
                    const card = document.createElement("div");
                    const isSelected = b.banco_id === selectedBancoId;
                    card.className = isSelected ? "selected-button-wrapper" : "normal-button-wrapper";
                    
                    let statusEmoji = "🟢";
                    if (b.estado_display === "SIN IDENTIFICAR") statusEmoji = "🟡";
                    else if (b.estado_display === "DISCREPANCIA") statusEmoji = "🔴";
                    
                    const btn = document.createElement("button");
                    const concStr = b.concepto || "";
                    const cuitStr = b.cuit_txt ? ` | CUIT: ${b.cuit_txt}` : "";
                    btn.innerHTML = `<strong>${statusEmoji} ${b.fecha}</strong> — ${formatCurrency(b.credito)}<br><span class="search-item-meta">🏦 ${concStr}${cuitStr}</span>`;
                    
                    btn.addEventListener("click", () => {
                        selectBanco(b.banco_id);
                    });
                    
                    card.appendChild(btn);
                    container.appendChild(card);
                });
                
                renderDetailPane();
            } else {
                container.innerHTML = `<div class="list-empty-state">Sin resultados</div>`;
                showDetailPlaceholder("No hay depósitos bancarios que coincidan con la búsqueda.");
            }
        }
    }

    function showDetailPlaceholder(msg) {
        const detailPanel = document.getElementById("detail-panel-container");
        detailPanel.innerHTML = `
            <div class="detail-placeholder">
                <span class="placeholder-icon">👈</span>
                <p>${msg}</p>
            </div>
        `;
    }

    // --- RENDERIZAR DETALLES (COLUMNA DERECHA) ---
    function parseDate(dateStr) {
        if (!dateStr) return null;
        dateStr = dateStr.trim();
        if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
            return new Date(dateStr + "T00:00:00");
        }
        if (/^\d{2}\/\d{2}\/\d{4}$/.test(dateStr)) {
            const [d, m, y] = dateStr.split("/");
            return new Date(`${y}-${m}-${d}T00:00:00`);
        }
        const d = new Date(dateStr);
        return isNaN(d.getTime()) ? null : d;
    }

    function dayDifference(date1, date2) {
        if (!date1 || !date2) return 0;
        const diffTime = date2.getTime() - date1.getTime();
        return Math.round(diffTime / (1000 * 60 * 60 * 24));
    }
    function formatDateReadable(date) {
        return date.toLocaleDateString("es-AR", { day: "numeric", month: "short", year: "numeric" });
    }

    function formatShortDate(date) {
        const d = String(date.getDate()).padStart(2, '0');
        const m = String(date.getMonth() + 1).padStart(2, '0');
        return `${d}/${m}`;
    }

    function formatMontoInput(input) {
        let val = input.value.replace(/[^0-9,.-]/g, '');
        input.value = val;
    }
    
    // =========================================================================
    // REGISTROS IMPORTADOS VIEWS (Grid.js)
    // =========================================================================
    
    // Diccionario temporal local de Obras Sociales a CUIT (para enriquecimiento crudo visual)
    const LOCAL_OS_CUIT_MAP = {
        "OSEP": "30623978164", 
        "OSDE": "30546741253", 
        "SANCOR": "30300000000",
        "OSECAC": "30679232106", 
        "PAMI": "30522763922", 
        "SWISS MEDICAL": "30678138300",
        "PREVENCION": "30713045000", 
        "GALENO": "30536481747", 
        "OMINT": "30685871239",
        "OSPE": "30661876715", 
        "OSPELSYM": "30657325372", 
        "PALERO": "18084418",
        "UNION PERSONAL": "30683032227",
        "IOSFA": "30714906948",
        "CIMESA": "30533836808",
        "AYE": "30680620713",
        "MUTUAL AGUA Y ENERGIA": "30546101890",
        "TV SALUD": "30516748385",
        "OSPRERA": "30547339416",
        "OSPAV": "33531576859",
        "INCLUIR": "30715815709",
        "JALIF": "22392224"
    };

    function enrichWithCuit(osName) {
        if (!osName) return osName;
        const upper = osName.toUpperCase().trim();
        for (const [key, cuit] of Object.entries(LOCAL_OS_CUIT_MAP)) {
            if (upper.includes(key)) {
                return `${osName} <span style="display:inline-block; margin-left:6px; padding:2px 5px; background:#e2e8f0; border-radius:4px; font-size:11px; color:#0f172a; font-weight:600;">CUIT: ${cuit}</span>`;
            }
        }
        return osName;
    }

    function enrichCuitWithOS(cuit) {
        if (!cuit) return cuit;
        const cleanCuit = String(cuit).replace(/[^0-9]/g, '').trim();
        for (const [os, mappedCuit] of Object.entries(LOCAL_OS_CUIT_MAP)) {
            if (cleanCuit === mappedCuit) {
                return `${cuit} <span style="display:inline-block; margin-left:6px; padding:2px 5px; background:var(--color-blue-light); border-radius:4px; font-size:11px; color:var(--color-blue); font-weight:600;">${os}</span>`;
            }
        }
        return cuit;
    }

    function enrichTextWithOS(text) {
        if (!text) return text;
        let result = String(text);
        
        // 1. Si contiene el CUIT, agregar la Obra Social
        for (const [os, cuit] of Object.entries(LOCAL_OS_CUIT_MAP)) {
            if (result.includes(cuit) && !result.includes(os)) {
                const badge = ` <span style="display:inline-block; padding:2px 5px; background:var(--color-blue-light); border-radius:4px; font-size:11px; color:var(--color-blue); font-weight:600;">${os}</span>`;
                result = result.replace(new RegExp(cuit, 'g'), `${cuit}${badge}`);
            }
        }
        
        // 2. Si contiene el nombre corto de la obra social (y no tiene ya su CUIT al lado), agregar el CUIT
        for (const [os, cuit] of Object.entries(LOCAL_OS_CUIT_MAP)) {
            if (os.length < 3) continue;
            const regex = new RegExp(`\\b${os}\\b`, 'i');
            if (regex.test(result) && !result.includes(cuit)) {
                const badge = ` <span style="display:inline-block; padding:2px 5px; background:#e2e8f0; border-radius:4px; font-size:11px; color:#0f172a; font-weight:600;">CUIT: ${cuit}</span>`;
                result = result.replace(regex, (match) => `${match}${badge}`);
            }
        }
        return result;
    }

    function renderCellWithActions(content, gridId, enrichFn = null) {
        if (!content && content !== 0) return "";
        const trimmedContent = String(content).trim().replace(/[\r\n]/g, ' ');
        const escapedContentForAttr = trimmedContent.replace(/'/g, "\\'").replace(/"/g, '&quot;');
        const displayContent = enrichFn ? enrichFn(trimmedContent) : trimmedContent;
        
        return gridjs.html(`<div style="position:relative; width:100%; height:100%; display:flex; align-items:center; justify-content:space-between; gap:10px; min-width:0;">
            <span style="flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0;">${displayContent}</span>
            <div class="cell-actions-container">
                <button class="cell-action-btn" title="Copiar valor" onclick="window.copyToClipboard('${escapedContentForAttr}', this)">📋</button>
                <button class="cell-action-btn" title="Filtrar por esta celda" onclick="window.triggerGridSearch('${gridId}', '${escapedContentForAttr}')">🔍</button>
            </div>
        </div>`);
    }

    window.copyToClipboard = function(text, btnEl) {
        navigator.clipboard.writeText(text).then(() => {
            if (window.showTooltip && window.hideTooltip) {
                const rect = btnEl.getBoundingClientRect();
                const fakeEvent = {
                    clientX: rect.left + rect.width / 2,
                    clientY: rect.top,
                    preventDefault: () => {}
                };
                window.showTooltip(fakeEvent, "¡Copiado!");
                setTimeout(() => {
                    window.hideTooltip();
                }, 1000);
            }
        }).catch(err => {
            console.error("Error al copiar texto: ", err);
        });
    };

    window.triggerGridSearch = function(gridId, val) {
        const gridWrapper = document.getElementById(gridId);
        if(!gridWrapper) return;
        const searchInput = gridWrapper.querySelector('input[type="search"]');
        if(searchInput) {
            // Limpiar $, espacios de no-rompimiento (NBSP, narrow NBSP) y espacios normales
            let cleaned = val.replace(/[\$\u00A0\u202F\s]/g, '').trim();
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
            nativeInputValueSetter.call(searchInput, cleaned);
            searchInput.dispatchEvent(new Event('input', { bubbles: true }));
        }
    };
    
    function updateGridTotal(countId, count) {
        const el = document.getElementById(countId);
        if (el) el.textContent = `(${count} registros)`;
    }

    function populateDatalakeFilter(selectId, dataArray, dataField) {
        const select = document.getElementById(selectId);
        if (!select) return;
        
        // Conservar la opción "ALL" (el primer option)
        const allOption = select.options[0];
        select.innerHTML = "";
        select.appendChild(allOption);
        
        const uniqueValues = [...new Set(dataArray.map(item => item[dataField]).filter(v => v))].sort().reverse();
        uniqueValues.forEach(val => {
            const opt = document.createElement("option");
            opt.value = val;
            opt.textContent = formatPeriod(val) || val;
            select.appendChild(opt);
        });
    }

    async function loadDataLakePrestaciones() {
        if (rawPrestacionesData.length === 0) {
            try {
                const res = await fetch("/api/data/prestaciones");
                rawPrestacionesData = await res.json();
                populateDatalakeFilter("filter-datalake-prestaciones-mes", rawPrestacionesData, "mes_auditoria");
                renderGridPrestaciones(rawPrestacionesData);
            } catch (err) {
                console.error("Error cargando Prestaciones Data Lake", err);
            }
        }
    }
    
    function renderGridPrestaciones(data) {
        updateGridTotal("count-prestaciones", data.length);
        const container = document.getElementById("grid-prestaciones");
        
        gridPrestacionesInstance = new gridjs.Grid({
            columns: [
                { name: "ID", width: '80px', formatter: (c) => renderCellWithActions(c, "grid-prestaciones") },
                { name: "Obra Social", formatter: (c) => renderCellWithActions(c, "grid-prestaciones", enrichWithCuit) },
                { name: "Paciente", formatter: (c) => renderCellWithActions(c, "grid-prestaciones") },
                { name: "Fecha Fact.", formatter: (c) => renderCellWithActions(c, "grid-prestaciones") },
                { name: "Periodo", formatter: (c) => renderCellWithActions(c, "grid-prestaciones") },
                { name: "Monto", formatter: (c) => renderCellWithActions(c, "grid-prestaciones") },
                { name: "Fact. Nro", formatter: (c) => renderCellWithActions(c, "grid-prestaciones") },
                { name: "Estado", formatter: (c) => renderCellWithActions(c, "grid-prestaciones") },
                { name: "Mes Aud.", formatter: (c) => renderCellWithActions(c, "grid-prestaciones") }
            ],
            data: data.map(i => [i.id, i.obra_social_nombre, i.paciente, i.fecha_factura, i.periodo, formatCurrency(i.monto), i.factura_nro, i.estado_conciliacion, i.mes_auditoria]),
            search: true,
            sort: true,
            fixedHeader: true,
            height: '100%',
            language: { search: { placeholder: "🔍 Buscar..." }, noRecordsFound: "No se encontraron registros" }
        }).render(container);
        
        // Setup Filtro
        document.getElementById("filter-datalake-prestaciones-mes").addEventListener("change", (e) => {
            const val = e.target.value;
            const filtered = val === "ALL" ? rawPrestacionesData : rawPrestacionesData.filter(i => i.mes_auditoria === val);
            updateGridTotal("count-prestaciones", filtered.length);
            gridPrestacionesInstance.updateConfig({ 
                data: filtered.map(i => [i.id, i.obra_social_nombre, i.paciente, i.fecha_factura, i.periodo, formatCurrency(i.monto), i.factura_nro, i.estado_conciliacion, i.mes_auditoria]) 
            }).forceRender();
        });
    }

    async function loadDataLakeFacturas() {
        if (rawFacturasData.length === 0) {
            try {
                const res = await fetch("/api/data/facturas");
                rawFacturasData = await res.json();
                populateDatalakeFilter("filter-datalake-facturas-mes", rawFacturasData, "mes_auditoria");
                renderGridFacturas(rawFacturasData);
            } catch (err) {
                console.error("Error cargando Facturas Data Lake", err);
            }
        }
    }
    
    function renderGridFacturas(data) {
        updateGridTotal("count-facturas", data.length);
        const container = document.getElementById("grid-facturas");
        gridFacturasInstance = new gridjs.Grid({
            columns: [
                { name: "Comprobante ID", formatter: (c) => renderCellWithActions(c, "grid-facturas") },
                { name: "CUIT Rel.", formatter: (c) => renderCellWithActions(c, "grid-facturas", enrichCuitWithOS) },
                { name: "Fecha Emisión", formatter: (c) => renderCellWithActions(c, "grid-facturas") },
                { name: "Monto Total", formatter: (c) => renderCellWithActions(c, "grid-facturas") },
                { name: "Tipo Comp.", formatter: (c) => renderCellWithActions(c, "grid-facturas") },
                { name: "Estado", formatter: (c) => renderCellWithActions(c, "grid-facturas") },
                { name: "Mes Aud.", formatter: (c) => renderCellWithActions(c, "grid-facturas") }
            ],
            data: data.map(i => [i.comprobante_id, i.cuit_txt, i.fecha_emision, formatCurrency(i.monto_total), i.tipo_comprobante, i.estado, i.mes_auditoria]),
            search: true,
            sort: true,
            fixedHeader: true,
            height: '100%',
            language: { search: { placeholder: "🔍 Buscar..." }, noRecordsFound: "No se encontraron registros" }
        }).render(container);
        
        document.getElementById("filter-datalake-facturas-mes").addEventListener("change", (e) => {
            const val = e.target.value;
            const filtered = val === "ALL" ? rawFacturasData : rawFacturasData.filter(i => i.mes_auditoria === val);
            updateGridTotal("count-facturas", filtered.length);
            gridFacturasInstance.updateConfig({ 
                data: filtered.map(i => [i.comprobante_id, i.cuit_txt, i.fecha_emision, formatCurrency(i.monto_total), i.tipo_comprobante, i.estado, i.mes_auditoria]) 
            }).forceRender();
        });
    }

    async function loadDataLakeBanco() {
        if (rawBancoData.length === 0) {
            try {
                const res = await fetch("/api/data/banco");
                rawBancoData = await res.json();
                populateDatalakeFilter("filter-datalake-banco-mes", rawBancoData, "mes_auditoria");
                renderGridBanco(rawBancoData);
            } catch (err) {
                console.error("Error cargando Banco Data Lake", err);
            }
        }
    }
    
    function renderGridBanco(data) {
        updateGridTotal("count-banco", data.length);
        const container = document.getElementById("grid-banco");
        gridBancoInstance = new gridjs.Grid({
            columns: [
                { name: "ID", width: '80px', formatter: (c) => renderCellWithActions(c, "grid-banco") },
                { name: "Fecha", formatter: (c) => renderCellWithActions(c, "grid-banco") },
                { name: "Concepto", formatter: (c) => renderCellWithActions(c, "grid-banco", enrichTextWithOS) },
                { name: "Detalle", formatter: (c) => renderCellWithActions(c, "grid-banco", enrichTextWithOS) },
                { name: "Monto Neto", formatter: (c) => renderCellWithActions(c, "grid-banco") },
                { name: "Saldo", formatter: (c) => renderCellWithActions(c, "grid-banco") },
                { name: "Mes Aud.", formatter: (c) => renderCellWithActions(c, "grid-banco") }
            ],
            data: data.map(i => {
                const monto = i.credito > 0 ? i.credito : (i.debito > 0 ? -i.debito : 0);
                return [i.id, i.fecha, i.concepto, i.detalle, formatCurrency(monto), formatCurrency(i.saldo), i.mes_auditoria];
            }),
            search: true,
            sort: true,
            fixedHeader: true,
            height: '100%',
            language: { search: { placeholder: "🔍 Buscar..." }, noRecordsFound: "No se encontraron registros" }
        }).render(container);
        
        const filterBancoData = () => {
            const tipo = document.getElementById("filter-datalake-banco-tipo").value;
            const mes = document.getElementById("filter-datalake-banco-mes").value;
            
            let filtered = rawBancoData;
            if (mes !== "ALL") filtered = filtered.filter(i => i.mes_auditoria === mes);
            if (tipo === "INGRESOS") filtered = filtered.filter(i => i.credito > 0);
            if (tipo === "EGRESOS") filtered = filtered.filter(i => i.debito > 0);
            
            updateGridTotal("count-banco", filtered.length);
            gridBancoInstance.updateConfig({ 
                data: filtered.map(i => {
                    const monto = i.credito > 0 ? i.credito : (i.debito > 0 ? -i.debito : 0);
                    return [i.id, i.fecha, i.concepto, i.detalle, formatCurrency(monto), formatCurrency(i.saldo), i.mes_auditoria];
                })
            }).forceRender();
        };
        
        document.getElementById("filter-datalake-banco-mes").addEventListener("change", filterBancoData);
        document.getElementById("filter-datalake-banco-tipo").addEventListener("change", filterBancoData);
    }

    function generateTimelineHTML(prestDateStr, afipDateStr, bancoDateStr) {
        const prestDate = parseDate(prestDateStr);
        const afipDate = parseDate(afipDateStr);
        const bancoDate = parseDate(bancoDateStr);
        
        let labelPrest = prestDate ? formatDateReadable(prestDate) : "Sin Fecha";
        let labelAfip = afipDate ? formatDateReadable(afipDate) : "Pendiente";
        let labelBanco = bancoDate ? formatDateReadable(bancoDate) : "Pendiente";
        
        let leftPrest = 0;
        let leftAfip = 45; 
        let leftBanco = 90; 
        
        let statusPrest = "green"; 
        let statusAfip = afipDate ? "blue" : "pending";
        let statusBanco = bancoDate ? "orange" : "pending";
        
        let tooltipPrest = `Prestación Registrada: ${labelPrest}`;
        let tooltipAfip = afipDate ? `Facturado en AFIP el ${labelAfip}` : "Pendiente de Facturación";
        let tooltipBanco = bancoDate ? `Acreditado en Banco el ${labelBanco}` : "Pendiente de Cobro";
        
        if (prestDate) {
            if (afipDate) {
                const diffDays = dayDifference(prestDate, afipDate);
                leftAfip = Math.min(95, Math.max(15, (diffDays / 120) * 100));
                tooltipAfip += ` (${diffDays} días de delay)`;
            }
            if (bancoDate) {
                const diffDays = dayDifference(prestDate, bancoDate);
                leftBanco = Math.min(100, Math.max(leftAfip + 15, (diffDays / 120) * 100));
                tooltipBanco += ` (${diffDays} días desde prestación)`;
                if (afipDate) {
                    const diffAfipBanco = dayDifference(afipDate, bancoDate);
                    tooltipBanco += ` / (${diffAfipBanco} días desde facturación)`;
                }
            }
        }
        
        let progressWidth = 0;
        if (bancoDate) {
            progressWidth = leftBanco;
        } else if (afipDate) {
            progressWidth = leftAfip;
        } else {
            progressWidth = 0;
        }
        
        const classPrest = leftPrest < 15 ? "first-event" : (leftPrest > 85 ? "last-event" : "");
        const classAfip = leftAfip < 15 ? "first-event" : (leftAfip > 85 ? "last-event" : "");
        const classBanco = leftBanco < 15 ? "first-event" : (leftBanco > 85 ? "last-event" : "");
        
        return `
            <div class="detail-card timeline-card">
                <div class="detail-header">📅 Línea de Tiempo del Ciclo Contable (Escala 120 días)</div>
                <div class="timeline-container">
                    <div class="timeline-line"></div>
                    <div class="timeline-progress" style="width: ${progressWidth}%;"></div>
                    
                    <div class="timeline-events">
                        <!-- Hito 1: Prestación -->
                        <div class="timeline-event ${classPrest}" style="left: ${leftPrest}%;">
                            <div class="event-dot ${statusPrest}"></div>
                            <div class="event-label">Prestación</div>
                            <div class="event-date">${prestDateStr ? formatShortDate(prestDate) : "—"}</div>
                            <div class="timeline-event-tooltip">${tooltipPrest}</div>
                        </div>
                        
                        <!-- Hito 2: Factura AFIP -->
                        <div class="timeline-event ${classAfip}" style="left: ${leftAfip}%;">
                            <div class="event-dot ${statusAfip}"></div>
                            <div class="event-label">Facturación</div>
                            <div class="event-date">${afipDateStr ? formatShortDate(afipDate) : "—"}</div>
                            <div class="timeline-event-tooltip">${tooltipAfip}</div>
                        </div>
                        
                        <!-- Hito 3: Cobro Banco -->
                        <div class="timeline-event ${classBanco}" style="left: ${leftBanco}%;">
                            <div class="event-dot ${statusBanco}"></div>
                            <div class="event-label">Cobro</div>
                            <div class="event-date">${bancoDateStr ? formatShortDate(bancoDate) : "—"}</div>
                            <div class="timeline-event-tooltip">${tooltipBanco}</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    async function saveManualConciliacionA() {
        const selFactura = document.getElementById("sel_factura_vinculo_a");
        const selBanco = document.getElementById("sel_banco_vinculo_a");
        const selEstado = document.getElementById("sel_estado_final_a");
        const txtObs = document.getElementById("txt_observaciones_a");
        
        if (!selFactura || !selBanco || !selEstado || !txtObs) return false;
        
        const payload = {
            prestacion_id: selectedPrestId,
            factura_id: selFactura.value || null,
            movimiento_banco_id: selBanco.value ? parseInt(selBanco.value) : null,
            estado_final: selEstado.value,
            observaciones: txtObs.value,
            mes_auditoria: currentPeriod
        };
        
        try {
            const res = await fetch("/api/conciliar", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            
            if (res.ok) {
                setHasUnsavedChanges(false);
                const pRes = await fetch(`/api/prestaciones?periodo=${currentPeriod}`);
                rawPrestaciones = await pRes.json();
                filterMasterList();
                return true;
            } else {
                alert("Error al guardar conciliación");
                return false;
            }
        } catch (e) {
            console.error(e);
            return false;
        }
    }

    async function saveManualConciliacionB() {
        const selPrest = document.getElementById("sel_prest_vinculo_b");
        const selEstadoB = document.getElementById("sel_estado_final_b");
        const txtObsB = document.getElementById("txt_observaciones_b");
        
        if (!selPrest || !selEstadoB || !txtObsB) return false;
        
        const p_id = selPrest.value ? parseInt(selPrest.value) : null;
        if (!p_id) {
            alert("Debe seleccionar una prestación para vincular.");
            return false;
        }
        
        const pInfo = currentPrestCands.find(p => p.id === p_id);
        const fact_id = pInfo ? pInfo.factura_id : null;
        
        const payload = {
            prestacion_id: p_id,
            factura_id: fact_id,
            movimiento_banco_id: selectedBancoId,
            estado_final: selEstadoB.value,
            observaciones: txtObsB.value,
            mes_auditoria: currentPeriod
        };
        
        try {
            const res = await fetch("/api/conciliar", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            
            if (res.ok) {
                setHasUnsavedChanges(false);
                const bRes = await fetch(`/api/banco?periodo=${currentPeriod}`);
                rawMovimientosBanco = await bRes.json();
                filterMasterList();
                return true;
            } else {
                alert("Error al guardar conciliación");
                return false;
            }
        } catch (e) {
            console.error(e);
            return false;
        }
    }

    // --- RENDERIZAR DETALLES (COLUMNA DERECHA) ---
    async function renderDetailPane() {
        const detailPanel = document.getElementById("detail-panel-container");
        
        // Validar rol de usuario
        const isReadOnly = session.role !== "auditor";
        
        if (conciliacionCamino === "A") {
            if (!selectedPrestId) return;
            
            // Cargar datos en vivo de la prestación seleccionada
            const prest = rawPrestaciones.find(p => p.prest_id === selectedPrestId);
            if (!prest) return;
            
            // Consulta de facturas y banco candidatos
            let facturasCands = [];
            let bancoCands = [];
            
            try {
                // Obtener facturas candidatas
                const resF = await fetch(`/api/candidatos/facturas?prest_id=${selectedPrestId}`);
                facturasCands = await resF.json();
                currentFacturasCands = facturasCands;
            } catch (e) { console.error(e); }
            
            // Obtener buscador de banco y checkbox de monto si ya se renderizaron para mantener el estado de búsqueda en el input
            let txtBancoVal = document.getElementById("search_banco_text_a")?.value || "";
            let chkMontoVal = document.getElementById("chk_filtrar_monto_a") ? document.getElementById("chk_filtrar_monto_a").checked : true;
            
            try {
                const resB = await fetch(`/api/candidatos/banco?prest_id=${selectedPrestId}&buscar_texto=${encodeURIComponent(txtBancoVal)}&filtrar_monto=${chkMontoVal}`);
                bancoCands = await resB.json();
                currentBancoCands = bancoCands;
            } catch (e) { console.error(e); }
            
            // Render HTML
            let html = `
                <!-- Ficha principal de Prestación -->
                <div class="detail-card" style="position: relative;">
                    <!-- Icono de información para procedencia (i) -->
                    <div class="audit-info-trigger">i</div>
                    <div class="audit-tooltip">
                        <strong>Procedencia de Datos:</strong><br>
                        📝 Archivo: ${prest.archivo_origen || "Desconocido"}<br>
                        📍 Fila: ${prest.nro_fila || "—"}
                    </div>
                    <div class="detail-header">📊 Datos de la Prestación (Gestión)</div>
                    <div class="ficha-grid" style="grid-template-columns: 1fr 1fr;">
                        <div>
                            <div class="info-label">Obra Social</div>
                            <div class="info-value">${prest.os}</div>
                            <div class="info-label">Paciente</div>
                            <div class="info-value">${prest.paciente}</div>
                        </div>
                        <div>
                            <div class="info-label">Monto de la Prestación</div>
                            <div class="info-value text-success font-semibold">${formatCurrency(prest.monto)}</div>
                            <div class="info-label">Período de Prestación</div>
                            <div class="info-value">${formatPeriod(prest.periodo)}</div>
                        </div>
                    </div>
                </div>
                
                <!-- Línea de tiempo contable -->
                ${generateTimelineHTML(prest.fecha_factura, prest.afip_fecha, prest.banco_fecha)}
                
                <!-- Factura AFIP Vinculada -->
                <div class="detail-card" style="position: relative;">
                    ${prest.fact_afip_id ? `
                        <div class="audit-info-trigger">i</div>
                        <div class="audit-tooltip">
                            <strong>Procedencia de Datos:</strong><br>
                            📄 Archivo: ${prest.afip_archivo || "Desconocido"}<br>
                            📍 Fila/Línea: ${prest.afip_fila || "—"}
                        </div>
                    ` : ""}
                    <div class="detail-header">📄 Factura de AFIP / ARCA (Vía 2)</div>
            `;
            
            if (prest.fact_afip_id) {
                html += `
                    <div class="ficha-grid" style="grid-template-columns: 1fr 1fr; margin-bottom: 15px;">
                        <div>
                            <div class="info-label">Comprobante ID</div>
                            <div class="info-value">${prest.fact_afip_id}</div>
                        </div>
                        <div>
                            <div class="info-label">Estado Facturación</div>
                            <div class="info-value"><span class="status-chip green">ACTIVO</span></div>
                        </div>
                    </div>
                `;
            } else {
                html += `<div class="warning-banner">⚠️ Sin Factura de AFIP asociada</div>`;
            }
            
            // Selector Facturas Candidatas
            html += `
                <div class="input-group">
                    <label for="sel_factura_vinculo_a">Asociar Factura AFIP</label>
                    <select id="sel_factura_vinculo_a" ${isReadOnly ? "disabled" : ""}>
                        <option value="">Ninguna / Desvincular</option>
            `;
            
            let isActualFactInCands = false;
            facturasCands.forEach(f => {
                const isSel = f.comprobante_id === prest.fact_afip_id;
                if (isSel) isActualFactInCands = true;
                html += `<option value="${f.comprobante_id}" ${isSel ? "selected" : ""}>Factura Nº ${f.comprobante_id} | Emisión: ${f.fecha_emision} | Monto: ${formatCurrency(f.monto_total)} | CUIT: ${f.cuit_txt}</option>`;
            });
            
            if (prest.fact_afip_id && !isActualFactInCands) {
                html += `<option value="${prest.fact_afip_id}" selected>Factura Nº ${prest.fact_afip_id} (Vinculada actualmente)</option>`;
            }
            
            html += `
                    </select>
                </div>
                </div> <!-- Cierre de card AFIP -->
                
                <!-- Movimiento Banco Vinculado -->
                <div class="detail-card" style="position: relative;">
                    ${prest.banco_id ? `
                        <div class="audit-info-trigger">i</div>
                        <div class="audit-tooltip">
                            <strong>Procedencia de Datos:</strong><br>
                            🏦 Archivo: ${prest.banco_archivo || "Desconocido"}<br>
                            📍 Fila: ${prest.banco_fila || "—"}
                        </div>
                    ` : ""}
                    <div class="detail-header">🏦 Depósito Bancario / Cobro (Vía 3)</div>
            `;
            
            if (prest.banco_id) {
                html += `
                     <div class="info-banner" id="banco-vinculo-info-a">
                        Cargando depósito vinculado actual...
                    </div>
                `;
            } else {
                html += `<div class="warning-banner">⚠️ Sin Depósito Bancario identificado</div>`;
            }
            
            // Buscador del Banco
            html += `
                <div class="ficha-grid" style="grid-template-columns: 1.5fr 1fr; margin-bottom: 12px; gap:10px;">
                    <div class="input-group" style="margin-bottom:0;">
                        <label>Buscar Depósito</label>
                        <input type="text" id="search_banco_text_a" value="${txtBancoVal}" placeholder="Concepto, detalle, CUIT..." ${isReadOnly ? "disabled" : ""}>
                    </div>
                    <div class="input-group" style="margin-bottom:0; display:flex; align-items:flex-end;">
                        <label class="filter-checkbox-label" style="padding-bottom:12px;">
                            <input type="checkbox" id="chk_filtrar_monto_a" ${chkMontoVal ? "checked" : ""} ${isReadOnly ? "disabled" : ""}> Filtrar por Importe Similar (±5%)
                        </label>
                    </div>
                </div>
                
                <div class="input-group">
                    <label for="sel_banco_vinculo_a">Asociar Depósito Bancario</label>
                    <select id="sel_banco_vinculo_a" ${isReadOnly ? "disabled" : ""}>
                        <option value="">Ninguno / Desvincular</option>
            `;
            
            let isActualBancoInCands = false;
            bancoCands.forEach(b => {
                const isSel = b.id === prest.banco_id;
                if (isSel) isActualBancoInCands = true;
                const c_str = b.concepto || "";
                const d_str = b.detalle ? ` (${b.detalle})` : "";
                html += `<option value="${b.id}" ${isSel ? "selected" : ""}>ID: ${b.id} | Fecha: ${b.fecha} | Monto: ${formatCurrency(b.credito)} | ${c_str}${d_str}</option>`;
            });
            
            if (prest.banco_id && !isActualBancoInCands) {
                html += `<option value="${prest.banco_id}" selected>ID: ${prest.banco_id} (Vinculado actualmente)</option>`;
            }
            
            html += `
                    </select>
                </div>
                </div> <!-- Cierre de card Banco -->
                
                <!-- Tarjeta de Estado Recomendado e Interacciones -->
                <div class="detail-card">
                    <div class="detail-header">⚙️ Conciliación y Acciones</div>
                    <div id="recomendacion-banner-a" class="info-banner">Calculando estado recomendado...</div>
            `;
            
            if (!isReadOnly) {
                html += `
                    <div class="ficha-grid" style="grid-template-columns: 1.2fr 2.8fr; gap:15px; margin-bottom: 20px;">
                        <div class="input-group" style="margin-bottom:0;">
                            <label for="sel_estado_final_a">Estado de Conciliación</label>
                            <select id="sel_estado_final_a">
                                <option value="CONCILIADO">CONCILIADO</option>
                                <option value="PENDIENTE_FACTURA">PENDIENTE_FACTURA</option>
                                <option value="PENDIENTE_COBRO">PENDIENTE_COBRO</option>
                                <option value="DISCREPANCIA">DISCREPANCIA</option>
                            </select>
                        </div>
                        <div class="input-group" style="margin-bottom:0;">
                            <label for="txt_observaciones_a">Observaciones del Auditor</label>
                            <textarea id="txt_observaciones_a" placeholder="Escribe observaciones de auditoría...">${prest.obs || ""}</textarea>
                        </div>
                    </div>
                    
                    <div class="detail-actions-panel">
                        <button class="btn-primary" id="btn-save-manual-a" style="flex: 1;" ${hasUnsavedChanges ? "" : "disabled"}>Guardar</button>
                        <button class="btn-secondary" id="btn-reset-a" style="flex: 1;" ${hasUnsavedChanges ? "" : "disabled"}>Descartar Cambios</button>
                        <button class="btn-secondary" id="btn-desvincular-a" style="flex: 1;">Desvincular por completo</button>
                    </div>
                `;
            } else {
                html += `
                    <div class="info-banner" style="background-color:rgba(156,163,175,0.05); color:var(--text-secondary); border: 1px solid var(--border-color); text-align:center;">
                        🔒 Acceso de Solo Lectura. Solo los Auditores autorizados pueden realizar modificaciones.
                    </div>
                `;
            }
            
            html += `</div>`; // Cierre de card de acciones
            
            detailPanel.innerHTML = html;
            
            // Petición asíncrona para rellenar los datos de banco vinculados
            if (prest.banco_id) {
                fetch(`/api/candidatos/banco?prest_id=${selectedPrestId}&filtrar_monto=false`).then(res => res.json()).then(cands => {
                    const bInfo = cands.find(b => b.id === prest.banco_id);
                    const bInfoDiv = document.getElementById("banco-vinculo-info-a");
                    if (bInfo && bInfoDiv) {
                        bInfoDiv.className = "status-chip green";
                        bInfoDiv.style.display = "block";
                        bInfoDiv.innerHTML = `<strong>Depósito ID ${bInfo.id}</strong> | Fecha: ${bInfo.fecha} | Acreditado: ${formatCurrency(bInfo.credito)}<br><span style="opacity:0.8;">${bInfo.concepto || ""}</span>`;
                    } else if (bInfoDiv) {
                        bInfoDiv.className = "warning-banner";
                        bInfoDiv.innerHTML = `⚠️ Depósito ID ${prest.banco_id} asociado, pero no se recuperaron detalles.`;
                    }
                }).catch(e => console.error(e));
            }
            
            // Adjuntar listeners de búsqueda interactiva
            const inpSearchBanco = document.getElementById("search_banco_text_a");
            const chkSearchBanco = document.getElementById("chk_filtrar_monto_a");
            
            // Debounce simple para el campo de búsqueda
            let searchTimeout = null;
            inpSearchBanco.addEventListener("input", () => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(async () => {
                    await renderDetailPane();
                    const inp = document.getElementById("search_banco_text_a");
                    inp.focus();
                    inp.setSelectionRange(inp.value.length, inp.value.length);
                }, 350);
            });
            
            chkSearchBanco.addEventListener("change", renderDetailPane);
            
            // Calcular y setear recomendación reactiva al cambiar selecciones de select
            const selFactura = document.getElementById("sel_factura_vinculo_a");
            const selBanco = document.getElementById("sel_banco_vinculo_a");
            const bannerRec = document.getElementById("recomendacion-banner-a");
            const selEstado = document.getElementById("sel_estado_final_a");
            
            async function updateRecomendacion() {
                const factId = selFactura.value;
                const bancoId = selBanco.value;
                
                let montoFact = null;
                let montoBanc = null;
                
                if (factId) {
                    const fInfo = facturasCands.find(f => f.comprobante_id === factId);
                    if (fInfo) montoFact = fInfo.monto_total;
                }
                
                if (bancoId) {
                    const bInfo = bancoCands.find(b => b.id === parseInt(bancoId));
                    if (bInfo) montoBanc = bInfo.credito;
                }
                
                let recEstado = "PENDIENTE_FACTURA";
                let recMsg = "";
                
                if (factId && bancoId) {
                    if (montoFact && montoBanc) {
                        const diffF = Math.abs(prest.monto - montoFact);
                        const diffB = Math.abs(prest.monto - montoBanc);
                        if (diffF < 0.01 && diffB < 0.01) {
                            recEstado = "CONCILIADO";
                            recMsg = "🟢 Conciliación completa: Prestación, Factura y Depósito coinciden exactamente en monto.";
                        } else {
                            recEstado = "DISCREPANCIA";
                            recMsg = `🔴 Discrepancia de montos: Prestación (${formatCurrency(prest.monto)}) vs Factura (${formatCurrency(montoFact)}) vs Banco (${formatCurrency(montoBanc)}).`;
                        }
                    } else {
                        recEstado = "CONCILIADO";
                        recMsg = "🟢 Ambos elementos seleccionados.";
                    }
                } else if (factId && !bancoId) {
                    recEstado = "PENDIENTE_COBRO";
                    recMsg = "🟡 Factura vinculada pero sin depósito bancario identificado (Pendiente de Cobro).";
                } else if (!factId && bancoId) {
                    recEstado = "DISCREPANCIA";
                    recMsg = "🔴 Pago recibido en banco pero sin factura de AFIP asociada (Discrepancia).";
                } else {
                    recEstado = "PENDIENTE_FACTURA";
                    recMsg = "🔵 Sin factura de AFIP ni depósito en banco identificado (Pendiente de Factura).";
                }
                
                if (bannerRec) {
                    bannerRec.textContent = recMsg;
                    if (recEstado === "CONCILIADO") {
                        bannerRec.style.backgroundColor = "var(--color-green-light)";
                        bannerRec.style.color = "var(--color-green)";
                        bannerRec.style.borderColor = "rgba(16, 185, 129, 0.2)";
                    } else if (recEstado === "DISCREPANCIA") {
                        bannerRec.style.backgroundColor = "var(--color-red-light)";
                        bannerRec.style.color = "var(--color-red)";
                        bannerRec.style.borderColor = "rgba(239, 68, 68, 0.2)";
                    } else {
                        bannerRec.style.backgroundColor = "var(--color-orange-light)";
                        bannerRec.style.color = "var(--color-orange)";
                        bannerRec.style.borderColor = "rgba(245, 158, 11, 0.2)";
                    }
                }
                
                if (selEstado) {
                    selEstado.value = recEstado;
                }
            }
            
            selFactura.addEventListener("change", updateRecomendacion);
            selBanco.addEventListener("change", updateRecomendacion);
            
            // Gatillar primera recomendacion
            updateRecomendacion();
            
            if (prest.estado && selEstado) {
                selEstado.value = prest.estado;
            }
            
            // Acciones de guardado
            if (!isReadOnly) {
                const btnSave = document.getElementById("btn-save-manual-a");
                const btnReset = document.getElementById("btn-reset-a");
                const btnUnlink = document.getElementById("btn-desvincular-a");
                
                if (btnSave) {
                    btnSave.addEventListener("click", async () => {
                        await saveManualConciliacionA();
                    });
                }
                
                if (btnReset) {
                    btnReset.addEventListener("click", () => {
                        setHasUnsavedChanges(false);
                        renderDetailPane();
                    });
                }
                
                if (btnUnlink) {
                    btnUnlink.addEventListener("click", async () => {
                        try {
                            const res = await fetch("/api/desvincular", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({ tipo: "prestacion", id: selectedPrestId })
                            });
                            
                            if (res.ok) {
                                setHasUnsavedChanges(false);
                                const pRes = await fetch(`/api/prestaciones?periodo=${currentPeriod}`);
                                rawPrestaciones = await pRes.json();
                                filterMasterList();
                            } else {
                                alert("Error al desvincular");
                            }
                        } catch (e) { console.error(e); }
                    });
                }
            }
            
        } else {
            // ----------------------------------------------------
            // CAMINO B: COBROS BANCARIOS ➔ PRESTACIONES
            // ----------------------------------------------------
            if (!selectedBancoId) return;
            
            const banco = rawMovimientosBanco.find(b => b.banco_id === selectedBancoId);
            if (!banco) return;
            
            let prestCands = [];
            
            let txtPrestVal = document.getElementById("search_prest_text_b")?.value || "";
            let chkMontoPrestVal = document.getElementById("chk_filtrar_monto_prest_b") ? document.getElementById("chk_filtrar_monto_prest_b").checked : true;
            
            try {
                const resP = await fetch(`/api/candidatos/prestaciones?banco_id=${selectedBancoId}&buscar_texto=${encodeURIComponent(txtPrestVal)}&filtrar_monto=${chkMontoPrestVal}`);
                prestCands = await resP.json();
                currentPrestCands = prestCands;
            } catch (e) { console.error(e); }
            
            let html = `
                <!-- Ficha del Depósito Bancario -->
                <div class="detail-card" style="position: relative;">
                    <!-- Icono de información para procedencia (i) -->
                    <div class="audit-info-trigger">i</div>
                    <div class="audit-tooltip">
                        <strong>Procedencia de Datos:</strong><br>
                        🏦 Archivo: ${banco.archivo_origen || "Desconocido"}<br>
                        📍 Fila: ${banco.nro_fila || "—"}
                    </div>
                    <div class="detail-header">🏦 Detalles del Depósito Bancario</div>
                    <div class="ficha-grid" style="grid-template-columns: 1fr 1fr;">
                        <div>
                            <div class="info-label">Fecha de Depósito</div>
                            <div class="info-value">${banco.fecha}</div>
                            <div class="info-label">Monto Acreditado</div>
                            <div class="info-value text-success font-semibold">${formatCurrency(banco.credito)}</div>
                        </div>
                        <div>
                            <div class="info-label">Concepto Bancario</div>
                            <div class="info-value">${banco.concepto}</div>
                            <div class="info-label">Detalle Extracto</div>
                            <div class="info-value">${banco.detalle || "Sin detalles"}</div>
                        </div>
                    </div>
                </div>
            `;
            
            // Loop a través de todas las prestaciones asociadas a este cobro (1-a-N)
            const hasAssoc = banco.asociaciones && banco.asociaciones.length > 0;
            if (hasAssoc) {
                banco.asociaciones.forEach((assoc, index) => {
                    html += `
                        <div class="detail-card" style="position: relative;">
                            <!-- Icono de información para procedencia (i) -->
                            <div class="audit-info-trigger">i</div>
                            <div class="audit-tooltip">
                                <strong>Procedencia de Datos:</strong><br>
                                📝 Prestación: ${assoc.prest_archivo || "Desconocido"} (Fila ${assoc.prest_fila || "—"})<br>
                                ${assoc.afip_archivo ? `📄 Factura AFIP: ${assoc.afip_archivo} (Fila ${assoc.afip_fila || "—"})` : "📄 Factura AFIP: Sin factura asociada"}
                            </div>
                            <div class="detail-header">📊 Prestación Asociada #${index + 1}</div>
                            <div class="ficha-grid" style="grid-template-columns: 1fr 1fr; margin-bottom: 15px;">
                                <div>
                                    <div class="info-label">ID Prestación</div>
                                    <div class="info-value">${assoc.prestacion_id}</div>
                                    <div class="info-label">Obra Social</div>
                                    <div class="info-value">${assoc.os}</div>
                                    <div class="info-label">Paciente</div>
                                    <div class="info-value">${assoc.paciente}</div>
                                </div>
                                <div>
                                    <div class="info-label">Monto Prestación</div>
                                    <div class="info-value" style="font-weight:700;">${formatCurrency(assoc.monto)}</div>
                                    <div class="info-label">Período</div>
                                    <div class="info-value">${formatPeriod(assoc.periodo)}</div>
                                    <div class="info-label">Factura AFIP</div>
                                    <div class="info-value">${assoc.factura_id || "Sin Factura AFIP"}</div>
                                </div>
                            </div>
                            
                            <!-- Línea de tiempo para esta asociación -->
                            ${generateTimelineHTML(assoc.fecha_factura, assoc.afip_fecha, banco.fecha)}
                        </div>
                    `;
                });
            } else {
                html += `<div class="warning-banner">⚠️ Sin prestación ni factura asociada a este cobro</div>`;
            }
            
            // Selector de Nueva Asociación
            html += `
                <div class="detail-card">
                    <div class="detail-header">🔗 Nueva Asociación / Vínculo Manual</div>
                    <div class="ficha-grid" style="grid-template-columns: 1.5fr 1fr; margin-bottom: 12px; gap:10px;">
                        <div class="input-group" style="margin-bottom:0;">
                            <label>Buscar Prestación</label>
                            <input type="text" id="search_prest_text_b" value="${txtPrestVal}" placeholder="Obra social o paciente..." ${isReadOnly ? "disabled" : ""}>
                        </div>
                        <div class="input-group" style="margin-bottom:0; display:flex; align-items:flex-end;">
                            <label class="filter-checkbox-label" style="padding-bottom:12px;">
                                <input type="checkbox" id="chk_filtrar_monto_prest_b" ${chkMontoPrestVal ? "checked" : ""} ${isReadOnly ? "disabled" : ""}> Filtrar por Importe Similar (±5%)
                            </label>
                        </div>
                    </div>
                    
                    <div class="input-group">
                        <label for="sel_prest_vinculo_b">Asociar Prestación</label>
                        <select id="sel_prest_vinculo_b" ${isReadOnly ? "disabled" : ""}>
                            <option value="">Ninguna / Desvincular</option>
            `;
            
            const firstAssoc = hasAssoc ? banco.asociaciones[0] : null;
            const firstPrestId = firstAssoc ? firstAssoc.prestacion_id : null;
            let isActualPrestInCands = false;
            
            prestCands.forEach(p => {
                const isSel = p.id === firstPrestId;
                if (isSel) isActualPrestInCands = true;
                const fNroStr = p.factura_id ? ` | Factura AFIP: ${p.factura_id}` : " | Sin Factura AFIP";
                html += `<option value="${p.id}" ${isSel ? "selected" : ""}>ID: ${p.id} | ${p.obra_social_nombre} | Paciente: ${p.paciente} | Monto: ${formatCurrency(p.monto)} | Período: ${p.periodo}${fNroStr}</option>`;
            });
            
            if (firstPrestId && !isActualPrestInCands) {
                const firstOS = firstAssoc ? firstAssoc.os : "";
                html += `<option value="${firstPrestId}" selected>ID: ${firstPrestId} | ${firstOS} (Vinculada actualmente)</option>`;
            }
            
            html += `
                        </select>
                    </div>
                </div> <!-- Cierre de card de nueva asociacion -->
                
                <!-- Tarjeta de Acciones -->
                <div class="detail-card">
                    <div class="detail-header">⚙️ Conciliación y Acciones</div>
                    <div id="recomendacion-banner-b" class="info-banner">Calculando estado recomendado...</div>
            `;
            
            if (!isReadOnly) {
                html += `
                    <div class="ficha-grid" style="grid-template-columns: 1.2fr 2.8fr; gap:15px; margin-bottom: 20px;">
                        <div class="input-group" style="margin-bottom:0;">
                            <label for="sel_estado_final_b">Estado de Conciliación</label>
                            <select id="sel_estado_final_b">
                                <option value="CONCILIADO">CONCILIADO</option>
                                <option value="PENDIENTE_FACTURA">PENDIENTE_FACTURA</option>
                                <option value="PENDIENTE_COBRO">PENDIENTE_COBRO</option>
                                <option value="DISCREPANCIA">DISCREPANCIA</option>
                            </select>
                        </div>
                        <div class="input-group" style="margin-bottom:0;">
                            <label for="txt_observaciones_b">Observaciones del Auditor</label>
                            <textarea id="txt_observaciones_b" placeholder="Observaciones de conciliación...">${banco.obs || ""}</textarea>
                        </div>
                    </div>
                    
                    <div class="detail-actions-panel">
                        <button class="btn-primary" id="btn-save-manual-b" style="flex: 1;" ${hasUnsavedChanges ? "" : "disabled"}>Guardar</button>
                        <button class="btn-secondary" id="btn-reset-b" style="flex: 1;" ${hasUnsavedChanges ? "" : "disabled"}>Descartar Cambios</button>
                        <button class="btn-secondary" id="btn-desvincular-b" style="flex: 1;">Desvincular por completo</button>
                    </div>
                `;
            } else {
                html += `
                    <div class="info-banner" style="background-color:rgba(156,163,175,0.05); color:var(--text-secondary); border: 1px solid var(--border-color); text-align:center;">
                        🔒 Acceso de Solo Lectura. Solo los Auditores autorizados pueden realizar modificaciones.
                    </div>
                `;
            }
            
            html += `</div>`;
            
            detailPanel.innerHTML = html;
            
            const inpSearchPrest = document.getElementById("search_prest_text_b");
            const chkSearchPrest = document.getElementById("chk_filtrar_monto_prest_b");
            
            let searchTimeoutB = null;
            inpSearchPrest.addEventListener("input", () => {
                clearTimeout(searchTimeoutB);
                searchTimeoutB = setTimeout(async () => {
                    await renderDetailPane();
                    const inp = document.getElementById("search_prest_text_b");
                    inp.focus();
                    inp.setSelectionRange(inp.value.length, inp.value.length);
                }, 350);
            });
            
            chkSearchPrest.addEventListener("change", renderDetailPane);
            
            const selPrest = document.getElementById("sel_prest_vinculo_b");
            const bannerRecB = document.getElementById("recomendacion-banner-b");
            const selEstadoB = document.getElementById("sel_estado_final_b");
            
            async function updateRecomendacionB() {
                const prestId = selPrest.value;
                let recEstado = "PENDIENTE_COBRO";
                let recMsg = "";
                
                if (prestId) {
                    const pInfo = prestCands.find(p => p.id === parseInt(prestId));
                    if (pInfo) {
                        if (pInfo.factura_id) {
                            const diff = Math.abs(banco.credito - pInfo.monto);
                            if (diff < 0.01) {
                                recEstado = "CONCILIADO";
                                recMsg = "🟢 Conciliación completa: Prestación, Factura de AFIP y Depósito coinciden exactamente.";
                            } else {
                                recEstado = "DISCREPANCIA";
                                recMsg = `🔴 Discrepancia de montos: Prestación (${formatCurrency(pInfo.monto)}) vs Banco (${formatCurrency(banco.credito)}).`;
                            }
                        } else {
                            recEstado = "DISCREPANCIA";
                            recMsg = "🔴 Depósito bancario vinculado a una prestación sin factura de AFIP emitida (Discrepancia de facturación).";
                        }
                    }
                } else {
                    recEstado = "PENDIENTE_COBRO";
                    recMsg = "🟡 Depósito bancario sin identificar. No se ha asociado ninguna prestación de gestión.";
                }
                
                if (bannerRecB) {
                    bannerRecB.textContent = recMsg;
                    if (recEstado === "CONCILIADO") {
                        bannerRecB.style.backgroundColor = "var(--color-green-light)";
                        bannerRecB.style.color = "var(--color-green)";
                        bannerRecB.style.borderColor = "rgba(16, 185, 129, 0.2)";
                    } else if (recEstado === "DISCREPANCIA") {
                        bannerRecB.style.backgroundColor = "var(--color-red-light)";
                        bannerRecB.style.color = "var(--color-red)";
                        bannerRecB.style.borderColor = "rgba(239, 68, 68, 0.2)";
                    } else {
                        bannerRecB.style.backgroundColor = "var(--color-orange-light)";
                        bannerRecB.style.color = "var(--color-orange)";
                        bannerRecB.style.borderColor = "rgba(245, 158, 11, 0.2)";
                    }
                }
                if (selEstadoB) selEstadoB.value = recEstado;
            }
            
            selPrest.addEventListener("change", updateRecomendacionB);
            updateRecomendacionB();
            
            if (banco.estado && selEstadoB) {
                selEstadoB.value = banco.estado;
            }
            
            if (!isReadOnly) {
                const btnSaveB = document.getElementById("btn-save-manual-b");
                const btnResetB = document.getElementById("btn-reset-b");
                const btnUnlinkB = document.getElementById("btn-desvincular-b");
                
                if (btnSaveB) {
                    btnSaveB.addEventListener("click", async () => {
                        await saveManualConciliacionB();
                    });
                }
                
                if (btnResetB) {
                    btnResetB.addEventListener("click", () => {
                        setHasUnsavedChanges(false);
                        renderDetailPane();
                    });
                }
                
                if (btnUnlinkB) {
                    btnUnlinkB.addEventListener("click", async () => {
                        try {
                            const res = await fetch("/api/desvincular", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({ tipo: "banco", id: selectedBancoId })
                            });
                            
                            if (res.ok) {
                                setHasUnsavedChanges(false);
                                const bRes = await fetch(`/api/banco?periodo=${currentPeriod}`);
                                rawMovimientosBanco = await bRes.json();
                                filterMasterList();
                            } else {
                                alert("Error al desvincular");
                            }
                        } catch (e) { console.error(e); }
                    });
                }
            }
        }
    }

    // --- BUSCADOR Y FILTROS DE CLIENTES ---
    const clientSearchInp = document.getElementById("clientes-search-input");
    const clientStatusFilter = document.getElementById("clientes-status-filter");
    
    if (clientSearchInp) {
        clientSearchInp.addEventListener("input", () => {
            loadClientes(clientSearchInp.value.trim());
        });
    }

    if (clientStatusFilter) {
        clientStatusFilter.addEventListener("change", () => {
            loadClientes(clientSearchInp.value.trim());
        });
    }

    // Función auxiliar para calcular diferencia de meses para el delay normal
    function getMonthsDiff(period1, period2) {
        if (!period1 || !period2) return 0;
        try {
            const [y1, m1] = period1.split("-").map(Number);
            const [y2, m2] = period2.split("-").map(Number);
            return (y2 - y1) * 12 + (m2 - m1);
        } catch (e) {
            return 0;
        }
    }

    async function loadAlertasData() {
        const loading = document.getElementById("alertas-loading");
        const emptyState = document.getElementById("alertas-empty-state");
        const list = document.getElementById("alertas-list");
        
        if (loading) loading.style.display = "block";
        if (emptyState) emptyState.style.display = "none";
        if (list) list.innerHTML = "";
        
        try {
            const res = await fetch("/api/alertas");
            const data = await res.json();
            
            if (loading) loading.style.display = "none";
            
            if (!data || data.length === 0) {
                if (emptyState) emptyState.style.display = "block";
                return;
            }
            
            data.forEach(item => {
                const card = document.createElement("div");
                card.className = "alerta-card";
                
                // Determinar el borde y la categoría de la alerta según los datos
                let borderClass = "border-ajuste";
                let badgeClass = "badge-ajuste";
                let badgeText = "Ajuste";
                
                if (item.categoria_auditoria) {
                    const cat = item.categoria_auditoria.toLowerCase();
                    if (cat.includes("sospechos") || cat.includes("investig")) {
                        borderClass = "border-sospechosa";
                        badgeClass = "badge-sospechosa";
                        badgeText = "Bajo Investigación";
                    } else if (cat.includes("emplead")) {
                        borderClass = "border-empleado";
                        badgeClass = "badge-empleado";
                        badgeText = "Empleado";
                    } else if (cat.includes("error")) {
                        borderClass = "border-error";
                        badgeClass = "badge-error";
                        badgeText = "Error de Carga";
                    } else if (cat.includes("aprob") || cat.includes("sin alerta")) {
                        borderClass = "border-aprobado";
                        badgeClass = "badge-aprobado";
                        badgeText = "Aprobado";
                    }
                } else {
                    // Auto-categorización inicial sugerida en base a las reglas
                    if (item.concepto.toLowerCase().includes("reverso")) {
                        borderClass = "border-error";
                        badgeClass = "badge-error";
                        badgeText = "Reverso (Sugerido)";
                    } else if (item.cuit_txt_asociado === "27174412702") {
                        borderClass = "border-empleado";
                        badgeClass = "badge-empleado";
                        badgeText = "Empleado (Sugerido)";
                    } else {
                        borderClass = "border-sospechosa";
                        badgeClass = "badge-sospechosa";
                        badgeText = "Sospechosa (Sugerido)";
                    }
                }
                
                card.classList.add(borderClass);
                
                // Formatear montos
                const debitoStr = item.debito > 0 ? formatCurrency(item.debito) : "";
                const creditoStr = item.credito > 0 ? formatCurrency(item.credito) : "";
                
                const selectValue = item.categoria_auditoria || "";
                const comentarioValue = item.comentario_auditoria || "";
                
                card.innerHTML = `
                    <div class="alerta-info">
                        <div class="alerta-header">
                            <span class="alerta-concept">${item.concepto}</span>
                            <span class="alerta-badge ${badgeClass}">${badgeText}</span>
                        </div>
                        <div class="alerta-detail">${item.detalle || "(Sin detalles)"}</div>
                        <div class="alerta-meta">
                            <span>📅 ${item.fecha} ${item.hora || ""}</span>
                            <span>📁 Fila ${item.nro_fila} (${item.archivo_origen})</span>
                        </div>
                    </div>
                    <div class="alerta-monto-pane">
                        <span class="alerta-monto-label">${item.debito > 0 ? 'Egreso (Débito)' : 'Ingreso (Crédito)'}</span>
                        <span class="alerta-monto ${item.debito > 0 ? 'debito' : 'credito'}">
                            ${item.debito > 0 ? '-' : '+'}&nbsp;${item.debito > 0 ? debitoStr : creditoStr}
                        </span>
                    </div>
                    <div class="alerta-acciones">
                        <div class="alerta-inputs">
                            <select class="alerta-select" id="select-alerta-${item.id}">
                                <option value="" ${selectValue === "" ? "selected" : ""}>-- Seleccionar Estado --</option>
                                <option value="Bajo Investigación" ${selectValue === "Bajo Investigación" ? "selected" : ""}>🔍 Bajo Investigación</option>
                                <option value="Transferencia a Empleado" ${selectValue === "Transferencia a Empleado" ? "selected" : ""}>👤 Transferencia a Empleado</option>
                                <option value="Error de Carga" ${selectValue === "Error de Carga" ? "selected" : ""}>⚠️ Error de Carga / Rebotado</option>
                                <option value="Ajuste Contable" ${selectValue === "Ajuste Contable" ? "selected" : ""}>📝 Ajuste Contable</option>
                                <option value="Sin Alerta / Aprobado" ${selectValue === "Sin Alerta / Aprobado" ? "selected" : ""}>✅ Sin Alerta / Aprobado</option>
                            </select>
                            <input type="text" class="alerta-comentario" id="comentario-alerta-${item.id}" 
                                   placeholder="Añadir nota explicativa..." value="${comentarioValue}">
                        </div>
                        <button class="btn-guardar-alerta disabled" id="btn-save-alerta-${item.id}" onclick="saveAlertaCatalogar(${item.id})">
                            Guardar
                        </button>
                    </div>
                `;
                
                list.appendChild(card);
                
                // Configurar lógica reactiva para activar el botón guardar al detectar cambios
                const sel = card.querySelector(`#select-alerta-${item.id}`);
                const inp = card.querySelector(`#comentario-alerta-${item.id}`);
                const btn = card.querySelector(`#btn-save-alerta-${item.id}`);
                
                const checkChanges = () => {
                    const currentSel = sel.value;
                    const currentInp = inp.value.trim();
                    if (currentSel !== selectValue || currentInp !== comentarioValue) {
                        btn.classList.remove("disabled");
                    } else {
                        btn.classList.add("disabled");
                    }
                };
                
                sel.addEventListener("change", checkChanges);
                inp.addEventListener("input", checkChanges);
            });
            
        } catch (error) {
            console.error("Error al cargar las alertas contables", error);
            if (loading) loading.style.display = "none";
        }
    }

    // Exponer saveAlertaCatalogar globalmente para que funcione con el onclick inline
    window.saveAlertaCatalogar = async function(id) {
        const sel = document.getElementById(`select-alerta-${id}`);
        const inp = document.getElementById(`comentario-alerta-${id}`);
        const btn = document.getElementById(`btn-save-alerta-${id}`);
        
        if (!sel) return;
        
        const categoria = sel.value;
        const comentario = inp ? inp.value.trim() : "";
        
        try {
            const res = await fetch("/api/movimiento/catalogar", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    id_movimiento: id,
                    categoria: categoria,
                    comentario: comentario
                })
            });
            
            const result = await res.json();
            if (result.status === "success") {
                showToast("Cambios guardados con éxito.");
                // Recargar las alertas para refrescar los bordes y estados sugeridos
                loadAlertasData();
            } else {
                showToast("Error al guardar cambios.");
            }
        } catch (e) {
            console.error(e);
            showToast("Error en la conexión al catalogar.");
        }
    };

    async function loadClientes(query = "") {
        try {
            const res = await fetch(`/api/clientes?query=${encodeURIComponent(query)}`);
            const data = await res.json();
            
            const container = document.getElementById("clientes-master-list");
            container.innerHTML = "";
            
            // Leer estado del filtro
            const filterVal = document.getElementById("master-filter-status")?.value || "all";
            const typeFilterVal = document.getElementById("master-filter-type")?.value || "all";
            
            // Filtrar clientes
            let filtered = data;
            if (filterVal === "bien") {
                filtered = filtered.filter(c => c.estado_filtro === "bien");
            } else if (filterVal === "problemas") {
                filtered = filtered.filter(c => c.estado_filtro === "problemas");
            }
            
            if (typeFilterVal !== "all") {
                filtered = filtered.filter(c => c.tipo_cliente === typeFilterVal);
            }
            
            // Actualizar contadores en el pie
            const lblTotal = document.getElementById("master-total-count");
            if (lblTotal) lblTotal.textContent = `Mostrando ${filtered.length} de ${data.length} clientes`;
            
            if (filtered.length > 0) {
                filtered.forEach(c => {
                    const card = document.createElement("div");
                    const isSelected = c.cuit_hash === selectedClienteHash;
                    card.className = isSelected ? "selected-button-wrapper" : "normal-button-wrapper";
                    
                    let tagLabel = c.tipo_cliente === "OS" ? "Obra Social" : "Particular";
                    let tagClass = c.tipo_cliente === "OS" ? "blue" : "orange";
                    
                    let tooltipText = c.tipo_cliente === "OS"
                        ? "Entidad Jurídica u Obra Social."
                        : "Paciente Particular (Facturación Directa).";

                    const btn = document.createElement("button");
                    btn.innerHTML = `
                        <div class="client-card-layout">
                            <div class="client-card-title">👤 ${c.nombre}</div>
                            <div class="client-card-cuit">CUIT: ${c.cuit}</div>
                            <span class="status-chip ${tagClass} client-card-status" onmouseenter="window.showTooltip(event, '${tooltipText}')" onmouseleave="window.hideTooltip()">${tagLabel}</span>
                        </div>
                    `;
                    
                    btn.addEventListener("click", () => {
                        selectedClienteHash = c.cuit_hash;
                        loadClientes(query); // Refrescar selección en maestro
                        showClienteFicha(c.cuit_hash, c.nombre, c.categoria || "Obra Social", c.cuit, c.tipo_cliente);
                    });
                    
                    card.appendChild(btn);
                    container.appendChild(card);
                });
            } else {
                container.innerHTML = `<div class="list-empty-state">No se encontraron clientes</div>`;
            }
        } catch (e) { console.error(e); }
    }

    async function showClienteFicha(cuitHash, nombre, categoria, cuitReal, tipoCliente) {
        try {
            // Ocultar placeholder y mostrar ficha
            document.getElementById("clientes-placeholder").classList.add("hidden");
            const fichaContainer = document.getElementById("cliente-ficha-container");
            fichaContainer.classList.remove("hidden");
            
            const res = await fetch(`/api/cliente/ficha?cuit_hash=${cuitHash}&nombre=${encodeURIComponent(nombre)}`);
            const data = await res.json();
            
            document.getElementById("ficha-cliente-nombre").textContent = nombre;
            // Mostrar CUIT real desencriptado en lugar de hash
            document.getElementById("ficha-cliente-cuit").textContent = `CUIT/DNI: ${cuitReal}`;
            
            // Verificar duplicidades sospechosas en la ficha
            const fDupBanner = document.getElementById("ficha-duplicate-banner");
            const fDupMsg = document.getElementById("ficha-duplicate-msg");
            if (fDupBanner && fDupMsg) {
                sugerenciaActiva = sugerenciasDuplicados.find(s => s.cuit_hash_a === cuitHash || s.cuit_hash_b === cuitHash);
                if (sugerenciaActiva) {
                    fDupBanner.style.display = "flex";
                    const dupNombre = sugerenciaActiva.cuit_hash_a === cuitHash ? sugerenciaActiva.nombre_b : sugerenciaActiva.nombre_a;
                    fDupMsg.textContent = `Este cliente comparte datos con el registro de ${dupNombre}.`;
                } else {
                    fDupBanner.style.display = "none";
                    sugerenciaActiva = null;
                }
            }
            
            const catBadge = document.getElementById("ficha-cliente-categoria-badge");
            let catClass = tipoCliente === "OS" ? "blue" : "orange";
            let catLabel = tipoCliente === "OS" ? "Obra Social" : "Particular";
            catBadge.className = `status-chip ${catClass}`;
            catBadge.innerHTML = catLabel;

            // Calcular montos totales para cada columna
            const totalPrestaciones = data.prestaciones.reduce((sum, p) => sum + p.monto, 0);
            const totalFacturas = data.facturas.reduce((sum, f) => sum + (f.estado === "ACTIVO" ? f.monto_total : 0), 0);
            const totalBanco = data.banco.reduce((sum, b) => sum + b.credito, 0);

            document.getElementById("col-prest-monto-total").textContent = formatCurrency(totalPrestaciones);
            document.getElementById("col-fact-monto-total").textContent = formatCurrency(totalFacturas);
            document.getElementById("col-banco-monto-total").textContent = formatCurrency(totalBanco);

            // Clasificar prestaciones para el gráfico de delay y conciliación
            let montoConciliado = 0;
            let montoDelayNormal = 0;
            let montoDelayExcedido = 0;

            data.prestaciones.forEach(p => {
                if (p.estado_conciliacion === "CONCILIADO") {
                    montoConciliado += p.monto;
                } else {
                    // Si no está conciliado, evaluar el delay contable
                    const diff = getMonthsDiff(p.mes_auditoria, currentPeriod);
                    if (diff <= 3) {
                        montoDelayNormal += p.monto;
                    } else {
                        montoDelayExcedido += p.monto;
                    }
                }
            });

            // Actualizar Leyenda dinámica del gráfico
            const pctConciliado = totalPrestaciones > 0 ? ((montoConciliado / totalPrestaciones) * 100).toFixed(1) : "0.0";
            const pctDelayNormal = totalPrestaciones > 0 ? ((montoDelayNormal / totalPrestaciones) * 100).toFixed(1) : "0.0";
            const pctDelayExcedido = totalPrestaciones > 0 ? ((montoDelayExcedido / totalPrestaciones) * 100).toFixed(1) : "0.0";

            const legendContainer = document.getElementById("chart-cliente-legend");
            legendContainer.innerHTML = `
                <div class="legend-row">
                    <span class="legend-label">
                        <span class="legend-color-dot" style="background-color:#047857;"></span>
                        Conciliado (Match 3 Vías)
                    </span>
                    <span class="legend-value">${formatCurrency(montoConciliado)} (${pctConciliado}%)</span>
                </div>
                <div class="legend-row">
                    <span class="legend-label">
                        <span class="legend-color-dot" style="background-color:#1D4ED8;"></span>
                        Faltante en Delay Normal (&le; 90d)
                    </span>
                    <span class="legend-value">${formatCurrency(montoDelayNormal)} (${pctDelayNormal}%)</span>
                </div>
                <div class="legend-row">
                    <span class="legend-label">
                        <span class="legend-color-dot" style="background-color:#B91C1C;"></span>
                        Faltante Fuera de Delay (&gt; 90d)
                    </span>
                    <span class="legend-value">${formatCurrency(montoDelayExcedido)} (${pctDelayExcedido}%)</span>
                </div>
                <div class="legend-row legend-total">
                    <span class="legend-label">Total Prestaciones</span>
                    <span class="legend-value">${formatCurrency(totalPrestaciones)} (100.0%)</span>
                </div>
            `;

            // Dibujar gráfico horizontal apilado en Chart.js
            if (chartCliente) {
                chartCliente.destroy();
            }
            
            const ctx = document.getElementById("chart-cliente-cobertura").getContext("2d");
            chartCliente = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: [''],
                    datasets: [
                        {
                            label: 'Conciliado',
                            data: [montoConciliado],
                            backgroundColor: '#047857',
                            borderRadius: { topLeft: 6, bottomLeft: 6, topRight: 0, bottomRight: 0 }
                        },
                        {
                            label: 'Delay Normal',
                            data: [montoDelayNormal],
                            backgroundColor: '#1D4ED8',
                            borderRadius: 0
                        },
                        {
                            label: 'Delay Excedido',
                            data: [montoDelayExcedido],
                            backgroundColor: '#B91C1C',
                            borderRadius: { topLeft: 0, bottomLeft: 0, topRight: 6, bottomRight: 6 }
                        }
                    ]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const val = context.raw;
                                    const pct = totalPrestaciones > 0 ? ((val / totalPrestaciones) * 100).toFixed(1) : "0.0";
                                    return `${context.dataset.label}: ${formatCurrency(val)} (${pct}%)`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            stacked: true,
                            max: totalPrestaciones > 0 ? totalPrestaciones : 100,
                            grid: { display: false },
                            ticks: {
                                callback: function(val) {
                                    return formatCurrency(val);
                                },
                                color: '#475569',
                                font: { size: 9 }
                            }
                        },
                        y: {
                            stacked: true,
                            display: false
                        }
                    }
                }
            });

            // 1. Renderizar Pacientes / Prestaciones (Vía 1)
            const listP = document.getElementById("clientes-pacientes-list");
            listP.innerHTML = "";
            if (data.pacientes && data.pacientes.length > 0) {
                data.pacientes.forEach(pac => {
                    const pacWrapper = document.createElement("div");
                    pacWrapper.className = "paciente-item";
                    pacWrapper.style.border = "1px solid #e2e8f0";
                    pacWrapper.style.borderRadius = "8px";
                    pacWrapper.style.overflow = "hidden";
                    
                    let htmlPrestaciones = pac.prestaciones.map(p => {
                        let statusIndicator = "";
                        if (p.estado_conciliacion === "CONCILIADO") statusIndicator = `<span class="status-chip green">Conciliado</span>`;
                        else if (p.estado_conciliacion === "DISCREPANCIA") statusIndicator = `<span class="status-chip red">Discrepancia</span>`;
                        else statusIndicator = `<span class="status-chip warning">Pendiente</span>`;
                        
                        return `
                        <div class="listview-item" style="border-top: 1px solid #e2e8f0; border-radius: 0; margin-bottom: 0;">
                            <div class="listview-item-title">${p.fecha_factura} - ${p.periodo}</div>
                            <div class="listview-item-details">
                                <span class="listview-item-date">Factura Nº ${p.factura_nro || "S/N"}</span>
                                ${statusIndicator}
                                <div class="listview-item-right">
                                    <span class="listview-item-amount font-mono color-primary">${formatCurrency(p.monto)}</span>
                                </div>
                            </div>
                        </div>
                        `;
                    }).join("");

                    pacWrapper.innerHTML = `
                        <div style="background: var(--bg-secondary); padding: 10px 15px; display: flex; justify-content: space-between; align-items: center; font-weight: 600;">
                            <span><span style="opacity:0.6; margin-right:5px;">👤</span> ${pac.paciente}</span>
                            <span class="font-mono">${formatCurrency(pac.total_monto)}</span>
                        </div>
                        <div style="display:flex; flex-direction:column;">
                            ${htmlPrestaciones}
                        </div>
                    `;
                    listP.appendChild(pacWrapper);
                });
            } else {
                listP.innerHTML = `<div class="list-empty-state">Sin prestaciones registradas</div>`;
            }
            
            // 2. Renderizar Facturas (Vía 2)
            const listF = document.getElementById("clientes-facturas-list");
            listF.innerHTML = "";
            if (data.facturas.length > 0) {
                data.facturas.forEach(f => {
                    const isAct = f.estado.toUpperCase() === "ACTIVO";
                    const borderCol = isAct ? "border-success" : "border-danger";
                    const statusIndicator = `<span class="status-indicator ${isAct ? 'green' : 'red'}" title="${f.estado}"></span>`;
                    
                    const item = document.createElement("div");
                    item.className = `listview-item ${borderCol}`;
                    
                    // Alerta de CUIT si la factura proviene de match indirecto por prestación
                    let cuitWarningHtml = "";
                    let cuitTooltipPart = "";
                    if (f.diferencia_cuit) {
                        cuitWarningHtml = `<span class="cuit-warning-badge" style="background-color:#fff7ed; color:#c2410c; border: 1px solid #ffedd5; font-size:0.65rem; font-weight:700; padding:2px 6px; border-radius:4px; margin-left:8px; cursor:help;" onmouseenter="showTooltip(event, 'La factura fue emitida al DNI/CUIT de 8 dígitos de esta persona o institución y se asoció mediante coincidencia difusa')" onmouseleave="hideTooltip()">⚠️ CUIT: ${f.cuit_factura}</span>`;
                        cuitTooltipPart = `<br>⚠️ <strong>Diferencia de CUIT:</strong> Factura emitida al CUIT/DNI ${f.cuit_factura} (se asoció indirectamente a través del match de prestaciones).`;
                    }
                    
                    const tooltipText = `<strong>Procedencia:</strong><br>📄 Archivo: ${f.archivo_origen || 'Desconocido'}<br>📍 Fila: ${f.nro_fila || '—'}${cuitTooltipPart}`;
                    
                    item.innerHTML = `
                        <div class="listview-item-title" title="${f.comprobante_id}" style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:4px;">
                            <span>${f.comprobante_id}</span>
                            ${cuitWarningHtml}
                        </div>
                        <div class="listview-item-details">
                            <div class="listview-item-meta-group">
                                <span class="listview-item-date">${f.fecha_emision}</span>
                                ${statusIndicator}
                            </div>
                            <div class="listview-item-right">
                                <span class="listview-item-amount color-blue">${formatCurrency(f.monto_total)}</span>
                                <span class="audit-info-trigger" 
                                      onmouseenter="showTooltip(event, \`${tooltipText}\`)" 
                                      onmouseleave="hideTooltip()">i</span>
                            </div>
                        </div>
                    `;
                    listF.appendChild(item);
                });
            } else {
                listF.innerHTML = `<div class="list-empty-state">Sin facturas registradas</div>`;
            }
            
            // 3. Renderizar Banco (Vía 3)
            const listB = document.getElementById("clientes-banco-list");
            listB.innerHTML = "";
            if (data.banco.length > 0) {
                data.banco.forEach(b => {
                    const item = document.createElement("div");
                    item.className = `listview-item border-success`;
                    
                    const tooltipText = `<strong>Procedencia:</strong><br>🏦 Archivo: ${b.archivo_origen || 'Desconocido'}<br>📍 Fila: ${b.nro_fila || '—'}`;
                    
                    item.innerHTML = `
                        <div class="listview-item-title" title="${b.concepto}">${b.concepto}</div>
                        <div class="listview-item-details">
                            <span class="listview-item-date">${b.fecha}</span>
                            <div class="listview-item-right">
                                <span class="listview-item-amount color-success">${formatCurrency(b.credito)}</span>
                                <span class="audit-info-trigger" 
                                      onmouseenter="showTooltip(event, \`${tooltipText}\`)" 
                                      onmouseleave="hideTooltip()">i</span>
                            </div>
                        </div>
                    `;
                    listB.appendChild(item);
                });
            } else {
                listB.innerHTML = `<div class="list-empty-state">Sin depósitos identificados</div>`;
            }
            
            // Auto-scroll suave hacia el panel de detalle en pantallas chicas
            document.getElementById("clientes-detail-panel").scrollTop = 0;
        } catch (e) { console.error(e); }
    }

    document.getElementById("btn-cerrar-ficha").addEventListener("click", () => {
        document.getElementById("cliente-ficha-container").classList.add("hidden");
        document.getElementById("clientes-placeholder").classList.remove("hidden");
        selectedClienteHash = null;
        loadClientes(clientSearchInp.value.trim()); // Refrescar maestro para quitar selección
    });

    // --- MODAL DE INGRESOS SIN IDENTIFICAR ---
    const kpiCardSinId = document.getElementById("kpi-card-sin-id");
    const modalSinId = document.getElementById("sin-identificar-modal");
    
    if (kpiCardSinId && modalSinId) {
        kpiCardSinId.addEventListener("click", async () => {
            document.getElementById("lbl-sin-id-periodo").textContent = formatPeriod(currentPeriod) || currentPeriod;
            const tbody = document.getElementById("tbl-sin-id-body");
            tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 20px; color: var(--text-secondary);">Cargando depósitos sin identificar...</td></tr>`;
            modalSinId.classList.remove("hidden");
            
            try {
                const res = await fetch(`/api/dashboard/sin_identificar?periodo=${currentPeriod}`);
                const data = await res.json();
                
                tbody.innerHTML = "";
                if (data.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 20px; color: var(--text-secondary);">No hay cobros sin asociar en este período. 🎉</td></tr>`;
                } else {
                    data.forEach(item => {
                        const tr = document.createElement("tr");
                        tr.style.borderBottom = "1px solid var(--border-color)";
                        
                        const tooltipText = `<strong>Procedencia:</strong><br>🏦 Archivo: ${item.archivo_origen || 'Desconocido'}<br>📍 Fila: ${item.nro_fila || '—'}`;
                        
                        tr.innerHTML = `
                            <td style="padding: 10px 15px;">${item.fecha}</td>
                            <td style="padding: 10px 15px; font-weight: 500;">${item.concepto}</td>
                            <td style="padding: 10px 15px; color: var(--text-secondary);">${item.detalle || '—'}</td>
                            <td style="padding: 10px 15px; font-weight: 600; text-align: right; color: var(--color-green);">${formatCurrency(item.monto)}</td>
                            <td style="padding: 10px 15px; text-align: center;">
                                <span class="audit-info-trigger" 
                                      onmouseenter="window.showTooltip(event, \`${tooltipText}\`)" 
                                      onmouseleave="window.hideTooltip()">i</span>
                            </td>
                        `;
                        tbody.appendChild(tr);
                    });
                }
            } catch (e) {
                console.error(e);
                tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 20px; color: var(--color-red);">Error al cargar los datos.</td></tr>`;
            }
        });
        
        // Cierre del modal
        const btnClose1 = document.getElementById("btn-close-sin-id");
        const btnClose2 = document.getElementById("btn-close-sin-id-ok");
        
        [btnClose1, btnClose2].forEach(btn => {
            if (btn) {
                btn.addEventListener("click", () => {
                    modalSinId.classList.add("hidden");
                });
            }
        });
    }

    // --- CONTROLADOR DE FUSIÓN Y UNIFICACIÓN DE CLIENTES ---
    const btnFichaUnificar = document.getElementById("btn-ficha-unificar-cuit");
    const btnDashboardReview = document.getElementById("btn-dashboard-review-duplicates");
    const btnCancelFusion = document.getElementById("btn-cancel-fusion");
    const btnConfirmFusion = document.getElementById("btn-confirm-fusion");
    const fusionModal = document.getElementById("fusion-modal");

    // Función para abrir el modal cargando los dos clientes y sus montos
    async function abrirModalFusion(sug) {
        if (!sug) return;
        
        // Cargar nombres, CUITs y justificación del motivo
        document.getElementById("fusion-main-name").textContent = sug.nombre_a;
        document.getElementById("fusion-main-cuit").textContent = `CUIT: ${sug.cuit_a}`;
        
        document.getElementById("fusion-dup-name").textContent = sug.nombre_b;
        document.getElementById("fusion-dup-cuit").textContent = `CUIT: ${sug.cuit_b}`;
        
        // Cargar motivo en el banner del modal
        const reasonText = document.getElementById("fusion-reason-text");
        if (reasonText) {
            reasonText.textContent = sug.razon_detallada || sug.razon || "Similitud de identificador fiscal o coincidencia de palabras significativas.";
        }
        
        // Colocar montos y procedencias inicialmente
        document.getElementById("fusion-main-prest").textContent = "...";
        document.getElementById("fusion-main-fact").textContent = "...";
        document.getElementById("fusion-main-banc").textContent = "...";
        document.getElementById("fusion-dup-prest").textContent = "...";
        document.getElementById("fusion-dup-fact").textContent = "...";
        document.getElementById("fusion-dup-banc").textContent = "...";
        
        const mainProc = document.getElementById("fusion-main-proc");
        const dupProc = document.getElementById("fusion-dup-proc");
        if (mainProc && dupProc) {
            mainProc.innerHTML = sug.procedencia_a && sug.procedencia_a.length > 0
                ? sug.procedencia_a.map(p => `<div style="padding: 2px 0;">${p}</div>`).join("")
                : `<div style="opacity: 0.6; font-style: italic;">Sin transacciones directas asociadas</div>`;
                
            dupProc.innerHTML = sug.procedencia_b && sug.procedencia_b.length > 0
                ? sug.procedencia_b.map(p => `<div style="padding: 2px 0;">${p}</div>`).join("")
                : `<div style="opacity: 0.6; font-style: italic;">Sin transacciones directas asociadas</div>`;
        }
        
        fusionModal.classList.remove("hidden");
        
        // Obtener montos acumulados llamando a la ficha de cada uno para comparar
        try {
            const resA = await fetch(`/api/cliente/ficha?cuit_hash=${sug.cuit_hash_a}&nombre=${encodeURIComponent(sug.nombre_a)}`);
            const dataA = await resA.json();
            const totalPrestA = dataA.prestaciones.reduce((sum, p) => sum + p.monto, 0);
            const totalFactA = dataA.facturas.reduce((sum, f) => sum + (f.estado === "ACTIVO" ? f.monto_total : 0), 0);
            const totalBancA = dataA.banco.reduce((sum, b) => sum + b.credito, 0);
            
            document.getElementById("fusion-main-prest").textContent = formatCurrency(totalPrestA);
            document.getElementById("fusion-main-fact").textContent = formatCurrency(totalFactA);
            document.getElementById("fusion-main-banc").textContent = formatCurrency(totalBancA);
            
            const resB = await fetch(`/api/cliente/ficha?cuit_hash=${sug.cuit_hash_b}&nombre=${encodeURIComponent(sug.nombre_b)}`);
            const dataB = await resB.json();
            const totalPrestB = dataB.prestaciones.reduce((sum, p) => sum + p.monto, 0);
            const totalFactB = dataB.facturas.reduce((sum, f) => sum + (f.estado === "ACTIVO" ? f.monto_total : 0), 0);
            const totalBancB = dataB.banco.reduce((sum, b) => sum + b.credito, 0);
            
            document.getElementById("fusion-dup-prest").textContent = formatCurrency(totalPrestB);
            document.getElementById("fusion-dup-fact").textContent = formatCurrency(totalFactB);
            document.getElementById("fusion-dup-banc").textContent = formatCurrency(totalBancB);
        } catch (e) {
            console.error("Error al cargar detalles comparativos:", e);
        }
    }

    if (btnFichaUnificar) {
        btnFichaUnificar.addEventListener("click", () => {
            abrirModalFusion(sugerenciaActiva);
        });
    }

    if (btnDashboardReview) {
        btnDashboardReview.addEventListener("click", () => {
            if (sugerenciasDuplicados.length > 0) {
                abrirModalFusion(sugerenciasDuplicados[0]);
            }
        });
    }

    if (btnCancelFusion) {
        btnCancelFusion.addEventListener("click", () => {
            fusionModal.classList.add("hidden");
        });
    }

    if (btnConfirmFusion) {
        btnConfirmFusion.addEventListener("click", async () => {
            const sug = sugerenciaActiva || (sugerenciasDuplicados.length > 0 ? sugerenciasDuplicados[0] : null);
            if (!sug) return;
            
            btnConfirmFusion.disabled = true;
            btnConfirmFusion.textContent = "Unificando...";
            
            try {
                const res = await fetch("/api/clientes/fusionar", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        cuit_hash_principal: sug.cuit_hash_a,
                        cuit_hash_duplicado: sug.cuit_hash_b
                    })
                });
                const data = await res.json();
                
                if (data.status === "success") {
                    alert("Clientes fusionados con éxito.");
                    fusionModal.classList.add("hidden");
                    
                    // Limpiar la ficha y el banner
                    document.getElementById("cliente-ficha-container").classList.add("hidden");
                    document.getElementById("clientes-placeholder").classList.remove("hidden");
                    selectedClienteHash = null;
                    
                    // Recargar todo reactivamente
                    await loadDashboardData();
                    await loadClientes(clientSearchInp.value.trim());
                } else {
                    alert(`Error al fusionar: ${data.detail || "Error desconocido"}`);
                }
            } catch (e) {
                console.error(e);
                alert("Error de conexión al fusionar clientes.");
            } finally {
                btnConfirmFusion.disabled = false;
                btnConfirmFusion.textContent = "🔗 Confirmar Fusión";
            }
        });
    }

    // Evento para alternar el dropdown de la campana de notificaciones
    const btnHeaderNotif = document.getElementById("btn-header-notif");
    const headerNotifDropdown = document.getElementById("header-notif-dropdown");
    if (btnHeaderNotif && headerNotifDropdown) {
        btnHeaderNotif.addEventListener("click", (e) => {
            e.stopPropagation();
            headerNotifDropdown.classList.toggle("hidden");
        });
        
        // Cerrar dropdown al hacer click en cualquier otra parte
        document.addEventListener("click", (e) => {
            if (!e.target.closest(".header-notif-wrapper")) {
                headerNotifDropdown.classList.add("hidden");
            }
        });
    }

    // Evento para descartar permanentemente un posible duplicado (No es la misma persona)
    const btnDismissDuplicate = document.getElementById("btn-dismiss-duplicate");
    if (btnDismissDuplicate) {
        btnDismissDuplicate.addEventListener("click", async () => {
            const sug = sugerenciaActiva || (sugerenciasDuplicados.length > 0 ? sugerenciasDuplicados[0] : null);
            if (!sug) return;
            
            btnDismissDuplicate.disabled = true;
            btnDismissDuplicate.textContent = "Descartando...";
            
            try {
                const res = await fetch("/api/clientes/descartar-duplicado", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        cuit_hash_a: sug.cuit_hash_a,
                        cuit_hash_b: sug.cuit_hash_b
                    })
                });
                const data = await res.json();
                
                if (data.status === "success") {
                    alert("Pareja descartada de forma permanente.");
                    fusionModal.classList.add("hidden");
                    
                    // Recargar todo reactivamente para quitar el elemento
                    await loadDashboardData();
                    if (typeof loadClientes === "function") {
                        await loadClientes(clientSearchInp.value.trim());
                    }
                } else {
                    alert(`Error al descartar: ${data.detail || "Error desconocido"}`);
                }
            } catch (e) {
                console.error(e);
                alert("Error de conexión al descartar sugerencia.");
            } finally {
                btnDismissDuplicate.disabled = false;
                btnDismissDuplicate.textContent = "🛡️ No es la misma persona";
            }
        });
    }

    // --- CARGAR / IMPORTAR ARCHIVOS ---
    const importForm = document.getElementById("import-form");
    const importReport = document.getElementById("import-report-container");
    
    importForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const filePrest = document.getElementById("file_prest").files[0];
        const fileAfip = document.getElementById("file_afip").files[0];
        const fileBanco = document.getElementById("file_banco").files[0];
        
        if (!filePrest && !fileAfip && !fileBanco) {
            alert("Sube al menos un archivo para procesar.");
            return;
        }
        
        // UI loading state
        const btnText = document.getElementById("import-btn-text");
        const btnSpinner = document.getElementById("import-spinner");
        const btnSubmit = document.getElementById("btn-submit-import");
        
        btnText.textContent = "Procesando archivos...";
        btnSpinner.classList.remove("hidden");
        btnSubmit.disabled = true;
        importReport.classList.add("hidden");
        
        const fd = new FormData();
        fd.append("periodo", currentPeriod);
        if (filePrest) fd.append("file_prest", filePrest);
        if (fileAfip) fd.append("file_afip", fileAfip);
        if (fileBanco) fd.append("file_banco", fileBanco);
        
        try {
            const res = await fetch("/api/importar", {
                method: "POST",
                body: fd
            });
            
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Error al procesar archivos");
            }
            
            const data = await res.json();
            
            // Mostrar reporte
            document.getElementById("rep-prest-count").textContent = data.imported.prestaciones || 0;
            document.getElementById("rep-afip-count").textContent = data.imported.afip || 0;
            document.getElementById("rep-banco-count").textContent = data.imported.banco || 0;
            
            document.getElementById("rep-conc").textContent = data.conciliados;
            document.getElementById("rep-pend-fact").textContent = data.pendientes_factura;
            document.getElementById("rep-pend-cobro").textContent = data.pendientes_cobro;
            document.getElementById("rep-disc").textContent = data.discrepancias;
            
            importReport.classList.remove("hidden");
            importForm.reset();
            // Ir al reporte
            importReport.scrollIntoView({ behavior: 'smooth' });
        } catch (err) {
            alert(err.message);
        } finally {
            btnText.textContent = "Procesar Archivos Subidos";
            btnSpinner.classList.add("hidden");
            btnSubmit.disabled = false;
        }
    });

    // --- EXPORTAR REPORTES ---
    const btnDownloadReport = document.getElementById("btn-download-report");
    if (btnDownloadReport) {
        btnDownloadReport.addEventListener("click", () => {
            window.open(`/api/exportar?periodo=${currentPeriod}`, "_blank");
        });
    }

    // --- MANEJO DEL MODAL DE CAMBIOS SIN GUARDAR ---
    const unsavedModal = document.getElementById("unsaved-modal");
    const btnModalSave = document.getElementById("btn-modal-save");
    const btnModalDiscard = document.getElementById("btn-modal-discard");
    const btnModalCancel = document.getElementById("btn-modal-cancel");
    
    function showUnsavedModal() {
        if (unsavedModal) unsavedModal.classList.remove("hidden");
    }
    
    function hideUnsavedModal() {
        if (unsavedModal) unsavedModal.classList.add("hidden");
    }
    
    if (btnModalCancel) {
        btnModalCancel.addEventListener("click", () => {
            hideUnsavedModal();
            pendingAction = null;
        });
    }
    
    if (btnModalDiscard) {
        btnModalDiscard.addEventListener("click", () => {
            hideUnsavedModal();
            setHasUnsavedChanges(false);
            if (pendingAction) {
                pendingAction();
                pendingAction = null;
            }
        });
    }
    
    if (btnModalSave) {
        btnModalSave.addEventListener("click", async () => {
            hideUnsavedModal();
            let saveSuccess = false;
            if (conciliacionCamino === "A") {
                saveSuccess = await saveManualConciliacionA();
            } else if (conciliacionCamino === "B") {
                saveSuccess = await saveManualConciliacionB();
            }
            
            if (saveSuccess) {
                setHasUnsavedChanges(false);
                if (pendingAction) {
                    pendingAction();
                    pendingAction = null;
                }
            } else {
                pendingAction = null;
            }
        });
    }

    // Escuchar cambios para marcar hasUnsavedChanges
    const detailContainer = document.getElementById("detail-panel-container");
    if (detailContainer) {
        detailContainer.addEventListener("change", (e) => {
            if (e.target && (e.target.id === "search_banco_text_a" || e.target.id === "chk_filtrar_monto_a" || 
                             e.target.id === "search_prest_text_b" || e.target.id === "chk_filtrar_monto_prest_b")) {
                return;
            }
            setHasUnsavedChanges(true);
        });
        
        detailContainer.addEventListener("input", (e) => {
            if (e.target && (e.target.id === "txt_observaciones_a" || e.target.id === "txt_observaciones_b")) {
                setHasUnsavedChanges(true);
            }
        });
    }
});

// --- GLOBAL TOOLTIP SYSTEM ---
const globalTooltip = document.createElement('div');
globalTooltip.id = 'global-tooltip';
document.body.appendChild(globalTooltip);

let tooltipTimer = null;

window.showTooltip = function(event, text) {
    // Limpiar timer previo si existiera
    if (tooltipTimer) clearTimeout(tooltipTimer);
    
    // Guardar referencia al elemento original
    const targetEl = event.target;
    
    tooltipTimer = setTimeout(() => {
        globalTooltip.innerHTML = text;
        globalTooltip.classList.add('active');
        
        const rect = targetEl.getBoundingClientRect();
        const tooltipRect = globalTooltip.getBoundingClientRect();
        
        // Por defecto arriba centrado
        let top = rect.top - tooltipRect.height - 8;
        let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
        
        // Si se sale por arriba, mostrar debajo
        if (top < 10) {
            top = rect.bottom + 8;
        }
        
        // Si se sale por izquierda/derecha
        if (left < 10) {
            left = 10;
        } else if (left + tooltipRect.width > window.innerWidth - 10) {
            left = window.innerWidth - tooltipRect.width - 10;
        }
        
        globalTooltip.style.top = `${top}px`;
        globalTooltip.style.left = `${left}px`;
    }, 1000); // 1 segundo de delay
};

window.hideTooltip = function() {
    if (tooltipTimer) clearTimeout(tooltipTimer);
    globalTooltip.classList.remove('active');
};
