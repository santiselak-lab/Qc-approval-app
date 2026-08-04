import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import linregress
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io
from datetime import datetime

st.set_page_config(
    page_title="LIMS AI - Informe con Curva Analítica",
    page_icon="🔬",
    layout="wide"
)

st.title("🔬 LIMS AI - Generación de Informes con Curva de Calibración")
st.caption("Cuantificación Gráfica, Regresión Lineal e Inserción Automática en Certificados PDF")

# --- ESTADOS DE SESIÓN ---
if 'base_maestro' not in st.session_state:
    st.session_state.base_maestro = pd.DataFrame([
        {
            "ID_Elemento": "CU-001",
            "Producto": "Sulfato de Cobre Pentahidratado",
            "Parametro": "Pureza CuSO4.5H2O",
            "Tecnica": "Titulometria",
            "Especificacion_Min": 98.0,
            "Especificacion_Max": 100.0,
            "Unidad": "%"
        },
        {
            "ID_Elemento": "CU-002",
            "Producto": "Sulfato de Cobre Pentahidratado",
            "Parametro": "Contenido de Cobre (Cu)",
            "Tecnica": "Espectrofotometria / AAS",
            "Especificacion_Min": 25.0,
            "Especificacion_Max": 25.3,
            "Unidad": "%"
        },
        {
            "ID_Elemento": "CU-005",
            "Producto": "Sulfato de Cobre Pentahidratado",
            "Parametro": "Plomo (Pb)",
            "Tecnica": "AAS",
            "Especificacion_Min": 0.0,
            "Especificacion_Max": 25.0,
            "Unidad": "ppm"
        },
        {
            "ID_Elemento": "CU-006",
            "Producto": "Sulfato de Cobre Pentahidratado",
            "Parametro": "Hierro (Fe)",
            "Tecnica": "AAS",
            "Especificacion_Min": 0.0,
            "Especificacion_Max": 390.0,
            "Unidad": "ppm"
        }
    ])

if 'aprobados' not in st.session_state:
    st.session_state.aprobados = {}

# --- PESTAÑAS ---
tab_curva, tab_historial = st.tabs([
    "📈 1. Cuantificación y Curva de Calibración",
    "📜 2. Certificados e Informes PDF"
])

