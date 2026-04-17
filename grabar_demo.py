import time
import os
import glob
from playwright.sync_api import sync_playwright

def grabar_demo():
    print("Iniciando motor de grabación Playwright...")
    with sync_playwright() as p:
        # Lanzamos chromium, podemos forzar color_scheme dark para la web, aunque nuestro CSS ya lo es
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            color_scheme="dark",
            record_video_dir="."
        )
        page = context.new_page()

        print("Navegando al login de Gestión Pymes...")
        page.goto("http://localhost:5000/login")
        
        # Secuencia de Login
        page.fill("input[name='username']", "admin")
        page.fill("input[name='password']", "admin123")
        page.click("button[type='submit']")

        print("Dashboard Principal - Esperando estabilización...")
        page.wait_for_selector(".kpi-grid")
        # Pausa para que se aprecien las tarjetas según tu coreografía
        time.sleep(3.5)

        print("Simulando movimiento del mouse hacia menú lateral...")
        sidebar_link = page.locator(".nav-item", has_text="Movimientos")
        box = sidebar_link.bounding_box()
        if box:
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=20)
        time.sleep(1)
        
        print("Clic en Módulo de Movimientos...")
        sidebar_link.click()
        page.wait_for_selector(".data-table")
        time.sleep(1.5)
        
        print("Realizando scroll suave por la tabla de datos...")
        # Mouse scrolling actions
        page.mouse.wheel(0, 800)
        time.sleep(2)
        page.mouse.wheel(0, -800)
        time.sleep(1.5)

        print("Simulando clic en Exportar a Excel...")
        export_btn = page.locator("text=Exportar a Excel")
        export_btn.click()
        time.sleep(3) # Pausa final antes del corte

        # Cerrar el contexto obliga a guardar el stream del video a disco
        context.close()
        browser.close()
        
        # Playwright guarda nativamente los videos en formato WebM con nombres aleatorios.
        # Buscamos el archivo generado y lo renombramos.
        videos = glob.glob("*.webm")
        if videos:
            latest_video = max(videos, key=os.path.getctime)
            nuevo_nombre = "Demo_Sistema_Pyme.webm"
            # Si ya existe, lo borramos para no generar conflicto
            if os.path.exists(nuevo_nombre):
                os.remove(nuevo_nombre)
            os.rename(latest_video, nuevo_nombre)
            print(f"🎬 ¡Grabación finalizada con éxito! Archivo guardado: {nuevo_nombre}")
            print("Nota: Playwright exporta WebM en lugar de MP4 de forma nativa por estabilidad.")

if __name__ == "__main__":
    grabar_demo()
