import asyncio
import glob
import os
import math
from playwright.async_api import async_playwright

async def grabar_demo_4k():
    print("Iniciando motor Async Playwright para grabación 4K UHD...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # Configuración 4K UHD y grabación en alta resolución
        context = await browser.new_context(
            viewport={"width": 3840, "height": 2160},
            color_scheme="dark",
            record_video_dir=".",
            record_video_size={"width": 3840, "height": 2160}
        )
        page = await context.new_page()

        print("Navegando al login de Gestión Pymes y autenticando...")
        await page.goto("http://localhost:5000/login")
        
        # Login rápido fuera del "tiempo" de cámara principal
        await page.fill("input[name='username']", "admin")
        await page.fill("input[name='password']", "admin123")
        await page.click("button[type='submit']")

        # 1. Dashboard Principal
        await page.wait_for_selector(".kpi-grid")
        
        # Inyectando CSS Cinematográfico
        print("Inyectando CSS cinematográfico (Smoothness & Hide Scrollbars)...")
        css_cinematico = """
            html { scroll-behavior: smooth !important; }
            ::-webkit-scrollbar { display: none !important; }
            body { -ms-overflow-style: none; scrollbar-width: none; }
        """
        await page.add_style_tag(content=css_cinematico)

        print("Mantenido estático por 4 segundos en Dashboard...")
        await page.wait_for_timeout(4000)

        # 2. Transición hacia tarjeta de Stock Crítico
        print("Movimiento suave hacia tarjeta de 'Stock Crítico'...")
        stock_kpi = page.locator("#kpi-stock")
        box = await stock_kpi.bounding_box()
        if box:
            target_x = box["x"] + box["width"] / 2
            target_y = box["y"] + box["height"] / 2
            # Move slowly (pasos altos)
            await page.mouse.move(target_x, target_y, steps=80)
            
        print("Efecto Hover estático por 2 segundos en Stock Crítico...")
        await page.wait_for_timeout(2000)
        
        print("Click hacia la vista de Inventario y Stock...")
        await stock_kpi.click()
        await page.wait_for_selector(".data-table")
        
        # Reinyectar CSS post-navegación
        await page.add_style_tag(content=css_cinematico)
        
        # 3. Interacción con Stock
        print("Realizando scroll muy lento hacia abajo...")
        await page.wait_for_timeout(1000)
        await page.mouse.wheel(0, 1500)
        await page.wait_for_timeout(3000)
        
        print("Realizando scroll muy lento hacia arriba...")
        await page.mouse.wheel(0, -1500)
        await page.wait_for_timeout(2000)

        # 4. Transición hacia Carga de Datos
        print("Movimiento suave hacia 'Importar CSV'...")
        nav_importar = page.locator(".nav-item", has_text="Importar CSV")
        box_nav = await nav_importar.bounding_box()
        if box_nav:
            await page.mouse.move(box_nav["x"] + box_nav["width"] / 2, box_nav["y"] + box_nav["height"] / 2, steps=80)
        await nav_importar.click()
        
        await page.wait_for_selector(".drop-zone")
        await page.add_style_tag(content=css_cinematico)

        # 5. Interacción de Mouse: Circular la zona de Drop Zone
        print("Mouse circulando suavemente el área de subida CSV...")
        drop_zone = page.locator(".drop-zone")
        dz_box = await drop_zone.bounding_box()
        if dz_box:
            cx = dz_box["x"] + dz_box["width"] / 2
            cy = dz_box["y"] + dz_box["height"] / 2
            r = 150 # Radio amplio en 4K
            # Movimiento circular suave (360 grados)
            for angle in range(0, 360, 8):
                rad = math.radians(angle)
                x = cx + r * math.cos(rad)
                y = cy + r * math.sin(rad)
                await page.mouse.move(x, y, steps=1) # 1 paso porque estamos iterando mucho
                
        print("Simulando clic final en Descargar Plantilla...")
        btn_plantilla = page.locator(".btn-success", has_text="Descargar Plantilla")
        box_plantilla = await btn_plantilla.bounding_box()
        if box_plantilla:
            await page.mouse.move(box_plantilla["x"] + box_plantilla["width"] / 2, box_plantilla["y"] + box_plantilla["height"] / 2, steps=60)
        await btn_plantilla.click()
        
        # Pausa final cinematográfica de 3 segundos
        await page.wait_for_timeout(3000) 
        
        await context.close()
        await browser.close()
        
        # Renombrar archivo de video auto-generado
        videos = glob.glob("*.webm")
        if videos:
            latest_video = max(videos, key=os.path.getctime)
            nuevo_nombre = "Demo_Comercial_4K.webm"
            if os.path.exists(nuevo_nombre):
                os.remove(nuevo_nombre)
            os.rename(latest_video, nuevo_nombre)
            print(f"==================================================")
            print(f"🎬 ¡Grabación 4K Cinematográfica finalizada con éxito!")
            print(f"Archivo guardado: {os.path.abspath(nuevo_nombre)}")
            print(f"==================================================")

if __name__ == "__main__":
    asyncio.run(grabar_demo_4k())
