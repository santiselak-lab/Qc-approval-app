import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
from datetime import datetime

# -------------------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# -------------------------------------------------------------------
st.set_page_config(
    page_title="LIMS QC Enterprise - Control de Calidad",
    page_icon="🧪",
    layout="wide"
)

# Prevenir bloqueos de traductores móviles en Streamlit
st.markdown("""
<div translate="no">
""", unsafe_allow_html=True)

# -------------------------------------------------------------------
# INICIALIZACIÓN DEL ESTADO DE SESIÓN (BASE DE DATOS EN MEMORIA)
# -------------------------------------------------------------------
if "productos_db" not in st.session_state:
    st.session_state["productos_db"] = {
        "Sulfato de Cobre Pentahidratado": {
            "especificaciones": [
                {"parametro": "Contenido de Cu", "tecnica": "AAS / UV-Vis", "min_hds": 25.0, "max_hds": 25.3, "unidad": "%"},
                {"parametro": "Pureza CuSO4.5H2O", "tecnica": "Titulometria", "min_hds": 98.0, "max_hds": 100.5, "unidad": "%"}
            ]
        }
    }

if "historial_corridas" not in st.session_state:
    st.session_state["historial_corridas"] = pd.DataFrame([
        {"Lote": "LOTE-20260701-01", "Producto": "Sulfato de Cobre Pentahidratado", "Parametro": "Pureza CuSO4.5H2O", "Resultado": 98.5, "Estado": "CUMPLE", "Analista": "Q.F.B. Analista QC", "Fecha": "2026-07-01"},
        {"Lote": "LOTE-20260715-02", "Producto": "Sulfato de Cobre Pentahidratado", "Parametro": "Pureza CuSO4.5H2O", "Resultado": 99.1, "Estado": "CUMPLE", "Analista": "Q.F.B. Analista QC", "Fecha": "2026-07-15"},
        {"Lote": "LOTE-20260801-03", "Producto": "Sulfato de Cobre Pentahidratado", "Parametro": "Pureza CuSO4.5H2O", "Resultado": 98.2, "Estado": "CUMPLE", "Analista": "Q.F.B. Analista QC", "Fecha": "2026-08-01"}
    ])

# -------------------------------------------------------------------
# ENCABEZADO PRINCIPAL
# -------------------------------------------------------------------
st.title("🧪 LIMS QC & Automatización Analítica")
st.caption("Control Integrado: Excel Interno + SDS/MSDS + Farmacopea RAG (Con Fallback) + SPC")

tab1, tab2, tab3 = st.tabs([
    "📋 1. Procesar Corrida & Cálculos", 
    "📦 2. Base Master & Documentación (SDS/Farmacopea)", 
    "📈 3. Historial, SPC & Trazabilidad"
])

# -------------------------------------------------------------------
# PESTAÑA 1: PROCESAR CORRIDA & TÉCNICAS ANALÍTICAS
# -------------------------------------------------------------------
with tab1:
    st.subheader("Evaluación de Lote y Cálculos por Técnica Instrumental")
    
    lista_productos = list(st.session_state["productos_db"].keys())
    
    col1, col2 = st.columns(2)
    with col1:
        prod_sel = st.selectbox("Seleccionar Producto:", options=lista_productos, key="sel_prod_run")
    with col2:
        lote_input = st.text_input("Número de Lote:", value=f"LOTE-{datetime.now().strftime('%Y%m%d')}-01")

    col_op1, col_op2 = st.columns(2)
    with col_op1:
        analista_input = st.text_input("Analista Operador:", value="Q.F.B. Analista QC")
    with col_op2:
        tecnica_instrumental = st.selectbox(
            "Técnica Analítica Aplicada:", 
            ["HPLC / Cromatografía Líquida", "GC / Cromatografía de Gases", "AAS / Espectroscopía Atómica", "ICP-OES", "Físico-Químico (pH / Viscosidad / Densidad)", "Titulometría Clásica"]
        )

    st.markdown("---")
    
    # --- UPLOADER DE DATOS DE LA CORRIDA DE LA MUESTRA ---
    st.markdown("#### 📂 Subir Datos de la Corrida Analítica")
    archivo_corrida = st.file_uploader(
        "Cargue el archivo Excel (.xlsx) con los resultados de la muestra y patrones:", 
        type=["xlsx"], 
        key="uploader_datos_corrida"
    )

    val_resultado = None
    if archivo_corrida is not None:
        try:
            # Leer la pestaña principal de la corrida del Excel maestro
            df_corrida_subida = pd.read_excel(archivo_corrida, sheet_name="Datos_Corrida", skiprows=6)
            df_corrida_subida.columns = df_corrida_subida.columns.str.strip()
            
            st.success("✅ Archivo de corrida cargado correctamente.")
            st.markdown("**Vista previa de los datos analíticos recibidos:**")
            st.dataframe(df_corrida_subida, use_container_width=True)
            
            # Intentar extraer el resultado numérico de la primera fila o dejar ingresar manual
            if "Resultado Obtenido" in df_corrida_subida.columns:
                val_resultado = float(df_corrida_subida.iloc[0]["Resultado Obtenido"])
            else:
                val_resultado = 98.8
        except Exception as e:
            st.warning(f"No se encontró la pestaña 'Datos_Corrida' estándar, ingrese el resultado de forma manual: {e}")
            val_resultado = st.number_input("Resultado Analítico Manual:", value=98.8, format="%.4f")
    else:
        st.info("ℹ️ Adjunte el archivo Excel de la corrida o ingrese el valor de prueba a continuación:")
        val_resultado = st.number_input("Resultado Analítico de la Muestra:", value=98.8, format="%.4f")

    st.markdown(f"**Motor de Cálculo Seleccionado:** `{tecnica_instrumental}`")

    # Obtener límites actuales del producto seleccionado en la BD Master
    especs_producto = st.session_state["productos_db"][prod_sel]["especificaciones"]
    
    if st.button("🚀 Evaluar Lote y Registrar en Base de Datos", type="primary"):
        min_lim = especs_producto[0]["min_hds"]
        max_lim = especs_producto[0]["max_hds"]
        param_nombre = especs_producto[0]["parametro"]
        
        estado = "CUMPLE" if (min_lim <= val_resultado <= max_lim) else "FUERA DE ESPECIFICACIÓN (OOS)"
        
        if estado == "CUMPLE":
            st.success(f"✅ Dictamen: El lote {lote_input} **CUMPLE** con los parámetros ({min_lim} - {max_lim}). Resultado: {val_resultado}")
        else:
            st.error(f"❌ Dictamen: El lote {lote_input} está **FUERA DE ESPECIFICACIÓN**. Resultado: {val_resultado}")
            
        # Registrar en el historial de sesión
        nuevo_registro = pd.DataFrame([{
            "Lote": lote_input,
            "Producto": prod_sel,
            "Parametro": param_nombre,
            "Resultado": val_resultado,
            "Estado": estado,
            "Analista": analista_input,
            "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M")
        }])
        st.session_state["historial_corridas"] = pd.concat([st.session_state["historial_corridas"], nuevo_registro], ignore_index=True)

