import os
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

# Función callback en Python que recibirá los datos capturados en el navegador
def handle_browser_event(source, event_info):
    frame_name = source["frame"].name if source and "frame" in source else ""
    frame_url = source["frame"].url if source and "frame" in source else ""
    
    print("\n" + "=" * 60)
    print(f"--> EVENTO REGISTRADO: [{event_info.get('type', '').upper()}]")
    if frame_name:
        print(f"   Frame Name: '{frame_name}'")
    if frame_url:
        print(f"   Frame URL: {frame_url}")
    print(f"   Etiqueta (Tag): <{event_info.get('tagName', '').lower()}>")
    if event_info.get('id'):
        print(f"   ID: #{event_info['id']}")
    if event_info.get('name'):
        print(f"   Name: {event_info['name']}")
    if event_info.get('className'):
        print(f"   Clase (Class): .{event_info['className'].replace(' ', '.')}")
    if event_info.get('text'):
        print(f"   Texto: '{event_info['text']}'")
    if event_info.get('value'):
        print(f"   Valor / Value: '{event_info['value']}'")
    if event_info.get('onclick'):
        print(f"   Onclick JS: {event_info['onclick']}")
    if event_info.get('href'):
        print(f"   Href: {event_info['href']}")
    if event_info.get('css'):
        print(f"   * Selector CSS sugerido: {event_info['css']}")
    if event_info.get('xpath'):
        print(f"   * Selector XPath sugerido: {event_info['xpath']}")
    print("=" * 60)


def on_new_page(new_page):
    print(f"\n[INFO] Nueva ventana/pestaña detectada: {new_page.url or 'Cargando...'}")


