# app_principal.py
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
# CONFIGURACIÓN DE LA PÁGINA
# =============================================================================
st.set_page_config(
    page_title="Dashboard de Gastos Generales",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# FUNCIONES DE CARGA Y LIMPIEZA
# =============================================================================
@st.cache_data(ttl=3600)  # Cache de 1 hora
def cargar_datos():
    """Carga datos desde Google Sheets"""
    try:
        # Conexión usando secrets de Streamlit Cloud
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        gc = gspread.authorize(credentials)
        
        # Cargar datos
        spreadsheet = gc.open_by_key(st.secrets["SPREADSHEET_ID"])
        worksheet = spreadsheet.worksheet("registro_gastos")
        datos = worksheet.get_all_records()
        df = pd.DataFrame(datos)
        
        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

def limpiar_datos(df):
    """Limpieza de datos"""
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
        else:
            return 'OTROS'
    
    df_clean['cuenta_principal'] = df_clean['subcuenta'].apply(clasificar_cuenta)
    
    # Eliminar filas sin fecha o monto
    df_clean = df_clean.dropna(subset=['fecha', 'monto'])
    
    return df_clean

# =============================================================================
# FUNCIONES DE GRÁFICOS
# =============================================================================
def crear_grafico_tendencias(df):
    """Crea gráfico de tendencias temporales"""
    df_diario = df.groupby(df['fecha'].dt.date)['monto'].sum().reset_index()
    df_diario['fecha'] = pd.to_datetime(df_diario['fecha'])
    
    fig = px.line(
        df_diario,
        x='fecha',
        y='monto',
        title='📈 Evolución Diaria de Gastos',
        labels={'monto': 'Monto ($ MXN)', 'fecha': 'Fecha'}
    )
    fig.update_layout(height=400, showlegend=False)
    return fig

def crear_grafico_cuentas(df):
    """Crea gráfico de barras por cuenta principal"""
    gastos_cuenta = df.groupby('cuenta_principal')['monto'].sum().sort_values(ascending=True)
    
    fig = px.bar(
        x=gastos_cuenta.values,
        y=gastos_cuenta.index,
        orientation='h',
        title='🏷️ Distribución por Cuenta Principal',
        labels={'x': 'Monto ($ MXN)', 'y': 'Cuenta'},
        color=gastos_cuenta.values,
        color_continuous_scale='viridis'
    )
    fig.update_layout(height=400, showlegend=False)
    return fig

def crear_grafico_formas_pago(df):
    """Crea gráfico de torta de formas de pago"""
    formas_pago = df['forma_pago'].value_counts()
    
    fig = px.pie(
        values=formas_pago.values,
        names=formas_pago.index,
        title='💳 Distribución por Forma de Pago',
        hole=0.4
    )
    fig.update_layout(height=400)
    return fig

def crear_grafico_proveedores(df):
    """Crea gráfico de top proveedores"""
    top_proveedores = df.groupby('proveedor')['monto'].sum().sort_values(ascending=False).head(10)
    
    fig = px.bar(
        x=top_proveedores.values,
        y=top_proveedores.index,
        orientation='h',
        title='🏢 Top 10 Proveedores por Monto',
        labels={'x': 'Monto ($ MXN)', 'y': 'Proveedor'},
        color=top_proveedores.values,
        color_continuous_scale='plasma'
    )
    fig.update_layout(height=500)
    return fig

# =============================================================================
# INTERFAZ PRINCIPAL
# =============================================================================
def main():
    # Header
    st.title("🚀 Dashboard de Gastos Generales")
    st.markdown("Análisis interactivo en tiempo real - Actualizado automáticamente")
    st.markdown("---")
    
    # Cargar datos
    with st.spinner('📥 Cargando datos desde Google Sheets...'):
        df_raw = cargar_datos()
        
    if df_raw.empty:
        st.error("❌ No se pudieron cargar los datos. Verifica la conexión con Google Sheets.")
        return
        
    df = limpiar_datos(df_raw)
    
    if df.empty:
        st.error("❌ No hay datos válidos después de la limpieza.")
        return
    
    # =========================================================================
    # SIDEBAR - FILTROS
    # =========================================================================
    st.sidebar.title("🎛️ Panel de Control")
    
    # Filtro de fechas
    fecha_min = df['fecha'].min().date()
    fecha_max = df['fecha'].max().date()
    
    st.sidebar.subheader("Filtrar por Fecha")
    rango_fechas = st.sidebar.date_input(
        "Selecciona el rango:",
        value=(fecha_min, fecha_max),
        min_value=fecha_min,
        max_value=fecha_max
    )
    
    if len(rango_fechas) == 2:
        df = df[(df['fecha'].dt.date >= rango_fechas[0]) & 
                (df['fecha'].dt.date <= rango_fechas[1])]
    
    # Filtro de cuentas
    st.sidebar.subheader("Filtrar por Cuenta")
    cuentas = ['TODAS'] + sorted(df['cuenta_principal'].unique().tolist())
    cuenta_seleccionada = st.sidebar.selectbox("Cuenta principal:", cuentas)
    
    if cuenta_seleccionada != 'TODAS':
        df = df[df['cuenta_principal'] == cuenta_seleccionada]
    
    # Filtro de montos
    st.sidebar.subheader("Filtrar por Monto")
    monto_min, monto_max = st.sidebar.slider(
        "Rango de montos:",
        min_value=float(df['monto'].min()),
        max_value=float(df['monto'].max()),
        value=(float(df['monto'].min()), float(df['monto'].max()))
    )
    df = df[(df['monto'] >= monto_min) & (df['monto'] <= monto_max)]
    
    # =========================================================================
    # MÉTRICAS PRINCIPALES
    # =========================================================================
    st.header("📊 Métricas Principales")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_gastado = df['monto'].sum()
        st.metric(
            "Total Gastado", 
            f"${total_gastado:,.2f} MXN",
            delta=None
        )
    
    with col2:
        transacciones = len(df)
        st.metric("Transacciones", f"{transacciones:,}")
    
    with col3:
        promedio = df['monto'].mean()
        st.metric("Promedio por Transacción", f"${promedio:,.2f} MXN")
    
    with col4:
        dias_activos = df['fecha'].nunique()
        st.metric("Días con Actividad", dias_activos)
    
    st.markdown("---")
    
    # =========================================================================
    # GRÁFICOS INTERACTIVOS
    # =========================================================================
    
    # Gráfico 1: Tendencias
    st.plotly_chart(crear_grafico_tendencias(df), use_container_width=True)
    
    # Gráficos 2 y 3: Cuentas y Formas de Pago
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(crear_grafico_cuentas(df), use_container_width=True)
    
    with col2:
        st.plotly_chart(crear_grafico_formas_pago(df), use_container_width=True)
    
    # Gráfico 4: Top Proveedores
    st.plotly_chart(crear_grafico_proveedores(df), use_container_width=True)
    
    # =========================================================================
    # TABLA DE DATOS
    # =========================================================================
    st.header("📋 Detalle de Transacciones")
    
    # Opciones de visualización
    col1, col2 = st.columns(2)
    with col1:
        filas_mostrar = st.slider("Número de filas a mostrar:", 10, 100, 20)
    with col2:
        columna_orden = st.selectbox("Ordenar por:", 
                                   ['fecha', 'monto', 'proveedor', 'cuenta_principal'])
    
    # Mostrar tabla
    df_tabla = df.sort_values(columna_orden, ascending=False).head(filas_mostrar)
    st.dataframe(
        df_tabla[['fecha', 'monto', 'proveedor', 'descripcion', 'forma_pago', 'cuenta_principal']],
        use_container_width=True,
        height=400
    )
    
    # =========================================================================
    # SECCIÓN DE EXPORTACIÓN
    # =========================================================================
    st.sidebar.markdown("---")
    st.sidebar.header("📥 Exportar Datos")
    
    # Convertir a CSV
    csv = df.to_csv(index=False, encoding='utf-8')
    
    st.sidebar.download_button(
        label="📄 Descargar CSV Completo",
        data=csv,
        file_name=f"gastos_generales_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )
    
    # Información de actualización
    st.sidebar.markdown("---")
    st.sidebar.info(
        f"""
        **ℹ️ Información del Dataset**
        - Período: {df['fecha'].min().strftime('%d/%m/%Y')} - {df['fecha'].max().strftime('%d/%m/%Y')}
        - Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}
        - Los datos se actualizan automáticamente cada hora
        """
    )

if __name__ == "__main__":
    main()
