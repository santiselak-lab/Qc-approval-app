import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import matplotlib.pyplot as plt
import os
import hashlib
import io
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# -------------------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# -------------------------------------------------------------------
st.set_page_config(
    page_title="LIMS QC Enterprise - Control de Calidad",
    page_icon="🧪",
    layout="wide"
)

st.markdown("""
<div translate="no">
""", unsafe_allow_html=True)

# -------------------------------------------------------------------
# INICIALIZACIÓN DEL ESTADO DE SESIÓN
# -------------------------------------------------------------------
if "productos_db" not in st.session_state:
    st.session_state["productos_db"] = {
        "Sulfato de Cobre Pentahidratado": {
            "especificaciones": [
                {"parametro": "Contenido de Cu", "tecnica": "AAS / Espectroscopía Atómica", "min_hds": 25.0, "max_hds": 25.3, "unidad": "%"},
                {"parametro": "Pureza CuSO4.5H2O", "tecnica": "Titulometria", "min_hds": 98.0, "max_hds": 100.5, "unidad": "%"}
            ]
        },
        "Ácido acético glacial": {
            "especificaciones": [
                {"parametro": "Pureza CH3COOH", "tecnica": "Titulometria", "min_hds": 99.0, "max_hds": 100.5, "unidad": "%"}
            ]
        }
    }

if "historial_corridas" not in st.session_state:
    st.session_state["historial_corridas"] = pd.DataFrame([
        {"Lote": "LOTE-20260701-01", "Producto": "Sulfato de Cobre Pentahidratado", "Parametro": "Pureza CuSO4.5H2O", "Resultado": 98.5, "Estado": "CUMPLE", "Analista": "Q.F.B. Analista QC", "JefeQC": "Ing. Químico - Jefe QC", "Fecha": "2026-07-01"},
        {"Lote": "LOTE-20260715-02", "Producto": "Sulfato de Cobre Pentahidratado", "Parametro": "Pureza CuSO4.5H2O", "Resultado": 99.1, "Estado": "CUMPLE", "Analista": "Q.F.B. Analista QC", "JefeQC": "Ing. Químico - Jefe QC", "Fecha": "2026-07-15"},
        {"Lote": "LOTE-20260801-03", "Producto": "Sulfato de Cobre Pentahidratado", "Parametro": "Pureza CuSO4.5H2O", "Resultado": 98.2, "Estado": "CUMPLE", "Analista": "Q.F.B. Analista QC", "JefeQC": "Ing. Químico - Jefe QC", "Fecha": "2026-08-01"},
        {"Lote": "LOTE-20260806-01", "Producto": "Ácido acético glacial", "Parametro": "Pureza CH3COOH", "Resultado": 99.7, "Estado": "CUMPLE", "Analista": "Q.F.B. Analista QC", "JefeQC": "Ing. Químico - Jefe QC", "Fecha": "2026-08-06"}
    ])

# -------------------------------------------------------------------
# FUNCIÓN PARA GENERAR GRÁFICA DE CURVA DE CALIBRACIÓN (MATPLOTLIB)
# -------------------------------------------------------------------
def generar_imagen_curva_calibracion(x_std, y_std, x_sample, y_sample, slope, intercept, r2, param_nombre):
    plt.figure(figsize=(6, 2.8))
    plt.scatter(x_std, y_std, color='#1b4f72', label='Standards (Calibración)', zorder=5)
    
    x_line = np.linspace(min(x_std)*0.9, max(x_std)*1.1, 100)
    y_line = slope * x_line + intercept
    plt.plot(x_line, y_line, color='#2e4053', linestyle='-', label=f'Regresión: y = {slope:.4f}x + {intercept:.4f}\n$R^2$ = {r2:.4f}')
    
    plt.scatter([x_sample], [y_sample], color='#c0392b', s=100, marker='*', label=f'Muestra (X={x_sample:.2f}, Y={y_sample:.2f})', zorder=6)
    plt.axvline(x=x_sample, color='#c0392b', linestyle='--', alpha=0.6)
    plt.axhline(y=y_sample, color='#c0392b', linestyle='--', alpha=0.6)
    
    plt.title(f"Curva de Calibración & Interpolación - {param_nombre}", fontsize=9, fontweight='bold', color='#1b4f72')
    plt.xlabel("Concentración", fontsize=8)
    plt.ylabel("Señal / Absorbancia", fontsize=8)
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend(fontsize=7, loc='upper left')
    plt.tight_layout()
    
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=200)
    img_buffer.seek(0)
    plt.close()
    return img_buffer

