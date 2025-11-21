import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta
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
        st.error(f"❌ Error cargando datos: {e}")
        return pd.DataFrame()

def limpiar_datos(df):
    """Limpieza completa de los datos"""
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
            'NÓMINA': ['NOMINA', 'NÓMINA', 'PAGO NOMINA'],
            'IMPUESTOS': ['ISR', 'ISN', 'IMSS', 'IMPUESTO', 'SAT'],
            'ARRENDAMIENTOS': ['ARRENDAMIENTO', 'RENTA'],
            'MERCADERÍA': ['MAYORK', 'INTUICIÓN', 'CO TAILOR', 'REDKAP', 'MI PLAYERA', 'MERCADERIA', 'MERCANCIA'],
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
# FUNCIONES DE GRÁFICAS INTERACTIVAS
# =============================================================================
def crear_grafico_tendencias(df):
    """Gráfico de líneas con tendencias temporales"""
    df_diario = df.groupby(df['fecha'].dt.date)['monto'].sum().reset_index()
    df_diario['fecha'] = pd.to_datetime(df_diario['fecha'])
    
    fig = px.line(
        df_diario,
        x='fecha',
        y='monto',
        title='📈 Evolución Diaria de Gastos',
        labels={'monto': 'Monto ($ MXN)', 'fecha': 'Fecha'},
        line_shape='spline'
    )
    
    # Agregar media móvil de 7 días
    df_diario['media_movil'] = df_diario['monto'].rolling(window=7, center=True).mean()
    fig.add_trace(go.Scatter(
        x=df_diario['fecha'],
        y=df_diario['media_movil'],
        mode='lines',
        name='Media Móvil (7 días)',
        line=dict(dash='dash', color='red')
    ))
    
    fig.update_layout(height=400, hovermode='x unified')
    return fig

def crear_grafico_barras_cuentas(df):
    """Gráfico de barras por cuenta principal"""
    gastos_cuenta = df.groupby('cuenta_principal')['monto'].sum().sort_values(ascending=True)
    
    fig = px.bar(
        x=gastos_cuenta.values,
        y=gastos_cuenta.index,
        orientation='h',
        title='🏷️ Gastos por Cuenta Principal',
        labels={'x': 'Monto ($ MXN)', 'y': 'Cuenta'},
        color=gastos_cuenta.values,
        color_continuous_scale='viridis'
    )
    
    fig.update_layout(height=400, showlegend=False)
    return fig

def crear_grafico_torta_formas_pago(df):
    """Gráfico de torta de formas de pago"""
    formas_pago = df['forma_pago'].value_counts()
    
    fig = px.pie(
        values=formas_pago.values,
        names=formas_pago.index,
        title='💳 Distribución por Forma de Pago',
        hole=0.4
    )
    
    fig.update_layout(height=400)
    return fig

def crear_grafico_top_proveedores(df):
    """Gráfico de top proveedores"""
    top_proveedores = df.groupby('proveedor')['monto'].sum().sort_values(ascending=False).head(15)
    
    fig = px.bar(
        x=top_proveedores.values,
        y=top_proveedores.index,
        orientation='h',
        title='🏢 Top 15 Proveedores por Monto',
        labels={'x': 'Monto ($ MXN)', 'y': 'Proveedor'},
        color=top_proveedores.values,
        color_continuous_scale='plasma'
    )
    
    fig.update_layout(height=500)
    return fig

def crear_grafico_mensual(df):
    """Gráfico de gastos mensuales"""
    df_mensual = df.copy()
    df_mensual['mes'] = df_mensual['fecha'].dt.to_period('M').astype(str)
    gastos_mensual = df_mensual.groupby(['mes', 'cuenta_principal'])['monto'].sum().reset_index()
    
    fig = px.bar(
        gastos_mensual,
        x='mes',
        y='monto',
        color='cuenta_principal',
        title='📅 Gastos Mensuales por Cuenta Principal',
        labels={'monto': 'Monto ($ MXN)', 'mes': 'Mes', 'cuenta_principal': 'Cuenta'}
    )
    
    fig.update_layout(height=400, xaxis_tickangle=-45)
    return fig

