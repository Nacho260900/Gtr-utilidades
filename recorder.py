import time
from playwright.sync_api import sync_playwright

# Función callback en Python que recibirá los datos capturados en el navegador
def handle_browser_event(source, event_info):
    frame_url = source["frame"].url
    print("\n" + "="*50)
    print(f"--> ELEMENTO INTERACTUADO en Frame: '{source['frame'].name}'")
    print(f"   URL del Frame: {frame_url}")
    print(f"   Accion: {event_info['type'].upper()}")
    print(f"   Etiqueta (Tag): {event_info['tagName']}")
    if event_info['id']:
        print(f"   ID: {event_info['id']}")
    if event_info['className']:
        print(f"   Clase (Class): {event_info['className']}")
    if event_info['text']:
        print(f"   Texto: '{event_info['text']}'")
    if event_info['value']:
        print(f"   Valor/Value: '{event_info['value']}'")
    print(f"   * Selector XPath sugerido: {event_info['xpath']}")
    print("="*50)

def run():
    print("Iniciando Grabador de Selectores Interactivo...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context(no_viewport=True)
        page = context.new_page()
        
        # Exponemos la función de Python en la ventana del navegador
        page.expose_binding("report_event", handle_browser_event)
        
        # Inyectamos el script rastreador en cada página y frame que se cargue
        tracker_script = """
        function getElementXPath(element) {
            if (!element) return '';
            if (element.id) {
                return '//*[@id="' + element.id + '"]';
            }
            if (element === document.body) {
                return '/html/body';
            }
            var ix = 0;
            var siblings = element.parentNode ? element.parentNode.childNodes : [];
            for (var i = 0; i < siblings.length; i++) {
                var sibling = siblings[i];
                if (sibling === element) {
                    return getElementXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                }
                if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                    ix++;
                }
            }
            return '';
        }

        // Registrar escuchadores de eventos
        document.addEventListener('click', function(e) {
            let el = e.target;
            // Si el elemento es un SVG o hijo, busquemos el ancestro más relevante (como botón o link)
            let targetEl = el;
            while (targetEl && targetEl.tagName !== 'BODY') {
                if (targetEl.id || targetEl.tagName === 'BUTTON' || targetEl.tagName === 'A' || targetEl.onclick) {
                    break;
                }
                targetEl = targetEl.parentNode || targetEl;
            }
            
            let info = {
                type: 'click',
                tagName: el.tagName,
                id: el.id,
                className: el.className,
                text: el.innerText ? el.innerText.trim().substring(0, 100) : '',
                value: el.value || '',
                xpath: getElementXPath(el)
            };
            
            // Si encontramos un contenedor relevante con más información, lo agregamos
            if (targetEl && targetEl !== el) {
                info.xpath = getElementXPath(targetEl);
                info.id = targetEl.id || info.id;
                info.className = targetEl.className || info.className;
            }
            
            try {
                window.report_event(info);
            } catch(err) {}
        }, true);

        document.addEventListener('change', function(e) {
            let el = e.target;
            let info = {
                type: 'change',
                tagName: el.tagName,
                id: el.id,
                className: el.className,
                text: el.options ? el.options[el.selectedIndex].text : '',
                value: el.value || '',
                xpath: getElementXPath(el)
            };
            try {
                window.report_event(info);
            } catch(err) {}
        }, true);
        """
        
        page.add_init_script(tracker_script)
        
        url = "http://172.16.20.10/NEOTEL/"
        print(f"Navegando a {url}...")
        try:
            page.goto(url, timeout=30000)
        except Exception as e:
            print(f"Error al navegar: {e}")
            
        print("Iniciando automatizacion inicial...")
        try:
            # 1. Login
            usuario_xpath = 'xpath=//*[@id="txtUsuario"]'
            password_xpath = 'xpath=//*[@id="txtClave"]'
            login_btn_xpath = 'xpath=//*[@id="NeoIngresarButton1"]'
            
            target_frame = None
            time.sleep(2)
            for frame in page.frames:
                if frame.locator(usuario_xpath).count() > 0:
                    target_frame = frame
                    break
            
            if target_frame:
                target_frame.locator(usuario_xpath).fill("1839")
                target_frame.locator(password_xpath).fill("2022")
                target_frame.locator(login_btn_xpath).click()
                print("Login completado. Esperando panel principal...")
            else:
                print("No se encontro el formulario de login. Continuando manualmente...")
                
            # 2. Esperamos al frame de modulos
            print("Esperando panel de modulos...")
            modulos_frame = None
            for _ in range(15):
                for frame in page.frames:
                    try:
                        if frame.locator("#favDiv2").count() > 0:
                            modulos_frame = frame
                            break
                    except Exception:
                        pass
                if modulos_frame:
                    break
                time.sleep(1)
                
            if modulos_frame:
                print("Abriendo CRM...")
                modulos_frame.locator("#favDiv2").click()
                time.sleep(2)
                
                # Seleccionar Movistar de forma robusta
                cbo_crm = modulos_frame.locator("select#cboCRM")
                cbo_crm.wait_for(state="attached", timeout=5000)
                cbo_crm.select_option(value="1")
                cbo_crm.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
                time.sleep(1)
                
                try:
                    modulos_frame.locator(".sumo_cboCRM p.CaptionCont").click(timeout=2000)
                    time.sleep(0.5)
                    modulos_frame.locator(".sumo_cboCRM .options li:has-text('1 - MOVISTAR')").click(timeout=2000)
                except Exception:
                    pass
                time.sleep(1)
                
                modulos_frame.locator("#btnSeleccionar").click()
                print("CRM Movistar seleccionado. Esperando a que termine de cargar...")
                
                try:
                    modulos_frame.locator(".waiting_div2, #imgLoading").wait_for(state="hidden", timeout=10000)
                except Exception:
                    pass
                
                # 3. Esperar alerta flotante SweetAlert ('OK') y hacer clic
                print("Esperando alerta flotante SweetAlert ('OK')...")
                main_frame = None
                for frame in page.frames:
                    if frame.name == "main" or "default.aspx" in frame.url:
                        main_frame = frame
                        break
                        
                if main_frame:
                    try:
                        confirm_alert_btn = main_frame.locator("button.confirm")
                        confirm_alert_btn.wait_for(state="visible", timeout=15000)
                        confirm_alert_btn.click()
                        print("Alerta flotante confirmada (OK).")
                        time.sleep(2)
                    except Exception as e:
                        print(f"Alerta flotante no aparecio o timeout: {e}")
                        
                    # 4. Abrir el monitor de usuarios evaluando la función JS directamente
                    print("Abriendo el monitor de usuarios llamando a setIFramePage()...")
                    try:
                        main_frame.evaluate("""
                            setIFramePage(
                                'ControlBoards_Custom_Test.aspx?TIPOACCION=EJ&IDPROC=5&DESCRIP=USERS_MONITOR&IDOPERACION=2&IDDATASOURCE=0&TYPE=5',
                                'Monitor de usuarios',
                                '',
                                1,
                                'fal fa-monitor-heart-rate'
                            )
                        """)
                        print("Llamada a setIFramePage ejecutada correctamente.")
                        time.sleep(3)
                        
                        # Buscar el frame de ejecucion
                        print("Localizando frame de ejecucion (hasta 40 segundos)...")
                        exec_frame = None
                        for _ in range(40):
                            for frame in page.frames:
                                try:
                                    if frame.locator("#EXECUTIONMODE").count() > 0:
                                        exec_frame = frame
                                        break
                                except Exception:
                                    pass
                            if exec_frame:
                                break
                            time.sleep(1)
                            
                        if exec_frame:
                            print("Seleccionando ejecucion en modo Ventana...")
                            exec_select = exec_frame.locator("select#EXECUTIONMODE")
                            exec_select.wait_for(state="attached", timeout=5000)
                            exec_select.select_option(value="WINDOWMODE")
                            exec_select.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
                            time.sleep(1)
                            
                            try:
                                # Clic en la barra para abrir el desplegable
                                exec_frame.locator(".sumo_EXECUTIONMODE p.CaptionCont").click(timeout=2000)
                                time.sleep(0.5)
                                # Clic en la opción "Ventana"
                                exec_frame.locator(".sumo_EXECUTIONMODE .options li:has-text('Ventana')").click(timeout=2000)
                            except Exception as e:
                                pass
                            time.sleep(1)
                            
                            # 13. Habilitar filtro por campañas (hacer clic en el checkbox/toggle)
                            print("Habilitando 'Filtro por campanas'...")
                            campanas_toggle = exec_frame.locator("#iconFiltro_por_Campañas")
                            campanas_toggle.wait_for(state="visible", timeout=5000)
                            campanas_toggle.click()
                            time.sleep(1)
                            
                            # 14. Abrir desplegable de campanas y elegir '50 - PREDICTIVO PORTABILIDAD'
                            print("Seleccionando la campana '50 - PREDICTIVO PORTABILIDAD'...")
                            exec_frame.locator(".sumo_Campañas p.CaptionCont").click()
                            time.sleep(0.5)
                            exec_frame.locator(".sumo_Campañas .options li:has-text('50 - PREDICTIVO PORTABILIDAD')").click()
                            time.sleep(0.5)
                            
                            # Presionar escape para cerrar la lista desplegable
                            page.keyboard.press("Escape")
                            time.sleep(1)
                            
                            # 15. Habilitar filtro de estado por usuario
                            print("Habilitando 'Filtro por estado de usuario'...")
                            estado_toggle = exec_frame.locator("#iconFiltro_por_Estado_de_Usuario")
                            estado_toggle.wait_for(state="visible", timeout=5000)
                            estado_toggle.click()
                            time.sleep(1)
                            
                            # 16. Seleccionar los estados de usuario requeridos
                            print("Seleccionando estados de usuarios...")
                            exec_frame.locator(".sumo_Estados_Usuarios p.CaptionCont").click()
                            time.sleep(1)
                            
                            estados_a_seleccionar = [
                                "Agente (Ent.)",
                                "Agente (Sal.)",
                                "Llamando (Sal.)",
                                "Logueado",
                                "Logueado SD",
                                "Ringing (Ent.)",
                                "Ringing (Sal.)"
                            ]
                            
                            li_count = exec_frame.locator(".sumo_Estados_Usuarios .options li").count()
                            li_items = []
                            for idx in range(li_count):
                                li_loc = exec_frame.locator(".sumo_Estados_Usuarios .options li").nth(idx)
                                li_items.append((li_loc.text_content().strip(), li_loc))
                                
                            clicked_indices = set()
                            
                            for estado in estados_a_seleccionar:
                                match_text = "Logueado" if estado == "Logueado SD" else estado
                                for idx, (txt, li_loc) in enumerate(li_items):
                                    if match_text in txt and idx not in clicked_indices:
                                        try:
                                            li_loc.click(timeout=2000)
                                            clicked_indices.add(idx)
                                            time.sleep(0.3)
                                        except Exception:
                                            pass
                                        break
                                    
                            page.keyboard.press("Escape")
                            time.sleep(1)
                            
                            # 17. Configurar columnas adicionales
                            print("Seleccionando 'Campaña / Cola' en Columnas Adicionales...")
                            exec_frame.locator(".sumo_Columnas_Adicionales p.CaptionCont").click()
                            time.sleep(0.5)
                            exec_frame.locator(".sumo_Columnas_Adicionales .options li:has-text('Campaña / Cola')").click()
                            time.sleep(0.5)
                            page.keyboard.press("Escape")
                            time.sleep(1)
                            
                            # 18. Hacer clic en btnEjecutar para lanzar el monitor y capturar la nueva ventana
                            print("Lanzando monitor de usuarios (#btnEjecutar)...")
                            popup_page = None
                            try:
                                with page.context.expect_page() as new_page_info:
                                    exec_frame.locator("#btnEjecutar").click()
                                popup_page = new_page_info.value
                            except Exception as launch_err:
                                print(f"Error al lanzar el monitor: {launch_err}")
                                
                            # Posicionar la nueva ventana si se abrió
                            if popup_page:
                                import json
                                import os
                                import ctypes
                                config_path = "window_config.json"
                                title_search = "Monitor de usuarios"
                                
                                def move_window_by_title(title_substring, x, y, w, h):
                                    EnumWindows = ctypes.windll.user32.EnumWindows
                                    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
                                    GetWindowText = ctypes.windll.user32.GetWindowTextW
                                    GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
                                    IsWindowVisible = ctypes.windll.user32.IsWindowVisible
                                    MoveWindow = ctypes.windll.user32.MoveWindow
                                    
                                    def foreach_window(hwnd, lParam):
                                        if IsWindowVisible(hwnd):
                                            length = GetWindowTextLength(hwnd)
                                            buff = ctypes.create_unicode_buffer(length + 1)
                                            GetWindowText(hwnd, buff, length + 1)
                                            title = buff.value
                                            if title_substring in title:
                                                MoveWindow(hwnd, x, y, w, h, True)
                                                return False
                                        return True
                                    EnumWindows(EnumWindowsProc(foreach_window), 0)

                                try:
                                    popup_page.wait_for_load_state("domcontentloaded", timeout=5000)
                                    time.sleep(2)
                                    hwnd_1 = None
                                    hwnd_2 = None
                                    if os.path.exists(config_path):
                                        with open(config_path, "r") as f:
                                            config = json.load(f)
                                        x2 = config['x'] + config['w'] - 16
                                        hwnd_1 = move_window_by_title(title_search, config['x'], config['y'], config['w'], config['h'])
                                        time.sleep(0.5)
                                        move_window_by_title(title_search, config['x'], config['y'], config['w'], config['h'])
                                        hwnd_2 = move_window_by_title(title_search, x2, config['y'], config['w'], config['h'], exclude_hwnds={hwnd_1})
                                        time.sleep(0.5)
                                        move_window_by_title(title_search, x2, config['y'], config['w'], config['h'], exclude_hwnds={hwnd_1})
                                        print("Ventana reposicionada con exito usando window_config.json y Win32 API.")
                                    else:
                                        # Fallback por defecto
                                        popup_page.evaluate("""() => {
                                            const offset = 8;
                                            const w = Math.floor(window.screen.availWidth / 3) + (offset * 2);
                                            const h = window.screen.availHeight + offset;
                                            window.moveTo(-offset, 0);
                                            window.resizeTo(w, h);
                                        }""")
                                        print("Ventana posicionada con calculos por defecto.")
                                except Exception as win_err:
                                    print(f"Advertencia al ajustar la ventana: {win_err}")
                                    
                            # 23. Lanzamiento del tercer monitor
                            print("\nEnfocando la pestaña de configuracion para el tercer monitor...")
                            try:
                                page.bring_to_front()
                                time.sleep(1)
                                
                                # Desactivar filtro de estados
                                print("Desactivando filtro de estados...")
                                exec_frame.locator("#iconFiltro_por_Estado_de_Usuario").click()
                                time.sleep(1)
                                
                                # Abrir campañas, deseleccionar 50 y seleccionar 140
                                print("Modificando filtro de campañas...")
                                exec_frame.locator(".sumo_Campañas p.CaptionCont").click()
                                time.sleep(1)
                                exec_frame.locator(".sumo_Campañas .options li:has-text('50 - PREDICTIVO PORTABILIDAD')").click()
                                time.sleep(0.5)
                                exec_frame.locator(".sumo_Campañas .options li:has-text('140')").first.click()
                                time.sleep(0.5)
                                page.keyboard.press("Escape")
                                time.sleep(1)
                                
                                # Lanzar tercer monitor
                                print("Lanzando tercer monitor (#btnEjecutar)...")
                                popup_page_3 = None
                                with page.context.expect_page() as new_page_info_3:
                                    exec_frame.locator("#btnEjecutar").click()
                                popup_page_3 = new_page_info_3.value
                                
                                if popup_page_3:
                                    popup_page_3.wait_for_load_state("domcontentloaded", timeout=5000)
                                    time.sleep(2)
                                    if os.path.exists(config_path):
                                        with open(config_path, "r") as f:
                                            config = json.load(f)
                                        x3 = config['x'] + (config['w'] * 2) - 32
                                        print(f"Posicionando el tercer monitor en X={x3}...")
                                        hwnd_3 = move_window_by_title(title_search, x3, config['y'], config['w'], config['h'], exclude_hwnds={hwnd_1, hwnd_2})
                                        time.sleep(0.5)
                                        move_window_by_title(title_search, x3, config['y'], config['w'], config['h'], exclude_hwnds={hwnd_1, hwnd_2})
                                        print("Tercer monitor posicionado.")
                                        
                                        # Traer los 3 al frente
                                        def bring_window_to_front(hwnd):
                                            if hwnd:
                                                ctypes.windll.user32.ShowWindow(hwnd, 9)
                                                ctypes.windll.user32.SetForegroundWindow(hwnd)
                                                ctypes.windll.user32.BringWindowToTop(hwnd)
                                        
                                        print("Enfocando los 3 monitores al frente...")
                                        time.sleep(1)
                                        bring_window_to_front(hwnd_1)
                                        time.sleep(0.3)
                                        bring_window_to_front(hwnd_2)
                                        time.sleep(0.3)
                                        bring_window_to_front(hwnd_3)
                            except Exception as err3:
                                print(f"Error al configurar tercer monitor: {err3}")
                            
                            time.sleep(5)
                        else:
                            print("No se localizo el frame de ejecucion. Continuando en modo manual...")
                    except Exception as e:
                        print(f"Error al abrir el monitor via setIFramePage: {e}. Continuando en modo manual...")
                else:
                    print("No se localizo el frame 'main'. Continuando en modo manual...")
            else:
                print("No se localizo el panel de modulos. Continuando en modo manual...")
                
        except Exception as e:
            print(f"Advertencia durante la automatizacion inicial: {e}")
            print("Continuando en modo manual...")
            
        # Inyectamos el script tracker en cada frame dinamicamente en un bucle
        print("\n=== El navegador esta listo ===")
        print("1. El login se realizara automaticamente.")
        print("2. Haz clic en las opciones del menu (CRM, Movistar, etc.).")
        print("3. Veras los selectores aqui en tiempo real.")
        print("Presiona Ctrl+C en esta terminal para finalizar.\n")
        
        try:
            while True:
                # Obtenemos todos los frames activos y les inyectamos el tracker si no lo tienen
                for frame in page.frames:
                    try:
                        # Verificamos si ya está inyectado para evitar duplicados
                        already_injected = frame.evaluate("typeof window.__tracker_installed !== 'undefined'")
                        if not already_injected:
                            frame.evaluate("""
                                window.__tracker_installed = true;
                                
                                function getElementXPath(element) {
                                    if (!element) return '';
                                    if (element.id) {
                                        return '//*[@id="' + element.id + '"]';
                                    }
                                    if (element === document.body) {
                                        return '/html/body';
                                    }
                                    var ix = 0;
                                    var siblings = element.parentNode ? element.parentNode.childNodes : [];
                                    for (var i = 0; i < siblings.length; i++) {
                                        var sibling = siblings[i];
                                        if (sibling === element) {
                                            return getElementXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                                        }
                                        if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                                            ix++;
                                        }
                                    }
                                    return '';
                                }

                                document.addEventListener('click', function(e) {
                                    let el = e.target;
                                    let targetEl = el;
                                    while (targetEl && targetEl.tagName !== 'BODY') {
                                        if (targetEl.id || targetEl.tagName === 'BUTTON' || targetEl.tagName === 'A' || targetEl.onclick) {
                                            break;
                                        }
                                        targetEl = targetEl.parentNode || targetEl;
                                    }
                                    
                                    let info = {
                                        type: 'click',
                                        tagName: el.tagName,
                                        id: el.id,
                                        className: el.className,
                                        text: el.innerText ? el.innerText.trim().substring(0, 100) : '',
                                        value: el.value || '',
                                        xpath: getElementXPath(el)
                                    };
                                    
                                    if (targetEl && targetEl !== el) {
                                        info.xpath = getElementXPath(targetEl);
                                        info.id = targetEl.id || info.id;
                                        info.className = targetEl.className || info.className;
                                    }
                                    
                                    try {
                                        window.report_event(info);
                                    } catch(err) {}
                                }, true);

                                document.addEventListener('change', function(e) {
                                    let el = e.target;
                                    let info = {
                                        type: 'change',
                                        tagName: el.tagName,
                                        id: el.id,
                                        className: el.className,
                                        text: el.options ? el.options[el.selectedIndex].text : '',
                                        value: el.value || '',
                                        xpath: getElementXPath(el)
                                    };
                                    try {
                                        window.report_event(info);
                                    } catch(err) {}
                                }, true);
                            """)
                    except Exception:
                        # Si el frame no está completamente cargado o listo, fallará pacíficamente
                        pass
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nCerrando grabador...")
            browser.close()

if __name__ == "__main__":
    run()