# -------------------------------------------------------------------
# FUNCIÓN PARA GENERAR CERTIFICADO PDF OFICIAL CON CURVA DE CALIBRACIÓN
# -------------------------------------------------------------------
def generar_pdf_certificado(lote, producto, parametro, resultado, min_lim, max_lim, unidad, estado, analista, jefe_qc, tecnica, reg_data, img_calib_bytes):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=14, textColor=colors.HexColor("#1b4f72"), alignment=1, spaceAfter=4)
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontSize=8.5, textColor=colors.HexColor("#566573"), alignment=1, spaceAfter=10)
    body_style = styles['Normal']
    
    story.append(Paragraph("<b>CERTIFICADO DE ANÁLISIS DE CALIDAD (CoA)</b>", title_style))
    story.append(Paragraph("Sistema LIMS QC Enterprise - Trazabilidad Analítica & Curva de Calibración", subtitle_style))
    story.append(Spacer(1, 4))
    
    data_meta = [
        [Paragraph("<b>Producto:</b>", body_style), Paragraph(producto, body_style), Paragraph("<b>N° de Lote:</b>", body_style), Paragraph(lote, body_style)],
        [Paragraph("<b>Técnica Analítica:</b>", body_style), Paragraph(tecnica, body_style), Paragraph("<b>Fecha de Emisión:</b>", body_style), Paragraph(datetime.now().strftime("%Y-%m-%d %H:%M"), body_style)],
        [Paragraph("<b>Analista Operador:</b>", body_style), Paragraph(analista, body_style), Paragraph("<b>Jefe de QC (Firma):</b>", body_style), Paragraph(jefe_qc, body_style)]
    ]
    t_meta = Table(data_meta, colWidths=[110, 160, 110, 160])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f2f4f4")),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#bdc3c7"))
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 8))
    
    story.append(Paragraph("<b>1. Evaluación Analítica vs Especificación Oficial</b>", styles['Heading3']))
    story.append(Spacer(1, 3))
    
    color_estado = colors.HexColor("#27ae60") if estado == "CUMPLE" else colors.HexColor("#c0392b")
    
    data_res = [
        ["Parámetro Evaluado", "Espec. Min", "Espec. Max", "Resultado", "Unidad", "Dictamen"],
        [parametro, f"{min_lim}", f"{max_lim}", f"{resultado:.4f}", unidad, estado]
    ]
    t_res = Table(data_res, colWidths=[140, 80, 80, 80, 50, 110])
    t_res.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2e4053")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#bdc3c7")),
        ('TEXTCOLOR', (5,1), (5,1), color_estado),
        ('FONTNAME', (5,1), (5,1), 'Helvetica-Bold')
    ]))
    story.append(t_res)
    story.append(Spacer(1, 8))
    
    story.append(Paragraph("<b>2. Modelo Matemático de Regresión & Interpolación de Muestra</b>", styles['Heading3']))
    story.append(Spacer(1, 3))
    
    data_reg = [
        ["Ecuación de Recta (y = mx + b)", "Pendiente (m)", "Intercepto (b)", "Coef. Correlación (R²)", "Señal Medida (Y)", "Concentración Interpolada (X)"],
        [f"y = {reg_data['m']:.4f}x + {reg_data['b']:.4f}", f"{reg_data['m']:.4f}", f"{reg_data['b']:.4f}", f"{reg_data['r2']:.4f}", f"{reg_data['y_sample']:.4f}", f"{resultado:.4f}"]
    ]
    t_reg = Table(data_reg, colWidths=[140, 75, 75, 80, 70, 100])
    t_reg.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#5d6d7e")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#bdc3c7"))
    ]))
    story.append(t_reg)
    story.append(Spacer(1, 8))
    
    if img_calib_bytes:
        story.append(Paragraph("<b>3. Análisis Gráfico: Curva de Calibración y Corte de Muestra</b>", styles['Heading3']))
        story.append(Spacer(1, 3))
        story.append(RLImage(img_calib_bytes, width=420, height=185))
        story.append(Spacer(1, 8))
    
    raw_hash_data = f"{lote}-{producto}-{resultado}-{datetime.now().strftime('%Y%m%d')}"
    hash_seguro = hashlib.sha256(raw_hash_data.encode()).hexdigest()[:16].upper()
    
    data_firmas = [
        [Paragraph(f"<b>Analista Responsable:</b><br/>{analista}<br/><br/>___________________________<br/>Firma Operador", body_style),
         Paragraph(f"<b>Aprobación Calidad:</b><br/>{jefe_qc}<br/><br/>___________________________<br/>Firma Autorizada (Jefe QC)", body_style)]
    ]
    t_firmas = Table(data_firmas, colWidths=[270, 270])
    t_firmas.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(t_firmas)
    story.append(Spacer(1, 10))
    
    story.append(Paragraph(f"<b>Trazabilidad 21 CFR Part 11:</b> Hash SHA-256: <code>{hash_seguro}</code>", ParagraphStyle('Hash', parent=body_style, fontSize=6.5, textColor=colors.HexColor("#7f8c8d"))))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# -------------------------------------------------------------------