def crear_grafico_pareto_subcuentas(df):
    """Análisis Pareto de subcuentas"""
    # Calcular Pareto
    subcuentas = df.groupby('subcuenta_limpia')['monto'].sum().sort_values(ascending=False)
    subcuentas = subcuentas[subcuentas > 0]  # Solo valores positivos
    
    total = subcuentas.sum()
    subcuentas_pct = (subcuentas / total) * 100
    subcuentas_cumsum = subcuentas_pct.cumsum()
    
    # Crear gráfico
    fig = go.Figure()
    
    # Barras
    fig.add_trace(go.Bar(
        x=subcuentas.index,
        y=subcuentas.values,
        name='Monto',
        marker_color='lightblue'
    ))
    
    # Línea de cumulative
    fig.add_trace(go.Scatter(
        x=subcuentas.index,
        y=subcuentas_cumsum.values,
        name='Acumulado %',
        yaxis='y2',
        line=dict(color='red', width=3)
    ))
    
    # Línea del 80%
    fig.add_hline(y=80, line_dash="dash", line_color="red")
    
    fig.update_layout(
        title='📊 Análisis Pareto - Subcuentas',
        xaxis_title='Subcuenta',
        yaxis_title='Monto ($ MXN)',
        yaxis2=dict(
            title='Porcentaje Acumulado (%)',
            overlaying='y',
            side='right',
            range=[0, 100]
        ),
        height=500,
        xaxis_tickangle=-45,
        showlegend=True
    )
    
    return fig

def crear_grafico_dispersion(df):
    """Gráfico de dispersión por fecha y monto"""
    fig = px.scatter(
        df,
        x='fecha',
        y='monto',
        color='cuenta_principal',
        size='monto',
        hover_data=['proveedor', 'descripcion'],
        title='🎯 Dispersión de Transacciones',
        labels={'monto': 'Monto ($ MXN)', 'fecha': 'Fecha', 'cuenta_principal': 'Cuenta Principal'}
    )
    
    fig.update_layout(height=500, xaxis=dict(rangeslider=dict(visible=True)))
    return fig

