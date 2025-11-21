# app_principal.py - PRUEBA DEFINITIVA
import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account
import traceback
from datetime import datetime

st.set_page_config(page_title="Prueba Conexión", layout="wide")

def prueba_conexion_definitiva():
    """Prueba de conexión ultra-detallada"""
    
    st.title("🔧 Prueba Definitiva de Conexión")
    st.markdown("---")
    
    # PASO 1: Verificar secrets
    st.subheader("1. ✅ VERIFICANDO SECRETS")
    try:
        spreadsheet_id = st.secrets.SPREADSHEET_ID
        gcp_secrets = st.secrets.gcp_service_account
        
        st.success("✅ SPREADSHEET_ID encontrado")
        st.info(f"📋 ID: {spreadsheet_id}")
        st.success("✅ gcp_service_account encontrado")
        st.info(f"📧 Email: {gcp_secrets.client_email}")
        
    except Exception as e:
        st.error(f"❌ Error con secrets: {e}")
        return False
    
    # PASO 2: Crear credenciales
    st.subheader("2. 🔐 CREANDO CREDENCIALES")
    try:
        credentials_dict = {
            "type": gcp_secrets.type,
            "project_id": gcp_secrets.project_id,
            "private_key_id": gcp_secrets.private_key_id,
            "private_key": gcp_secrets.private_key,
            "client_email": gcp_secrets.client_email,
            "client_id": gcp_secrets.client_id,
            "auth_uri": gcp_secrets.auth_uri,
            "token_uri": gcp_secrets.token_uri,
            "auth_provider_x509_cert_url": gcp_secrets.auth_provider_x509_cert_url,
            "client_x509_cert_url": gcp_secrets.client_x509_cert_url
        }
        
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        st.success("✅ Credenciales creadas correctamente")
        
    except Exception as e:
        st.error(f"❌ Error creando credenciales: {e}")
        st.code(traceback.format_exc())
        return False
    
    # PASO 3: Autorizar gspread
    st.subheader("3. 🔑 AUTORIZANDO GSPREAD")
    try:
        gc = gspread.authorize(credentials)
        st.success("✅ Gspread autorizado correctamente")
        
    except Exception as e:
        st.error(f"❌ Error autorizando gspread: {e}")
        st.code(traceback.format_exc())
        return False
    
    # PASO 4: Abrir el spreadsheet
    st.subheader("4. 📂 ABRIENGO GOOGLE SHEET")
    try:
        st.info(f"🔍 Intentando abrir: {spreadsheet_id}")
        spreadsheet = gc.open_by_key(spreadsheet_id)
        st.success("✅ Google Sheet abierto correctamente")
        
        # Mostrar información del sheet
        st.info(f"📄 Título del Sheet: {spreadsheet.title}")
        
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("""
        ❌❌❌ GOOGLE SHEET NO ENCONTRADO ❌❌❌
        
        **Esto significa que:**
        1. ❌ El SPREADSHEET_ID es incorrecto O
        2. ❌ El Sheet NO está compartido con la Service Account
        
        **Verifica:**
        - ✅ SPREADSHEET_ID: 134YXDwV5Fe17Vt-tFh1GzC33f2zFVey75AALv5X-RNc
        - ✅ Email de Service Account: gastos-generales-dash@dashboardgastosgen.iam.gserviceaccount.com
        
        **¿Estás SEGURO de que compartiste el Sheet correcto?**
        """)
        return False
    except Exception as e:
        st.error(f"❌ Error abriendo Sheet: {e}")
        st.code(traceback.format_exc())
        return False
    
    # PASO 5: Acceder a la hoja
    st.subheader("5. 📋 ACCEDIENDO A LA HOJA")
    try:
        worksheet = spreadsheet.worksheet("registro_general_gastos")
        st.success("✅ Hoja 'registro_gastos' encontrada")
        
    except gspread.exceptions.WorksheetNotFound:
        st.error("""
        ❌ HOJA 'registro_gastos' NO ENCONTRADA
        
        **El Sheet existe pero la hoja no se llama 'registro_gastos'**
        
        **Hojas disponibles en este Sheet:"""
        )
        # Mostrar hojas disponibles
        try:
            worksheets = spreadsheet.worksheets()
            hojas = [ws.title for ws in worksheets]
            st.write("📑 Hojas disponibles:", hojas)
        except:
            st.write("No se pudieron listar las hojas")
        return False
    except Exception as e:
        st.error(f"❌ Error accediendo a la hoja: {e}")
        return False
    
    # PASO 6: Leer datos
    st.subheader("6. 📊 LEYENDO DATOS")
    try:
        datos = worksheet.get_all_records()
        df = pd.DataFrame(datos)
        st.success(f"🎉 ¡ÉXITO! Datos cargados: {len(df)} registros")
        
        # Mostrar preview
        st.subheader("📋 Vista Previa de Datos")
        st.dataframe(df.head(10))
        
        # Mostrar columnas
        st.subheader("🏷️ Columnas Encontradas")
        st.write(list(df.columns))
        
        return True
        
    except Exception as e:
        st.error(f"❌ Error leyendo datos: {e}")
        st.code(traceback.format_exc())
        return False

def main():
    # Ejecutar prueba completa
    resultado = prueba_conexion_definitiva()
    
    if resultado:
        st.balloons()
        st.success("""
        🎉 ¡CONEXIÓN EXITOSA!
        
        El problema está resuelto. Ahora puedes usar el dashboard completo.
        """)
    else:
        st.error("""
        🚨 **PROBLEMA NO RESUELTO**
        
        **Posibles causas:**
        1. 📧 **Email incorrecto al compartir** - Verifica que compartiste con: gastos-generales-dash@dashboardgastosgen.iam.gserviceaccount.com
        2. 🔑 **Permisos incorrectos** - Debe ser "Editor"
        3. 📄 **Sheet incorrecto** - Verifica que sea el Sheet correcto
        4. ⏰ **Demora en permisos** - A veces Google tarda unos minutos en aplicar los permisos
        
        **¿Puedes:**
        - Verificar en Google Sheets → "Compartir" que aparezca el email de la Service Account?
        - Intentar recargar esta página en 2-3 minutos?
        """)

if __name__ == "__main__":
    main()
