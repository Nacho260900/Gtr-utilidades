import os
import time
import json
import asyncio
import ctypes
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()

USUARIO = os.getenv("USUARIO", "1839")
PASSWORD = os.getenv("PASSWORD", "2022")

async def extraer_datos_de_monitor(page, monitor_id, monitor_label=""):
    """
    Extrae la lista completa de filas y datos de agentes en tiempo real desde la tabla #grid1_rows.
    """
    if not page or page.is_closed():
        return None
    try:
        data = await page.evaluate("""
        () => {
            const rows = Array.from(document.querySelectorAll("#grid1_rows tr"));
            const totalText = document.getElementById("grid1_registros")?.textContent?.trim() || "";
            
            const agentes = rows.map((tr) => {
                const tds = Array.from(tr.querySelectorAll("td"));
                if (tds.length < 3) return null;
                
                const rawUsuario = tds[0].textContent.trim();
                const rawEstado = tds[1].textContent.trim();
                const rawCampana = tds[2].textContent.trim();
                const bgColor = tr.style.backgroundColor || "";
                
                // Extraer Usuario: "1014 - VERONICA , RUSSO"
                let id_usuario = "";
                let nombre = rawUsuario;
                const uMatch = rawUsuario.match(/^(\\d+)\\s*-\\s*(.+)$/);
                if (uMatch) {
                    id_usuario = uMatch[1].trim();
                    nombre = uMatch[2].trim();
                }
                
                // Extraer Estado: "Agente (0:02:44) | 111557616871 (NO PROCESADO)" o "Logueado (0:00:09)"
                let estado = rawEstado;
                let duracion = "";
                let telefono = "";
                let tipo_llamada = "";
                
                const partsEstado = rawEstado.split("|").map(s => s.trim());
                const eMatch = partsEstado[0].match(/^([^(]+)\\s*\\(([^)]+)\\)/);
                if (eMatch) {
                    estado = eMatch[1].trim();
                    duracion = eMatch[2].trim();
                } else {
                    estado = partsEstado[0];
                }
                
                if (partsEstado.length > 1) {
                    const telPart = partsEstado[1];
                    const tMatch = telPart.match(/^([^(]+)(?:\\(([^)]+)\\))?/);
                    if (tMatch) {
                        telefono = (tMatch[1] || "").trim();
                        tipo_llamada = (tMatch[2] || "").trim();
                    }
                }
                
                // Extraer Campaña: "50 - PREDICTIVO PORTABILIDAD (Predictivo) | N/A"
                let id_campana = "";
                let campana = rawCampana;
                let tipo_discador = "";
                let cola = "";
                
                const partsCamp = rawCampana.split("|").map(s => s.trim());
                if (partsCamp.length > 1) {
                    cola = partsCamp[1];
                }
                
                const cMatch = partsCamp[0].match(/^([^(]+)(?:\\(([^)]+)\\))?/);
                if (cMatch) {
                    const campText = cMatch[1].trim();
                    tipo_discador = (cMatch[2] || "").trim();
                    const cidMatch = campText.match(/^(\\d+)\\s*-\\s*(.+)$/);
                    if (cidMatch) {
                        id_campana = cidMatch[1].trim();
                        campana = cidMatch[2].trim();
                    } else {
                        campana = campText;
                    }
                }
                
                return {
                    id_usuario,
                    nombre,
                    estado,
                    duracion,
                    telefono,
                    tipo_llamada,
                    id_campana,
                    campana,
                    tipo_discador,
                    cola,
                    color_fondo: bgColor,
                    raw: {
                        usuario: rawUsuario,
                        estado: rawEstado,
                        campana: rawCampana
                    }
                };
            }).filter(Boolean);
            
            return {
                total_registros_texto: totalText,
                total_registros: agentes.length,
                agentes: agentes
            };
        }
        """)
        if data:
            data["monitor_id"] = monitor_id
            data["monitor_label"] = monitor_label
            return data
    except Exception as e:
        return {"monitor_id": monitor_id, "monitor_label": monitor_label, "error": str(e), "agentes": []}
    return None

def duracion_a_segundos(dur_str):
    """
    Convierte formatos 'H:MM:SS', 'MM:SS' o 'S' a segundos enteros.
    """
    if not dur_str:
        return 0
    try:
        parts = [int(p) for p in str(dur_str).strip().split(":") if p.strip().isdigit()]
        if len(parts) == 3:  # H:MM:SS
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:  # MM:SS
            return parts[0] * 60 + parts[1]
        elif len(parts) == 1:
            return parts[0]
    except Exception:
        return 0
    return 0

