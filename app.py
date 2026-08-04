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

st.set_page_config(page_title="Sistema de Gestión y Aprobación QC", page_icon="🔬", layout="wide")

st.title("🔬 Sistema de Control de Calidad y Aprobación")
st.caption("Módulo de Evaluación Analítica con Supervisión Humana")

# Estado global persistente en memoria para demostración/módulos
if 'pendientes' not in st.session_state:
    st.session_state.pendientes = {}

if 'aprobados' not in st.session_state:
    st.session_state.aprobados = {}

# Pestañas de la App
tab_analista, tab_supervisor, tab_historial = st.tabs([
    "📤 1. Cargar Corrida (Analista)", 
    "🧐 2. Panel de Revisión (Supervisor)", 
    "📂 3. Registros Aprobados"
])

# ---------------------------------------------------------
# TAB 1: MÓDULO DEL ANALISTA
# ---------------------------------------------------------
with tab_analista:
    st.subheader("Carga y Preparación de Borrador")
    lote_id = st.text_input("Número de Lote:", value="LOTE-2026-001")
    producto_nombre = st.text_input("Nombre del Producto / Activo:", value="Principio Activo A (10 mg/mL)")
    spec_min = st.number_input("Especificación Mínima (%):", value=95.0, step=0.1)
    spec_max = st.number_input("Especificación Máxima (%):", value=105.0, step=0.1)

    archivo_csv = st.file_uploader("Selecciona el archivo .CSV de la corrida analítica:", type=["csv"])

    if archivo_csv is not None:
        try:
            df = pd.read_csv(archivo_csv)
            st.success("Archivo de corrida cargado exitosamente.")
            st.dataframe(df.head(5), use_container_width=True)

            if st.button("🚀 GENERAR BORRADOR PARA REVISIÓN", type="primary"):
                # Procesamiento analítico
                conc_std = np.array([2.0, 5.0, 8.0, 12.0])
                area_std = np.array([20500, 50800, 81200, 120900])
                slope, intercept, r_val, _, _ = linregress(conc_std, area_std)
                r2 = r_val**2

                if 'Area_Pico_1' in df.columns and 'Area_Pico_2' in df.columns:
                    df['Area_Promedio'] = (df['Area_Pico_1'] + df['Area_Pico_2']) / 2
                elif 'Area' in df.columns:
                    df['Area_Promedio'] = df['Area']
                else:
                    df['Area_Promedio'] = 50000 # Valor por defecto de prueba

                df['Concentracion'] = (df['Area_Promedio'] - intercept) / slope

                # Guardar en registros pendientes
                st.session_state.pendientes[lote_id] = {
                    'lote': lote_id,
                    'producto': producto_nombre,
                    'min': spec_min,
                    'max': spec_max,
                    'r2': r2,
                    'datos': df,
                    'fecha_carga': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'estado': 'PENDIENTE_REVISION'
                }
                st.success(f"Borrador guardado para el lote {lote_id}. Ahora está disponible en el Panel de Revisión del Supervisor.")

        except Exception as e:
            st.error(f"Error procesando el archivo CSV: {str(e)}")

