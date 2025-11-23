import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import os
import csv # Necesario para la detección robusta del separador

# ============================================
# PASO 1: EXTRAER LISTA DE PROFESORES DE ETSII
# ============================================

def get_profesores_etsii():
    
    """
    Extrae la lista de profesores del departamento de ETSII de la URJC
    """
    url = "https://servicios.urjc.es/pdi/departamento/Y157"
    print("Obteniendo lista de profesores de ETSII...")
    
    response = requests.get(url)
    # Manejar codificación por si acaso
    response.encoding = response.apparent_encoding 
    soup = BeautifulSoup(response.text, 'html.parser')
    
    profesores = []
    
    # Buscar todos los enlaces que apuntan a /pdi/ver/
    enlaces_profes = soup.find_all('a', href=lambda x: x and '/pdi/ver/' in x)
    
    for enlace in enlaces_profes:
        nombre = enlace.text.strip()
        # Eliminar el posible "(Profesor)" o similar
        nombre_limpio = nombre.split('(')[0].strip() 
        username = enlace['href'].split('/pdi/ver/')[-1]
        
        profesores.append({
            'nombre': nombre_limpio,
            'username': username,
            'url_perfil': f"https://servicios.urjc.es{enlace['href']}"
        })
    
    print(f"Encontrados {len(profesores)} profesores")
    return profesores


# ============================================
# CONFIGURAR SELENIUM
# ============================================

def setup_driver():
    """
    Configura el navegador Chrome con Selenium
    """
    chrome_options = Options()
    
    # Configurar carpeta de descargas
    download_dir = os.path.abspath("data/csv")
    Path(download_dir).mkdir(parents=True, exist_ok=True)
    
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Opciones para mejor rendimiento/ejecución sin errores
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080") 
    # chrome_options.add_argument("--headless")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver


# ============================================
# PASO 2: BUSCAR PROFESOR EN PORTAL CIENTÍFICO
# ============================================

def buscar_en_portal_cientifico(driver, nombre_completo):
    """
    Busca un profesor en el Portal Científico URJC usando Selenium
    """
    portal_url = "https://portalcientifico.urjc.es/es/"
    
    try:
        print(f"Buscando en Portal Científico...")
        driver.get(portal_url)
        
        # Esperar a que cargue la página
        time.sleep(4)
        
        # Buscar el campo de búsqueda por su ID exacto
        try:
            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "inputSearch-ipublic-nav"))
            )
        except:
            print(f"No se encontró el cuadro de búsqueda")
            return None
        
        # Escribir el nombre completo (apellidos + nombre)
        search_box.clear()
        search_box.send_keys(nombre_completo)
        print(f"Escrito: {nombre_completo}")
        
        # Esperar a que aparezca el desplegable con resultados
        time.sleep(3)
        
        # Buscar el primer resultado dentro del desplegable
        try:
            resultado = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#resultado-nav a.list-group-item"))
            )
            
            # Hacer clic en el primer resultado
            resultado.click()
            print(f"Haciendo clic en resultado del desplegable")
            
            # Esperar a que cargue el perfil
            time.sleep(4)
            
            # Confirmar la URL actual
            url_perfil_final = driver.current_url
            print(f"Perfil encontrado: {url_perfil_final}")
            return url_perfil_final
            
        except Exception as e:
            print(f"No aparecieron resultados para '{nombre_completo}'. Error: {e}")
            return None
            
    except Exception as e:
        print(f"Error buscando: {e}")
        return None


# ============================================
# PASO 3: DESCARGAR CSV DE PRODUCCIÓN
# ============================================

def descargar_csv_produccion(driver, url_perfil_investigador, nombre_profesor):
    """
    Accede al perfil del investigador y descarga el CSV usando Selenium
    """
    try:
        # Navegar al perfil
        driver.get(url_perfil_investigador)
        time.sleep(3)
        
        # Buscar y hacer clic en la pestaña "Producción"
        try:
            tab_produccion = driver.find_element(By.LINK_TEXT, "Producción")
            tab_produccion.click()
            time.sleep(3)
        except:
            print(f"No se encontró pestaña Producción")
            return None
        
        # Buscar el botón CSV
        try:
            boton_csv = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'buttons-csv')]"))
            )
            
            # Hacer clic en el botón
            boton_csv.click()
            print(f"Descargando CSV de {nombre_profesor}...")
            
            # Esperar a que se complete la descarga
            time.sleep(5) # Aumentar la espera por si la descarga es lenta
            
            # Renombrar el archivo descargado
            download_dir = "data/csv"
            import glob
            list_of_files = glob.glob(f'{download_dir}/*')
            
            if list_of_files:
                # Ordenar por fecha de creación para asegurar que es el último
                latest_file = max(list_of_files, key=os.path.getctime)
                
                # Crear nombre de archivo seguro
                nombre_seguro = nombre_profesor.replace(' ', '_').replace(',', '').replace('.', '')
                new_filename = f"{download_dir}/{nombre_seguro}.csv"
                
                # Si ya existe, eliminarlo primero (limpieza)
                if os.path.exists(new_filename):
                    os.remove(new_filename)
                    
                os.rename(latest_file, new_filename)
                print(f"CSV guardado: {new_filename}")
                return new_filename
            else:
                print(f"No se encontró archivo descargado")
                return None
                
        except Exception as e:
            print(f"Error haciendo clic en botón CSV: {e}")
            return None
            
    except Exception as e:
        print(f"Error en descarga: {e}")
        return None


# ============================================
# FUNCIÓN PRINCIPAL
# ============================================

def main():
    """
    Ejecuta el proceso completo de descarga de CSVs
    """
    
    # Obtener lista de profesores
    profesores = get_profesores_etsii()
    
    print(f"\nTotal profesores encontrados: {len(profesores)}")
    print("\nIniciando Selenium para descargar CSVs...\n")
    
    driver = setup_driver()
    exitosos = 0
    
    try:
        for i, profesor in enumerate(profesores, 1):
            print(f"\n{'='*60}")
            print(f"[{i}/{len(profesores)}] {profesor['nombre']}")
            print(f"{'='*60}")
            
            url_portal = buscar_en_portal_cientifico(driver, profesor['nombre'])
            
            if url_portal:
                csv_path = descargar_csv_produccion(driver, url_portal, profesor['nombre'])
                if csv_path:
                    exitosos += 1
            
            time.sleep(2)
        
        print(f"\n{'='*60}")
        print("Proceso completado!")
        print(f"CSVs descargados exitosamente: {exitosos}/{len(profesores)}")
        print(f"{'='*60}")
        
    finally:
        driver.quit()
        print("\nNavegador cerrado")

if __name__ == "__main__":
    main()