def run():
    print("==================================================")
    print("  Iniciando Grabador de Selectores / Módulos")
    print("==================================================")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context(no_viewport=True)
        
        # Exponemos la función de captura a nivel de contexto (para todas las páginas y popups)
        context.expose_binding("report_event", handle_browser_event)
        context.on("page", on_new_page)
        
        # Script tracker inyectable en cada página y frame
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

        function getSuggestedCSS(el) {
            if (!el) return '';
            if (el.id) return '#' + el.id;
            if (el.getAttribute('name')) return el.tagName.toLowerCase() + '[name="' + el.getAttribute('name') + '"]';
            if (el.className && typeof el.className === 'string') {
                let classes = el.className.trim().split(/\\s+/).filter(Boolean);
                if (classes.length > 0) {
                    return el.tagName.toLowerCase() + '.' + classes.join('.');
                }
            }
            return el.tagName.toLowerCase();
        }

        // Registrar escuchadores de eventos
        document.addEventListener('click', function(e) {
            let el = e.target;
            let targetEl = el;
            while (targetEl && targetEl.tagName !== 'BODY') {
                if (targetEl.id || targetEl.tagName === 'BUTTON' || targetEl.tagName === 'A' || targetEl.getAttribute('onclick') || targetEl.onclick) {
                    break;
                }
                targetEl = targetEl.parentNode || targetEl;
            }
            
            let info = {
                type: 'click',
                tagName: el.tagName,
                id: el.id || '',
                name: el.getAttribute('name') || '',
                className: (typeof el.className === 'string') ? el.className : '',
                text: el.innerText ? el.innerText.trim().substring(0, 150) : (el.textContent ? el.textContent.trim().substring(0, 150) : ''),
                value: el.value || '',
                onclick: el.getAttribute('onclick') || '',
                href: el.getAttribute('href') || '',
                xpath: getElementXPath(el),
                css: getSuggestedCSS(el)
            };
            
            if (targetEl && targetEl !== el) {
                info.xpath = getElementXPath(targetEl);
                info.css = getSuggestedCSS(targetEl);
                if (!info.id && targetEl.id) info.id = targetEl.id;
                if (!info.name && targetEl.getAttribute('name')) info.name = targetEl.getAttribute('name');
                if (!info.onclick && targetEl.getAttribute('onclick')) info.onclick = targetEl.getAttribute('onclick');
                if (!info.href && targetEl.getAttribute('href')) info.href = targetEl.getAttribute('href');
            }
            
            try {
                if (window.report_event) {
                    window.report_event(info);
                }
            } catch(err) {}
        }, true);

        document.addEventListener('change', function(e) {
            let el = e.target;
            let info = {
                type: 'change',
                tagName: el.tagName,
                id: el.id || '',
                name: el.getAttribute('name') || '',
                className: (typeof el.className === 'string') ? el.className : '',
                text: el.options && el.selectedIndex >= 0 ? el.options[el.selectedIndex].text : '',
                value: el.value || '',
                xpath: getElementXPath(el),
                css: getSuggestedCSS(el)
            };
            try {
                if (window.report_event) {
                    window.report_event(info);
                }
            } catch(err) {}
        }, true);
        """
        
        context.add_init_script(tracker_script)
        
        page = context.new_page()
        
        url = "http://172.16.20.10/NEOTEL/"
        print(f"Navegando a {url}...")
        try:
            page.goto(url, timeout=30000)
        except Exception as e:
            print(f"Error al navegar: {e}")
            
        print("Iniciando proceso de Login automático...")
        try:
            usuario_xpath = 'xpath=//*[@id="txtUsuario"]'
            password_xpath = 'xpath=//*[@id="txtClave"]'
            login_btn_xpath = 'xpath=//*[@id="NeoIngresarButton1"]'
            
            # Buscar frame con el formulario de login
            login_frame = None
            for _ in range(20):
                for frame in page.frames:
                    try:
                        if frame.locator(usuario_xpath).count() > 0:
                            login_frame = frame
                            break
                    except Exception:
                        pass
                if login_frame:
                    break
                time.sleep(1)
            
            if login_frame:
                usuario = os.getenv("USUARIO", "1839")
                password = os.getenv("PASSWORD", "2022")
                print(f"Completando credenciales (Usuario: {usuario})...")
                login_frame.locator(usuario_xpath).fill(usuario)
                login_frame.locator(password_xpath).fill(password)
                login_frame.locator(login_btn_xpath).click()
                print("Clic en Ingresar realizado.")
                
                # Esperar a que el login se procese y se cargue la pantalla principal
                time.sleep(3)
                print("Login completado con éxito.")
            else:
                print("No se encontró el formulario de login automático. Puedes loguearte manualmente.")
                
        except Exception as e:
            print(f"Advertencia durante el login automático: {e}")
            print("Puedes continuar manualmente en el navegador.")

        # --- ABRIR AUTOMÁTICAMENTE CALL CENTER ---
        print("\nAbriendo módulo 'Call Center' (#favDiv1)...")
        try:
            modulos_frame = None
            for _ in range(25):
                for frame in page.frames:
                    try:
                        if frame.locator("#favDiv1, #favImg1").count() > 0:
                            modulos_frame = frame
                            break
                    except Exception:
                        pass
                if modulos_frame:
                    break
                time.sleep(1)

            if modulos_frame:
                print("Haciendo clic en 'Call Center'...")
                callcenter_btn = modulos_frame.locator("#favDiv1, #favImg1").first
                try:
                    callcenter_btn.click()
                except Exception:
                    modulos_frame.evaluate("() => { let el = document.querySelector('#favDiv1') || document.querySelector('#favImg1'); if (el) el.click(); }")

                print("Esperando apertura de la pestaña de Call Center (CALLCENTER)...")
                trunks_menu_loc = None
                menu_frame = None

                for intento in range(30):
                    time.sleep(1)
                    for p_idx, current_p in enumerate(context.pages):
                        for f_idx, frame in enumerate(current_p.frames):
                            try:
                                loc = frame.locator("#NeoWebMenu1WebMenu1_13_8, .MENUOPTION:has-text('Trunks')")
                                if loc.count() > 0:
                                    trunks_menu_loc = loc.first
                                    menu_frame = frame
                                    print(f"¡Opción 'Trunks' detectada en el menú (Pestaña #{p_idx+1}, Frame: '{frame.name}')!")
                                    break
                            except Exception:
                                pass
                        if trunks_menu_loc:
                            break
                    if trunks_menu_loc:
                        break
                    if intento % 5 == 0:
                        print(f"   Buscando menú Trunks (intento {intento+1}/30)... Pestañas abiertas: {len(context.pages)}")

                # --- PROCESO TRUNKS VÍA MENÚ LATERAL ---
                if menu_frame and trunks_menu_loc:
                    print("\n1. Haciendo clic en 'Trunks' en la barra lateral (#NeoWebMenu1WebMenu1_13_8)...")
                    try:
                        trunks_menu_loc.scroll_into_view_if_needed(timeout=2000)
                        trunks_menu_loc.click(timeout=5000)
                    except Exception as e_click:
                        print(f"   Ajustando clic con evento DOM: {e_click}")
                        menu_frame.evaluate("""() => {
                            let el = document.getElementById('NeoWebMenu1WebMenu1_13_8') || 
                                     Array.from(document.querySelectorAll('.MENUOPTION')).find(e => e.textContent.includes('Trunks'));
                            if (el) {
                                el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                                el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
                                el.click();
                            }
                        }""")
                    time.sleep(2)

                    print("2. Esperando carga de la pestaña Trunks (Trunks.aspx)...")
                    trunks_frame = None
                    for intento in range(25):
                        time.sleep(1)
                        for current_p in context.pages:
                            for frame in current_p.frames:
                                try:
                                    if "TRUNKS" in frame.url.upper() or frame.locator("#cboCampaigns").count() > 0:
                                        trunks_frame = frame
                                        break
                                except Exception:
                                    pass
                            if trunks_frame:
                                break
                        if trunks_frame:
                            break

                    if trunks_frame:
                        print(f"¡Frame de Trunks localizado con éxito: '{trunks_frame.name}' ({trunks_frame.url})!")
                        time.sleep(2)

                        print("3. Abriendo selector de campañas (#cntCabecera)...")
                        try:
                            cabecera = trunks_frame.locator("#cntCabecera, p.CaptionCont").first
                            cabecera.wait_for(state="visible", timeout=8000)
                            cabecera.click()
                            print("   Desplegable abierto.")
                            time.sleep(1)
                        except Exception as e_cab:
                            print(f"   Advertencia al abrir desplegable: {e_cab}")
                            trunks_frame.evaluate("() => { let el = document.getElementById('cntCabecera') || document.querySelector('.CaptionCont'); if (el) el.click(); }")
                            time.sleep(1)

                        print("4. Configurando selección: Todas las campañas activas EXCEPTO 1, 10, 27 y 50...")
                        res_config = trunks_frame.evaluate("""() => {
                            const noDeseadas = ['1', '10', '27', '50'];
                            const lis = Array.from(document.querySelectorAll('.options li, .SumoSelect li'));
                            let seleccionadas = [];
                            let deseleccionadas = [];

                            // 1. Primero intentar presionar 'Select All' si existe
                            const selectAllBtn = document.querySelector('.select-all, .MultiControls .select-all, p.select-all');
                            if (selectAllBtn) {
                                selectAllBtn.click();
                            }

                            // 2. Iterar sobre cada opción de la lista para garantizar el estado exacto
                            for (const li of lis) {
                                const txt = (li.textContent || '').trim();
                                if (!txt) continue;

                                const matchExact = txt.match(/^(\\d+)\\s*-\\s*/);
                                const idCampana = matchExact ? matchExact[1] : '';

                                const esNoDeseada = noDeseadas.includes(idCampana) || 
                                                    noDeseadas.some(id => txt.startsWith(id + ' -') || txt.startsWith(id + '-'));

                                const isSelected = li.classList.contains('selected') || 
                                                   (li.querySelector('input') && li.querySelector('input').checked);

                                const clickTarget = li.querySelector('label') || li.querySelector('i') || li;

                                if (esNoDeseada) {
                                    // Queremos que NO esté seleccionada
                                    if (isSelected) {
                                        clickTarget.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                                        clickTarget.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
                                        clickTarget.click();
                                        deseleccionadas.push(txt);
                                    }
                                } else {
                                    // Queremos que SÍ esté seleccionada
                                    if (!isSelected) {
                                        clickTarget.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                                        clickTarget.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
                                        clickTarget.click();
                                        seleccionadas.push(txt);
                                    }
                                }
                            }

                            // 3. Sincronizar select subyacente y disparar change
                            const sel = document.getElementById('cboCampaigns') || document.querySelector('select[name="cboCampaigns"]');
                            if (sel) {
                                for (let opt of sel.options) {
                                    const matchExact = opt.text.match(/^(\\d+)\\s*-\\s*/);
                                    const idEncontrado = matchExact ? matchExact[1] : opt.value;
                                    opt.selected = !noDeseadas.includes(idEncontrado) && !noDeseadas.includes(opt.value);
                                }
                                sel.dispatchEvent(new Event('input', { bubbles: true }));
                                sel.dispatchEvent(new Event('change', { bubbles: true }));
                                if (sel.onchange) sel.onchange();
                            }

                            return {
                                total_opciones: lis.length,
                                seleccionadas: seleccionadas,
                                deseleccionadas: deseleccionadas
                            };
                        }""")

                        print(f"   Resultado configuración: {res_config}")
                        time.sleep(1)

                        # Cerrar desplegable con Escape
                        page.keyboard.press("Escape")
                        time.sleep(0.5)
                        print("¡Proceso de selección finalizado con éxito!")
                    else:
                        print("No se localizó el frame de Trunks (Trunks.aspx) tras esperar.")
            else:
                print("No se localizó el panel de módulos inicial.")
        except Exception as err_cc:
            print(f"Advertencia al abrir Call Center / Trunks: {err_cc}")

        # Mensaje de instrucciones para el usuario
        print("\n" + "=" * 70)
        print("   ¡TRUNKS ABIERTO Y CONFIGURADO CON CAMPAÑA 50!")
        print("=" * 70)
        print(" Revisa que la pantalla de Trunks se muestre correctamente.")
        print(" Si deseas seguir grabando otras acciones, interactúa normalmente.")
        print(" Presiona Ctrl+C en esta terminal cuando termines.")
        print("=" * 70 + "\n")
        
        # Bucle de captura interactiva y detección de posición en tiempo real
        import json
        last_positions = {}
        try:
            while True:
                # 1. Monitorear y registrar la posición y tamaño exactos de cada ventana abierta
                for idx, current_page in enumerate(context.pages):
                    try:
                        pos = current_page.evaluate("""() => ({
                            title: document.title,
                            url: window.location.href,
                            x: window.screenX,
                            y: window.screenY,
                            w: window.outerWidth,
                            h: window.outerHeight
                        })""")
                        key = f"page_{idx}"
                        prev = last_positions.get(key)
                        if not prev or prev['x'] != pos['x'] or prev['y'] != pos['y'] or prev['w'] != pos['w'] or prev['h'] != pos['h']:
                            last_positions[key] = pos
                            print(f"\n[POSICION ACTUALIZADA] Ventana #{idx+1} ('{pos['title']}'):")
                            print(f"   X={pos['x']}, Y={pos['y']}, Ancho={pos['w']}, Alto={pos['h']}")
                            
                            # Si es la ventana del monitor de canales o una pestaña secundaria
                            cfg_data = {
                                "title": pos['title'],
                                "x": pos['x'],
                                "y": pos['y'],
                                "w": pos['w'],
                                "h": pos['h']
                            }
                            with open("canales_window_config.json", "w", encoding="utf-8") as f:
                                json.dump(cfg_data, f, indent=4)
                            print("   --> ¡Coordenadas guardadas en 'canales_window_config.json'!")
                    except Exception:
                        pass

                # 2. Asegurar que el script esté inyectado en todos los frames y páginas activas
                for current_page in context.pages:
                    for frame in current_page.frames:
                        try:
                            already_injected = frame.evaluate("typeof window.__tracker_installed !== 'undefined'")
                            if not already_injected:
                                frame.evaluate("window.__tracker_installed = true;")
                                frame.evaluate(tracker_script)
                        except Exception:
                            pass
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nGrabador detenido por el usuario.")
            if os.path.exists("canales_window_config.json"):
                print("Configuración guardada exitosamente en 'canales_window_config.json'.")
            print("Cerrando navegador...")
            browser.close()

if __name__ == "__main__":
    run()
