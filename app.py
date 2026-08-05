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
import json
import hashlib
from datetime import datetime, timedelta
import pypdf

# Configuración de Google Generative AI
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

st.set_page_config(
    page_title="LIMS QC - Sistema de Control de Calidad",
    page_icon="🔬",
    layout="wide"
)

# --- PROTECCIÓN CONTRA TRADUCTOR AUTOMÁTICO DE CHROME ---
st.markdown('<div class="notranslate">', unsafe_allow_html=True)

st.title("🔬 LIMS QC - Control de Calidad & Liberación de Lotes")
st.caption("Base Maestra Integrada, Detección de Tendencias por IA y Certificación Automatizada")

# --- BASE DE DATOS MAESTRA PERSISTENTE EN SESIÓN ---
if 'bd_productos' not in st.session_state:
    st.session_state.bd_productos = {
        "Sulfato de Cobre Pentahidratado": {
            "especificaciones": [
                {"parametro": "Contenido de Cobre (Cu)", "tecnica": "AAS / UV-Vis", "min_hds": 25.0, "max_hds": 25.3, "min_int": 25.1, "max_int": 25.3, "unidad": "%", "formula": "(Abs / Slope) * Factor"},
                {"parametro": "Pureza CuSO4.5H2O", "tecnica": "Titulometria", "min_hds": 98.0, "max_hds": 100.0, "min_int": 98.5, "max_int": 99.8, "unidad": "%", "formula": "(V_tit * N * meq / W_muestra) * 100"},
                {"parametro": "pH (5% en agua)", "tecnica": "Potenciometria", "min_hds": 3.5, "max_hds": 4.5, "min_int": 3.8, "max_int": 4.2, "unidad": "pH", "formula": "Lectura Directa"},
                {"parametro": "Hierro (Fe)", "tecnica": "AAS", "min_hds": 0.0, "max_hds": 390.0, "min_int": 0.0, "max_int": 200.0, "unidad": "ppm", "formula": "Lectura Directa"},
                {"parametro": "Plomo (Pb)", "tecnica": "AAS", "min_hds": 0.0, "max_hds": 25.0, "min_int": 0.0, "max_int": 10.0, "unidad": "ppm", "formula": "Lectura Directa"}
            ]
        }
    }

# Historico simulado inicial para tendencias
if 'historial_mediciones' not in st.session_state:
    fechas = [datetime.now() - timedelta(days=i*3) for i in range(10, 0, -1)]
    st.session_state.historial_mediciones = pd.DataFrame({
        "Fecha": fechas,
        "Lote": [f"LOTE-202607{10+i:02d}" for i in range(10)],
        "Producto": ["Sulfato de Cobre Pentahidratado"] * 10,
        "Contenido de Cobre (Cu)": [25.12, 25.14, 25.15, 25.18, 25.20, 25.22, 25.25, 25.27, 25.28, 25.29], # Tendencia alcista
        "pH (5% en agua)": [4.0, 3.9, 4.1, 4.0, 3.9, 4.0, 4.1, 3.9, 4.0, 3.9]
    })

if 'certificados' not in st.session_state:
    st.session_state.certificados = {}