def crear_heatmap_semanal(df):
    """Heatmap de patrones semanales"""
    df_heatmap = df.copy()
    df_heatmap['dia_semana'] = df_heatmap['fecha'].dt.day_name()
    df_heatmap['semana'] = df_heatmap['fecha'].dt.isocalendar().week
    
    # Ordenar días de la semana
    dias_orden = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    df_heatmap['dia_semana'] = pd.Categorical(df_heatmap['dia_semana'], categories=dias_orden, ordered=True)
    
    # Preparar datos para heatmap
    heatmap_data = df_heatmap.groupby(['semana', 'dia_semana'])['monto'].sum().unstack(fill_value=0)
    
    fig = px.imshow(
        heatmap_data.T,  # Transponer para días en Y, semanas en X
        title='🔥 Patrón Semanal de Gastos',
        labels=dict(x="Semana", y="Día de la Semana", color="Monto"),
        aspect="auto",
        color_continuous_scale="Blues"
    )
    
    fig.update_layout(height=400)
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
        st.error("❌ No se pudieron cargar los datos.")
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
    
    st.sidebar.subheader("📅 Rango de Fechas")
    rango_fechas = st.sidebar.date_input(
        "Selecciona el período:",
        value=(fecha_min, fecha_max),
        min_value=fecha_min,
        max_value=fecha_max
    )
    
    if len(rango_fechas) == 2:
        df = df[(df['fecha'].dt.date >= rango_fechas[0]) & 
                (df['fecha'].dt.date <= rango_fechas[1])]
    
    # Filtro de cuentas
    st.sidebar.subheader("🏷️ Filtro por Cuenta")
    cuentas = ['TODAS'] + sorted(df['cuenta_principal'].unique().tolist())
    cuenta_seleccionada = st.sidebar.selectbox("Cuenta principal:", cuentas)
    
    if cuenta_seleccionada != 'TODAS':
        df = df[df['cuenta_principal'] == cuenta_seleccionada]
    
    # Filtro de formas de pago
    st.sidebar.subheader("💳 Filtro por Forma de Pago")
    formas_pago = ['TODAS'] + sorted(df['forma_pago'].unique().tolist())
    forma_pago_seleccionada = st.sidebar.selectbox("Forma de pago:", formas_pago)
    
    if forma_pago_seleccionada != 'TODAS':
        df = df[df['forma_pago'] == forma_pago_seleccionada]
    
    # Filtro de montos
    st.sidebar.subheader("💰 Filtro por Monto")
    monto_min, monto_max = st.sidebar.slider(
        "Rango de montos ($ MXN):",
        min_value=float(df['monto'].min()),
        max_value=float(df['monto'].max()),
        value=(float(df['monto'].min()), float(df['monto'].max())),
        step=1000.0
    )
    df = df[(df['monto'] >= monto_min) & (df['monto'] <= monto_max)]
    
    # =========================================================================
    # MÉTRICAS PRINCIPALES
    # =========================================================================
    st.header("📊 Métricas Principales")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_gastado = df['monto'].sum()
        st.metric("Total Gastado", f"${total_gastado:,.2f} MXN")
    
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
    
    # SECCIÓN 1: Tendencias Temporales
    st.header("📈 Análisis Temporal")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(crear_grafico_tendencias(df), use_container_width=True)
    
    with col2:
        st.plotly_chart(crear_grafico_mensual(df), use_container_width=True)
    
    # SECCIÓN 2: Distribución por Categorías
    st.header("🏷️ Análisis por Categorías")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(crear_grafico_barras_cuentas(df), use_container_width=True)
    
    with col2:
        st.plotly_chart(crear_grafico_torta_formas_pago(df), use_container_width=True)
    
    # SECCIÓN 3: Análisis Pareto
    st.header("📊 Análisis Pareto")
    st.plotly_chart(crear_grafico_pareto_subcuentas(df), use_container_width=True)
    
    # SECCIÓN 4: Top Proveedores
    st.header("🏢 Análisis de Proveedores")
    st.plotly_chart(crear_grafico_top_proveedores(df), use_container_width=True)
    
    # SECCIÓN 5: Análisis Detallado
    st.header("🎯 Análisis Detallado")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(crear_grafico_dispersion(df), use_container_width=True)
    
    with col2:
        st.plotly_chart(crear_heatmap_semanal(df), use_container_width=True)
    
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
    
    # Formatear para mejor visualización
    df_display = df_tabla.copy()
    df_display['fecha'] = df_display['fecha'].dt.strftime('%d/%m/%Y')
    df_display['monto'] = df_display['monto'].apply(lambda x: f"${x:,.2f}")
    
    st.dataframe(
        df_display[['fecha', 'monto', 'proveedor', 'descripcion', 'forma_pago', 'cuenta_principal']],
        use_container_width=True,
        height=400
    )
    
    # =========================================================================
    # EXPORTACIÓN Y INFO
    # =========================================================================
    st.sidebar.markdown("---")
    st.sidebar.header("📥 Exportar Datos")
    
    # Convertir a CSV
    csv = df.to_csv(index=False, encoding='utf-8')
    
    st.sidebar.download_button(
        label="📄 Descargar CSV",
        data=csv,
        file_name=f"gastos_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )
    
    # Información
    st.sidebar.markdown("---")
    st.sidebar.info(
        f"""
        **ℹ️ Información del Dataset**
        - **Período:** {df['fecha'].min().strftime('%d/%m/%Y')} - {df['fecha'].max().strftime('%d/%m/%Y')}
        - **Transacciones:** {len(df):,}
        - **Total:** ${df['monto'].sum():,.2f} MXN
        - **Última actualización:** {datetime.now().strftime('%d/%m/%Y %H:%M')}
        """
    )

if __name__ == "__main__":
    main()
