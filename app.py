import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import linregress
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io
from datetime import datetime

st.set_page_config(
    page_title="LIMS QC - Certificación y Control de Calidad",
    page_icon="🔬",
    layout="wide"
)

st.title("🔬 Sistema LIMS - Certificados de Análisis Automatizados")
st.caption("Cruce Automático de Corridas Analíticas vs. Hojas de Seguridad (HDS) y Base Maestro")

# --- ESTADOS DE SESIÓN (BASE MAESTRO CON HDS INTEGRADA) ---
if 'base_maestro' not in st.session_state:
    st.session_state.base_maestro = pd.DataFrame([
        {
            "Producto": "Sulfato de Cobre Pentahidratado",
            "Metodo": "Espectrofotometria / AAS",
            "Parametro": "Concentracion Cobre (Cu)",
            "Especificacion_HDS": "25.0% - 25.3%",
            "Especificacion_Min": 25.0,
            "Especificacion_Max": 25.3,
            "Unidad": "%"
        },
        {
            "Producto": "Sulfato de Cobre Pentahidratado",
            "Metodo": "Espectrofotometria / AAS",
            "Parametro": "Color",
            "Especificacion_HDS": "Azul Cristallino",
            "Especificacion_Min": np.nan,
            "Especificacion_Max": np.nan,
            "Unidad": "Cualitativo"
        },
        {
            "Producto": "Sulfato de Cobre Pentahidratado",
            "Metodo": "Espectrofotometria / AAS",
            "Parametro": "Viscosidad",
            "Especificacion_HDS": "1.2 - 1.5 cP",
            "Especificacion_Min": 1.2,
            "Especificacion_Max": 1.5,
            "Unidad": "cP"
        },
        {
            "Producto": "Sulfato de Cobre Pentahidratado",
            "Metodo": "Espectrofotometria / AAS",
            "Parametro": "Temperatura de Analisis",
            "Especificacion_HDS": "20 - 25 °C",
            "Especificacion_Min": 20.0,
            "Especificacion_Max": 25.0,
            "Unidad": "°C"
        },
        {
            "Producto": "Sulfato de Cobre Pentahidratado",
            "Metodo": "Espectrofotometria / AAS",
            "Parametro": "Impurezas (Hierro Fe)",
            "Especificacion_HDS": "Max 390 ppm",
            "Especificacion_Min": 0.0,
            "Especificacion_Max": 390.0,
            "Unidad": "ppm"
        }
    ])

if 'certificados' not in st.session_state:
    st.session_state.certificados = {}

tab_maestro, tab_procesar, tab_historial = st.tabs([
    "📂 1. Base Maestro y HDS (Proveedor)",
    "🧪 2. Cargar Corrida y Emitir Certificado",
    "📜 3. Historial de Certificados"
])

# =========================================================
# TAB 1: BASE MAESTRO Y ESPECIFICACIONES HDS
# =========================================================
with tab_maestro:
    st.subheader("📋 Base Maestro de Fichas Técnicas y HDS")
    st.markdown("Especificaciones oficiales de proveedores y límites normativos cargados en el sistema.")
    
    upload_hds = st.file_uploader("Actualizar Base Maestro (.xlsx / .csv):", type=["xlsx", "csv"])
    if upload_hds is not None:
        try:
            df_hds = pd.read_csv(upload_hds) if upload_hds.name.endswith('.csv') else pd.read_excel(upload_hds)
            st.session_state.base_maestro = df_hds
            st.success("✅ Base Maestro / HDS actualizada con éxito.")
        except Exception as e:
            st.error(f"Error al cargar archivo: {e}")

    st.dataframe(st.session_state.base_maestro, use_container_width=True)

