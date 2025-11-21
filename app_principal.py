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
        st.error(f"Error cargando datos: {e}")
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
# FUNCIONES DE GRÁFICAS INTERACTIVAS CON IDs ÚNICOS
# =============================================================================
def crear_grafico_tendencias(df):
    """Gráfico de líneas con tendencias temporales"""
    df_diario = df.groupby(df['fecha'].dt.date)['monto'].sum().reset_index()
    df_diario['fecha'] = pd.to_datetime(df_diario['fecha'])
    
    fig = px.line(
        df_diario,
        x='fecha',
        y='monto',
        title='Evolucion Diaria de Gastos',
        labels={'monto': 'Monto ($ MXN)', 'fecha': 'Fecha'},
        line_shape='spline'
    )
    
    # Agregar media móvil de 7 días
    df_diario['media_movil'] = df_diario['monto'].rolling(window=7, center=True).mean()
    fig.add_trace(go.Scatter(
        x=df_diario['fecha'],
        y=df_diario['media_movil'],
        mode='lines',
        name='Media Movil (7 dias)',
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
        title='Gastos por Cuenta Principal',
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
        title='Distribucion por Forma de Pago',
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
        title='Top 15 Proveedores por Monto',
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
        title='Gastos Mensuales por Cuenta Principal',
        labels={'monto': 'Monto ($ MXN)', 'mes': 'Mes', 'cuenta_principal': 'Cuenta'}
    )
    
    fig.update_layout(height=400, xaxis_tickangle=-45)
    return fig

def crear_grafico_pareto_subcuentas(df):
    """Análisis Pareto de subcuentas con indicación del punto 80%"""
    # Calcular Pareto
    subcuentas = df.groupby('subcuenta_limpia')['monto'].sum().sort_values(ascending=False)
    subcuentas = subcuentas[subcuentas > 0]  # Solo valores positivos
    
    total = subcuentas.sum()
    subcuentas_pct = (subcuentas / total) * 100
    subcuentas_cumsum = subcuentas_pct.cumsum()
    
    # Encontrar el punto exacto del 80%
    punto_80 = None
    subcuenta_80 = None
    for i, (subcuenta, cum_pct) in enumerate(zip(subcuentas.index, subcuentas_cumsum.values)):
        if cum_pct >= 80 and punto_80 is None:
            punto_80 = i
            subcuenta_80 = subcuenta
            break
    
    # Crear gráfico
    fig = go.Figure()
    
    # Barras de valores individuales
    fig.add_trace(go.Bar(
        x=subcuentas.index,
        y=subcuentas.values,
        name='Monto por Subcuenta',
        marker_color='#1f77b4',
        hovertemplate='<b>%{x}</b><br>Monto: $%{y:,.2f} MXN<br>Porcentaje: %{customdata:.1f}%<extra></extra>',
        customdata=subcuentas_pct.values
    ))
    
    # Línea de cumulative
    fig.add_trace(go.Scatter(
        x=subcuentas.index,
        y=subcuentas_cumsum.values,
        name='Porcentaje Acumulado',
        yaxis='y2',
        line=dict(color='#ff7f0e', width=3),
        hovertemplate='<b>%{x}</b><br>Acumulado: %{y:.1f}%<extra></extra>'
    ))
    
    # Línea horizontal del 80%
    fig.add_hline(
        y=80, 
        line_dash="dash", 
        line_color="red",
        annotation_text="Linea 80%", 
        annotation_position="top left"
    )
    
    # Flecha y anotación del punto 80% si existe
    if punto_80 is not None and subcuenta_80 is not None:
        # Agregar punto en el 80%
        fig.add_trace(go.Scatter(
            x=[subcuenta_80],
            y=[80],
            mode='markers+text',
            marker=dict(size=12, color='red', symbol='circle'),
            text=["80%"],
            textposition="top center",
            name='Punto 80%',
            showlegend=False
        ))
        
        # Agregar línea vertical desde el punto 80%
        fig.add_shape(
            type="line",
            x0=subcuenta_80,
            y0=0,
            x1=subcuenta_80,
            y1=80,
            line=dict(color="red", width=2, dash="dot")
        )
    
    fig.update_layout(
        title='Analisis Pareto - Subcuentas<br><sub>Principio 80/20: Pocas subcuentas generan la mayor parte del gasto</sub>',
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
        showlegend=True,
        hovermode='x unified'
    )
    
    # Mostrar estadísticas del Pareto en un expander
    with st.expander("Estadisticas del Analisis Pareto", expanded=False):
        if punto_80 is not None:
            st.success(f"""
            **Insight del Principio 80/20:**
            
            - **{punto_80 + 1} subcuentas** ({(punto_80 + 1)/len(subcuentas)*100:.1f}% del total) generan **80% del gasto total**
            - **{len(subcuentas) - (punto_80 + 1)} subcuentas** ({(len(subcuentas) - (punto_80 + 1))/len(subcuentas)*100:.1f}% del total) generan solo **20% del gasto**
            
            **Recomendacion:** Enfoca tus esfuerzos de control en las **primeras {punto_80 + 1} subcuentas** para maximizar el impacto.
            """)
            
            # Mostrar las subcuentas críticas
            st.subheader("Subcuentas Criticas (80% del gasto):")
            subcuentas_criticas = subcuentas.head(punto_80 + 1)
            for i, (subcuenta, monto) in enumerate(subcuentas_criticas.items(), 1):
                porcentaje = (monto / total) * 100
                st.write(f"{i}. **{subcuenta}**: ${monto:,.2f} MXN ({porcentaje:.1f}%)")
        else:
            st.warning("No se pudo calcular el punto 80% - Los datos pueden estar muy distribuidos")
    
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
        title='Dispersion de Transacciones',
        labels={'monto': 'Monto ($ MXN)', 'fecha': 'Fecha', 'cuenta_principal': 'Cuenta Principal'}
    )
    
    fig.update_layout(height=500, xaxis=dict(rangeslider=dict(visible=True)))
    return fig

