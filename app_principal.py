# app_principal.py - VERSIÓN CON DEBUG COMPLETO
import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2 import service_account
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="Dashboard Gastos", layout="wide")

def debug_secrets():
    """Debug completo de los secrets"""
    st.title("🔧 Debug de Configuración")
    
    st.subheader("1. Secrets Disponibles:")
    try:
        # Mostrar todas las keys disponibles
        secrets_keys = list(st.secrets.keys())
        st.write(f"Keys encontradas: {secrets_keys}")
        
        # Verificar SPREADSHEET_ID
        if 'SPREADSHEET_ID' in st.secrets:
            st.success(f"✅ SPREADSHEET_ID: {st.secrets.SPREADSHEET_ID}")
        else:
            st.error("❌ SPREADSHEET_ID no encontrado")
            
        # Verificar gcp_service_account
        if 'gcp_service_account' in st.secrets:
            st.success("✅ gcp_service_account encontrado")
            gcp = st.secrets.gcp_service_account
            st.write("Campos en gcp_service_account:", list(gcp.keys()))
        else:
            st.error("❌ gcp_service_account no encontrado")
            
    except Exception as e:
        st.error(f"Error accediendo a secrets: {e}")

def cargar_datos_seguro():
    """Intenta cargar datos de forma segura"""
    try:
        # Verificar secrets básicos
        if 'SPREADSHEET_ID' not in st.secrets:
            st.error("SPREADSHEET_ID no encontrado en secrets")
            return pd.DataFrame()
            
        if 'gcp_service_account' not in st.secrets:
            st.error("gcp_service_account no encontrado en secrets")
            return pd.DataFrame()
        
        # Obtener valores
        spreadsheet_id = st.secrets.SPREADSHEET_ID
        gcp_secrets = st.secrets.gcp_service_account
        
        st.info(f"SPREADSHEET_ID: {spreadsheet_id}")
        st.info(f"Client Email: {gcp_secrets.client_email}")
        
        # Crear credenciales
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
        
        # Conectar a Google Sheets
        gc = gspread.authorize(credentials)
        spreadsheet = gc.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet("registro_gastos")
        datos = worksheet.get_all_records()
        df = pd.DataFrame(datos)
        
        st.success(f"✅ Datos cargados: {len(df)} registros")
        return df
        
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("""
        ❌ Google Sheet no encontrado
        
        **Verifica que:**
        1. El SPREADSHEET_ID sea correcto
        2. El Sheet esté compartido con: **gastos-generales-dash@dashboardgastosgen.iam.gserviceaccount.com**
        """)
    except gspread.exceptions.APIError as e:
        st.error(f"❌ Error de API: {e}")
        st.info("Verifica los permisos de la Service Account")
    except Exception as e:
        st.error(f"❌ Error inesperado: {e}")
    
    return pd.DataFrame()

def main():
    # Primero mostrar debug
    debug_secrets()
    
    st.markdown("---")
    
    # Intentar cargar datos
    st.subheader("2. 🔄 Probando Conexión...")
    
    with st.spinner('Conectando con Google Sheets...'):
        df = cargar_datos_seguro()
    
    if not df.empty:
        st.success("🎉 ¡Conexión exitosa!")
        st.subheader("3. 📊 Vista Previa de Datos:")
        st.dataframe(df.head(10))
        
        # Métricas simples
        st.subheader("4. 📈 Métricas Básicas:")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Registros", len(df))
        with col2:
            if 'monto' in df.columns:
                df['monto_clean'] = pd.to_numeric(df['monto'].astype(str).str.replace('$', '').str.replace(',', ''), errors='coerce')
                total = df['monto_clean'].sum()
                st.metric("Total", f"${total:,.2f}")
        with col3:
            if 'fecha' in df.columns:
                df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
                dias = df['fecha'].nunique()
                st.metric("Días", dias)
    
    else:
        st.error("""
        ## 🚨 Configuración Requerida
        
        **Problemas detectados:**
        
        1. **Secrets mal configurados** - Verifica el formato en Streamlit Cloud
        2. **Sheet no compartido** - Comparte con: gastos-generales-dash@dashboardgastosgen.iam.gserviceaccount.com
        3. **SPREADSHEET_ID incorrecto** - Verifica el ID del Google Sheet
        
        **Formato correcto de secrets:**
        ```toml
        SPREADSHEET_ID = "134YXDwV5Fe17Vt-tFh1GzC33f2zFVey75AALv5X-RNc"
        
        [gcp_service_account]
        type = "service_account"
        project_id = "dashboardgastosgen"
        private_key_id = "342d3c1bb95ab7b8662f318888967eb97a95c1c6"
        private_key = "-----BEGIN PRIVATE KEY-----\\nMIIEvQ...\\n-----END PRIVATE KEY-----\\n"
        client_email = "gastos-generales-dash@dashboardgastosgen.iam.gserviceaccount.com"
        client_id = "100175800584016359802"
        auth_uri = "https://accounts.google.com/o/oauth2/auth"
        token_uri = "https://oauth2.googleapis.com/token"
        auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
        client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/gastos-generales-dash%40dashboardgastosgen.iam.gserviceaccount.com"
        ```
        """)

if __name__ == "__main__":
    main()