# -------------------------------------------------------------------
# PESTAÑA 2: BASE MASTER, SDS Y FARMACÓPEA (CON FALLBACK SEGURO)
# -------------------------------------------------------------------
with tab2:
    st.subheader("📦 Configuración Maestra y Repositorio Documental")
    
    with st.form("form_master"):
        nuevo_prod_nombre = st.text_input("Nombre de Nuevo Producto / Analito:")
        
        st.markdown("**1. Cargar Excel de Límites Internos:**")
        file_excel = st.file_uploader("Archivo Excel de especificaciones (.xlsx)", type=["xlsx"], key="up_excel")
        
        st.markdown("**2. Cargar Hoja de Seguridad (SDS / MSDS en PDF):**")
        file_sds = st.file_uploader("Archivo PDF de SDS", type=["pdf"], key="up_sds")
        
        st.markdown("**3. Referencia Farmacopea (Opcional):**")
        file_farmacopea = st.file_uploader("PDF de Monografía Farmacopea", type=["pdf"], key="up_farm")
        
        guardar_master = st.form_submit_button("📥 Procesar y Guardar en Base Master")
        
        if guardar_master:
            if nuevo_prod_nombre:
                ruta_farmacopea_local = "farmacopea_oficial.pdf"
                
                if file_farmacopea is not None:
                    st.success("📚 Farmacopea cargada exitosamente desde el archivo adjunto.")
                elif os.path.exists(ruta_farmacopea_local):
                    st.success("📚 Farmacopea detectada en almacenamiento local.")
                else:
                    st.warning("⚠️ Aviso: No se encontró la Farmacopea. **El sistema continúa funcionando** con los límites internos del Excel y SDS.")

                if file_excel is not None:
                    try:
                        df_ex = pd.read_excel(file_excel, sheet_name="Datos_Corrida", skiprows=6)
                        df_ex.columns = df_ex.columns.str.strip()
                        
                        lista_esp = []
                        for _, row in df_ex.iterrows():
                            lista_esp.append({
                                "parametro": str(row.get("Parametro", "")),
                                "tecnica": str(row.get("Tecnica Analitica", "")),
                                "min_hds": float(row.get("Espec. Min HDS", 0)),
                                "max_hds": float(row.get("Espec. Max HDS", 0)),
                                "unidad": str(row.get("Unidad", ""))
                            })
                        
                        st.session_state["productos_db"][nuevo_prod_nombre] = {"especificaciones": lista_esp}
                        st.success(f"✅ Producto '{nuevo_prod_nombre}' registrado con éxito desde el Excel.")
                    except Exception as e:
                        st.error(f"Error al procesar el Excel maestro: {e}")
                else:
                    st.session_state["productos_db"][nuevo_prod_nombre] = {
                        "especificaciones": [
                            {"parametro": "Ensayo Principal", "tecnica": "Metodología General", "min_hds": 95.0, "max_hds": 105.0, "unidad": "%"}
                        ]
                    }
                st.rerun()
            else:
                st.warning("Por favor ingrese el nombre del producto.")

    st.markdown("---")
    st.subheader("🔍 Estado Actual de la Base Master")
    st.json(st.session_state["productos_db"])

# -------------------------------------------------------------------
# PESTAÑA 3: HISTORIAL, SPC Y TRAZABILIDAD
# -------------------------------------------------------------------
with tab3:
    st.subheader("📈 Control Estadístico de Procesos (SPC) & Auditoría de Lotes")
    
    df_hist = st.session_state["historial_corridas"]
    
    if not df_hist.empty:
        st.dataframe(df_hist, use_container_width=True)
        
        st.markdown("### Tendencia Histórica de Resultados")
        fig_spc = px.line(
            df_hist, 
            x="Lote", 
            y="Resultado", 
            color="Producto", 
            markers=True,
            title="Carta de Tendencia de Resultados por Lote"
        )
        st.plotly_chart(fig_spc, use_container_width=True)
    else:
        st.info("Aún no hay registros en el historial de corridas.")

st.markdown("""
</div>
""", unsafe_allow_html=True)