def segundos_a_duracion(segundos):
    """
    Convierte una cantidad de segundos a formato HH:MM:SS
    """
    total_sec = int(round(segundos))
    h = total_sec // 3600
    m = (total_sec % 3600) // 60
    s = total_sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

async def ciclo_captura_tiempo_real(monitores_info, intervalo=3, json_file="monitores_live.json"):
    """
    Ciclo continuo que extrae datos y calcula el tiempo promedio de agentes en 'Logueado' de los 3 monitores cada 3 segundos.
    """
    print(f"\n[INFO] Extractor en tiempo real activo (cada {intervalo}s). Datos guardados en: '{json_file}'")
    print("Calculando tiempo promedio de agentes en estado 'Logueado' (Promedio Global de los 3 Monitores)...\n")
    print("Presiona Ctrl+C en esta terminal para detener la ejecucion y cerrar los monitores.\n")
    
    while True:
        timestamp_ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        resumen_monitores = {
            "timestamp": timestamp_ahora,
            "metricas_logueados": {
                "global": {},
                "por_monitor": {}
            },
            "monitores": []
        }
        
        todas_duraciones_seg = []
        breakdown_console = []
        
        for info in monitores_info:
            page_obj = info.get("page")
            m_id = info.get("id")
            m_label = info.get("label", "")
            
            m_data = await extraer_datos_de_monitor(page_obj, m_id, m_label)
            if m_data and "error" not in m_data:
                resumen_monitores["monitores"].append(m_data)
                
                # Filtrar agentes en estado "Logueado" (independiente del color de fondo de la fila)
                agentes_logueados = [
                    ag for ag in m_data.get("agentes", [])
                    if "logueado" in ag.get("estado", "").lower()
                ]
                
                duraciones_seg = [
                    duracion_a_segundos(ag.get("duracion", "0"))
                    for ag in agentes_logueados
                ]
                
                todas_duraciones_seg.extend(duraciones_seg)
                
                cant_log = len(agentes_logueados)
                if cant_log > 0:
                    prom_seg = sum(duraciones_seg) / cant_log
                    min_seg = min(duraciones_seg)
                    max_seg = max(duraciones_seg)
                    prom_fmt = segundos_a_duracion(prom_seg)
                    min_fmt = segundos_a_duracion(min_seg)
                    max_fmt = segundos_a_duracion(max_seg)
                else:
                    prom_seg = 0
                    prom_fmt = "00:00:00"
                    min_fmt = "00:00:00"
                    max_fmt = "00:00:00"
                    
                resumen_monitores["metricas_logueados"]["por_monitor"][str(m_id)] = {
                    "label": m_label,
                    "agentes_logueados": cant_log,
                    "promedio_segundos": round(prom_seg, 2),
                    "promedio_formato": prom_fmt,
                    "minimo_formato": min_fmt,
                    "maximo_formato": max_fmt
                }
                
                breakdown_console.append(f"M{m_id}: {cant_log} ({prom_fmt})")
            else:
                err_msg = m_data.get("error", "Desconectado") if m_data else "Cerrado"
                breakdown_console.append(f"M{m_id}: [Error]")
        
        # Cálculo métricas globales consolidadas (todos los agentes logueados de los 3 monitores)
        total_global = len(todas_duraciones_seg)
        if total_global > 0:
            prom_global_seg = sum(todas_duraciones_seg) / total_global
            min_global_seg = min(todas_duraciones_seg)
            max_global_seg = max(todas_duraciones_seg)
            prom_global_fmt = segundos_a_duracion(prom_global_seg)
            min_global_fmt = segundos_a_duracion(min_global_seg)
            max_global_fmt = segundos_a_duracion(max_global_seg)
        else:
            prom_global_seg = 0
            prom_global_fmt = "00:00:00"
            min_global_fmt = "00:00:00"
            max_global_fmt = "00:00:00"
            
        resumen_monitores["metricas_logueados"]["global"] = {
            "total_agentes_logueados": total_global,
            "promedio_segundos": round(prom_global_seg, 2),
            "promedio_formato": prom_global_fmt,
            "minimo_formato": min_global_fmt,
            "maximo_formato": max_global_fmt
        }
        
        # Guardar en archivo JSON local en tiempo real
        try:
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(resumen_monitores, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error al escribir en {json_file}: {e}")
            
        linea_log = f"[{timestamp_ahora}] [LOGUEADOS GLOBAL] Total: {total_global} | Promedio: {prom_global_fmt} ({prom_global_seg:.1f}s) | " + " | ".join(breakdown_console)
        print(linea_log)
            
        await asyncio.sleep(intervalo)


async def ejecutar_flujo_completo(browser, window_index, campana_text, estados_list=None):
    print(f"\n==========================================")
    print(f"   [Ventana {window_index}] Iniciando proceso completo")
    print(f"==========================================")
    
    # Cada flujo se ejecuta en un contexto independiente (ventana independiente con sesión propia)
    context = await browser.new_context(no_viewport=True)
    page = await context.new_page()
    
    url = "http://172.16.20.10/NEOTEL/"
    print(f"[{window_index}] 1. Navegando a {url}...")
    try:
        await page.goto(url, timeout=30000)
    except Exception as e:
        print(f"[{window_index}] Error de conexion al abrir la IP: {e}")
        return None
        
    print(f"[{window_index}] 2. Esperando formulario de login...")
    try:
        usuario_xpath = 'xpath=//*[@id="txtUsuario"]'
        password_xpath = 'xpath=//*[@id="txtClave"]'
        login_btn_xpath = 'xpath=//*[@id="NeoIngresarButton1"]'
        
        # Buscar frame de login
        login_frame = None
        for _ in range(20):
            for frame in page.frames:
                if await frame.locator(usuario_xpath).count() > 0:
                    login_frame = frame
                    break
            if login_frame:
                break
            await asyncio.sleep(1)
            
        if not login_frame:
            print(f"[{window_index}] Error: No se encontro el frame de login.")
            return None
            
        print(f"[{window_index}] 3. Completando credenciales...")
        await login_frame.locator(usuario_xpath).fill(USUARIO)
        await login_frame.locator(password_xpath).fill(PASSWORD)
        
        print(f"[{window_index}] 4. Haciendo clic en 'Log In'...")
        await login_frame.locator(login_btn_xpath).click()
        print(f"[{window_index}] Login enviado. Esperando panel principal...")
        
    except Exception as e:
        print(f"[{window_index}] Error al iniciar sesion: {e}")
        return None

    # 5. Esperar al frame interactivo de modulos buscando '#favDiv2'
    print(f"[{window_index}] 5. Localizando panel de modulos (#favDiv2)...")
    modulos_frame = None
    for _ in range(25):
        for frame in page.frames:
            try:
                if await frame.locator("#favDiv2").count() > 0:
                    modulos_frame = frame
                    break
            except Exception:
                pass
        if modulos_frame:
            break
        await asyncio.sleep(1)
        
    if not modulos_frame:
        print(f"[{window_index}] Error: No se localizo el frame de modulos.")
        return None
        
    # 6. Hacer clic en CRM
    print(f"[{window_index}] 6. Haciendo clic en 'CRM'...")
    try:
        crm_card = modulos_frame.locator("#favDiv2")
        await crm_card.wait_for(state="visible", timeout=15000)
        await crm_card.click()
    except Exception as e:
        print(f"[{window_index}] Error al hacer clic en CRM: {e}")
        return None
        
    # 7. Seleccionar '1 - MOVISTAR'
    print(f"[{window_index}] 7. Seleccionando opcion '1 - MOVISTAR'...")
    try:
        cbo_crm = modulos_frame.locator("select#cboCRM")
        await cbo_crm.wait_for(state="attached", timeout=10000)
        await cbo_crm.select_option(value="1")
        await cbo_crm.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
        await asyncio.sleep(1)
        
        try:
            await modulos_frame.locator(".sumo_cboCRM p.CaptionCont").click(timeout=3000)
            await asyncio.sleep(0.5)
            await modulos_frame.locator(".sumo_cboCRM .options li:has-text('1 - MOVISTAR')").click(timeout=3000)
        except Exception:
            pass
            
    except Exception as e:
        print(f"[{window_index}] Error al seleccionar opcion en dropdown: {e}")
        return None
        
    # 8. Confirmar seleccion con #btnSeleccionar
    print(f"[{window_index}] 8. Confirmando seleccion con 'Seleccionar'...")
    try:
        confirm_btn = modulos_frame.locator("#btnSeleccionar")
        await confirm_btn.wait_for(state="visible", timeout=10000)
        await confirm_btn.click()
        
        try:
            await modulos_frame.locator(".waiting_div2, #imgLoading").wait_for(state="hidden", timeout=15000)
        except Exception:
            pass
            
    except Exception as e:
        print(f"[{window_index}] Error al hacer clic en Seleccionar: {e}")
        return None

    # 9. Esperar alerta SweetAlert ('OK') y confirmar
    print(f"[{window_index}] 9. Esperando alerta flotante SweetAlert ('OK')...")
    main_frame = None
    for _ in range(25):
        for frame in page.frames:
            if frame.name == "main" or "default.aspx" in frame.url:
                main_frame = frame
                break
        if main_frame:
            break
        await asyncio.sleep(1)
        
    if not main_frame:
        print(f"[{window_index}] Error: No se localizo el frame 'main'.")
        return None
        
    try:
        confirm_alert_btn = main_frame.locator("button.confirm")
        await confirm_alert_btn.wait_for(state="visible", timeout=15000)
        await confirm_alert_btn.click()
        print(f"[{window_index}] Alerta flotante confirmada (OK).")
        await asyncio.sleep(2)
    except Exception as e:
        print(f"[{window_index}] Alerta flotante no requerida o confirmada: {e}")

    # 10. Abrir monitor de usuarios llamando a setIFramePage()
    print(f"[{window_index}] 10. Abriendo monitor de usuarios llamando a setIFramePage()...")
    try:
        await main_frame.evaluate("""
            setIFramePage(
                'ControlBoards_Custom_Test.aspx?TIPOACCION=EJ&IDPROC=5&DESCRIP=USERS_MONITOR&IDOPERACION=2&IDDATASOURCE=0&TYPE=5',
                'Monitor de usuarios',
                '',
                1,
                'fal fa-monitor-heart-rate'
            )
        """)
    except Exception as e:
        print(f"[{window_index}] Error al llamar a setIFramePage: {e}")
        return None
        
    # 11. Localizar panel de ejecución
    print(f"[{window_index}] 11. Localizando panel de ejecucion...")
    exec_frame = None
    for _ in range(40):
        for frame in page.frames:
            try:
                if await frame.locator("#EXECUTIONMODE").count() > 0:
                    exec_frame = frame
                    break
            except Exception:
                pass
        if exec_frame:
            break
        await asyncio.sleep(1)
        
    if not exec_frame:
        print(f"[{window_index}] Error: No se localizo el frame de ejecucion.")
        return None
        
    # 12. Seleccionar modo 'Ventana' (WINDOWMODE)
    print(f"[{window_index}] 12. Seleccionando modo 'Ventana'...")
    try:
        exec_select = exec_frame.locator("select#EXECUTIONMODE")
        await exec_select.wait_for(state="attached", timeout=10000)
        await exec_select.select_option(value="WINDOWMODE")
        await exec_select.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
        await asyncio.sleep(0.5)
        try:
            await exec_frame.locator(".sumo_EXECUTIONMODE p.CaptionCont").click(timeout=3000)
            await asyncio.sleep(0.3)
            await exec_frame.locator(".sumo_EXECUTIONMODE .options li:has-text('Ventana')").click(timeout=3000)
        except Exception:
            pass
    except Exception as e:
        print(f"[{window_index}] Error al seleccionar modo Ventana: {e}")
        return None

    # 13. Habilitar filtro por campañas y seleccionar la campaña
    print(f"[{window_index}] 13. Habilitando 'Filtro por campanas' y seleccionando '{campana_text}'...")
    try:
        campanas_toggle = exec_frame.locator("#iconFiltro_por_Campañas")
        await campanas_toggle.wait_for(state="visible", timeout=10000)
        await campanas_toggle.click()
        await asyncio.sleep(1)
        
        await exec_frame.locator(".sumo_Campañas p.CaptionCont").click()
        await asyncio.sleep(0.5)
        
        selected_campana = await exec_frame.evaluate("""
            (target) => {
                const container = document.querySelector('.sumo_Campañas');
                if (!container) return 'no_sumo_Campañas';
                const lis = Array.from(container.querySelectorAll('.options li'));
                const cleanTarget = String(target).replace(/[\\s\\u00a0]+/g, ' ').trim().toLowerCase();
                const targetDigits = String(target).match(/^\\d+/)?.[0] || String(target).match(/\\d+/)?.[0];
                
                for (const li of lis) {
                    const rawText = li.textContent || '';
                    const cleanText = rawText.replace(/[\\s\\u00a0]+/g, ' ').trim().toLowerCase();
                    const liDigits = cleanText.match(/^\\d+/)?.[0];
                    
                    let isMatch = false;
                    if (targetDigits && liDigits && targetDigits === liDigits) {
                        isMatch = true;
                    } else if (cleanText.includes(cleanTarget) || cleanTarget.includes(cleanText)) {
                        isMatch = true;
                    }
                    
                    if (isMatch) {
                        if (!li.classList.contains('selected')) {
                            const label = li.querySelector('label') || li;
                            label.click();
                        }
                        return rawText.trim();
                    }
                }
                return 'no_match (disponibles: ' + lis.length + ')';
            }
        """, campana_text)
        print(f"[{window_index}] Campaña seleccionada en DOM: {selected_campana}")
        await asyncio.sleep(0.5)
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.5)
    except Exception as e:
        print(f"[{window_index}] Error al seleccionar campana: {e}")
        return None

    # 14. Configurar filtro por estado de usuario (si aplica)
    if estados_list:
        print(f"[{window_index}] 14. Habilitando 'Filtro por estado de usuario'...")
        try:
            estado_toggle = exec_frame.locator("#iconFiltro_por_Estado_de_Usuario")
            await estado_toggle.wait_for(state="visible", timeout=10000)
            await estado_toggle.click()
            await asyncio.sleep(1)
            
            print(f"[{window_index}] Seleccionando estados requeridos...")
            await exec_frame.locator(".sumo_Estados_Usuarios p.CaptionCont").click()
            await asyncio.sleep(0.5)
            
            clicked_estados = await exec_frame.evaluate("""
                (estados) => {
                    const lis = Array.from(document.querySelectorAll('.sumo_Estados_Usuarios .options li'));
                    const results = [];
                    const clickedIndices = new Set();
                    
                    for (const estado of estados) {
                        const estClean = estado.toLowerCase().replace(/[\\/\\s]/g, '');
                        for (let i = 0; i < lis.length; i++) {
                            if (clickedIndices.has(i)) continue;
                            const li = lis[i];
                            const txt = (li.textContent || '').trim();
                            const txtClean = txt.toLowerCase().replace(/[\\/\\s]/g, '');
                            
                            let isMatch = false;
                            if (estado === "Logueado SD" || estado === "Logueado S/D") {
                                isMatch = txtClean.includes("logueadosd") || (txtClean.includes("logueado") && txtClean.includes("sd"));
                            } else if (estado === "Logueado") {
                                isMatch = (txt.toLowerCase() === "logueado") || (txtClean.startsWith("logueado") && !txtClean.includes("sd"));
                            } else {
                                isMatch = txtClean.includes(estClean) || txt.toLowerCase().includes(estado.toLowerCase());
                            }
                            
                            if (isMatch) {
                                li.click();
                                clickedIndices.add(i);
                                results.push(txt);
                                break;
                            }
                        }
                    }
                    return results;
                }
            """, estados_list)
            print(f"[{window_index}] Estados seleccionados: {clicked_estados}")
            await asyncio.sleep(0.5)
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"[{window_index}] Error al configurar estados de usuario: {e}")
            return None
    else:
        print(f"[{window_index}] 14. Filtro por estado de usuario no requerido (se omite).")

    # 15. Configurar Columnas Adicionales ('Campaña / Cola')
    print(f"[{window_index}] 15. Seleccionando 'Campaña / Cola' en Columnas Adicionales...")
    try:
        await exec_frame.locator(".sumo_Columnas_Adicionales p.CaptionCont").click()
        await asyncio.sleep(0.5)
        selected_col = await exec_frame.evaluate("""
            () => {
                const lis = Array.from(document.querySelectorAll('.sumo_Columnas_Adicionales .options li'));
                for (const li of lis) {
                    const txt = (li.textContent || '').trim();
                    if (txt.includes('Campaña') || txt.includes('Campana') || txt.includes('Cola')) {
                        li.click();
                        return txt;
                    }
                }
                return null;
            }
        """)
        print(f"[{window_index}] Columna adicional seleccionada: {selected_col}")
        await asyncio.sleep(0.5)
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.5)
    except Exception as e:
        print(f"[{window_index}] Error al seleccionar columnas adicionales: {e}")
        return None

    # 16. Lanzar el monitor con #btnEjecutar
    print(f"[{window_index}] 16. Iniciando el monitor (#btnEjecutar)...")
    popup_page = None
    try:
        async with page.context.expect_page() as new_page_info:
            btn_ejecutar = exec_frame.locator("#btnEjecutar")
            await btn_ejecutar.wait_for(state="visible", timeout=10000)
            await btn_ejecutar.click()
        popup_page = await new_page_info.value
        print(f"\n=== Monitor {window_index} lanzado con exito en una nueva ventana ===")
        
        # Etiquetar el título de la ventana para identificarla unívocamente
        try:
            await popup_page.wait_for_load_state("domcontentloaded", timeout=10000)
            await popup_page.evaluate(f"document.title = 'Monitor de usuarios - {window_index}'")
        except Exception:
            pass
    except Exception as e:
        print(f"[{window_index}] Error al lanzar el monitor: {e}")
        return page, None
        
    return page, popup_page

