import os
import time
import asyncio
from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()

USUARIO = os.getenv("USUARIO", "1839")
PASSWORD = os.getenv("PASSWORD", "2022")


async def ejecutar_flujo_trunks(browser, window_index, modo_campana="50"):
    """
    Ejecuta el flujo completo de inicio de sesión, ingreso a Call Center y configuración de Trunks.
    - modo_campana == "50": Selecciona únicamente la campaña '50 - PREDICTIVA PRINCIPAL'.
    - modo_campana == "resto": Selecciona todas las campañas EXCEPTO '1', '10', '27' y '50'.
    """
    print(f"\n[{window_index}] Iniciando Trunks ({'Campaña 50' if modo_campana == '50' else 'Todas excepto 1, 10, 27, 50'})...")

    context = await browser.new_context(no_viewport=True)
    page = await context.new_page()

    # 1. Login
    url = "http://172.16.20.10/NEOTEL/"
    print(f"[{window_index}] 1. Navegando a {url}...")
    try:
        await page.goto(url, timeout=30000)
    except Exception as e:
        print(f"[{window_index}] Error al navegar: {e}")
        return None

    try:
        usuario_xpath = 'xpath=//*[@id="txtUsuario"]'
        password_xpath = 'xpath=//*[@id="txtClave"]'
        login_btn_xpath = 'xpath=//*[@id="NeoIngresarButton1"]'

        login_frame = None
        for _ in range(20):
            for frame in page.frames:
                try:
                    if await frame.locator(usuario_xpath).count() > 0:
                        login_frame = frame
                        break
                except Exception:
                    pass
            if login_frame:
                break
            await asyncio.sleep(1)

        if not login_frame:
            print(f"[{window_index}] Error: No se encontró formulario de login.")
            return None

        print(f"[{window_index}] 2. Completando credenciales...")
        await login_frame.locator(usuario_xpath).fill(USUARIO)
        await login_frame.locator(password_xpath).fill(PASSWORD)
        await login_frame.locator(login_btn_xpath).click()
        print(f"[{window_index}] Login enviado. Esperando módulos...")
        await asyncio.sleep(3)

    except Exception as e:
        print(f"[{window_index}] Error durante el login: {e}")
        return None

    # 2. Localizar panel de módulos y hacer clic en Call Center
    print(f"[{window_index}] 3. Localizando módulo 'Call Center' (#favDiv1)...")
    modulos_frame = None
    for _ in range(25):
        for frame in page.frames:
            try:
                if await frame.locator("#favDiv1, #favImg1").count() > 0:
                    modulos_frame = frame
                    break
            except Exception:
                pass
        if modulos_frame:
            break
        await asyncio.sleep(1)

    if not modulos_frame:
        print(f"[{window_index}] Error: No se localizó panel de módulos.")
        return None

    print(f"[{window_index}] 4. Haciendo clic en 'Call Center'...")
    try:
        callcenter_btn = modulos_frame.locator("#favDiv1, #favImg1").first
        await callcenter_btn.click()
    except Exception:
        await modulos_frame.evaluate("() => { let el = document.querySelector('#favDiv1') || document.querySelector('#favImg1'); if (el) el.click(); }")

    # 3. Esperar a que cargue la vista de Call Center y ubicar el menú lateral
    print(f"[{window_index}] 5. Esperando menú lateral de Call Center...")
    trunks_menu_loc = None
    menu_frame = None

    for intento in range(30):
        await asyncio.sleep(1)
        for current_p in context.pages:
            for frame in current_p.frames:
                try:
                    loc = frame.locator("#NeoWebMenu1WebMenu1_13_8, .MENUOPTION:has-text('Trunks')")
                    if await loc.count() > 0:
                        trunks_menu_loc = loc.first
                        menu_frame = frame
                        break
                except Exception:
                    pass
            if trunks_menu_loc:
                break
        if trunks_menu_loc:
            break

    if not menu_frame or not trunks_menu_loc:
        print(f"[{window_index}] Error: No se localizó la opción 'Trunks' en el menú lateral.")
        return None

    # 4. Clic en 'Trunks'
    print(f"[{window_index}] 6. Haciendo clic en 'Trunks' en el menú lateral...")
    try:
        await trunks_menu_loc.scroll_into_view_if_needed(timeout=2000)
        await trunks_menu_loc.click(timeout=5000)
    except Exception:
        await menu_frame.evaluate("""() => {
            let el = document.getElementById('NeoWebMenu1WebMenu1_13_8') || 
                     Array.from(document.querySelectorAll('.MENUOPTION')).find(e => e.textContent.includes('Trunks'));
            if (el) {
                el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
                el.click();
            }
        }""")
    await asyncio.sleep(2)

    # 5. Esperar frame de Trunks (Trunks.aspx)
    print(f"[{window_index}] 7. Esperando carga de la pestaña Trunks (Trunks.aspx)...")
    trunks_frame = None
    for _ in range(25):
        await asyncio.sleep(1)
        for current_p in context.pages:
            for frame in current_p.frames:
                try:
                    if "TRUNKS" in frame.url.upper() or await frame.locator("#cboCampaigns").count() > 0:
                        trunks_frame = frame
                        break
                except Exception:
                    pass
            if trunks_frame:
                break
        if trunks_frame:
            break

    if not trunks_frame:
        print(f"[{window_index}] Error: No se localizó el frame de Trunks.")
        return None

    await asyncio.sleep(1.5)

    # 6. Abrir selector de campañas
    print(f"[{window_index}] 8. Abriendo selector de campañas (#cntCabecera)...")
    try:
        cabecera = trunks_frame.locator("#cntCabecera, p.CaptionCont").first
        await cabecera.wait_for(state="visible", timeout=8000)
        await cabecera.click()
    except Exception:
        await trunks_frame.evaluate("() => { let el = document.getElementById('cntCabecera') || document.querySelector('.CaptionCont'); if (el) el.click(); }")
    await asyncio.sleep(1)

    # 7. Configurar campañas según el modo
    if modo_campana == "50":
        print(f"[{window_index}] 9. Seleccionando únicamente Campaña '50 - PREDICTIVA PRINCIPAL'...")
        await trunks_frame.evaluate("""() => {
            const sel = document.getElementById('cboCampaigns') || document.querySelector('select[name="cboCampaigns"]');
            
            // Clic en la opción 50 en la lista
            const lis = Array.from(document.querySelectorAll('.options li, .SumoSelect li'));
            for (const li of lis) {
                const txt = (li.textContent || '').trim();
                if (txt.includes('50') && (txt.includes('PREDICTIVA') || txt.includes('PRINCIPAL') || txt.startsWith('50'))) {
                    const target = li.querySelector('label') || li.querySelector('i') || li;
                    target.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                    target.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
                    target.click();
                    break;
                }
            }

            if (sel) {
                sel.value = '50';
                for (let opt of sel.options) {
                    if (opt.value === '50' || opt.text.includes('50')) {
                        opt.selected = true;
                        break;
                    }
                }
                sel.dispatchEvent(new Event('input', { bubbles: true }));
                sel.dispatchEvent(new Event('change', { bubbles: true }));
                if (sel.onchange) sel.onchange();
            }
        }""")
    else:
        print(f"[{window_index}] 9. Configurando 'Todas las campañas EXCEPTO 1, 10, 27 y 50'...")
        await trunks_frame.evaluate("""() => {
            const noDeseadas = ['1', '10', '27', '50'];
            const lis = Array.from(document.querySelectorAll('.options li, .SumoSelect li'));

            // Select all primero si existe
            const selectAllBtn = document.querySelector('.select-all, .MultiControls .select-all, p.select-all');
            if (selectAllBtn) {
                selectAllBtn.click();
            }

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
                    if (isSelected) {
                        clickTarget.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                        clickTarget.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
                        clickTarget.click();
                    }
                } else {
                    if (!isSelected) {
                        clickTarget.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                        clickTarget.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
                        clickTarget.click();
                    }
                }
            }

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
        }""")

    await asyncio.sleep(1)
    await page.keyboard.press("Escape")
    print(f"[{window_index}] ¡Trunks configurado y listo con éxito!")
    return context, page


async def run():
    print("==================================================")
    print("  Iniciando Automatización: 2 VENTANAS DE TRUNKS")
    print("==================================================")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--start-maximized"])

        # Ejecución asíncrona en paralelo de ambos Trunks
        results = await asyncio.gather(
            ejecutar_flujo_trunks(browser, 1, modo_campana="50"),
            ejecutar_flujo_trunks(browser, 2, modo_campana="resto")
        )

        print("\n==================================================")
        print("   AMBOS TRUNKS ABIERTOS Y EN EJECUCIÓN")
        print("   - Ventana 1: Campaña 50")
        print("   - Ventana 2: Todas excepto 1, 10, 27 y 50")
        print("   Presiona Ctrl+C en esta terminal para cerrar.")
        print("==================================================\n")

        try:
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, asyncio.CancelledError):
            print("\nCerrando navegadores...")
            await browser.close()


if __name__ == "__main__":
    asyncio.run(run())
