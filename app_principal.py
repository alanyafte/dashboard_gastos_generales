# app_principal.py - VERSIÓN CORREGIDA
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import gspread
from google.oauth2 import service_account
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURACIÓN
# =============================================================================
st.set_page_config(
    page_title="Dashboard de Gastos Generales",
    page_icon="📊",
    layout="wide"
)

# =============================================================================
# VERIFICACIÓN DE SECRETS
# =============================================================================
def verificar_secrets():
    """Verifica que todos los secrets estén configurados correctamente"""
    try:
        if 'SPREADSHEET_ID' not in st.secrets:
            st.error("❌ SPREADSHEET_ID faltante en secrets")
            return False
            
        if 'gcp_service_account' not in st.secrets:
            st.error("❌ gcp_service_account faltante en secrets")
            return False
            
        gcp = st.secrets.gcp_service_account
        campos_requeridos = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
        
        for campo in campos_requeridos:
            if campo not in gcp:
                st.error(f"❌ {campo} faltante en gcp_service_account")
                return False
                
        return True
        
    except Exception as e:
        st.error(f"❌ Error verificando secrets: {e}")
        return False

# =============================================================================
# FUNCIONES DE CARGA - VERSIÓN CORREGIDA
# =============================================================================
@st.cache_data(ttl=3600)
def cargar_datos():
    """Carga datos desde Google Sheets - Versión corregida"""
    
    if not verificar_secrets():
        return pd.DataFrame()
    
    try:
        # Obtener los secrets
        spreadsheet_id = st.secrets.SPREADSHEET_ID
        gcp_secrets = st.secrets.gcp_service_account
        
        # Crear el diccionario de credenciales CORRECTAMENTE
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
        
        # Crear credenciales
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        
        # Autorizar y cargar datos
        gc = gspread.authorize(credentials)
        spreadsheet = gc.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet("registro_gastos")
        datos = worksheet.get_all_records()
        df = pd.DataFrame(datos)
        
        st.success(f"✅ Datos cargados exitosamente: {len(df)} registros")
        return df
        
    except Exception as e:
        st.error(f"❌ Error cargando datos: {str(e)}")
        
        # Debug adicional
        st.info("""
        **🔧 Información para Debug:**
        
        - Verifica que el Google Sheet esté compartido con: **gastos-generales-dash@dashboardgastosgen.iam.gserviceaccount.com**
        - Verifica que la hoja se llame exactamente: **registro_gastos**
        - Los secrets deben estar en formato TOML válido
        """)
        
        return pd.DataFrame()

# =============================================================================
# FUNCIONES DE LIMPIEZA
# =============================================================================
def limpiar_datos(df):
    """Limpieza de datos"""
    if df.empty:
        return df
        
    df_clean = df.copy()
    
    # Normalizar columnas
    df_clean.columns = [col.lower().strip() for col in df_clean.columns]
    
    # Limpiar fecha
    df_clean['fecha'] = pd.to_datetime(df_clean['fecha'], errors='coerce', dayfirst=True)
    
    # Limpiar monto
    df_clean['monto'] = (
        df_clean['monto'].astype(str)
        .str.replace('$', '', regex=False)
        .str.replace(',', '', regex=False)
        .str.strip()
    )
    df_clean['monto'] = pd.to_numeric(df_clean['monto'], errors='coerce')
    
    # Limpiar textos
    for col in ['proveedor', 'descripcion', 'forma_pago', 'cuenta', 'subcuenta']:
        if col in df_clean.columns:
            df_clean[col] = (
                df_clean[col].astype(str)
                .str.strip()
                .str.upper()
                .replace(['NAN', 'NONE', 'NULL', ''], 'NO ESPECIFICADO')
            )
    
    # Clasificar cuentas principales
    def clasificar_cuenta(subcuenta):
        subcuenta_str = str(subcuenta)
        if 'NOMINA' in subcuenta_str or 'NÓMINA' in subcuenta_str:
            return 'NÓMINA'
        elif 'ARRENDAMIENTO' in subcuenta_str:
            return 'ARRENDAMIENTOS'
        elif 'IMPUESTO' in subcuenta_str or 'ISR' in subcuenta_str or 'ISN' in subcuenta_str:
            return 'IMPUESTOS'
        elif 'MERCADERIA' in subcuenta_str or 'MERCANC' in subcuenta_str:
            return 'MERCADERÍA'
        elif 'MATERIA' in subcuenta_str:
            return 'MATERIA PRIMA'
        elif 'GASTOS' in subcuenta_str:
            return 'GASTOS OPERATIVOS'
        elif 'SERVICIOS' in subcuenta_str:
            return 'SERVICIOS'
        elif 'VIAJES' in subcuenta_str:
            return 'VIAJES'
        else:
            return 'OTROS'
    
    df_clean['cuenta_principal'] = df_clean['subcuenta'].apply(clasificar_cuenta)
    df_clean['subcuenta_limpia'] = df_clean['subcuenta'].str.replace('SUB_', '', regex=False)
    df_clean = df_clean.dropna(subset=['fecha', 'monto'])
    
    return df_clean

# =============================================================================
# INTERFAZ PRINCIPAL SIMPLIFICADA
# =============================================================================
def main():
    st.title("🚀 Dashboard de Gastos Generales")
    st.markdown("---")
    
    # Verificar secrets primero
    if not verificar_secrets():
        st.error("""
        ## 🔐 Configuración Requerida
        
        Por favor verifica que los secrets estén configurados correctamente en Streamlit Cloud.
        """)
        return
    
    # Cargar datos
    with st.spinner('📥 Cargando datos desde Google Sheets...'):
        df_raw = cargar_datos()
    
    if df_raw.empty:
        st.error("No se pudieron cargar los datos. Verifica la configuración.")
        return
        
    # Limpiar datos
    df = limpiar_datos(df_raw)
    
    if df.empty:
        st.error("No hay datos válidos después de la limpieza.")
        return
    
    # =========================================================================
    # MÉTRICAS PRINCIPALES
    # =========================================================================
    st.header("📊 Métricas Principales")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_gastado = df['monto'].sum()
        st.metric("Total Gastado", f"${total_gastado:,.2f}")
    
    with col2:
        transacciones = len(df)
        st.metric("Transacciones", f"{transacciones:,}")
    
    with col3:
        promedio = df['monto'].mean()
        st.metric("Promedio", f"${promedio:,.2f}")
    
    with col4:
        dias = df['fecha'].nunique()
        st.metric("Días Activos", dias)
    
    st.markdown("---")
    
    # =========================================================================
    # GRÁFICOS SIMPLES
    # =========================================================================
    
    # Tendencias
    st.subheader("📈 Evolución de Gastos")
    df_diario = df.groupby(df['fecha'].dt.date)['monto'].sum().reset_index()
    fig_tendencias = px.line(df_diario, x='fecha', y='monto', title='Gastos Diarios')
    st.plotly_chart(fig_tendencias, use_container_width=True)
    
    # Cuentas principales
    st.subheader("🏷️ Distribución por Cuenta")
    gastos_cuenta = df.groupby('cuenta_principal')['monto'].sum().sort_values(ascending=True)
    fig_cuentas = px.bar(
        x=gastos_cuenta.values, 
        y=gastos_cuenta.index, 
        orientation='h',
        title='Gastos por Cuenta Principal'
    )
    st.plotly_chart(fig_cuentas, use_container_width=True)
    
    # Tabla de datos
    st.subheader("📋 Últimas Transacciones")
    st.dataframe(df.head(20), use_container_width=True)

if __name__ == "__main__":
    main()