async def run():
    print("Iniciando automatizacion de 3 Ventanas de Monitores en paralelo...")
    async with async_playwright() as p:
        # Iniciar Chromium en modo visible
        browser = await p.chromium.launch(headless=False, args=["--start-maximized"])

        # Listas de estados requeridos
        estados_monitor_1 = [
            "Agente (Ent.)",
            "Agente (Sal.)",
            "Llamando (Sal.)",
            "Logueado",
            "Logueado SD",
            "Ringing (Ent.)",
            "Ringing (Sal.)"
        ]

        estados_monitor_2 = [
            "Descanso",
            "Descanso Ext.",
            "Funciones Int.",
            "Mostrando",
            "Mostrar",
            "No Registrado",
            "Pausa"
        ]

        # Ejecutar los 3 flujos completos en paralelo en 3 ventanas diferentes
        results = await asyncio.gather(
            ejecutar_flujo_completo(browser, 1, "50", estados_monitor_1),
            ejecutar_flujo_completo(browser, 2, "50", estados_monitor_2),
            ejecutar_flujo_completo(browser, 3, "140", None)
        )
        orig_page_1, popup_page_1 = results[0] if results[0] else (None, None)
        orig_page_2, popup_page_2 = results[1] if results[1] else (None, None)
        orig_page_3, popup_page_3 = results[2] if results[2] else (None, None)

        # Ajustar posición y tamaño de las 3 ventanas con Win32 API
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2) # PROCESS_PER_MONITOR_DPI_AWARE
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
        
        class RECT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_int),
                        ("top", ctypes.c_int),
                        ("right", ctypes.c_int),
                        ("bottom", ctypes.c_int)]
        
        def move_window_by_title(title_substring, x, y, w, h, exclude_hwnds=None):
            target_hwnd = None
            EnumWindows = ctypes.windll.user32.EnumWindows
            EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            GetWindowText = ctypes.windll.user32.GetWindowTextW
            GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
            IsWindowVisible = ctypes.windll.user32.IsWindowVisible
            MoveWindow = ctypes.windll.user32.MoveWindow
            
            def foreach_window(hwnd, lParam):
                nonlocal target_hwnd
                if IsWindowVisible(hwnd):
                    if exclude_hwnds and hwnd in exclude_hwnds:
                        return True
                    length = GetWindowTextLength(hwnd)
                    buff = ctypes.create_unicode_buffer(length + 1)
                    GetWindowText(hwnd, buff, length + 1)
                    title = buff.value
                    if title_substring in title:
                        MoveWindow(hwnd, x, y, w, h, True)
                        target_hwnd = hwnd
                        return False
                return True
            
            EnumWindows(EnumWindowsProc(foreach_window), 0)
            return target_hwnd

        user32 = ctypes.windll.user32
        monitors = []
        
        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_ulong),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", ctypes.c_ulong)
            ]
        
        def monitor_enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)
            if user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi)):
                monitors.append({
                    "left": mi.rcWork.left,
                    "top": mi.rcWork.top,
                    "width": mi.rcWork.right - mi.rcWork.left,
                    "height": mi.rcWork.bottom - mi.rcWork.top
                })
            return True
            
        MonitorEnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumDisplayMonitors(0, 0, MonitorEnumProc(monitor_enum_proc), 0)
        
        monitors.sort(key=lambda m: m["left"])
        target_monitor = monitors[-1] if len(monitors) > 1 else monitors[0]
        
        b_x = 7
        b_y = 7
        step_w = target_monitor["width"] // 3
        
        config = {
            "x": target_monitor["left"] - b_x,
            "y": target_monitor["top"],
            "w": step_w + (b_x * 2),
            "h": target_monitor["height"] + b_y,
            "step_x": step_w
        }
        
        hwnd_1 = None
        hwnd_2 = None
        hwnd_3 = None

        print("\nPosicionando los 3 monitores en pantalla...")
        await asyncio.sleep(2)
        
        # Monitor 1 (Tercio 1)
        hwnd_1 = move_window_by_title("Monitor de usuarios - 1", config['x'], config['y'], config['w'], config['h'])
        if not hwnd_1:
            hwnd_1 = move_window_by_title("Monitor de usuarios", config['x'], config['y'], config['w'], config['h'])
        print("Monitor 1 posicionado en Tercio 1.")

        # Monitor 2 (Tercio 2)
        x2 = config['x'] + config['step_x']
        hwnd_2 = move_window_by_title("Monitor de usuarios - 2", x2, config['y'], config['w'], config['h'], exclude_hwnds={hwnd_1})
        if not hwnd_2:
            hwnd_2 = move_window_by_title("Monitor de usuarios", x2, config['y'], config['w'], config['h'], exclude_hwnds={hwnd_1})
        print("Monitor 2 posicionado en Tercio 2.")

        # Monitor 3 (Tercio 3)
        x3 = config['x'] + (config['step_x'] * 2)
        hwnd_3 = move_window_by_title("Monitor de usuarios - 3", x3, config['y'], config['w'], config['h'], exclude_hwnds={hwnd_1, hwnd_2})
        if not hwnd_3:
            hwnd_3 = move_window_by_title("Monitor de usuarios", x3, config['y'], config['w'], config['h'], exclude_hwnds={hwnd_1, hwnd_2})
        print("Monitor 3 posicionado en Tercio 3.")

        # Aplicar zoom del 90% y dimensiones calibradas en las 3 ventanas emergentes
        print("\nAplicando zoom de 90% y dimensiones calibradas...")
        js_code = """
        () => {
            document.body.style.zoom = "0.9";
            let el = document.getElementById("grid1_div");
            if (el) {
                el.style.top = "-54px";
                el.style.left = "-15px";
                el.style.width = "780px";
                el.style.height = "1027px";
                el.style.position = "absolute";
            }
        }
        """
        for p_obj in [popup_page_1, popup_page_2, popup_page_3]:
            if p_obj:
                try:
                    await p_obj.evaluate(js_code)
                except Exception as e:
                    print(f"Advertencia al inyectar auto-ajuste: {e}")

        # Cerrar las ventanas de navegación/configuración originales (dejando únicamente los 3 monitores)
        print("\nCerrando las 3 ventanas de configuracion originales...")
        for orig_p in [orig_page_1, orig_page_2, orig_page_3]:
            if orig_p:
                try:
                    await orig_p.close()
                except Exception as e:
                    print(f"Advertencia al cerrar ventana original: {e}")

        # Traer los 3 monitores al frente
        def bring_window_to_front(hwnd):
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 9)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
                ctypes.windll.user32.BringWindowToTop(hwnd)

        print("\nTrayendo los 3 monitores al frente...")
        try:
            await asyncio.sleep(1)
            bring_window_to_front(hwnd_1)
            await asyncio.sleep(0.3)
            bring_window_to_front(hwnd_2)
            await asyncio.sleep(0.3)
            bring_window_to_front(hwnd_3)
            print("Los 3 monitores han sido enfocados al frente.")
        except Exception as e:
            print(f"Advertencia al traer ventanas al frente: {e}")

        monitores_info = [
            {"id": 1, "label": "Campaña 50 - Estados 1", "page": popup_page_1},
            {"id": 2, "label": "Campaña 50 - Estados 2", "page": popup_page_2},
            {"id": 3, "label": "Campaña 140", "page": popup_page_3},
        ]

        print("\n=== Automatizacion completada con exito ===")
        try:
            await ciclo_captura_tiempo_real(monitores_info, intervalo=3, json_file="monitores_live.json")
        except (KeyboardInterrupt, asyncio.CancelledError):
            print("\nCerrando monitores y navegador...")
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