# ENCABEZADO PRINCIPAL
# -------------------------------------------------------------------
st.title("🧪 LIMS QC & Automatización Analítica")
st.caption("Control Integrado: Excel Inteligente + Curva de Calibración + Regresión Lineal + Reportes PDF")

tab1, tab2, tab3 = st.tabs([
    "📋 1. Procesar Corrida & Calibración", 
    "📦 2. Base Master & Documentación (SDS/Farmacopea)", 
    "📈 3. Historial, SPC & Trazabilidad"
])

# -------------------------------------------------------------------
# PESTAÑA 1: PROCESAR CORRIDA & CURVA DE CALIBRACIÓN
# -------------------------------------------------------------------
with tab1:
    st.subheader("Configuración de Corrida y Carga de Datos")
    
    lista_productos = list(st.session_state["productos_db"].keys())
    
    col1, col2 = st.columns(2)
    with col1:
        prod_sel = st.selectbox("Seleccionar Producto:", options=lista_productos, key="sel_prod_run")
    with col2:
        lote_input = st.text_input("Número de Lote:", value=f"LOTE-{datetime.now().strftime('%Y%m%d')}-01")

    col_op1, col_op2, col_op3 = st.columns(3)
    with col_op1:
        analista_input = st.text_input("Analista Operador:", value="Q.F.B. Analista QC")
    with col_op2:
        jefe_qc_input = st.text_input("Jefe de Control de Calidad (Firma):", value="Ing. Químico - Jefe QC")
    with col_op3:
        tecnica_instrumental = st.selectbox(
            "Técnica Analítica:", 
            ["AAS / Espectroscopía Atómica", "HPLC / Cromatografía Líquida", "GC / Cromatografía de Gases", "ICP-OES", "Físico-Químico (pH / Viscosidad)", "Titulometria Clásica"]
        )

    st.markdown("---")
    
    st.markdown("#### 📂 Cargar Archivo Excel de Corrida y Calibración")
    archivo_corrida = st.file_uploader(
        "Sube tu archivo Excel (.xlsx) con los estándares de calibración y la señal de la muestra:", 
        type=["xlsx"], 
        key="uploader_datos_corrida"
    )

    x_std_default = np.array([0.0, 5.0, 10.0, 15.0, 20.0])
    y_std_default = np.array([0.02, 1.05, 2.08, 3.12, 4.15])
    y_sample_input_default = 2.50

    x_std = x_std_default
    y_std = y_std_default
    y_sample_val = y_sample_input_default

    if archivo_corrida is not None:
        try:
            xls_file = pd.ExcelFile(archivo_corrida)
            sheet_name_to_use = xls_file.sheet_names[0]
            
            for sh in xls_file.sheet_names:
                if any(k in sh.lower() for k in ["calib", "std", "curva", "dato", "corrida", "muestra"]):
                    sheet_name_to_use = sh
                    break
            
            df_excel = pd.read_excel(archivo_corrida, sheet_name=sheet_name_to_use)
            df_excel.columns = df_excel.columns.astype(str).str.strip().str.lower()
            
            st.success(f"✅ Excel leído desde la pestaña: `{sheet_name_to_use}`")
            
            cols_lower = list(df_excel.columns)
            col_conc = next((c for c in cols_lower if any(term in c for term in ["conc", "standard", "std", "x"])), None)
            col_senal = next((c for c in cols_lower if any(term in c for term in ["senal", "absorbancia", "area", "y", "lectura"])), None)
            
            if col_conc and col_senal:
                df_clean = df_excel[[col_conc, col_senal]].dropna()
                x_std = df_clean[col_conc].to_numpy(dtype=float)
                y_std = df_clean[col_senal].to_numpy(dtype=float)
            
            col_muestra_val = next((c for c in cols_lower if any(term in c for term in ["muestra", "sample", "resultado", "valor"])), None)
            if col_muestra_val:
                y_sample_val = float(df_excel[col_muestra_val].dropna().iloc[0])
                
        except Exception as e:
            st.warning(f"No se pudieron extraer automáticamente los estándares: {e}. Usando valores por defecto.")

    # Ocultar la tabla de edición y los inputs en un expander para no ensuciar la pantalla móvil
    with st.expander("⚙️ Ajustes Avanzados: Ver / Editar Estándares de Calibración & Señal de Muestra Manual", expanded=False):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.write("Valores de Estándares Activos:")
            df_std_edit = pd.DataFrame({"Concentración (X)": x_std, "Señal / Absorbancia (Y)": y_std})
            df_std_edited = st.data_editor(df_std_edit, num_rows="dynamic", key="editor_std")
            x_std = df_std_edited["Concentración (X)"].to_numpy(dtype=float)
            y_std = df_std_edited["Señal / Absorbancia (Y)"].to_numpy(dtype=float)
            
        with col_c2:
            st.write("Lectura Instrumental de la Muestra:")
            y_sample_val = st.number_input("Señal / Absorbancia Medida en la Muestra (Y):", value=float(y_sample_val), format="%.4f")

    # Obtener especificaciones del producto seleccionado
    especs_producto = st.session_state["productos_db"][prod_sel]["especificaciones"]
    param_obj = especs_producto[0]
    min_lim = param_obj["min_hds"]
    max_lim = param_obj["max_hds"]
    param_nombre = param_obj["parametro"]
    unidad_medida = param_obj["unidad"]

    st.markdown(f"**Parámetro evaluado en base master:** `{param_nombre}` (Límites permitidos: {min_lim} - {max_lim} {unidad_medida})")

    if st.button("🚀 Evaluar Lote, Registrar y Generar Certificado PDF con Curva", type="primary"):
        # Cálculo matemático interno al presionar el botón
        if len(x_std) > 1 and len(y_std) > 1:
            slope, intercept = np.polyfit(x_std, y_std, 1)
            correlation_matrix = np.corrcoef(x_std, y_std)
            r_val = correlation_matrix[0, 1] if not np.isnan(correlation_matrix[0, 1]) else 0.0
            r2 = r_val ** 2
            val_resultado = (y_sample_val - intercept) / slope if slope != 0 else 0.0
        else:
            slope, intercept, r2 = 1.0, 0.0, 1.0
            val_resultado = y_sample_val

        reg_data = {
            "m": slope,
            "b": intercept,
            "r2": r2,
            "y_sample": y_sample_val
        }

        estado = "CUMPLE" if (min_lim <= val_resultado <= max_lim) else "FUERA DE ESPECIFICACIÓN (OOS)"
        
        if estado == "CUMPLE":
            st.success(f"✅ Dictamen: El lote {lote_input} **CUMPLE**. Concentración Interpolada: {val_resultado:.4f} {unidad_medida}")
        else:
            st.error(f"❌ Dictamen: El lote {lote_input} está **FUERA DE ESPECIFICACIÓN**. Concentración Interpolada: {val_resultado:.4f} {unidad_medida}")
            
        nuevo_registro = pd.DataFrame([{
            "Lote": lote_input,
            "Producto": prod_sel,
            "Parametro": param_nombre,
            "Resultado": val_resultado,
            "Estado": estado,
            "Analista": analista_input,
            "JefeQC": jefe_qc_input,
            "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M")
        }])
        st.session_state["historial_corridas"] = pd.concat([st.session_state["historial_corridas"], nuevo_registro], ignore_index=True)

        img_buf = generar_imagen_curva_calibracion(x_std, y_std, val_resultado, y_sample_val, slope, intercept, r2, param_nombre)

        pdf_bytes = generar_pdf_certificado(
            lote=lote_input,
            producto=prod_sel,
            parametro=param_nombre,
            resultado=val_resultado,
            min_lim=min_lim,
            max_lim=max_lim,
            unidad=unidad_medida,
            estado=estado,
            analista=analista_input,
            jefe_qc=jefe_qc_input,
            tecnica=tecnica_instrumental,
            reg_data=reg_data,
            img_calib_bytes=img_buf
        )

        st.markdown("### 📥 Descargar Certificado de Análisis con Curva de Calibración")
        st.download_button(
            label="📄 Descargar Certificado PDF Oficial con Curva",
            data=pdf_bytes,
            file_name=f"CoA_{lote_input}_{prod_sel.replace(' ', '_')}.pdf",
            mime="application/pdf"
        )

