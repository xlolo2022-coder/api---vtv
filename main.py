from fastapi import FastAPI, HTTPException
from DrissionPage import ChromiumPage, ChromiumOptions
import time
import os

app = FastAPI(
    title="VTV Consulta API",
    description="API para consultar estado e historial de VTV en PBA",
    version="1.0"
)

# Configuración de Chromium para entornos headless / Docker / Render
co = ChromiumOptions()
co.no_imgs(False)
co.headless(True)  # En servidores corre sin pantalla física

# Buscar el binario de Chromium si está en Linux / Render
if os.path.exists("/usr/bin/chromium"):
    co.set_browser_path("/usr/bin/chromium")
elif os.path.exists("/usr/bin/chromium-browser"):
    co.set_browser_path("/usr/bin/chromium-browser")

print("[*] Iniciando navegador Chromium en segundo plano...")
page = ChromiumPage(addr_or_opts=co)

try:
    page.get("https://vtv.gba.gob.ar/consultar-vtv")
except Exception as e:
    print(f"[-] Error inicializando la web de VTV: {e}")


@app.get("/")
def home():
    return {"status": "ok", "message": "API VTV activa. Usa /consultar/{patente}"}


@app.get("/consultar/{patente}")
def consultar_vtv(patente: str):
    patente_clean = patente.strip().upper()

    try:
        # 1. Encontrar input, limpiar y escribir patente
        input_box = page.ele('#nroObleaPatente', timeout=5)
        if not input_box:
            raise HTTPException(status_code=500, detail="No se encontró el campo de búsqueda en la web de VTV.")

        input_box.clear()
        input_box.input(patente_clean)

        # 2. Clic en el botón consultar
        btn_consultar = page.ele('.consultarVTV__btn', timeout=5)
        if btn_consultar:
            btn_consultar.click()
        else:
            raise HTTPException(status_code=500, detail="No se encontró el botón de consultar.")

        # 3. Esperar renderizado y hacer scroll para forzar la carga de tarjetas
        time.sleep(4)
        try:
            page.scroll.down(800)
            time.sleep(2)
        except:
            pass

        # 4. Cerrar cartel emergente (SweetAlert) si aparece
        try:
            swal_btn = page.ele('.swal2-confirm', timeout=1)
            if swal_btn:
                swal_btn.click()
                time.sleep(1)
        except:
            pass

        # 5. Verificar si cargó el contenedor de respuesta
        response_container = page.ele('.consultarVTV__response', timeout=6)
        if not response_container or "Resultados de la Verificación" not in response_container.text:
            return {
                "patente": patente_clean,
                "encontrado": False,
                "mensaje": "No se encontró información o la patente no existe."
            }

        # Extracción de datos del vehículo
        try:
            marca = response_container.eles('.responseConsultaVtv__vehicle_datos_item_container')[0].ele('tag:p').text
        except:
            marca = "No disponible"

        try:
            modelo = response_container.eles('.responseConsultaVtv__vehicle_datos_item_container')[1].ele('tag:p').text
        except:
            modelo = "No disponible"

        try:
            oblea_actual = response_container.eles('.responseConsultaVtv__vehicle_datos_item_container')[2].ele('tag:p').text
        except:
            oblea_actual = "No disponible"

        try:
            estado_actual = response_container.ele('.responseConsultaVtv__estado_badge').text
        except:
            estado_actual = "No disponible"

        # Detalle de última verificación
        ultima_verificacion = None
        vencimiento_actual = None
        try:
            rows = response_container.eles('.responseConsultaVtv__estado_row')
            if len(rows) > 0:
                ultima_verificacion = rows[0].ele('tag:p').text
            if len(rows) > 1:
                vencimiento_actual = rows[1].ele('tag:p').text
        except:
            pass

        # Extracción del historial completo mediante JS
        js_script = """
        const cards = document.querySelectorAll('.responseConsultaVtv__historial_list .responseConsultaVtvItem__card');
        const results = [];
        cards.forEach(card => {
            const fecha = card.querySelector('.responseConsultaVtvItem__h3')?.textContent || '';
            const estado = card.querySelector('.responseConsultaVtvItem__badge')?.textContent || '';
            const detalles = [...card.querySelectorAll('.responseConsultaVtv__location')].map(el => el.textContent.trim());
            const vencimiento = card.querySelector('.responseConsultaVtv__right > h3.responseConsultaVtv__vencimiento')?.textContent || '';
            results.push({ fecha, estado, detalles, vencimiento });
        });
        return results;
        """
        historial_raw = page.run_js(js_script) or []

        # Estructurar bien las tarjetas del historial
        historial_procesado = []
        for item in historial_raw:
            detalles = item.get("detalles", [])
            planta = detalles[0] if len(detalles) > 0 else "N/D"
            tipo_inspeccion = detalles[1] if len(detalles) > 1 else "N/D"
            numero_oblea = detalles[2] if len(detalles) > 2 else "Sin oblea"

            historial_procesado.append({
                "fecha": item.get("fecha", "").replace("Fecha de Verificación: ", "").strip(),
                "estado": item.get("estado", "").strip(),
                "planta": planta.replace("Planta: ", "").strip(),
                "tipo_inspeccion": tipo_inspeccion.replace("Tipo de Inspección: ", "").strip(),
                "numero_oblea": numero_oblea.replace("Número Oblea: ", "").strip(),
                "vencimiento": item.get("vencimiento", "").replace("Vencimiento: ", "").strip()
            })

        return {
            "patente": patente_clean,
            "encontrado": True,
            "vehiculo": {
                "marca": marca,
                "modelo": modelo,
                "oblea_actual": oblea_actual,
                "estado_actual": estado_actual,
                "ultima_verificacion": ultima_verificacion,
                "vencimiento_actual": vencimiento_actual
            },
            "cantidad_historico": len(historial_procesado),
            "historial": historial_procesado
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando patente {patente_clean}: {str(e)}")