# =========================================================
# TAB 1: CUANTIFICACIÓN Y GENERACIÓN DE INFORME
# =========================================================
with tab_curva:
    st.subheader("📊 Módulo de Calibración y Liberación Analítica")
    
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        param_cuant = st.selectbox("Parámetro a Analizar:", st.session_state.base_maestro['Parametro'].unique())
    with col_c2:
        lote_cuant = st.text_input("Número de Lote:", value=f"SULF-2026-01")
    with col_c3:
        analista_nombre = st.text_input("Analista Responsable:", value="Q.F.B. Analista QC")

    row_param = st.session_state.base_maestro[st.session_state.base_maestro['Parametro'] == param_cuant].iloc[0]

    st.markdown("---")
    st.markdown("#### 1. Datos del Trazado del Equipo (Patrones de Calibración)")

    default_patrones = pd.DataFrame({
        "Patrón": ["STD 1", "STD 2", "STD 3", "STD 4", "STD 5"],
        "Concentración (ppm)": [2.0, 5.0, 10.0, 15.0, 20.0],
        "Absorbancia": [0.085, 0.210, 0.425, 0.630, 0.845]
    })

    df_patrones = st.data_editor(default_patrones, num_rows="dynamic", use_container_width=True)

    st.markdown("#### 2. Lectura de la Muestra del Lote")
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        abs_muestra = st.number_input("Absorbancia / Respuesta Obtenida:", value=0.430, format="%.4f")
    with col_m2:
        factor_dilucion = st.number_input("Factor de Dilución:", value=1.0, min_value=0.1)
    with col_m3:
        sup_nombre = st.text_input("Supervisor Aprobador:", value="Q.F.B. Jefe de Control de Calidad")

    if st.button("🚀 PROCESAR Y GENERAR INFORME OFICIAL CON GRÁFICA", type="primary", use_container_width=True):
        # 1. Regresión Lineal
        x = df_patrones["Concentración (ppm)"].values
        y = df_patrones["Absorbancia"].values
        slope, intercept, r_value, p_value, std_err = linregress(x, y)
        r2 = r_value ** 2

        # 2. Cuantificación Muestra
        conc_muestra = ((abs_muestra - intercept) / slope) * factor_dilucion
        spec_min = float(row_param['Especificacion_Min'])
        spec_max = float(row_param['Especificacion_Max'])
        dictamen = "CUMPLE" if spec_min <= conc_muestra <= spec_max else "OOS (DESVÍO)"

        # 3. Generar Gráfica Matplotlib en Memoria
        fig, ax = plt.subplots(figsize=(6, 3.2), dpi=200)
        ax.scatter(x, y, color='#1E40AF', label='Patrones (STD)', s=40)
        
        x_line = np.linspace(min(x)*0.8, max(x)*1.1, 100)
        ax.plot(x_line, slope * x_line + intercept, color='#DC2626', linestyle='--', label=f'R² = {r2:.4f}')
        
        conc_sin_dil = (abs_muestra - intercept) / slope
        ax.scatter([conc_sin_dil], [abs_muestra], color='#16A34A', marker='X', s=120, label=f'Muestra: {conc_muestra:.2f} {row_param["Unidad"]}')

        ax.set_xlabel(f"Concentración ({row_param['Unidad']})", fontsize=8)
        ax.set_ylabel("Absorbancia / Respuesta", fontsize=8)
        ax.set_title(f"Curva de Calibración - {param_cuant}", fontsize=10, fontweight='bold')
        ax.grid(True, linestyle=':', alpha=0.5)
        ax.legend(fontsize=7)
        plt.tight_layout()

        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=200)
        img_buffer.seek(0)
        plt.close()

        # 4. Construcción del PDF con ReportLab
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        story = []
        styles = getSampleStyleSheet()

        # Encabezado
        story.append(Paragraph("<b>INFORME TÉCNICO DE LIBERACIÓN Y CUANTIFICACIÓN ANALÍTICA</b>", styles['Title']))
        story.append(Spacer(1, 10))

        info_header = f"""
        <b>Lote:</b> {lote_cuant} | <b>Producto:</b> {row_param['Producto']}<br/>
        <b>Parámetro:</b> {param_cuant} ({row_param['Tecnica']})<br/>
        <b>Analista:</b> {analista_nombre} | <b>Supervisor:</b> {sup_nombre}<br/>
        <b>Fecha de Emisión:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        story.append(Paragraph(info_header, styles['Normal']))
        story.append(Spacer(1, 12))

        # Tabla Resumen Analítico
        tabla_resumen = [
            ["Ecuación de Calibración", "Coeficiente R²", "Resultado Muestra", "Especificación", "Dictamen"],
            [f"Y = {slope:.4f}X + {intercept:.4f}", f"{r2:.5f}", f"{conc_muestra:.2f} {row_param['Unidad']}", f"{spec_min} - {spec_max} {row_param['Unidad']}", dictamen]
        ]
        t_res = Table(tabla_resumen, colWidths=[130, 80, 110, 110, 80])
        t_res.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0F172A")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
            ('PADDING', (0,0), (-1,-1), 5)
        ]))
        story.append(t_res)
        story.append(Spacer(1, 15))

        # Insertar Gráfica en el PDF
        story.append(Paragraph("<b>CUANTIFICACIÓN GRÁFICA (REGRESIÓN LINEAL)</b>", styles['Heading2']))
        story.append(Spacer(1, 5))
        story.append(RLImage(img_buffer, width=420, height=224))
        story.append(Spacer(1, 15))

        # Pie con Firma Digital
        firma_text = f"""
        <b>ESTATUS DE LIBERACIÓN:</b> <font color="{'green' if dictamen == 'CUMPLE' else 'red'}"><b>{dictamen}</b></font><br/>
        ____________________________________________<br/>
        <b>Firma de Conformidad:</b> {sup_nombre}
        """
        story.append(Paragraph(firma_text, styles['Normal']))

        doc.build(story)
        pdf_buffer.seek(0)

        # Guardar en Historial
        st.session_state.aprobados[lote_cuant] = {
            'lote': lote_cuant,
            'pdf_bytes': pdf_buffer.getvalue(),
            'fecha': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'supervisor': sup_nombre,
            'parametro': param_cuant,
            'resultado': f"{conc_muestra:.2f} {row_param['Unidad']}",
            'dictamen': dictamen
        }

        st.success(f"✅ Informe Oficial del Lote {lote_cuant} generado correctamente con la curva integrada.")
        
        # Muestra previa en pantalla
        st.image(img_buffer, caption=f"Curva de Calibración Oficial - {param_cuant}", use_column_width=False, width=500)
        
        st.download_button(
            label=f"📥 Descargar Informe PDF Oficial ({lote_cuant})",
            data=pdf_buffer.getvalue(),
            file_name=f"Informe_Analitico_{lote_cuant}.pdf",
            mime="application/pdf"
        )

# =========================================================
# TAB 2: CERTIFICADOS E HISTORIAL
# =========================================================
with tab_historial:
    st.subheader("📜 Historial de Informes Emitidos")
    if not st.session_state.aprobados:
        st.info("No hay informes guardados en esta sesión.")
    else:
        for l_id, data in st.session_state.aprobados.items():
            st.write(f"📄 **Lote:** `{l_id}` | **Parámetro:** `{data['parametro']}` | **Resultado:** `{data['resultado']}` | **Dictamen:** `{data['dictamen']}`")
            st.download_button(
                label=f"📥 Descargar PDF {l_id}",
                data=data['pdf_bytes'],
                file_name=f"Informe_Analitico_{l_id}.pdf",
                mime="application/pdf",
                key=f"btn_{l_id}"
            )