def crear_grafico_tendencias_cuentas(df):
    """Crea gráfico de líneas para tendencias de cuentas principales"""
    df_tendencias = df.groupby([df['fecha'].dt.date, 'cuenta_principal'])['monto'].sum().reset_index()
    df_tendencias['fecha'] = pd.to_datetime(df_tendencias['fecha'])
    
    fig = px.line(
        df_tendencias,
        x='fecha',
        y='monto',
        color='cuenta_principal',
        title='Tendencias por Cuenta Principal - Lineas Temporales',
        labels={'monto': 'Monto Diario ($ MXN)', 'fecha': 'Fecha', 'cuenta_principal': 'Cuenta Principal'},
        hover_data={'monto': ':.2f'}
    )
    
    fig.update_layout(
        height=480,
        template='plotly_white',
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.7,  # Mover la leyenda más abajo
            xanchor="center",
            x=0.5
        ),
        margin=dict(t=60, b=80, l=60, r=60),  # Ajustar márgenes
        title_x=0,  # Centrar el título
        title_y=0.95  # Mover el título más arriba
    )
    return fig

def crear_grafico_area_apilada(df):
    """Crea gráfico de área apilada para ver contribución"""
    df_tendencias = df.groupby([df['fecha'].dt.date, 'cuenta_principal'])['monto'].sum().reset_index()
    df_tendencias['fecha'] = pd.to_datetime(df_tendencias['fecha'])
    
    fig = px.area(
        df_tendencias,
        x='fecha',
        y='monto',
        color='cuenta_principal',
        title='Composicion Diaria de Gastos - Area Apilada',
        labels={'monto': 'Monto Acumulado ($ MXN)', 'fecha': 'Fecha', 'cuenta_principal': 'Cuenta Principal'}
    )
    
    fig.update_layout(
        height=400,
        template='plotly_white',
        hovermode='x unified'
    )
    return fig

