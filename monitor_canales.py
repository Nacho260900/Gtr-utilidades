import os
import time
import json
import ctypes
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

USUARIO = os.getenv("USUARIO", "1839")
PASSWORD = os.getenv("PASSWORD", "2022")
CONFIG_FILE = "canales_window_config.json"

# Configurar soporte para alta resolución (DPI Awareness) en Windows
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def cargar_config_ventana():
    """Carga la configuración guardada de posición y tamaño."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ADVERTENCIA] No se pudo leer {CONFIG_FILE}: {e}")
    # Valores por defecto calibrados
    return {
        "title": "ChartBoards",
        "x": 2660,
        "y": 306,
        "w": 546,
        "h": 553
    }


def move_window_by_title(title_substring, x, y, w, h):
    """Mueve y redimensiona una ventana en Windows buscando por título."""
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
            length = GetWindowTextLength(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                GetWindowText(hwnd, buff, length + 1)
                title = buff.value
                if title_substring.lower() in title.lower():
                    MoveWindow(hwnd, x, y, w, h, True)
                    target_hwnd = hwnd
                    return False
        return True

    EnumWindows(EnumWindowsProc(foreach_window), 0)
    return target_hwnd


def bring_window_to_front(hwnd):
    """Enfoca la ventana y la trae al frente."""
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        ctypes.windll.user32.BringWindowToTop(hwnd)


def run():
    print("==================================================")
    print("   Iniciando Automatización: MONITOR DE CANALES")
    print("==================================================")
    
    cfg = cargar_config_ventana()
    print(f"Configuración cargada: X={cfg['x']}, Y={cfg['y']}, Ancho={cfg['w']}, Alto={cfg['h']}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context(no_viewport=True)
        page = context.new_page()

        # 1. Login
        url = "http://172.16.20.10/NEOTEL/"
        print(f"1. Navegando a {url}...")
        try:
            page.goto(url, timeout=30000)
        except Exception as e:
            print(f"Error al navegar: {e}")
            return

        print("2. Ejecutando inicio de sesión...")
        try:
            usuario_xpath = 'xpath=//*[@id="txtUsuario"]'
            password_xpath = 'xpath=//*[@id="txtClave"]'
            login_btn_xpath = 'xpath=//*[@id="NeoIngresarButton1"]'

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

            if not login_frame:
                print("Error: No se encontró el formulario de login.")
                return

            print(f"   Completando credenciales (Usuario: {USUARIO})...")
            login_frame.locator(usuario_xpath).fill(USUARIO)
            login_frame.locator(password_xpath).fill(PASSWORD)
            login_frame.locator(login_btn_xpath).click()
            print("   Login enviado. Esperando panel de módulos...")
            time.sleep(3)

        except Exception as e:
            print(f"Error durante el login: {e}")
            return

        # 2. Localizar panel de módulos y hacer clic en Call Center
        print("3. Localizando módulo 'Call Center' (#favDiv1)...")
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

        if not modulos_frame:
            print("Error: No se localizó el panel de módulos.")
            return

        print("4. Haciendo clic en 'Call Center'...")
        callcenter_btn = modulos_frame.locator("#favDiv1, #favImg1").first
        try:
            callcenter_btn.click()
        except Exception:
            modulos_frame.evaluate("() => { let el = document.querySelector('#favDiv1') || document.querySelector('#favImg1'); if (el) el.click(); }")

        # 3. Esperar carga de la vista de Call Center
        print("5. Localizando frame de Call Center (CALLCENTER/Home.aspx)...")
        cc_frame = None
        for intento in range(30):
            time.sleep(1)
            for current_p in context.pages:
                for frame in current_p.frames:
                    try:
                        frame_url_up = frame.url.upper()
                        if "CALLCENTER" in frame_url_up or "HOME.ASPX" in frame_url_up:
                            if frame.locator("td#favDiv1, #favDiv1").count() > 0:
                                cc_frame = frame
                                break
                        elif frame.locator("td#favDiv1").count() > 0 and "MODULOS" not in frame_url_up:
                            cc_frame = frame
                            break
                    except Exception:
                        pass
                if cc_frame:
                    break
            if cc_frame:
                break

        if not cc_frame:
            print("Error: No se localizó el frame de Call Center.")
            return

        # 4. Clic en Canales Campañas y seleccionar canales todos
        print("6. Haciendo clic en 'Canales Campañas' (td#favDiv1)...")
        canales_btn = cc_frame.locator("td#favDiv1, #favDiv1").first
        canales_btn.wait_for(state="visible", timeout=10000)
        canales_btn.click()
        time.sleep(1)

        print("7. Seleccionando 'canales todos' en el menú...")
        clicked = False
        for _ in range(15):
            for current_p in context.pages:
                for frame in current_p.frames:
                    try:
                        res = frame.evaluate("""() => {
                            const items = Array.from(document.querySelectorAll('.context-menu-item, li, span, a'));
                            for (const el of items) {
                                const txt = (el.textContent || '').trim().toLowerCase();
                                if (txt === 'canales todos' || (txt.includes('canales') && txt.includes('todos'))) {
                                    el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
                                    el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
                                    el.click();
                                    return true;
                                }
                            }
                            return false;
                        }""")
                        if res:
                            clicked = True
                            break
                    except Exception:
                        pass
                if clicked:
                    break
            if clicked:
                break
            time.sleep(0.5)

        if not clicked:
            for current_p in context.pages:
                for frame in current_p.frames:
                    try:
                        loc = frame.locator(".context-menu-item:has-text('canales todos'), li:has-text('canales todos'), text='canales todos'")
                        if loc.count() > 0:
                            loc.first.click(force=True)
                            clicked = True
                            break
                    except Exception:
                        pass
                if clicked:
                    break

        print("8. Esperando apertura del pop-up del Monitor de Canales...")
        time.sleep(3)

        # 5. Posicionamiento de la ventana emergente según configuración
        title_search = cfg.get("title", "ChartBoards")
        print(f"9. Posicionando ventana '{title_search}' en X={cfg['x']}, Y={cfg['y']}, Ancho={cfg['w']}, Alto={cfg['h']}...")
        hwnd = move_window_by_title(title_search, cfg['x'], cfg['y'], cfg['w'], cfg['h'])
        if not hwnd:
            # Reintento por si el título contiene "Canal" o "Monitor"
            hwnd = move_window_by_title("Canal", cfg['x'], cfg['y'], cfg['w'], cfg['h'])
        
        if hwnd:
            time.sleep(0.5)
            move_window_by_title(title_search, cfg['x'], cfg['y'], cfg['w'], cfg['h'])
            bring_window_to_front(hwnd)
            print("¡Monitor de Canales posicionado con éxito en pantalla!")
        else:
            print("Advertencia: No se pudo localizar el HWND de la ventana emergente por título.")

        print("\n==================================================")
        print("   MONITOR DE CANALES ACTIVO Y EN EJECUCIÓN")
        print("   Presiona Ctrl+C en esta terminal para cerrar.")
        print("==================================================\n")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nCerrando Monitor de Canales...")
            browser.close()


if __name__ == "__main__":
    run()