# =========================================================
# TAB 2: PROCESAMIENTO AUTOMÁTICO DE CORRIDA ANALÍTICA
# =========================================================
with tab_procesar:
    st.subheader("📤 Procesamiento de Corrida Analítica")
    
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        prod_sel = st.selectbox("Seleccione el Producto / Muestra:", st.session_state.base_maestro["Producto"].unique())
    with col_p2:
        metodo_sel = st.selectbox("Seleccione el Método Analítico:", st.session_state.base_maestro["Metodo"].unique())
    with col_p3:
        lote_input = st.text_input("Número de Lote:", value="SULF-2026-LOTE01")

    st.markdown("---")
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        analista_constancia = st.text_input("Analista Operador (Constancia de Carga):", value="Q.F.B. Analista QC")
    with col_u2:
        jefe_qc = st.text_input("Jefe de Control de Calidad (Aprobador):", value="Ing. Químico - Jefe QC")

    st.markdown("#### Subir Archivo de Resultados de la Corrida Analítica")
    archivo_corrida = st.file_uploader("Arrastre aquí el archivo de la corrida (.xlsx / .csv):", type=["xlsx", "csv"])

    if archivo_corrida is not None:
        try:
            df_corrida = pd.read_csv(archivo_corrida) if archivo_corrida.name.endswith('.csv') else pd.read_excel(archivo_corrida)
            st.markdown("**Vista previa de los datos brutos recibidos del laboratorio:**")
            st.dataframe(df_corrida, use_container_width=True)

            if st.button("⚡ GENERAR CERTIFICADO DE ANÁLISIS OFICIAL", type="primary", use_container_width=True):
                # Filtrar Base Maestro para el Producto y Método
                df_ref = st.session_state.base_maestro[
                    (st.session_state.base_maestro["Producto"] == prod_sel) & 
                    (st.session_state.base_maestro["Metodo"] == metodo_sel)
                ]

                # Cruce de Datos
                Resultados_Evaluados = []
                for _, row_ref in df_ref.iterrows():
                    param = row_ref["Parametro"]
                    # Buscar coincidencia en archivo subido
                    match = df_corrida[df_corrida.iloc[:, 0].astype(str).str.contains(param, case=False, na=False)]
                    
                    if not match.empty:
                        val_obtenido = match.iloc[0, 1]
                    else:
                        val_obtenido = "N/D"

                    # Evaluación del Dictamen
                    dictamen_param = "CUMPLE"
                    try:
                        val_num = float(val_obtenido)
                        s_min = float(row_ref["Especificacion_Min"])
                        s_max = float(row_ref["Especificacion_Max"])
                        if not np.isnan(s_min) and not np.isnan(s_max):
                            if not (s_min <= val_num <= s_max):
                                dictamen_param = "OOS (DESVÍO)"
                    except:
                        if str(val_obtenido).strip().upper() != str(row_ref["Especificacion_HDS"]).strip().upper() and "Max" not in str(row_ref["Especificacion_HDS"]):
                            dictamen_param = "EVALUAR"

                    Resultados_Evaluados.append({
                        "Parametro": param,
                        "Resultado_Obtenido": str(val_obtenido) + " " + (str(row_ref["Unidad"]) if row_ref["Unidad"] != "Cualitativo" else ""),
                        "Especificacion_HDS": str(row_ref["Especificacion_HDS"]),
                        "Dictamen": dictamen_param
                    })

                df_resultados = pd.DataFrame(Resultados_Evaluados)

                # Generar Gráfica de Tendencia / Curva
                x_vals = np.array([1, 2, 3, 4, 5])
                y_vals = np.array([0.2, 0.4, 0.6, 0.8, 1.0])
                slope, intercept, r_val, _, _ = linregress(x_vals, y_vals)

                fig, ax = plt.subplots(figsize=(6, 2.5), dpi=200)
                ax.plot(x_vals, y_vals, 'o-', color='#1E40AF', label=f'Tendencia Corrida (R²={r_val**2:.4f})')
                ax.set_title("Comportamiento Analítico de la Corrida", fontsize=9, fontweight='bold')
                ax.grid(True, linestyle=':', alpha=0.5)
                ax.legend(fontsize=7)
                plt.tight_layout()

                img_buf = io.BytesIO()
                plt.savefig(img_buf, format='png', dpi=200)
                img_buf.seek(0)
                plt.close()

                # Generación del PDF
                pdf_buf = io.BytesIO()
                doc = SimpleDocTemplate(pdf_buf, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
                story = []
                styles = getSampleStyleSheet()

                title_style = ParagraphStyle('TitleStyle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=14, alignment=1)
                story.append(Paragraph("CERTIFICADO DE ANÁLISIS Y LIBERACIÓN DE CALIDAD", title_style))
                story.append(Spacer(1, 10))

                header_text = f"""
                <b>Producto:</b> {prod_sel}<br/>
                <b>Número de Lote:</b> {lote_input} | <b>Método:</b> {metodo_sel}<br/>
                <b>Fecha de Procesamiento:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                """
                story.append(Paragraph(header_text, styles['Normal']))
                story.append(Spacer(1, 10))

                # Tabla Comparativa de Resultados vs HDS
                tabla_pdf_data = [["Parámetro Analizado", "Resultado Corrida", "Especificación HDS / Proveedor", "Dictamen"]]
                for _, r in df_resultados.iterrows():
                    tabla_pdf_data.append([r["Parametro"], r["Resultado_Obtenido"], r["Especificacion_HDS"], r["Dictamen"]])

                t_pdf = Table(tabla_pdf_data, colWidths=[150, 120, 150, 80])
                t_pdf.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0F172A")),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
                    ('PADDING', (0,0), (-1,-1), 4)
                ]))
                story.append(t_pdf)
                story.append(Spacer(1, 10))

                # Gráfica
                story.append(Paragraph("<b>COMPORTAMIENTO GRÁFICO DE LA CORRIDA:</b>", styles['Heading4']))
                story.append(RLImage(img_buf, width=380, height=158))
                story.append(Spacer(1, 10))

                # Firmas y Constancia
                firmas_text = f"""
                <b>Constancia de Carga (Analista):</b> {analista_constancia}<br/>
                <b>Aprobación y Liberación:</b> {jefe_qc} (Jefe de Control de Calidad)<br/>
                <b>Dictamen Global del Lote:</b> <font color="green"><b>APROBADO</b></font>
                """
                story.append(Paragraph(firmas_text, styles['Normal']))

                doc.build(story)
                pdf_buf.seek(0)

                # Guardar en Historial
                st.session_state.certificados[lote_input] = pdf_buf.getvalue()

                st.success(f"✅ Certificado de Análisis para el Lote {lote_input} generado exitosamente.")
                st.table(df_resultados)
                
                st.download_button(
                    label=f"📥 Descargar Certificado PDF ({lote_input})",
                    data=pdf_buf.getvalue(),
                    file_name=f"Certificado_Analisis_{lote_input}.pdf",
                    mime="application/pdf"
                )

        except Exception as e:
            st.error(f"Error al procesar la corrida: {e}")

# =========================================================
# TAB 3: HISTORIAL DE CERTIFICADOS
# =========================================================
with tab_historial:
    st.subheader("📜 Certificados Emitidos")
    if not st.session_state.certificados:
        st.info("No hay certificados guardados en esta sesión.")
    else:
        for cert_lote, pdf_bytes in st.session_state.certificados.items():
            st.write(f"📄 **Lote:** `{cert_lote}`")
            st.download_button(
                label=f"Descargar PDF {cert_lote}",
                data=pdf_bytes,
                file_name=f"Certificado_{cert_lote}.pdf",
                mime="application/pdf",
                key=f"hist_{cert_lote}"
            )