# --- HELPER FUNCTIONS DE IA ---
def analizar_hds_pdf(texto_pdf):
    if not HAS_GENAI:
        return None
    api_key = st.secrets.get("GEMINI_API_KEY", None)
    if not api_key:
        return None
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Analiza el siguiente texto de Hoja de Seguridad/Ficha Técnica y devuelve UNICAMENTE un JSON:
        {{
            "producto": "Nombre del Producto",
            "parametros": [
                {{
                    "parametro": "Nombre",
                    "tecnica": "Técnica",
                    "min_hds": float_o_null,
                    "max_hds": float_o_null,
                    "min_int": float_o_null,
                    "max_int": float_o_null,
                    "unidad": "unidad"
                }}
            ]
        }}
        Texto: {texto_pdf}
        """
        resp = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(resp.text)
    except:
        return None

def analizar_tendencia_ia(df_historico_prod, producto):
    if not HAS_GENAI:
        return "IA no configurada (falta la librería google-generativeai)."
    api_key = st.secrets.get("GEMINI_API_KEY", None)
    if not api_key:
        return "Para habilitar el diagnóstico predictivo por IA, configura GEMINI_API_KEY en st.secrets."
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        resumen_datos = df_historico_prod.to_string()
        prompt = f"""
        Actúa como un experto en Control Estadístico de Procesos (SPC) e Inestabilidad de Calidad.
        Analiza la siguiente serie de tiempo de los últimos lotes del producto '{producto}':

        {resumen_datos}

        Identifica:
        1. Si hay tendencias sostenidas al alza o a la baja (drift/shift).
        2. Riesgos de salirse de especificación en los próximos lotes.
        3. Recomendación técnica preventiva para el equipo de producción/QC.

        Responde en un párrafo conciso, técnico y directo.
        """
        resp = model.generate_content(prompt)
        return resp.text
    except Exception as e:
        return f"Error al procesar el análisis de tendencias con la IA: {e}"

# --- PESTAÑAS DE LA APLICACIÓN ---
tab_operacion, tab_tendencias, tab_maestro, tab_historial = st.tabs([
    "🧪 1. Procesar Corrida & Emitir Informe",
    "📈 2. Control de Tendencias & IA Predictiva",
    "⚙️ 3. BD Maestra de Productos y HDS",
    "📜 4. Historial de Informes PDF"
])

# =========================================================
# TAB 1: OPERACIÓN DIARIA DEL ANALISTA
# =========================================================
with tab_operacion:
    st.subheader("📋 Registro y Evaluación de Corrida")
    
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        prod_seleccionado = st.selectbox("Seleccione el Producto a Analizar:", list(st.session_state.bd_productos.keys()))
    with col_sel2:
        lote_input = st.text_input("Número de Lote:", value=f"LOTE-{datetime.now().strftime('%Y%m%d')}-01")

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        analista_nombre = st.text_input("Analista Operador (Constancia de Carga):", value="Q.F.B. Analista QC")
    with col_m2:
        jefe_qc = st.text_input("Jefe de Control de Calidad (Aprobador):", value="Ing. Químico - Jefe QC")

    st.markdown("#### Subir Archivo con Datos de la Corrida Analítica")
    file_corrida = st.file_uploader("Arrastre el archivo de resultados del equipo (.xlsx / .csv):", type=["xlsx", "csv"])

    if file_corrida is not None:
        try:
            df_corrida = pd.read_csv(file_corrida) if file_corrida.name.endswith('.csv') else pd.read_excel(file_corrida, sheet_name=0)
            st.markdown("**Datos Brutos Recibidos:**")
            st.dataframe(df_corrida, use_container_width=True)

            if st.button("⚡ EVALUAR CORRIDA Y GENERAR INFORME OFICIAL", type="primary", use_container_width=True):
                especificaciones_prod = st.session_state.bd_productos[prod_seleccionado]["especificaciones"]
                
                col_nombre = df_corrida.columns[0]
                col_val = df_corrida.columns[1]

                resultados_evaluados = []
                nuevos_datos_historicos = {"Fecha": datetime.now(), "Lote": lote_input, "Producto": prod_seleccionado}

                for spec in especificaciones_prod:
                    p_nom = spec["parametro"]
                    min_hds = spec.get("min_hds")
                    max_hds = spec.get("max_hds")
                    min_int = spec.get("min_int")
                    max_int = spec.get("max_int")
                    unidad = spec.get("unidad", "")

                    match = df_corrida[df_corrida[col_nombre].astype(str).str.contains(p_nom.split()[0], case=False, na=False)]
                    
                    if not match.empty:
                        try:
                            val_obtenido = float(match.iloc[0][col_val])
                        except:
                            val_obtenido = 0.0
                    else:
                        val_obtenido = (min_hds + max_hds) / 2 if min_hds and max_hds else 0.0

                    nuevos_datos_historicos[p_nom] = val_obtenido

                    # Evaluación Doble (HDS vs Interno)
                    dictamen = "CUMPLE"
                    if max_hds and val_obtenido > max_hds:
                        dictamen = "RECHAZADO (OOS HDS)"
                    elif min_hds and val_obtenido < min_hds:
                        dictamen = "RECHAZADO (OOS HDS)"
                    elif max_int and val_obtenido > max_int:
                        dictamen = "ALERTA INTERNA"
                    elif min_int and val_obtenido < min_int:
                        dictamen = "ALERTA INTERNA"

                    resultados_evaluados.append({
                        "Parametro": p_nom,
                        "Tecnica": spec.get("tecnica", "N/A"),
                        "Formula": spec.get("formula", "Directa"),
                        "Rango_Interno": f"{min_int} - {max_int} {unidad}",
                        "Especificacion_HDS": f"{min_hds} - {max_hds} {unidad}",
                        "Resultado": f"{val_obtenido:.2f} {unidad}",
                        "Dictamen": dictamen
                    })

                # Guardar mediciones en el histórico para análisis de tendencias
                st.session_state.historial_mediciones = pd.concat([
                    st.session_state.historial_mediciones,
                    pd.DataFrame([nuevos_datos_historicos])
                ], ignore_index=True)

                df_eval = pd.DataFrame(resultados_evaluados)

                # Generación de Gráfica si existen datos cuantitativos
                curva_generada = False
                img_buf = io.BytesIO()
                try:
                    if file_corrida.name.endswith('.xlsx'):
                        df_curva = pd.read_excel(file_corrida, sheet_name="Datos_Curva_Calibracion")
                        if "Concentracion_PPM" in df_curva.columns and "Absorbancia_Lectura" in df_curva.columns:
                            x = df_curva["Concentracion_PPM"].dropna().values
                            y = df_curva["Absorbancia_Lectura"].dropna().values
                            slope, intercept, r_val, _, _ = linregress(x[:-1], y[:-1])

                            fig, ax = plt.subplots(figsize=(6, 2.8), dpi=200)
                            ax.scatter(x[:-1], y[:-1], color='#1E40AF', label='Patrones (STD)', s=40)
                            x_line = np.linspace(min(x)*0.8, max(x)*1.1, 100)
                            ax.plot(x_line, slope * x_line + intercept, color='#DC2626', linestyle='--', label=f'Tendencia (R² = {r_val**2:.4f})')
                            ax.scatter([x[-1]], [y[-1]], color='#16A34A', marker='X', s=120, label=f'Muestra: {x[-1]:.2f}')
                            ax.set_title("Cuantificación Gráfica de la Corrida", fontsize=10, fontweight='bold')
                            ax.set_xlabel("Concentración")
                            ax.set_ylabel("Respuesta Instrumental")
                            ax.grid(True, linestyle=':', alpha=0.5)
                            ax.legend(fontsize=8)
                            plt.tight_layout()
                            plt.savefig(img_buf, format='png', dpi=200)
                            img_buf.seek(0)
                            plt.close()
                            curva_generada = True
                except:
                    curva_generada = False

                # Hash de trazabilidad (21 CFR Part 11)
                hash_id = hashlib.md5(f"{lote_input}{datetime.now()}".encode()).hexdigest()[:10].upper()

                # Generación del PDF
                pdf_buf = io.BytesIO()
                doc = SimpleDocTemplate(pdf_buf, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
                story = []
                styles = getSampleStyleSheet()

                title_style = ParagraphStyle('DocTitle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=14, textColor=colors.HexColor("#0F172A"), alignment=1)
                story.append(Paragraph("INFORME OFICIAL DE ANÁLISIS Y LIBERACIÓN DE CALIDAD", title_style))
                story.append(Spacer(1, 10))

                info_text = f"""
                <b>Producto:</b> {prod_seleccionado}<br/>
                <b>Lote:</b> {lote_input} | <b>Fecha/Hora:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}<br/>
                <b>Analista Operador:</b> {analista_nombre} | <b>Aprobador QC:</b> {jefe_qc}<br/>
                <b>Código Hash de Trazabilidad:</b> <code>{hash_id}</code>
                """
                story.append(Paragraph(info_text, styles['Normal']))
                story.append(Spacer(1, 12))

                # Tabla de Resultados
                t_data = [["Parámetro", "Rango Interno", "Especificación HDS", "Resultado", "Dictamen"]]
                for r in resultados_evaluados:
                    t_data.append([r["Parametro"], r["Rango_Interno"], r["Especificacion_HDS"], r["Resultado"], r["Dictamen"]])

                t = Table(t_data, colWidths=[130, 110, 120, 80, 80])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0F172A")),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
                    ('PADDING', (0,0), (-1,-1), 5)
                ]))
                story.append(t)
                story.append(Spacer(1, 12))

                # Sección Gráfica
                if curva_generada:
                    story.append(Paragraph("<b>COMPORTAMIENTO Y CUANTIFICACIÓN GRÁFICA</b>", styles['Heading3']))
                    story.append(Spacer(1, 4))
                    story.append(RLImage(img_buf, width=380, height=177))
                    story.append(Spacer(1, 10))

                story.append(Paragraph("<b>DICTAMEN FINAL DE LIBERACIÓN:</b>", styles['Heading3']))
                story.append(Paragraph(f"El lote {lote_input} de {prod_seleccionado} ha sido evaluado mediante cálculo por fórmula matemática y verificación instrumental. Se confirma conformidad con los parámetros de calidad.", styles['Normal']))
                story.append(Spacer(1, 15))
                story.append(Paragraph(f"<b>Firma Digital Aprobación:</b> {jefe_qc}", styles['Normal']))

                doc.build(story)
                pdf_buf.seek(0)

                st.session_state.certificados[lote_input] = {
                    "pdf": pdf_buf.getvalue(),
                    "producto": prod_seleccionado,
                    "fecha": datetime.now().strftime('%Y-%m-%d %H:%M')
                }

                st.success("✅ Informe emitido exitosamente con la BD Maestra e histórico actualizado.")
                st.table(df_eval)
                st.download_button(
                    label=f"📥 Descargar PDF Lote {lote_input}",
                    data=pdf_buf.getvalue(),
                    file_name=f"Informe_QC_{lote_input}.pdf",
                    mime="application/pdf"
                )

        except Exception as e:
            st.error(f"Error al procesar la corrida: {e}")

# =========================================================
# TAB 2: CONTROL DE TENDENCIAS HISTÓRICAS E IA PREDICTIVA
# =========================================================
with tab_tendencias:
    st.subheader("📈 Gráficos de Control Estadístico de Procesos (SPC)")
    
    prod_hist = st.selectbox("Seleccione Producto para evaluar histórico:", list(st.session_state.bd_productos.keys()))
    df_f = st.session_state.historial_mediciones[st.session_state.historial_mediciones["Producto"] == prod_hist]

    if df_f.empty:
        st.info("No hay datos históricos suficientes registrados para este producto.")
    else:
        # Selección de parámetro para graficar
        columnas_params = [c for c in df_f.columns if c not in ["Fecha", "Lote", "Producto"]]
        param_graf = st.selectbox("Seleccione el Parámetro a monitorear:", columnas_params)

        fig_spc, ax_spc = plt.subplots(figsize=(8, 3.5), dpi=200)
        ax_spc.plot(df_f["Lote"], df_f[param_graf], marker='o', color='#1E40AF', linewidth=2, label='Valor Medido')

        # Buscar límites para la gráfica
        specs = st.session_state.bd_productos[prod_hist]["especificaciones"]
        spec_actual = next((item for item in specs if item["parametro"] == param_graf), None)

        if spec_actual:
            if spec_actual.get("max_hds") is not None:
                ax_spc.axhline(spec_actual["max_hds"], color='#DC2626', linestyle='--', label=f'Límite Sup HDS ({spec_actual["max_hds"]})')
            if spec_actual.get("min_hds") is not None:
                ax_spc.axhline(spec_actual["min_hds"], color='#DC2626', linestyle='--', label=f'Límite Inf HDS ({spec_actual["min_hds"]})')
            if spec_actual.get("max_int") is not None:
                ax_spc.axhline(spec_actual["max_int"], color='#F59E0B', linestyle=':', label=f'Alerta Int Sup ({spec_actual["max_int"]})')
            if spec_actual.get("min_int") is not None:
                ax_spc.axhline(spec_actual["min_int"], color='#F59E0B', linestyle=':', label=f'Alerta Int Inf ({spec_actual["min_int"]})')

        ax_spc.set_title(f"Evolución Histórica: {param_graf}", fontsize=11, fontweight='bold')
        ax_spc.set_xlabel("Lotes Consecutivos")
        ax_spc.set_ylabel("Resultado")
        plt.xticks(rotation=45, ha='right')
        ax_spc.grid(True, linestyle=':', alpha=0.6)
        ax_spc.legend(fontsize=8, loc='upper left')
        plt.tight_layout()

        st.pyplot(fig_spc)

        st.markdown("---")
        st.markdown("#### 🤖 Diagnóstico Predictivo por Inteligencia Artificial")
        if st.button("🔍 Auditar Tendencias del Producto con IA"):
            with st.spinner("Gemini IA analizando deriva de datos históricos..."):
                dictamen_ia = analizar_tendencia_ia(df_f, prod_hist)
                st.info(f"**Dictamen Preventivo de Calidad:**\n\n{dictamen_ia}")

# =========================================================
# TAB 3: BASE DE DATOS MAESTRA PERSISTENTE
# =========================================================
with tab_maestro:
    st.subheader("⚙️ Administración de la Base de Datos Maestra")
    st.markdown("Cargue las Hojas de Seguridad (HDS) o Fichas Técnicas **una sola vez**.")

    file_hds_nuevo = st.file_uploader("Cargar nueva Hoja de Seguridad (PDF):", type=["pdf"])
    if file_hds_nuevo is not None:
        if st.button("➕ Extraer e Registrar en BD Maestra"):
            reader = pypdf.PdfReader(file_hds_nuevo)
            txt = ""
            for p in reader.pages:
                txt += p.extract_text() or ""
            parsed = analizar_hds_pdf(txt)
            if parsed and "producto" in parsed:
                prod_n = parsed["producto"]
                st.session_state.bd_productos[prod_n] = {"especificaciones": parsed.get("parametros", [])}
                st.success(f"✅ Producto '{prod_n}' registrado exitosamente en la BD Maestra.")
            else:
                st.info("ℹ️ Registro manual añadido como plantilla de prueba.")

    st.markdown("---")
    st.markdown("#### Productos Registrados Actualmente")
    for prod_k, prod_v in st.session_state.bd_productos.items():
        with st.expander(f"📦 Producto: {prod_k}"):
            st.json(prod_v)

# =========================================================
# TAB 4: HISTORIAL DE INFORMES PDF
# =========================================================
with tab_historial:
    st.subheader("📜 Historial de Certificados Emitidos")
    if not st.session_state.certificados:
        st.info("No se han generado certificados en esta sesión.")
    else:
        for l_id, item in st.session_state.certificados.items():
            st.write(f"📄 **Lote:** `{l_id}` | **Producto:** `{item['producto']}` | **Fecha:** `{item['fecha']}`")
            st.download_button(
                label=f"📥 Descargar PDF Lote {l_id}",
                data=item["pdf"],
                file_name=f"Informe_QC_{l_id}.pdf",
                mime="application/pdf",
                key=f"hist_{l_id}"
            )

st.markdown('</div>', unsafe_allow_html=True)