# ---------------------------------------------------------
# TAB 2: PANEL DE REVISIÓN Y APROBACIÓN (SUPERVISOR)
# ---------------------------------------------------------
with tab_supervisor:
    st.subheader("Bandeja de Entrada para Revisión Humana")
    
    if len(st.session_state.pendientes) == 0:
        st.info("No hay informes pendientes de revisión.")
    else:
        lotes_lista = list(st.session_state.pendientes.keys())
        lote_sel = st.selectbox("Seleccione Lote a Evaluar:", lotes_lista)
        
        item = st.session_state.pendientes[lote_sel]
        
        st.write(f"**Producto:** {item['producto']}")
        st.write(f"**Fecha Carga:** {item['fecha_carga']}")
        st.write(f"**R² de Calibración:** {item['r2']:.4f}")
        st.write(f"**Especificación:** {item['min']}% - {item['max']}%")
        
        st.dataframe(item['datos'][['Sample_ID', 'Area_Promedio', 'Concentracion']] if 'Sample_ID' in item['datos'].columns else item['datos'], use_container_width=True)
        
        st.markdown("---")
        st.subheader("Dictamen del Supervisor")
        observaciones = st.text_area("Observaciones o Comentarios Técnicos:", value="Verificado conforme a la norma vigente.")
        nombre_supervisor = st.text_input("Nombre / Firma del Revisor:", value="Q.F.B. Supervisor de Calidad")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ APROBAR Y AUTORIZAR INFORME", type="primary", use_container_width=True):
                # Generación de PDF Oficial
                buffer = io.BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
                story = []
                styles = getSampleStyleSheet()

                story.append(Paragraph("<b>CERTIFICADO DE ANÁLISIS DE CALIDAD</b>", styles['Heading1']))
                story.append(Paragraph(f"<b>Producto:</b> {item['producto']} | <b>Lote:</b> {item['lote']}", styles['Heading2']))
                story.append(Spacer(1, 10))

                tabla_datos = [["Muestra / ID", "Área Promedio", "Resultado (%)", "Especificación", "Estado"]]
                df_det = item['datos']
                
                for idx, r in df_det.iterrows():
                    c = r['Concentracion'] if 'Concentracion' in r else 100.0
                    s_id = str(r['Sample_ID']) if 'Sample_ID' in r else f"Muestra-{idx+1}"
                    cumple = item['min'] <= c <= item['max']
                    dict_str = "CUMPLE" if cumple else "OOS (DESVÍO)"
                    tabla_datos.append([s_id, f"{r['Area_Promedio']:.0f}", f"{c:.2f}%", f"{item['min']}-{item['max']}%", dict_str])

                t = Table(tabla_datos, colWidths=[110, 110, 100, 110, 90])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A365D")),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                    ('PADDING', (0,0), (-1,-1), 6)
                ]))
                story.append(t)
                story.append(Spacer(1, 15))

                stamp = f"<b>VALIDACIÓN HUMANA DE CALIDAD</b><br/>"
                stamp += f"<b>Aprobado Por:</b> {nombre_supervisor}<br/>"
                stamp += f"<b>Fecha de Autorización:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>"
                stamp += f"<b>Observaciones:</b> {observaciones}<br/>"
                stamp += f"<b>Estatus:</b> <font color='green'><b>DOCUMENTO OFICIAL APROBADO</b></font>"
                story.append(Paragraph(stamp, styles['Normal']))

                doc.build(story)
                buffer.seek(0)

                # Mover de pendientes a aprobados
                st.session_state.aprobados[lote_sel] = {
                    'lote': lote_sel,
                    'pdf_bytes': buffer.getvalue(),
                    'fecha_aprobacion': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'supervisor': nombre_supervisor
                }
                del st.session_state.pendientes[lote_sel]
                st.success(f"¡Lote {lote_sel} aprobado con éxito!")
                st.rerun()

        with col2:
            if st.button("❌ RECHAZAR REPORTE", use_container_width=True):
                del st.session_state.pendientes[lote_sel]
                st.warning(f"Lote {lote_sel} rechazado y removido de la lista.")
                st.rerun()

# ---------------------------------------------------------
# TAB 3: REGISTROS Y DESCARGA DE INFORMES APROBADOS
# ---------------------------------------------------------
with tab_historial:
    st.subheader("Certificados Autorizados")
    if len(st.session_state.aprobados) == 0:
        st.info("Aún no existen informes aprobados.")
    else:
        for l_id, data in st.session_state.aprobados.items():
            with st.expander(f"📜 Certificado Autorizado - Lote: {l_id}"):
                st.write(f"**Aprobado por:** {data['supervisor']}")
                st.write(f"**Fecha:** {data['fecha_aprobacion']}")
                st.download_button(
                    label=f"📥 Descargar PDF Oficial Lote {l_id}",
                    data=data['pdf_bytes'],
                    file_name=f"Certificado_Oficial_{l_id}.pdf",
                    mime="application/pdf"
                )
