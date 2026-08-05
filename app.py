import streamlit as st
import pandas as pd
import plotly.express as px

# -------------------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# -------------------------------------------------------------------
st.set_page_config(
    page_title="LIMS QC - Calidad & Liberación de Lotes",
    page_icon="🧪",
    layout="wide"
)

# -------------------------------------------------------------------
# INICIALIZACIÓN DEL ESTADO DE SESIÓN (PERSISTENCIA)
# -------------------------------------------------------------------
if "productos_db" not in st.session_state:
    # Carga inicial por defecto
    st.session_state["productos_db"] = {
        "Sulfato de Cobre Pentahidratado": {
            "especificaciones": [
                {"parametro": "Contenido de Cobre (Cu)", "tecnica": "AAS / UV-Vis", "min_hds": 25.0, "max_hds": 25.3, "unidad": "%"},
                {"parametro": "Pureza CuSO4.5H2O", "tecnica": "Titulometria", "min_hds": 98.0, "max_hds": 100.5, "unidad": "%"}
            ]
        }
    }

# -------------------------------------------------------------------
# ENCABEZADO PRINCIPAL
# -------------------------------------------------------------------
st.title("🧪 Calidad & Liberación de Lotes")
st.caption("Base Maestra Integrada, Detección de Tendencias y Certificación Automatizada")

tab1, tab2 = st.tabs(["📋 1. Procesar Corrida & Emitir Informe", "📦 2. Registro & Base de Datos Master"])

# -------------------------------------------------------------------
# PESTAÑA 1: PROCESAR CORRIDA
# -------------------------------------------------------------------
with tab1:
    st.subheader("📋 Registro y Evaluación de Corrida")
    
    # Obtener lista actualizada de productos dinámicamente
    lista_productos = list(st.session_state["productos_db"].keys())
    
    col_prod, col_lote = st.columns(2)
    with col_prod:
        producto_seleccionado = st.selectbox(
            "Seleccione el Producto a Analizar:",
            options=lista_productos,
            key="select_producto_analizar"
        )
    
    with col_lote:
        numero_lote = st.text_input("Número de Lote:", value="AAG-20260805-01")
        
    col_analista, col_jefe = st.columns(2)
    with col_analista:
        analista = st.text_input("Analista Operador:", value="Q.F.B. Analista QC")
    with col_jefe:
        jefe_qc = st.text_input("Jefe de Control de Calidad:", value="Ing. Químico - Jefe QC")

    st.markdown("---")
    st.subheader("Subir Archivo con Datos de la Corrida (Excel)")
    
    archivo_subido = st.file_uploader(
        "Cargue la hoja de cálculo (.xlsx) con los resultados analíticos:",
        type=["xlsx"]
    )
    
    if archivo_subido is not None:
        try:
            # Leer pestaña 'Datos_Corrida'
            df_corrida = pd.read_excel(archivo_subido, sheet_name="Datos_Corrida", skiprows=6)
            
            # Limpieza de columnas
            df_corrida.columns = df_corrida.columns.str.strip()
            
            st.success("✅ Archivo cargado correctamente.")
            st.markdown("### 📊 Resultados Analíticos Evaluados")
            st.dataframe(df_corrida, use_container_width=True)
            
            # Mostrar gráfico si existe histórico
            try:
                df_historico = pd.read_excel(archivo_subido, sheet_name="Historico_Lotes", skiprows=2)
                st.markdown("### 📈 Control Estadístico de Procesos (SPC)")
                fig = px.line(
                    df_historico, 
                    x="Lote", 
                    y="Pureza / Riqueza (%)", 
                    markers=True,
                    title="Tendencia de Pureza por Lote"
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                pass

        except Exception as e:
            st.error(f"Error al procesar la hoja 'Datos_Corrida': {e}")

    # Visualización de Hojas de Seguridad / Especificaciones del producto seleccionado
    if producto_seleccionado in st.session_state["productos_db"]:
        st.markdown("---")
        st.subheader(f"📄 Especificaciones de Calidad / HDS: {producto_seleccionado}")
        especs = st.session_state["productos_db"][producto_seleccionado].get("especificaciones", [])
        if especs:
            df_especs = pd.DataFrame(especs)
            
            # Renombrar columnas para visualización clara
            df_especs_view = df_especs.rename(columns={
                "parametro": "Parámetro",
                "tecnica": "Técnica Analítica",
                "min_hds": "Espec. Min HDS",
                "max_hds": "Espec. Max HDS",
                "unidad": "Unidad"
            })
            st.table(df_especs_view)
        else:
            st.info("No hay especificaciones registradas para este producto.")

# -------------------------------------------------------------------
# PESTAÑA 2: REGISTRO & BASE DE DATOS MASTER
# -------------------------------------------------------------------
with tab2:
    st.subheader("📦 Agregar Nuevo Producto / Actualizar Especificaciones (HDS)")
    
    with st.form("form_nuevo_producto"):
        nombre_nuevo_prod = st.text_input("Nombre del Producto / Analito (Ej: Ácido Acético Glacial):")
        
        st.markdown("**Cargar Especificaciones desde Excel:**")
        excel_espec_file = st.file_uploader("Subir Excel maestro del producto:", type=["xlsx"], key="file_espec_master")
        
        btn_guardar = st.form_submit_button("💾 Guardar / Actualizar en Base Master")
        
        if btn_guardar:
            if nombre_nuevo_prod and excel_espec_file is not None:
                try:
                    # Leer especificaciones del Excel
                    df_master = pd.read_excel(excel_espec_file, sheet_name="Datos_Corrida", skiprows=6)
                    df_master.columns = df_master.columns.str.strip()
                    
                    especificaciones_lista = []
                    for _, row in df_master.iterrows():
                        especificaciones_lista.append({
                            "parametro": str(row.get("Parametro", "")),
                            "tecnica": str(row.get("Tecnica Analitica", "")),
                            "min_hds": float(row.get("Espec. Min HDS", 0)),
                            "max_hds": float(row.get("Espec. Max HDS", 0)),
                            "unidad": str(row.get("Unidad", ""))
                        })
                    
                    # Actualizar estado global
                    st.session_state["productos_db"][nombre_nuevo_prod] = {
                        "especificaciones": especificaciones_lista
                    }
                    st.success(f"¡Producto '{nombre_nuevo_prod}' registrado con éxito!")
                    # Refrescar la aplicación para actualizar el selectbox
                    st.rerun()
                    
                except Exception as err:
                    st.error(f"Error al estructurar especificaciones desde el Excel: {err}")
            else:
                st.warning("Asegúrese de ingresar el nombre del producto y adjuntar el archivo Excel.")

    st.markdown("---")
    st.subheader("🔍 Productos Registrados Actualmente en el Sistema")
    st.json(st.session_state["productos_db"])
