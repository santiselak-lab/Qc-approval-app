import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import linregress
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io
from datetime import datetime

st.set_page_config(page_title="Sistema QC - Control y Aprobación", page_icon="🔬", layout="wide")

st.title("🔬 Sistema de Control de Calidad y Aprobación QC")
st.caption("Gestión Integrada de Especificaciones, Evaluación Analítica y Dictamen Oficial")

# Inicialización de bases de datos persistentes en sesión
if 'base_productos' not in st.session_state:
    # Base por defecto de ejemplo
    st.session_state.base_productos = pd.DataFrame([
        {"Codigo": "PROD-001", "Producto": "Paracetamol 500mg", "Parametro": "Valoración", "Especificacion_Min": 95.0, "Especificacion_Max": 105.0, "Unidad": "%"},
        {"Codigo": "PROD-002", "Producto": "Ibuprofeno 400mg", "Parametro": "Valoración", "Especificacion_Min": 98.0, "Especificacion_Max": 102.0, "Unidad": "%"},
        {"Codigo": "PROD-003", "Producto": "Muestra Biofertilizante", "Parametro": "pH", "Especificacion_Min": 6.5, "Especificacion_Max": 7.5, "Unidad": "pH"}
    ])

if 'pendientes' not in st.session_state:
    st.session_state.pendientes = {}

if 'aprobados' not in st.session_state:
    st.session_state.aprobados = {}

# Pestañas del Sistema
tab_db, tab_analista, tab_supervisor, tab_historial = st.tabs([
    "📊 1. Base de Especificaciones (Excel)",
    "📤 2. Cargar Corrida / Análisis", 
    "🧐 3. Panel de Revisión (Supervisor)", 
    "📂 4. Certificados Aprobados"
])

# ---------------------------------------------------------
# TAB 1: BASE DE DATOS Y CARGA DE EXCEL MAESTRO
# ---------------------------------------------------------
with tab_db:
    st.subheader("⚙️ Carga del Excel Maestro de Especificaciones")
    st.write("Sube el archivo Excel `.xlsx` o `.csv` que contiene el catálogo de productos con sus especificaciones de calidad.")

    archivo_maestro = st.file_uploader("Selecciona el Excel Maestro de Especificaciones:", type=["xlsx", "csv"], key="db_uploader")

    if archivo_maestro is not None:
        try:
            if archivo_maestro.name.endswith('.csv'):
                df_maestro = pd.read_csv(archivo_maestro)
            else:
                df_maestro = pd.read_excel(archivo_maestro)
            
            # Verificar columnas mínimas requeridas
            columnas_requeridas = {'Codigo', 'Producto', 'Especificacion_Min', 'Especificacion_Max'}
            if columnas_requeridas.issubset(df_maestro.columns):
                st.session_state.base_productos = df_maestro
                st.success("✅ ¡Base de datos de especificaciones actualizada exitosamente!")
            else:
                st.error(f"El Excel debe incluir al menos las siguientes columnas: {columnas_requeridas}")
        except Exception as e:
            st.error(f"Error al leer el archivo Excel: {str(e)}")

    st.markdown("---")
    st.subheader("📋 Catálogo Actual de Productos y Rangos Activos")
    st.dataframe(st.session_state.base_productos, use_container_width=True)