# -------------------------------------------------------------------
# PESTAÑA 2: BASE MASTER, SDS Y FARMACÓPEA
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
                st.session_state["productos_db"][nuevo_prod_nombre] = {
                    "especificaciones": [
                        {"parametro": "Ensayo Principal", "tecnica": "Metodología General", "min_hds": 95.0, "max_hds": 105.0, "unidad": "%"}
                    ]
                }
                st.success(f"✅ Producto '{nuevo_prod_nombre}' registrado con éxito.")
                st.rerun()
            else:
                st.warning("Por favor ingrese el nombre del producto.")

    st.markdown("---")
    st.subheader("🔍 Estado Actual de la Base Master")
    st.json(st.session_state["productos_db"])

# -------------------------------------------------------------------
# PESTAÑA 3: HISTORIAL, SPC Y SEGUIMIENTO AISLADO
# -------------------------------------------------------------------
with tab3:
    st.subheader("📈 Control Estadístico de Procesos (SPC) & Seguimiento por Analito")
    
    df_hist = st.session_state["historial_corridas"]
    
    if not df_hist.empty:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            prod_lista_hist = df_hist["Producto"].unique().tolist()
            prod_filtro = st.selectbox("Filtrar por Producto:", options=prod_lista_hist, key="filtro_hist_prod")
        
        df_filtrado_prod = df_hist[df_hist["Producto"] == prod_filtro]
        
        with col_f2:
            param_lista_hist = df_filtrado_prod["Parametro"].unique().tolist()
            param_filtro = st.selectbox("Filtrar por Parámetro / Analito:", options=param_lista_hist, key="filtro_hist_param")
            
        df_final_spc = df_filtrado_prod[df_filtrado_prod["Parametro"] == param_filtro]
        
        st.markdown(f"### Histórico Filtrado para: `{prod_filtro}` -> `{param_filtro}`")
        st.dataframe(df_final_spc, use_container_width=True)
        
        if not df_final_spc.empty:
            fig_spc = px.line(
                df_final_spc, 
                x="Lote", 
                y="Resultado", 
                markers=True,
                title=f"Tendencia SPC - {param_filtro} ({prod_filtro})"
            )
            st.plotly_chart(fig_spc, use_container_width=True)
        else:
            st.info("No hay suficientes datos para graficar con este filtro.")
    else:
        st.info("Aún no hay registros en el historial de corridas.")

st.markdown("""
</div>
""", unsafe_allow_html=True)