def crear_heatmap_semanal_avanzado(df):
    """Crea heatmap de patrones semanales (versión avanzada)"""
    df_heatmap = df.copy()
    df_heatmap['dia_semana'] = df_heatmap['fecha'].dt.day_name()
    df_heatmap['semana'] = df_heatmap['fecha'].dt.isocalendar().week
    
    # Mapear días de la semana en orden
    dias_orden = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    df_heatmap['dia_semana'] = pd.Categorical(df_heatmap['dia_semana'], categories=dias_orden, ordered=True)
    
    # Agrupar por semana y día
    heatmap_data = df_heatmap.groupby(['semana', 'dia_semana'])['monto'].sum().unstack(fill_value=0)
    
    fig = px.imshow(
        heatmap_data.T,
        title='Patron Semanal de Gastos',
        labels=dict(x="Semana", y="Dia de la Semana", color="Monto"),
        aspect="auto",
        color_continuous_scale="Blues"
    )
    
    fig.update_layout(height=400)
    return fig

def crear_grafico_crecimiento_mensual(df):
    """Crea gráfico de crecimiento mensual"""
    df_mensual = df.copy()
    df_mensual['mes'] = df_mensual['fecha'].dt.to_period('M').astype(str)
    df_mensual = df_mensual.groupby(['mes', 'cuenta_principal'])['monto'].sum().reset_index()
    df_mensual['mes'] = pd.to_datetime(df_mensual['mes'])
    
    # Calcular crecimiento
    df_mensual = df_mensual.sort_values(['cuenta_principal', 'mes'])
    df_mensual['crecimiento'] = df_mensual.groupby('cuenta_principal')['monto'].pct_change() * 100
    
    fig = px.line(
        df_mensual.dropna(),
        x='mes',
        y='crecimiento',
        color='cuenta_principal',
        title='Crecimiento Porcentual Mensual',
        labels={'crecimiento': 'Crecimiento (%)', 'mes': 'Mes', 'cuenta_principal': 'Cuenta Principal'},
        markers=True
    )
    
    fig.add_hline(y=0, line_dash="dash", line_color="red", opacity=0.5)
    
    fig.update_layout(
        height=400,
        template='plotly_white',
        xaxis=dict(tickformat="%b %Y"),
        hovermode='x unified',
        yaxis=dict(ticksuffix="%")
    )
    return fig

def crear_treemap_subcuentas(df):
    """Crea gráfico de árbol de subcuentas"""
    fig = px.treemap(
        df,
        path=['cuenta_principal', 'subcuenta_limpia'],
        values='monto',
        title='Mapa de Arbol de Gastos por Cuenta y Subcuenta',
        color='monto',
        color_continuous_scale='Blues'
    )
    
    fig.update_layout(height=500)
    fig.update_traces(
        hovertemplate='<b>%{label}</b><br>Monto Total: $%{value:,.2f} MXN<extra></extra>'
    )
    return fig

