# debug_app.py
import streamlit as st
import pandas as pd
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
    page_title="Debug - Dashboard Gastos",
    page_icon="🔍",
    layout="wide"
)

# =============================================================================
# FUNCIONES DE CARGA (COPIADAS DE app_principal.py)
# =============================================================================
@st.cache_data(ttl=3600)
def cargar_datos():
    """Carga datos desde Google Sheets - MISMA FUNCIÓN QUE app_principal.py"""
    try:
        credentials = service_account.Credentials.from_service_account_info(
            dict(st.secrets.gcp_service_account),
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        
        gc = gspread.authorize(credentials)
        spreadsheet = gc.open_by_key(st.secrets.SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet("registro_gastos")
        datos = worksheet.get_all_records()
        df = pd.DataFrame(datos)
        
        return df
        
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

def limpiar_datos(df):
    """Limpieza completa de los datos - MISMA FUNCIÓN QUE app_principal.py"""
    df_clean = df.copy()
    
    # Normalizar nombres de columnas
    df_clean.columns = [col.lower().strip() for col in df_clean.columns]
    
    # Convertir fecha
    df_clean['fecha'] = pd.to_datetime(df_clean['fecha'], errors='coerce', dayfirst=True)
    
    # Convertir monto
    df_clean['monto'] = (
        df_clean['monto'].astype(str)
        .str.replace('$', '', regex=False)
        .str.replace(',', '', regex=False)
        .str.strip()
    )
    df_clean['monto'] = pd.to_numeric(df_clean['monto'], errors='coerce')
    
    # Limpiar textos
    columnas_texto = ['proveedor', 'descripcion', 'forma_pago', 'cuenta', 'subcuenta']
    for col in columnas_texto:
        if col in df_clean.columns:
            df_clean[col] = (
                df_clean[col].astype(str)
                .str.strip()
                .str.upper()
                .replace(['NAN', 'NONE', 'NULL', ''], 'NO ESPECIFICADO')
            )
    
    # Clasificar cuentas principales (MEJORADA)
    def clasificar_cuenta_principal(subcuenta):
        if not isinstance(subcuenta, str):
            return "SIN_CLASIFICAR"
        
        subcuenta_clean = subcuenta.replace("SUB_", "").strip()
        
        # Diccionario mejorado de clasificación
        categorias = {
            'NOMINA': ['NOMINA', 'NÓMINA', 'PAGO NOMINA'],
            'IMPUESTOS': ['ISR', 'ISN', 'IMSS', 'IMPUESTO', 'SAT'],
            'ARRENDAMIENTOS': ['ARRENDAMIENTO', 'RENTA'],
            'MERCADERIA': ['MAYORK', 'INTUICION', 'CO TAILOR', 'REDKAP', 'MI PLAYERA', 'MERCADERIA', 'MERCANCIA'],
            'MATERIA_PRIMA': ['TECALSER', 'COSTUMATIC', 'MATERIA'],
            'SERVICIOS': ['SERVICIO', 'TERCEROS', 'CONTABILIDAD', 'CONSULTOR'],
            'GASTOS_OPERATIVOS': ['GASOLINA', 'VIAJES', 'OFICINA', 'SEGURO', 'VEHICULO', 'SOFTWARE'],
            'FINANCIEROS': ['INTERES', 'COMISION', 'BANCARIO']
        }
        
        for categoria, palabras in categorias.items():
            if any(palabra in subcuenta_clean for palabra in palabras):
                return categoria
        
        return "OTROS"
    
    df_clean['cuenta_principal'] = df_clean['subcuenta'].apply(clasificar_cuenta_principal)
    df_clean['subcuenta_limpia'] = df_clean['subcuenta'].str.replace('SUB_', '', regex=False)
    
    # Eliminar filas sin fecha o monto
    df_clean = df_clean.dropna(subset=['fecha', 'monto'])
    
    return df_clean

# =============================================================================
# FUNCIONES DE DEBUG MEJORADAS
# =============================================================================
def analizar_diferencia_montos(df):
    """Analiza la diferencia de $72,959.43"""
    
    st.header("🔍 Análisis de Diferencia: $72,959.43")
    
    # Total actual del dashboard
    total_dashboard = df['monto'].sum()
    total_excel = 43471190.18
    diferencia = total_excel - total_dashboard
    
    st.error(f"""
    **Diferencia encontrada:** ${diferencia:,.2f}
    - Excel: ${total_excel:,.2f}
    - Dashboard: ${total_dashboard:,.2f}
    """)
    
    return diferencia

def identificar_filas_perdidas(df_original, df_limpio):
    """Identifica qué filas se perdieron en la limpieza"""
    
    st.header("📋 Análisis de Filas Perdidas")
    
    filas_perdidas = len(df_original) - len(df_limpio)
    
    if filas_perdidas > 0:
        st.warning(f"**Se perdieron {filas_perdidas} filas en la limpieza**")
        
        # Identificar por qué se perdieron
        df_original['monto_valido'] = pd.to_numeric(
            df_original['monto'].astype(str)
            .str.replace('$', '', regex=False)
            .str.replace(',', '', regex=False)
            .str.strip(), 
            errors='coerce'
        ).notna()
        
        df_original['fecha_valida'] = pd.to_datetime(
            df_original['fecha'], errors='coerce', dayfirst=True
        ).notna()
        
        # Filas problemáticas
        filas_monto_invalido = len(df_original[~df_original['monto_valido']])
        filas_fecha_invalida = len(df_original[~df_original['fecha_valida']])
        
        st.write(f"**Filas con monto inválido:** {filas_monto_invalido}")
        st.write(f"**Filas con fecha inválida:** {filas_fecha_invalida}")
        
        # Mostrar ejemplos de filas problemáticas
        if filas_monto_invalido > 0:
            with st.expander("🔧 Ver Montos Inválidos (primeros 10)"):
                problemas_monto = df_original[~df_original['monto_valido']].head(10)
                st.dataframe(problemas_monto[['fecha', 'monto', 'proveedor', 'descripcion']])
        
        if filas_fecha_invalida > 0:
            with st.expander("📅 Ver Fechas Inválidas (primeros 10)"):
                problemas_fecha = df_original[~df_original['fecha_valida']].head(10)
                st.dataframe(problemas_fecha[['fecha', 'monto', 'proveedor', 'descripcion']])
    
    else:
        st.success("✅ No se perdieron filas en la limpieza")

def buscar_transacciones_grandes(df):
    """Busca transacciones grandes que podrían explicar la diferencia"""
    
    st.header("💰 Transacciones que Podrían Explicar la Diferencia")
    
    diferencia_objetivo = 72959.43
    
    # Buscar transacciones individuales grandes
    transacciones_grandes = df[df['monto'] > diferencia_objetivo * 0.9].sort_values('monto', ascending=False)
    
    if not transacciones_grandes.empty:
        st.subheader(f"Transacciones mayores a ${diferencia_objetivo * 0.9:,.2f}")
        
        for _, transaccion in transacciones_grandes.iterrows():
            st.write(f"**${transaccion['monto']:,.2f}** - {transaccion['fecha'].strftime('%d/%m/%Y')} - {transaccion['proveedor']} - {transaccion['descripcion']}")
    
    # Buscar transacciones alrededor de la diferencia
    st.subheader("Transacciones cercanas a la diferencia")
    transacciones_cercanas = df[
        (df['monto'] > diferencia_objetivo * 0.8) & 
        (df['monto'] < diferencia_objetivo * 1.2)
    ].sort_values('monto', ascending=False)
    
    if not transacciones_cercanas.empty:
        for _, transaccion in transacciones_cercanas.iterrows():
            st.write(f"**${transaccion['monto']:,.2f}** - {transaccion['fecha'].strftime('%d/%m/%Y')} - {transaccion['proveedor']}")

def analizar_por_mes(df):
    """Análisis detallado por mes"""
    
    st.header("📅 Análisis por Mes")
    
    # Calcular totales mensuales
    df_mensual = df.copy()
    df_mensual['mes'] = df_mensual['fecha'].dt.to_period('M').astype(str)
    totales_mensual = df_mensual.groupby('mes')['monto'].sum()
    
    # Mostrar en columnas
    cols = st.columns(3)
    for i, (mes, total) in enumerate(totales_mensual.items()):
        with cols[i % 3]:
            st.metric(f"Mes {mes}", f"${total:,.2f}")

def analizar_proveedores_clave(df):
    """Análisis específico de proveedores"""
    
    st.header("🏢 Análisis por Proveedor")
    
    # Top proveedores por monto
    top_proveedores = df.groupby('proveedor')['monto'].sum().sort_values(ascending=False).head(10)
    
    st.subheader("Top 10 Proveedores por Monto")
    for i, (proveedor, monto) in enumerate(top_proveedores.items(), 1):
        st.write(f"{i}. **{proveedor}**: ${monto:,.2f}")

def exportar_datos_para_analisis(df_original, df_limpio):
    """Permite exportar datos para análisis externo"""
    
    st.header("📤 Exportar Datos para Análisis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Exportar datos originales
        csv_original = df_original.to_csv(index=False)
        st.download_button(
            label="📥 Descargar Datos Originales (CSV)",
            data=csv_original,
            file_name="datos_originales_debug.csv",
            mime="text/csv"
        )
    
    with col2:
        # Exportar datos limpios
        csv_limpio = df_limpio.to_csv(index=False)
        st.download_button(
            label="📥 Descargar Datos Limpios (CSV)",
            data=csv_limpio,
            file_name="datos_limpios_debug.csv",
            mime="text/csv"
        )

# =============================================================================
# INTERFAZ PRINCIPAL DEL DEBUG
# =============================================================================
def main():
    st.title("🔍 Debug - Dashboard de Gastos")
    st.markdown("Herramienta de diagnóstico para identificar diferencias en los datos")
    st.markdown("---")
    
    # Cargar datos
    with st.spinner('Cargando datos para análisis...'):
        df_raw = cargar_datos()
    
    if df_raw.empty:
        st.error("No se pudieron cargar los datos para el análisis")
        return
    
    # Limpiar datos
    df_clean = limpiar_datos(df_raw)
    
    if df_clean.empty:
        st.error("No hay datos válidos después de la limpieza")
        return
    
    # Mostrar resumen ejecutivo
    st.header("📊 Resumen Ejecutivo")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total = df_clean['monto'].sum()
        st.metric("Total Dashboard", f"${total:,.2f}")
    
    with col2:
        st.metric("Total Excel", "$43,471,190.18")
    
    with col3:
        diferencia = 43471190.18 - total
        st.metric("Diferencia", f"${diferencia:,.2f}")
    
    with col4:
        st.metric("Filas Procesadas", f"{len(df_clean):,}")
    
    st.markdown("---")
    
    # Ejecutar análisis en pestañas
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 Análisis Principal", 
        "📋 Filas Perdidas", 
        "💰 Transacciones", 
        "📊 Métricas"
    ])
    
    with tab1:
        analizar_diferencia_montos(df_clean)
        st.markdown("---")
        analizar_por_mes(df_clean)
    
    with tab2:
        identificar_filas_perdidas(df_raw, df_clean)
    
    with tab3:
        buscar_transacciones_grandes(df_clean)
        st.markdown("---")
        analizar_proveedores_clave(df_clean)
    
    with tab4:
        st.header("📈 Métricas Detalladas")
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Estadísticas Básicas")
            st.write(f"**Rango de fechas:** {df_clean['fecha'].min().strftime('%d/%m/%Y')} - {df_clean['fecha'].max().strftime('%d/%m/%Y')}")
            st.write(f"**Promedio por transacción:** ${df_clean['monto'].mean():,.2f}")
            st.write(f"**Mediana:** ${df_clean['monto'].median():,.2f}")
            st.write(f"**Monto máximo:** ${df_clean['monto'].max():,.2f}")
        
        with col2:
            st.subheader("Distribución")
            st.write(f"**Cuentas principales únicas:** {df_clean['cuenta_principal'].nunique()}")
            st.write(f"**Proveedores únicos:** {df_clean['proveedor'].nunique()}")
            st.write(f"**Formas de pago únicas:** {df_clean['forma_pago'].nunique()}")
    
    st.markdown("---")
    exportar_datos_para_analisis(df_raw, df_clean)
    
    # Información final
    st.markdown("---")
    st.info("""
    **Siguientes pasos recomendados:**
    1. Revisar las filas con montos o fechas inválidas
    2. Verificar el formato de los montos en Excel
    3. Comprobar que no haya filas filtradas en Excel
    4. Validar las conversiones de fecha/monto problemáticas
    """)

if __name__ == "__main__":
    main()