# ---------------------------------------------------------
# TAB 2: MÓDULO DEL ANALISTA
# ---------------------------------------------------------
with tab_analista:
    st.subheader("📤 Carga de Corrida Analítica")
    
    if st.session_state.base_productos.empty:
        st.warning("No hay productos cargados en la base de datos. Carga primero un Excel en la Tab 1.")
    else:
        # Selección interactiva de producto desde el maestro
        lista_productos = st.session_state.base_productos['Producto'].unique().tolist()
        prod_seleccionado = st.selectbox("Seleccione el Producto a Analizar:", lista_productos)
        
        # Filtrar especificaciones del producto seleccionado
        info_prod = st.session_state.base_productos[st.session_state.base_productos['Producto'] == prod_seleccionado].iloc[0]
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.info(f"**Código:** {info_prod.get('Codigo', 'N/A')}")
        with col_b:
            st.info(f"**Espec. Mínima:** {info_prod['Especificacion_Min']} {info_prod.get('Unidad', '')}")
        with col_c:
            st.info(f"**Espec. Máxima:** {info_prod['Especificacion_Max']} {info_prod.get('Unidad', '')}")

        lote_id = st.text_input("Número de Lote:", value="LOTE-2026-001")
        archivo_corrida = st.file_uploader("Selecciona el archivo Excel/CSV con los resultados de la corrida:", type=["csv", "xlsx"], key="corrida_uploader")

        if archivo_corrida is not None:
            try:
                if archivo_corrida.name.endswith('.csv'):
                    df_corrida = pd.read_csv(archivo_corrida)
                else:
                    df_corrida = pd.read_excel(archivo_corrida)

                st.success("Archivo de la corrida cargado.")
                st.dataframe(df_corrida.head(5), use_container_width=True)

                if st.button("🚀 GENERAR BORRADOR PARA REVISIÓN", type="primary"):
                    # Procesamiento analítico base
                    if 'Area_Pico_1' in df_corrida.columns and 'Area_Pico_2' in df_corrida.columns:
                        df_corrida['Area_Promedio'] = (df_corrida['Area_Pico_1'] + df_corrida['Area_Pico_2']) / 2
                    elif 'Area' in df_corrida.columns:
                        df_corrida['Area_Promedio'] = df_corrida['Area']
                    elif 'Resultado' in df_corrida.columns:
                        df_corrida['Concentracion'] = df_corrida['Resultado']
                        df_corrida['Area_Promedio'] = 0
                    else:
                        df_corrida['Area_Promedio'] = 50000

                    if 'Concentracion' not in df_corrida.columns:
                        # Curva de calibración tipo
                        conc_std = np.array([2.0, 5.0, 8.0, 12.0])
                        area_std = np.array([20500, 50800, 81200, 120900])
                        slope, intercept, r_val, _, _ = linregress(conc_std, area_std)
                        df_corrida['Concentracion'] = (df_corrida['Area_Promedio'] - intercept) / slope

                    # Evaluación contra el Maestro
                    spec_min = float(info_prod['Especificacion_Min'])
                    spec_max = float(info_prod['Especificacion_Max'])
                    
                    df_corrida['Cumple'] = df_corrida['Concentracion'].apply(
                        lambda val: "CUMPLE" if (spec_min <= val <= spec_max) else "OOS (DESVÍO)"
                    )

                    # Registrar en pendientes de revisión
                    st.session_state.pendientes[lote_id] = {
                        'lote': lote_id,
                        'producto': prod_seleccionado,
                        'codigo': info_prod.get('Codigo', 'N/A'),
                        'min': spec_min,
                        'max': spec_max,
                        'unidad': info_prod.get('Unidad', '%'),
                        'datos': df_corrida,
                        'fecha_carga': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    st.success(f"✅ Lote {lote_id} evaluado contra norma y enviado al Panel del Supervisor.")

            except Exception as e:
                st.error(f"Error procesando la corrida: {str(e)}")

# ---------------------------------------------------------
# TAB 3: PANEL DE REVISIÓN Y APROBACIÓN (SUPERVISOR)
# ---------------------------------------------------------
with tab_supervisor:
    st.subheader("🧐 Bandeja de Entrada para Dictamen Humano")
    
    if len(st.session_state.pendientes) == 0:
        st.info("No hay informes pendientes de revisión.")
    else:
        lote_sel = st.selectbox("Seleccione Lote a Revisar:", list(st.session_state.pendientes.keys()))
        item = st.session_state.pendientes[lote_sel]
        
        st.write(f"**Producto:** {item['producto']} ({item['codigo']})")
        st.write(f"**Especificación Oficial:** {item['min']} a {item['max']} {item['unidad']}")
        st.write(f"**Fecha Carga:** {item['fecha_carga']}")
        
        st.dataframe(item['datos'], use_container_width=True)
        
        st.markdown("---")
        st.subheader("Dictamen y Validación Técnica")
        observaciones = st.text_area("Observaciones del Supervisor:", value="Análisis verificado conforme a la especificación vigente en el maestro.")
        nombre_supervisor = st.text_input("Nombre y Firma del Responsable:", value="Q.F.B. Supervisor de Calidad")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ APROBAR Y EMITIR PDF OFICIAL", type="primary", use_container_width=True):
                # Generación de Informe PDF
                buffer = io.BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
                story = []
                styles = getSampleStyleSheet()

                story.append(Paragraph("<b>CERTIFICADO OFICIAL DE CONTROL DE CALIDAD</b>", styles['Heading1']))
                story.append(Paragraph(f"<b>Producto:</b> {item['producto']} | <b>Lote:</b> {item['lote']}", styles['Heading2']))
                story.append(Paragraph(f"<b>Especificación Norma:</b> {item['min']} - {item['max']} {item['unidad']}", styles['Normal']))
                story.append(Spacer(1, 10))

                tabla_datos = [["Muestra / ID", "Resultado", "Unidad", "Especificación", "Dictamen"]]
                
                for idx, r in item['datos'].iterrows():
                    s_id = str(r['Sample_ID']) if 'Sample_ID' in r else f"Muestra-{idx+1}"
                    val = r['Concentracion'] if 'Concentracion' in r else 0.0
                    dict_str = r.get('Cumple', 'EVALUADO')
                    tabla_datos.append([s_id, f"{val:.2f}", item['unidad'], f"{item['min']}-{item['max']}", dict_str])

                t = Table(tabla_datos, colWidths=[110, 100, 80, 120, 110])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A365D")),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                    ('PADDING', (0,0), (-1,-1), 6)
                ]))
                story.append(t)
                story.append(Spacer(1, 15))

                stamp = f"<b>VALIDACIÓN Y FIRMA DIGITAL</b><br/>"
                stamp += f"<b>Aprobado Por:</b> {nombre_supervisor}<br/>"
                stamp += f"<b>Fecha Autorización:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>"
                stamp += f"<b>Observaciones:</b> {observaciones}<br/>"
                stamp += f"<b>Estatus:</b> <font color='green'><b>APROBADO Y LIBERADO</b></font>"
                story.append(Paragraph(stamp, styles['Normal']))

                doc.build(story)
                buffer.seek(0)

                st.session_state.aprobados[lote_sel] = {
                    'lote': lote_sel,
                    'pdf_bytes': buffer.getvalue(),
                    'fecha_aprobacion': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'supervisor': nombre_supervisor
                }
                del st.session_state.pendientes[lote_sel]
                st.success(f"¡Lote {lote_sel} aprobado y certificado generado!")
                st.rerun()

        with col2:
            if st.button("❌ RECHAZAR REPORTE", use_container_width=True):
                del st.session_state.pendientes[lote_sel]
                st.warning(f"Lote {lote_sel} rechazado.")
                st.rerun()

# ---------------------------------------------------------
# TAB 4: CERTIFICADOS APROBADOS
# ---------------------------------------------------------
with tab_historial:
    st.subheader("📜 Certificados de Calidad Emitidos")
    if len(st.session_state.aprobados) == 0:
        st.info("No hay certificados emitidos aún.")
    else:
        for l_id, data in st.session_state.aprobados.items():
            with st.expander(f"📜 Certificado Autorizado - Lote: {l_id}"):
                st.write(f"**Aprobado por:** {data['supervisor']}")
                st.write(f"**Fecha:** {data['fecha_aprobacion']}")
                st.download_button(
                    label=f"📥 Descargar PDF Certificado Lote {l_id}",
                    data=data['pdf_bytes'],
                    file_name=f"Certificado_Oficial_{l_id}.pdf",
                    mime="application/pdf"
                )
