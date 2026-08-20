import time
from playwright.sync_api import sync_playwright

def run():
    print("Iniciando automatizacion de Monitores (Paso a Paso)...")
    with sync_playwright() as p:
        # Iniciar navegador Chromium en modo visible (headed) y maximizado
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context(no_viewport=True)
        page = context.new_page()
        
        url = "http://172.16.20.10/NEOTEL/"
        print(f"1. Navegando a {url}...")
        try:
            page.goto(url, timeout=30000)
        except Exception as e:
            print(f"Error de conexion al abrir la IP: {e}")
            browser.close()
            return
            
        print("2. Esperando formulario de login...")
        try:
            usuario_xpath = 'xpath=//*[@id="txtUsuario"]'
            password_xpath = 'xpath=//*[@id="txtClave"]'
            login_btn_xpath = 'xpath=//*[@id="NeoIngresarButton1"]'
            
            # Buscar frame de login
            login_frame = None
            for _ in range(15):
                for frame in page.frames:
                    if frame.locator(usuario_xpath).count() > 0:
                        login_frame = frame
                        break
                if login_frame:
                    break
                time.sleep(1)
                
            if not login_frame:
                print("Error: No se encontro el frame de login.")
                browser.close()
                return
                
            print("3. Completando credenciales...")
            login_frame.locator(usuario_xpath).fill("1839")
            login_frame.locator(password_xpath).fill("2022")
            
            print("4. Haciendo clic en 'Log In'...")
            login_frame.locator(login_btn_xpath).click()
            print("Login enviado. Esperando carga del panel principal...")
            
        except Exception as e:
            print(f"Error al iniciar sesion: {e}")
            browser.close()
            return

        # 5. Esperar al frame interactivo de modulos buscando el elemento '#favDiv2'
        print("5. Localizando panel de modulos (buscando elemento '#favDiv2' en los frames)...")
        modulos_frame = None
        for _ in range(25):
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
            
        if not modulos_frame:
            print("Error: No se localizo el frame de modulos (el elemento '#favDiv2' no aparecio en ningun frame).")
            # Imprimimos los frames activos para debug
            print("Frames activos en la pagina:")
            for idx, frame in enumerate(page.frames):
                print(f"  Frame {idx}: name='{frame.name}', url='{frame.url}'")
            browser.close()
            return
            
        print(f"Panel localizado: '{modulos_frame.name}' ({modulos_frame.url})")
        
        # 6. Hacer clic en la tarjeta CRM (favDiv2)
        print("6. Haciendo clic en la tarjeta 'CRM'...")
        try:
            crm_card = modulos_frame.locator("#favDiv2")
            crm_card.wait_for(state="visible", timeout=15000)
            crm_card.click()
            print("Tarjeta 'CRM' clickeada.")
        except Exception as e:
            print(f"Error al hacer clic en CRM: {e}")
            browser.close()
            return
            
        # 7. Seleccionar la campaña '1 - MOVISTAR' de forma ultra-robusta (Programática + Clics)
        print("7. Seleccionando la opcion '1 - MOVISTAR'...")
        try:
            # 1. Selección programática en el select oculto
            cbo_crm = modulos_frame.locator("select#cboCRM")
            cbo_crm.wait_for(state="attached", timeout=10000)
            cbo_crm.select_option(value="1")
            
            # 2. Forzar el evento 'change' para que Neotel ejecute cboCRM_Change
            cbo_crm.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
            time.sleep(1)
            
            # 3. Simular clics en la interfaz visual de SumoSelect para asegurar la consistencia del DOM
            try:
                modulos_frame.locator(".sumo_cboCRM p.CaptionCont").click(timeout=3000)
                time.sleep(0.5)
                modulos_frame.locator(".sumo_cboCRM .options li:has-text('1 - MOVISTAR')").click(timeout=3000)
            except Exception:
                # Si falla el clic visual por estar oculto, la selección programática ya está hecha
                pass
                
            print("Opcion '1 - MOVISTAR' seleccionada.")
        except Exception as e:
            print(f"Error al seleccionar la opcion en el dropdown: {e}")
            browser.close()
            return
            
        # 8. Hacer clic en el boton de confirmacion (#btnSeleccionar)
        print("8. Confirmando seleccion con boton 'Seleccionar'...")
        try:
            confirm_btn = modulos_frame.locator("#btnSeleccionar")
            confirm_btn.wait_for(state="visible", timeout=10000)
            confirm_btn.click()
            print("Seleccion confirmada exitosamente.")
            
            # Esperar a que el spinner de carga desaparezca
            print("Esperando a que termine de cargar la pantalla de inicio...")
            try:
                modulos_frame.locator(".waiting_div2, #imgLoading").wait_for(state="hidden", timeout=15000)
            except Exception:
                pass
                
        except Exception as e:
            print(f"Error al hacer clic en el boton Seleccionar: {e}")
            browser.close()
            return

        # 9. Esperar 10 segundos o aguardar al botón 'OK' (SweetAlert) y hacer clic
        print("9. Esperando alerta flotante SweetAlert ('OK')...")
        main_frame = None
        for frame in page.frames:
            if frame.name == "main" or "default.aspx" in frame.url:
                main_frame = frame
                break
                
        if not main_frame:
            print("Error: No se localizo el frame 'main'.")
            browser.close()
            return
            
        try:
            confirm_alert_btn = main_frame.locator("button.confirm")
            confirm_alert_btn.wait_for(state="visible", timeout=15000)
            confirm_alert_btn.click()
            print("Alerta flotante confirmada (OK).")
            time.sleep(2)
        except Exception as e:
            print(f"Error o timeout al confirmar la alerta flotante: {e}")
            
        # 10. Abrir el monitor de usuarios evaluando la función JS directamente
        print("10. Abriendo el monitor de usuarios llamando a setIFramePage()...")
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
        except Exception as e:
            print(f"Error al abrir el monitor via setIFramePage: {e}")
            browser.close()
            return
            
        # 11. Localizar el frame del formulario de ejecucion (contiene #EXECUTIONMODE)
        print("11. Localizando panel de ejecucion (hasta 40 segundos)...")
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
            
        if not exec_frame:
            print("Error: No se localizo el frame de ejecucion (elemento '#EXECUTIONMODE' no encontrado).")
            # Mostrar los frames para diagnóstico
            for idx, frame in enumerate(page.frames):
                print(f"  Frame {idx}: name='{frame.name}', url='{frame.url}'")
            browser.close()
            return
            
        # 12. Seleccionar 'WINDOWMODE' (Ventana)
        print("12. Seleccionando modo 'Ventana'...")
        try:
            # 1. Selección programática en el select oculto
            exec_select = exec_frame.locator("select#EXECUTIONMODE")
            exec_select.wait_for(state="attached", timeout=10000)
            exec_select.select_option(value="WINDOWMODE")
            
            # 2. Forzar evento change por si acaso
            exec_select.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
            time.sleep(1)
            
            # 3. Simular clics en la interfaz visual de SumoSelect para abrir la lista y seleccionar
            try:
                # Clic en la barra para abrir el desplegable
                exec_frame.locator(".sumo_EXECUTIONMODE p.CaptionCont").click(timeout=3000)
                time.sleep(0.5)
                # Clic en la opción "Ventana"
                exec_frame.locator(".sumo_EXECUTIONMODE .options li:has-text('Ventana')").click(timeout=3000)
            except Exception as e:
                print(f"No se pudo completar el clic visual en SumoSelect (se usara la seleccion programatica): {e}")
                
            print("Modo 'Ventana' seleccionado con exito.")
        except Exception as e:
            print(f"Error al seleccionar modo Ventana: {e}")
            browser.close()
            return

        # 13. Habilitar filtro por campañas (hacer clic en el checkbox/toggle)
        print("13. Habilitando 'Filtro por campanas'...")
        try:
            campanas_toggle = exec_frame.locator("#iconFiltro_por_Campañas")
            campanas_toggle.wait_for(state="visible", timeout=10000)
            campanas_toggle.click()
            print("Filtro por campanas habilitado.")
            time.sleep(1)
        except Exception as e:
            print(f"Error al habilitar filtro por campanas: {e}")
            browser.close()
            return
            
        # 14. Abrir desplegable de campanas y elegir '50 - PREDICTIVO PORTABILIDAD'
        print("14. Seleccionando la campana '50 - PREDICTIVO PORTABILIDAD'...")
        try:
            # Abrir el menú SumoSelect de campañas
            exec_frame.locator(".sumo_Campañas p.CaptionCont").click()
            time.sleep(0.5)
            
            # Clic en la opción 50
            exec_frame.locator(".sumo_Campañas .options li:has-text('50 - PREDICTIVO PORTABILIDAD')").click()
            time.sleep(0.5)
            
            # Presionar escape para cerrar la lista desplegable
            page.keyboard.press("Escape")
            time.sleep(1)
        except Exception as e:
            print(f"Error al seleccionar campana: {e}")
            browser.close()
            return

        # 15. Habilitar filtro de estado por usuario
        print("15. Habilitando 'Filtro por estado de usuario'...")
        try:
            estado_toggle = exec_frame.locator("#iconFiltro_por_Estado_de_Usuario")
            estado_toggle.wait_for(state="visible", timeout=10000)
            estado_toggle.click()
            print("Filtro por estado de usuario habilitado.")
            time.sleep(1)
        except Exception as e:
            print(f"Error al habilitar filtro de estado por usuario: {e}")
            browser.close()
            return

        # 16. Seleccionar los estados de usuario requeridos
        print("16. Seleccionando estados de usuarios...")
        try:
            # Abrir el menú SumoSelect de estados de usuarios
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
            
            # Obtener todos los elementos de la lista en tiempo real
            li_count = exec_frame.locator(".sumo_Estados_Usuarios .options li").count()
            li_items = []
            for idx in range(li_count):
                li_loc = exec_frame.locator(".sumo_Estados_Usuarios .options li").nth(idx)
                li_items.append((li_loc.text_content().strip(), li_loc))
                
            clicked_indices = set()
            
            for estado in estados_a_seleccionar:
                # Si es "Logueado SD", buscamos el segundo "Logueado" en la interfaz
                match_text = "Logueado" if estado == "Logueado SD" else estado
                
                found = False
                for idx, (txt, li_loc) in enumerate(li_items):
                    if match_text in txt and idx not in clicked_indices:
                        print(f"  Haciendo clic en: {txt} (indice {idx})")
                        li_loc.click()
                        clicked_indices.add(idx)
                        time.sleep(0.3)
                        found = True
                        break
                if not found:
                    print(f"  No se pudo seleccionar el estado: {estado}")
            
            # Presionar escape para cerrar el menú desplegable
            page.keyboard.press("Escape")
            time.sleep(1)
            print("Estados de usuario seleccionados con exito.")
        except Exception as e:
            print(f"Error al seleccionar los estados de usuario: {e}")
            browser.close()
            return

        # 17. Configurar columnas adicionales
        print("17. Seleccionando 'Campaña / Cola' en Columnas Adicionales...")
        try:
            # Abrir el menú SumoSelect de Columnas Adicionales
            exec_frame.locator(".sumo_Columnas_Adicionales p.CaptionCont").click()
            time.sleep(0.5)
            
            # Clic en la opción "Campaña / Cola"
            exec_frame.locator(".sumo_Columnas_Adicionales .options li:has-text('Campaña / Cola')").click()
            time.sleep(0.5)
            
            # Presionar escape para cerrar el desplegable
            page.keyboard.press("Escape")
            time.sleep(1)
            print("Columnas adicionales configuradas con exito.")
        except Exception as e:
            print(f"Error al seleccionar columnas adicionales: {e}")
            browser.close()
            return

        # 18. Hacer clic en el botón 'btnEjecutar' para abrir el monitor de usuarios en una nueva ventana
        print("18. Iniciando el monitor de usuarios (#btnEjecutar)...")
        popup_page = None
        try:
            # Esperamos a que el navegador detecte la nueva ventana abierta tras el clic
            with page.context.expect_page() as new_page_info:
                btn_ejecutar = exec_frame.locator("#btnEjecutar")
                btn_ejecutar.wait_for(state="visible", timeout=10000)
                btn_ejecutar.click()
            popup_page = new_page_info.value
            print("\n=== Monitor lanzado con exito en una nueva ventana ===")
        except Exception as e:
            print(f"Error al lanzar el monitor: {e}")
            browser.close()
            return

        # 19. Ajustar posición y tamaño de la nueva ventana (usando API nativa de Windows via ctypes)
        if popup_page:
            import json
            import os
            import ctypes
            
            # Estructura RECT para GetWindowRect
            class RECT(ctypes.Structure):
                _fields_ = [("left", ctypes.c_int),
                            ("top", ctypes.c_int),
                            ("right", ctypes.c_int),
                            ("bottom", ctypes.c_int)]
            
            def get_window_coords_by_title(title_substring):
                coords = None
                EnumWindows = ctypes.windll.user32.EnumWindows
                EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
                GetWindowText = ctypes.windll.user32.GetWindowTextW
                GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
                IsWindowVisible = ctypes.windll.user32.IsWindowVisible
                GetWindowRect = ctypes.windll.user32.GetWindowRect
                
                def foreach_window(hwnd, lParam):
                    nonlocal coords
                    if IsWindowVisible(hwnd):
                        length = GetWindowTextLength(hwnd)
                        buff = ctypes.create_unicode_buffer(length + 1)
                        GetWindowText(hwnd, buff, length + 1)
                        title = buff.value
                        if title_substring in title:
                            rect = RECT()
                            GetWindowRect(hwnd, ctypes.byref(rect))
                            coords = {
                                "x": rect.left,
                                "y": rect.top,
                                "w": rect.right - rect.left,
                                "h": rect.bottom - rect.top
                            }
                            return False
                    return True
                
                EnumWindows(EnumWindowsProc(foreach_window), 0)
                return coords
            
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
            
            config_path = "window_config.json"
            title_search = "Monitor de usuarios"
            hwnd_1 = None
            hwnd_2 = None
            
            try:
                # Esperamos a que la ventana esté lista
                popup_page.wait_for_load_state("domcontentloaded", timeout=10000)
                time.sleep(2) # Esperar a que el S.O. registre e inicialice la ventana física
                
                if os.path.exists(config_path):
                    # Si ya existe la configuración, la cargamos y aplicamos via Win32 API
                    with open(config_path, "r") as f:
                        config = json.load(f)
                    print(f"Cargando posicion de ventana desde {config_path}: {config}")
                    
                    hwnd_1 = move_window_by_title(title_search, config['x'], config['y'], config['w'], config['h'])
                    time.sleep(0.5)
                    # Re-aplicar por si acaso el S.O. estaba en transición
                    move_window_by_title(title_search, config['x'], config['y'], config['w'], config['h'])
                    print("Ventana 1 reposicionada exitosamente con Win32 API.")
                else:
                    # Si no existe, le pedimos al usuario que la acomode
                    print("\n" + "="*60)
                    print("=== CONFIGURACION DE POSICION DE VENTANA ===")
                    print("Acomoda la ventana del monitor manualmente en la pantalla (posicion y tamaño).")
                    print("Una vez que la tengas lista, presiona ENTER aqui en esta terminal...")
                    print("="*60)
                    
                    input() # Espera al enter en la consola
                    
                    # Leemos la posición real usando la API de Windows
                    coords = get_window_coords_by_title(title_search)
                    if coords:
                        # Guardamos la configuración en un archivo json
                        with open(config_path, "w") as f:
                            json.dump(coords, f, indent=4)
                        print(f"\nConfiguracion guardada en '{config_path}': {coords}")
                        print("En las proximas ejecuciones se abrira en esta misma posicion de forma automatica.")
                        
                        # Guardamos el hwnd_1 tras calibrar
                        hwnd_1 = move_window_by_title(title_search, coords['x'], coords['y'], coords['w'], coords['h'])
                    else:
                        print("No se pudo detectar la ventana del monitor mediante Win32 API.")
            except Exception as e:
                print(f"Advertencia al configurar la ventana 1: {e}")
                
            # 20. Enfocar la pantalla de configuración, deseleccionar estados previos y seleccionar los otros
            print("\n20. Enfocando la pestaña de configuracion para el segundo monitor...")
            try:
                page.bring_to_front()
                time.sleep(1)
                
                # Abrir el menú SumoSelect de estados de usuarios
                exec_frame.locator(".sumo_Estados_Usuarios p.CaptionCont").click()
                time.sleep(1)
                
                # Obtener elementos en tiempo real
                li_count = exec_frame.locator(".sumo_Estados_Usuarios .options li").count()
                li_items = []
                for idx in range(li_count):
                    li_loc = exec_frame.locator(".sumo_Estados_Usuarios .options li").nth(idx)
                    li_items.append((li_loc.text_content().strip(), li_loc))
                    
                # Deseleccionamos los que marcamos al principio
                print("Deseleccionando los estados anteriores...")
                clicked_indices = set()
                for estado in estados_a_seleccionar:
                    match_text = "Logueado" if estado == "Logueado SD" else estado
                    for idx, (txt, li_loc) in enumerate(li_items):
                        if match_text in txt and idx not in clicked_indices:
                            li_loc.click()
                            clicked_indices.add(idx)
                            time.sleep(0.2)
                            break
                            
                # Seleccionamos los otros estados (Descanso, Descanso Ext., Funciones Int., etc.)
                nuevos_estados = ["Descanso", "Descanso Ext.", "Funciones Int.", "Mostrando", "Mostrar", "No Registrado", "Pausa"]
                print("Seleccionando los estados restantes...")
                new_clicked_indices = set()
                for estado in nuevos_estados:
                    for idx, (txt, li_loc) in enumerate(li_items):
                        if estado.lower() in txt.lower() and idx not in new_clicked_indices:
                            li_loc.click()
                            new_clicked_indices.add(idx)
                            time.sleep(0.2)
                            break
                            
                # Presionar escape para cerrar el menú desplegable
                page.keyboard.press("Escape")
                time.sleep(1)
                print("Estados actualizados para el segundo monitor.")
            except Exception as e:
                print(f"Error al configurar estados del segundo monitor: {e}")
                browser.close()
                return
                
            # 21. Lanzar el segundo monitor de usuarios
            print("21. Lanzando el segundo monitor de usuarios (#btnEjecutar)...")
            popup_page_2 = None
            try:
                with page.context.expect_page() as new_page_info_2:
                    btn_ejecutar = exec_frame.locator("#btnEjecutar")
                    btn_ejecutar.click()
                popup_page_2 = new_page_info_2.value
                print("Segundo monitor lanzado exitosamente.")
            except Exception as e:
                print(f"Error al lanzar el segundo monitor: {e}")
                browser.close()
                return
                
            # 22. Ajustar la posición y tamaño del segundo monitor (segundo tercio)
            if popup_page_2:
                try:
                    popup_page_2.wait_for_load_state("domcontentloaded", timeout=10000)
                    time.sleep(2) # Esperamos al S.O.
                    
                    if os.path.exists(config_path):
                        with open(config_path, "r") as f:
                            config = json.load(f)
                            
                        # El segundo tercio comienza exactamente al lado del primero (X = X1 + Ancho1)
                        # Restamos 16px para compensar los bordes invisibles de Windows y que queden perfectamente pegados
                        x2 = config['x'] + config['w'] - 16
                        
                        print(f"Posicionando el segundo monitor en X={x2}, Y={config['y']}, W={config['w']}, H={config['h']}")
                        hwnd_2 = move_window_by_title(title_search, x2, config['y'], config['w'], config['h'], exclude_hwnds={hwnd_1})
                        time.sleep(0.5)
                        move_window_by_title(title_search, x2, config['y'], config['w'], config['h'], exclude_hwnds={hwnd_1})
                        print("Segundo monitor posicionado en el segundo tercio.")
                    else:
                        print("No se encontro configuracion guardada para alinear el segundo monitor.")
                except Exception as e:
                    print(f"Advertencia al posicionar el segundo monitor: {e}")
                    
            # 23. Configurar y lanzar el tercer monitor
            print("\n23. Enfocando la pestaña de configuracion para el tercer monitor...")
            try:
                page.bring_to_front()
                time.sleep(1)
                
                # Desactivar el filtro de estado de usuario
                print("Desactivando el filtro de estado de usuario...")
                estado_toggle = exec_frame.locator("#iconFiltro_por_Estado_de_Usuario")
                estado_toggle.wait_for(state="visible", timeout=10000)
                estado_toggle.click()
                time.sleep(1)
                
                # Abrir desplegable de campañas
                print("Modificando filtro de campañas para el tercer monitor...")
                exec_frame.locator(".sumo_Campañas p.CaptionCont").click()
                time.sleep(1)
                
                # Deseleccionar campaña 50
                print("Deseleccionando campana 50...")
                exec_frame.locator(".sumo_Campañas .options li:has-text('50 - PREDICTIVO PORTABILIDAD')").click()
                time.sleep(0.5)
                
                # Seleccionar campaña 140
                print("Seleccionando campana 140...")
                exec_frame.locator(".sumo_Campañas .options li:has-text('140')").first.click()
                time.sleep(0.5)
                
                # Presionar escape para cerrar
                page.keyboard.press("Escape")
                time.sleep(1)
                print("Campañas actualizadas para el tercer monitor.")
            except Exception as e:
                print(f"Error al configurar filtros del tercer monitor: {e}")
                browser.close()
                return
                
            # 24. Lanzar el tercer monitor
            print("24. Lanzando el tercer monitor de usuarios (#btnEjecutar)...")
            popup_page_3 = None
            try:
                with page.context.expect_page() as new_page_info_3:
                    btn_ejecutar = exec_frame.locator("#btnEjecutar")
                    btn_ejecutar.click()
                popup_page_3 = new_page_info_3.value
                print("Tercer monitor lanzado exitosamente.")
            except Exception as e:
                print(f"Error al lanzar el tercer monitor: {e}")
                browser.close()
                return
                
            # 25. Ajustar la posición y tamaño del tercer monitor (tercer tercio)
            if popup_page_3:
                try:
                    popup_page_3.wait_for_load_state("domcontentloaded", timeout=10000)
                    time.sleep(2) # Esperamos al S.O.
                    
                    if os.path.exists(config_path):
                        with open(config_path, "r") as f:
                            config = json.load(f)
                            
                # El tercer tercio comienza al lado del segundo (X = X1 + Ancho1 * 2)
                        # Restamos 32px para compensar los bordes invisibles acumulados de Windows
                        x3 = config['x'] + (config['w'] * 2) - 32
                        
                        print(f"Posicionando el tercer monitor en X={x3}, Y={config['y']}, W={config['w']}, H={config['h']}")
                        hwnd_3 = move_window_by_title(title_search, x3, config['y'], config['w'], config['h'], exclude_hwnds={hwnd_1, hwnd_2})
                        time.sleep(0.5)
                        move_window_by_title(title_search, x3, config['y'], config['w'], config['h'], exclude_hwnds={hwnd_1, hwnd_2})
                        print("Tercer monitor posicionado en el tercer tercio.")
                    else:
                        print("No se encontro configuracion guardada para alinear el tercer monitor.")
                except Exception as e:
                    print(f"Advertencia al posicionar el tercer monitor: {e}")
                    
            # 26. Traer los 3 monitores al frente de la pantalla
            def bring_window_to_front(hwnd):
                if hwnd:
                    # SW_RESTORE = 9
                    ctypes.windll.user32.ShowWindow(hwnd, 9)
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                    ctypes.windll.user32.BringWindowToTop(hwnd)
            
            print("\n26. Trayendo los 3 monitores al frente de la pantalla...")
            try:
                time.sleep(1)
                bring_window_to_front(hwnd_1)
                time.sleep(0.3)
                bring_window_to_front(hwnd_2)
                time.sleep(0.3)
                bring_window_to_front(hwnd_3)
                print("Los 3 monitores han sido enfocados al frente.")
            except Exception as e:
                print(f"Advertencia al traer las ventanas al frente: {e}")

        print("\n=== Automatizacion completada con exito ===")
        print("El navegador permanecera abierto. Presiona Ctrl+C en esta terminal para cerrarlo.")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nCerrando navegador...")
            browser.close()

if __name__ == "__main__":
    run()