# =============================================================================
# INTERFAZ PRINCIPAL
# =============================================================================
def main():
    # Header
    st.title("Dashboard de Gastos Generales")
    st.markdown("Analisis interactivo en tiempo real - Actualizado automaticamente")
    st.markdown("---")
    
    # Cargar datos
    with st.spinner('Cargando datos desde Google Sheets...'):
        df_raw = cargar_datos()
        
    if df_raw.empty:
        st.error("No se pudieron cargar los datos.")
        return
        
    df = limpiar_datos(df_raw)
    
    if df.empty:
        st.error("No hay datos validos despues de la limpieza.")
        return
    
    # =========================================================================
    # SIDEBAR - FILTROS
    # =========================================================================
    st.sidebar.title("Panel de Control")
    
    # Filtro de fechas
    fecha_min = df['fecha'].min().date()
    fecha_max = df['fecha'].max().date()
    
    st.sidebar.subheader("Rango de Fechas")
    rango_fechas = st.sidebar.date_input(
        "Selecciona el periodo:",
        value=(fecha_min, fecha_max),
        min_value=fecha_min,
        max_value=fecha_max
    )
    
    if len(rango_fechas) == 2:
        df = df[(df['fecha'].dt.date >= rango_fechas[0]) & 
                (df['fecha'].dt.date <= rango_fechas[1])]
    
    # Filtro de cuentas
    st.sidebar.subheader("Filtro por Cuenta")
    cuentas = ['TODAS'] + sorted(df['cuenta_principal'].unique().tolist())
    cuenta_seleccionada = st.sidebar.selectbox("Cuenta principal:", cuentas)
    
    if cuenta_seleccionada != 'TODAS':
        df = df[df['cuenta_principal'] == cuenta_seleccionada]
    
    # Filtro de formas de pago
    st.sidebar.subheader("Filtro por Forma de Pago")
    formas_pago = ['TODAS'] + sorted(df['forma_pago'].unique().tolist())
    forma_pago_seleccionada = st.sidebar.selectbox("Forma de pago:", formas_pago)
    
    if forma_pago_seleccionada != 'TODAS':
        df = df[df['forma_pago'] == forma_pago_seleccionada]
    
    # Filtro de montos
    st.sidebar.subheader("Filtro por Monto")
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
    st.header("Metricas Principales")

    # Usar 2 filas de 2 columnas cada una
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)
    
    with col1:
        total_gastado = df['monto'].sum()
        st.metric(
            label="Total Gastado", 
            value=f"${total_gastado:,.2f}",
            delta=None
        )
    
    with col2:
        transacciones = len(df)
        st.metric(
            label="Total Transacciones", 
            value=f"{transacciones:,}",
            delta=None
        )
    
    with col3:
        promedio = df['monto'].mean()
        st.metric(
            label="Promedio por Transaccion", 
            value=f"${promedio:,.2f}",
            delta=None
        )
    
    with col4:
        dias_activos = df['fecha'].nunique()
        st.metric(
            label="Dias con Actividad", 
            value=dias_activos,
            delta=None
        )
    
    st.markdown("---")
    
    # =========================================================================
    # GRÁFICOS INTERACTIVOS
    # =========================================================================
    
    # SECCIÓN 1: Tendencias Temporales
    st.header("Analisis Temporal")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(crear_grafico_tendencias(df), use_container_width=True, key="tendencias_1")
    
    with col2:
        st.plotly_chart(crear_grafico_mensual(df), use_container_width=True, key="mensual_1")
    
    # SECCIÓN 2: Distribución por Categorías
    st.header("Analisis por Categorias")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(crear_grafico_barras_cuentas(df), use_container_width=True, key="barras_1")
    
    with col2:
        st.plotly_chart(crear_grafico_torta_formas_pago(df), use_container_width=True, key="torta_1")
    
    # SECCIÓN 3: Análisis Pareto
    st.header("Analisis Pareto")
    st.plotly_chart(crear_grafico_pareto_subcuentas(df), use_container_width=True, key="pareto_1")
    
    # SECCIÓN 4: Top Proveedores
    st.header("Analisis de Proveedores")
    st.plotly_chart(crear_grafico_top_proveedores(df), use_container_width=True, key="proveedores_1")
    
    # SECCIÓN 5: Análisis Detallado
    st.header("Analisis Detallado")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(crear_grafico_dispersion(df), use_container_width=True, key="dispersion_1")
    
    with col2:
        st.plotly_chart(crear_heatmap_semanal_avanzado(df), use_container_width=True, key="heatmap_1")
    
    # =========================================================================
    # NUEVA SECCIÓN: ANÁLISIS AVANZADO
    # =========================================================================
    st.header("Analisis Avanzado")

    # Pestañas para organizar los gráficos avanzados
    tab1, tab2, tab3, tab4 = st.tabs([
        "Tendencias Detalladas", 
        "Patrones Semanales", 
        "Crecimiento", 
        "Estructura"
    ])
    
    with tab1:
        st.subheader("Tendencias por Cuenta Principal")
        col1, col2 = st.columns(2)
        
        with col1:
            st.plotly_chart(crear_grafico_tendencias_cuentas(df), use_container_width=True, key="tendencias_cuentas_1")
        
        with col2:
            st.plotly_chart(crear_grafico_area_apilada(df), use_container_width=True, key="area_apilada_1")
    
    with tab2:
        st.subheader("Patrones de Comportamiento Semanal")
        st.plotly_chart(crear_heatmap_semanal_avanzado(df), use_container_width=True, key="heatmap_avanzado_1")
        
        # Estadísticas semanales
        col1, col2, col3 = st.columns(3)
        with col1:
            df_temp = df.copy()
            df_temp['dia_semana'] = df_temp['fecha'].dt.day_name()
            dia_max = df_temp.groupby('dia_semana')['monto'].sum().idxmax()
            st.metric("Dia de Mayor Gasto", dia_max)
        
        with col2:
            promedio_diario = df_temp.groupby('dia_semana')['monto'].mean().mean()
            st.metric("Promedio Diario", f"${promedio_diario:,.2f}")
        
        with col3:
            dias_activos = df['fecha'].nunique()
            st.metric("Dias Analizados", dias_activos)
    
    with tab3:
        st.subheader("Analisis de Crecimiento Mensual")
        st.plotly_chart(crear_grafico_crecimiento_mensual(df), use_container_width=True, key="crecimiento_1")
        
        # Métricas de crecimiento
        df_mensual = df.copy()
        df_mensual['mes'] = df_mensual['fecha'].dt.to_period('M')
        crecimiento_data = df_mensual.groupby('mes')['monto'].sum().pct_change().dropna()
        
        if not crecimiento_data.empty:
            col1, col2 = st.columns(2)
            with col1:
                crecimiento_promedio = crecimiento_data.mean() * 100
                st.metric("Crecimiento Mensual Promedio", f"{crecimiento_promedio:+.1f}%")
            
            with col2:
                meses_crecimiento = (crecimiento_data > 0).sum()
                total_meses = len(crecimiento_data)
                st.metric("Meses con Crecimiento", f"{meses_crecimiento}/{total_meses}")
    
    with tab4:
        st.subheader("Estructura de Gastos")
        st.plotly_chart(crear_treemap_subcuentas(df), use_container_width=True, key="treemap_1")
        
        # Estadísticas de estructura
        col1, col2 = st.columns(2)
        with col1:
            cuentas_unicas = df['cuenta_principal'].nunique()
            st.metric("Cuentas Principales", cuentas_unicas)
        
        with col2:
            subcuentas_unicas = df['subcuenta_limpia'].nunique()
            st.metric("Subcuentas Unicas", subcuentas_unicas)
        
    # =========================================================================
    # TABLA DE DATOS
    # =========================================================================
    st.header("Detalle de Transacciones")
    
    # Opciones de visualización
    col1, col2 = st.columns(2)
    with col1:
        filas_mostrar = st.slider("Numero de filas a mostrar:", 10, 100, 20)
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
    st.sidebar.header("Exportar Datos")
    
    # Convertir a CSV
    csv = df.to_csv(index=False, encoding='utf-8')
    
    st.sidebar.download_button(
        label="Descargar CSV",
        data=csv,
        file_name=f"gastos_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )
    
    # Información
    st.sidebar.markdown("---")
    st.sidebar.info(
        f"""
        **Informacion del Dataset**
        - **Periodo:** {df['fecha'].min().strftime('%d/%m/%Y')} - {df['fecha'].max().strftime('%d/%m/%Y')}
        - **Transacciones:** {len(df):,}
        - **Total:** ${df['monto'].sum():,.2f} MXN
        - **Ultima actualizacion:** {datetime.now().strftime('%d/%m/%Y %H:%M')}
        """
    )

if __name__ == "__main__":
    main()
