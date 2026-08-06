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
                {"parametro": "Contenido de Cu", "tecnica": "AAS / UV-Vis", "min_hds": 25.0, "max_hds": 25.3, "unidad": "%"},
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
# FUNCIÓN PARA GENERAR GRÁFICA MATPLOTLIB PARA EL PDF
# -------------------------------------------------------------------
def generar_imagen_grafica(df_resultados, param_nombre):
    plt.figure(figsize=(6, 2.5))
    plt.plot(df_resultados.index + 1, df_resultados["Resultado"], marker='o', color='#1b4f72', linestyle='-', linewidth=2)
    plt.axhline(y=df_resultados["Resultado"].mean(), color='r', linestyle='--', label=f"Media: {df_resultados['Resultado'].mean():.2f}")
    plt.title(f"Comportamiento de Replicados - {param_nombre}", fontsize=10, fontweight='bold', color='#1b4f72')
    plt.xlabel("N° de Replicado / Muestra", fontsize=8)
    plt.ylabel("Resultado", fontsize=8)
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend(fontsize=8)
    plt.tight_layout()
    
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=200)
    plt.buffer_size = img_buffer.seek(0)
    plt.close()
    return img_buffer

# -------------------------------------------------------------------
# FUNCIÓN PARA GENERAR CERTIFICADO PDF OFICIAL CON GRÁFICA Y ESTADÍSTICA
# -------------------------------------------------------------------
def generar_pdf_certificado(lote, producto, parametro, resultado, min_lim, max_lim, unidad, estado, analista, jefe_qc, tecnica, stats, img_grafica_bytes):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle', parent=styles['Heading1'], fontSize=15, textColor=colors.HexColor("#1b4f72"), alignment=1, spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'SubTitleStyle', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor("#566573"), alignment=1, spaceAfter=15
    )
    body_style = styles['Normal']
    
    # Encabezado
    story.append(Paragraph("<b>CERTIFICADO DE ANÁLISIS DE CALIDAD (CoA)</b>", title_style))
    story.append(Paragraph("Sistema LIMS QC Enterprise - Trazabilidad Analítica & Estadística", subtitle_style))
    story.append(Spacer(1, 5))
    
    # Datos Generales
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
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#bdc3c7"))
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))
    
    # Tabla de Resultados
    story.append(Paragraph("<b>1. Evaluación Analítica vs Especificación Oficial</b>", styles['Heading3']))
    story.append(Spacer(1, 4))
    
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
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#bdc3c7")),
        ('TEXTCOLOR', (5,1), (5,1), color_estado),
        ('FONTNAME', (5,1), (5,1), 'Helvetica-Bold')
    ]))
    story.append(t_res)
    story.append(Spacer(1, 10))
    
    # Análisis Estadístico y Matemático
    story.append(Paragraph("<b>2. Resumen Estadístico (Matemático) de la Corrida</b>", styles['Heading3']))
    story.append(Spacer(1, 4))
    
    data_stat = [
        ["Promedio (Media)", "Desviación Estándar (SD)", "Coef. de Variación (%CV)", "Mínimo Replicado", "Máximo Replicado"],
        [f"{stats['media']:.4f}", f"{stats['sd']:.4f}", f"{stats['cv']:.2f}%", f"{stats['min']:.4f}", f"{stats['max']:.4f}"]
    ]
    t_stat = Table(data_stat, colWidths=[110, 110, 110, 100, 110])
    t_stat.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#5d6d7e")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#bdc3c7"))
    ]))
    story.append(t_stat)
    story.append(Spacer(1, 10))
    
    # Gráfica en PDF
    if img_grafica_bytes:
        story.append(Paragraph("<b>3. Análisis Gráfico de la Corrida Analítica</b>", styles['Heading3']))
        story.append(Spacer(1, 4))
        story.append(RLImage(img_grafica_bytes, width=420, height=175))
        story.append(Spacer(1, 10))
    
    # Firmas y Trazabilidad
    raw_hash_data = f"{lote}-{producto}-{resultado}-{datetime.now().strftime('%Y%m%d')}"
    hash_seguro = hashlib.sha256(raw_hash_data.encode()).hexdigest()[:16].upper()
    
    data_firmas = [
        [Paragraph(f"<b>Analista Responsable:</b><br/>{analista}<br/><br/>___________________________<br/>Firma Operador", body_style),
         Paragraph(f"<b>Aprobación Calidad:</b><br/>{jefe_qc}<br/><br/>___________________________<br/>Firma Autorizada (Jefe QC)", body_style)]
    ]
    t_firmas = Table(data_firmas, colWidths=[270, 270])
    t_firmas.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(t_firmas)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph(f"<b>Trazabilidad 21 CFR Part 11:</b> Hash SHA-256: <code>{hash_seguro}</code>", ParagraphStyle('Hash', parent=body_style, fontSize=7, textColor=colors.HexColor("#7f8c8d"))))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# -------------------------------------------------------------------
# ENCABEZADO PRINCIPAL
# -------------------------------------------------------------------
st.title("🧪 LIMS QC & Automatización Analítica")
st.caption("Control Integrado: Excel Inteligente + Cálculos Estadísticos + Gráficos Automáticos + Reportes PDF")

tab1, tab2, tab3 = st.tabs([
    "📋 1. Procesar Corrida & Cálculos", 
    "📦 2. Base Master & Documentación (SDS/Farmacopea)", 
    "📈 3. Historial, SPC & Trazabilidad"
])

# -------------------------------------------------------------------
# PESTAÑA 1: PROCESAR CORRIDA & TÉCNICAS ANALÍTICAS
# -------------------------------------------------------------------
with tab1:
    st.subheader("Evaluación de Lote, Estadísticas, Gráficos y Certificado")
    
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
            ["HPLC / Cromatografía Líquida", "GC / Cromatografía de Gases", "AAS / Espectroscopía Atómica", "ICP-OES", "Físico-Químico (pH / Viscosidad)", "Titulometría Clásica"]
        )

    st.markdown("---")
    
    # --- UPLOADER INTELIGENTE DE EXCEL ---
    st.markdown("#### 📂 Cargar Archivo Excel de Resultados de Corrida")
    archivo_corrida = st.file_uploader(
        "Sube tu archivo Excel (.xlsx). El sistema detectará automáticamente los títulos y columnas:", 
        type=["xlsx"], 
        key="uploader_datos_corrida"
    )

    df_cargado_raw = None
    resultados_serie = pd.Series([98.8]) # Valor por defecto

    if archivo_corrida is not None:
        try:
            # Leer el Excel de manera flexible (primera hoja disponible)
            xls_file = pd.ExcelFile(archivo_corrida)
            sheet_name_to_use = xls_file.sheet_names[0]
            
            # Buscar si hay alguna hoja con nombre similar a datos o corrida
            for sh in xls_file.sheet_names:
                if any(k in sh.lower() for k in ["dato", "corrida", "muestra", "resultado", "analisis"]):
                    sheet_name_to_use = sh
                    break
            
            df_cargado_raw = pd.read_excel(archivo_corrida, sheet_name=sheet_name_to_use)
            
            # Normalizar nombres de columnas (quitar espacios, convertir a minúsculas)
            df_cargado_raw.columns = df_cargado_raw.columns.astype(str).str.strip().str.lower()
            
            st.success(f"✅ Excel leído con éxito desde la pestaña: `{sheet_name_to_use}`")
            st.dataframe(df_cargado_raw, use_container_width=True)
            
            # Detectar inteligentemente la columna de resultados
            col_resultado_candidata = None
            for col in df_cargado_raw.columns:
                if any(term in col for term in ["resultado", "valor", "concentracion", "lectura", " ensayo", "%", "ppm", "mg"]):
                    col_resultado_candidata = col
                    break
            
            if col_resultado_candidata is not None:
                resultados_serie = pd.to_numeric(df_cargado_raw[col_resultado_candidata], errors='coerce').dropna()
                st.info(f"🔍 Columna de resultados detectada automáticamente: `{col_resultado_candidata}` ({len(resultados_serie)} valores encontrados).")
            else:
                # Si no encuentra ninguna, tomar la primera columna numérica que encuentre
                for col in df_cargado_raw.columns:
                    if pd.api.types.is_numeric_dtype(df_cargado_raw[col]):
                        resultados_serie = df_cargado_raw[col].dropna()
                        st.info(f"ℹ️ Usando la primera columna numérica detectada: `{col}`")
                        break
                        
        except Exception as e:
            st.error(f"Error al procesar el archivo Excel: {e}")
            resultados_serie = pd.Series([98.8])
    else:
        st.info("ℹ️ Sin archivo adjunto. Se usará el valor manual de prueba a continuación:")
        val_manual = st.number_input("Valor Analítico Manual:", value=98.8, format="%.4f")
        resultados_serie = pd.Series([val_manual])

    # Valor principal a reportar (promedio de la serie cargada o valor único)
    val_resultado = float(resultados_serie.mean()) if not resultados_serie.empty else 98.8

    # Cálculo Estadístico Matemático de los datos cargados
    stats_corrida = {
        "media": float(resultados_serie.mean()),
        "sd": float(resultados_serie.std(ddof=1)) if len(resultados_serie) > 1 else 0.0,
        "cv": float((resultados_serie.std(ddof=1) / resultados_serie.mean()) * 100) if len(resultados_serie) > 1 and resultados_serie.mean() != 0 else 0.0,
        "min": float(resultados_serie.min()),
        "max": float(resultados_serie.max())
    }

    # Mostrar Métricas Estadísticas en Pantalla
    st.markdown("### 📊 Análisis Estadístico y Matemático en Vivo")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Promedio", f"{stats_corrida['media']:.4f}")
    m2.metric("Desv. Estándar (SD)", f"{stats_corrida['sd']:.4f}")
    m3.metric("% Coef. Variación", f"{stats_corrida['cv']:.2f}%")
    m4.metric("Valor Mínimo", f"{stats_corrida['min']:.4f}")
    m5.metric("Valor Máximo", f"{stats_corrida['max']:.4f}")

    # Gráfica Interactiva en Streamlit (Plotly)
    if len(resultados_serie) > 0:
        df_plot = pd.DataFrame({"Replicado": range(1, len(resultados_serie) + 1), "Resultado": resultados_serie.values})
        fig_interactiva = px.line(
            df_plot, x="Replicado", y="Resultado", markers=True,
            title="Tendencia Gráfica de Replicados de la Muestra",
            labels={"Resultado": "Valor Medido", "Replicado": "N° de Muestra"}
        )
        fig_interactiva.add_hline(y=stats_corrida['media'], line_dash="dash", line_color="red", annotation_text=f"Media: {stats_corrida['media']:.2f}")
        st.plotly_chart(fig_interactiva, use_container_width=True)

    # Obtener especificaciones del producto seleccionado
    especs_producto = st.session_state["productos_db"][prod_sel]["especificaciones"]
    param_obj = especs_producto[0] # Parámetro de referencia principal
    min_lim = param_obj["min_hds"]
    max_lim = param_obj["max_hds"]
    param_nombre = param_obj["parametro"]
    unidad_medida = param_obj["unidad"]

    st.markdown(f"**Parámetro evaluado en base master:** `{param_nombre}` (Límites permitidos: {min_lim} - {max_lim} {unidad_medida})")

    if st.button("🚀 Evaluar Lote, Registrar y Generar Certificado PDF Completo", type="primary"):
        estado = "CUMPLE" if (min_lim <= val_resultado <= max_lim) else "FUERA DE ESPECIFICACIÓN (OOS)"
        
        if estado == "CUMPLE":
            st.success(f"✅ Dictamen: El lote {lote_input} **CUMPLE** con los parámetros. Resultado Promedio: {val_resultado:.4f} {unidad_medida}")
        else:
            st.error(f"❌ Dictamen: El lote {lote_input} está **FUERA DE ESPECIFICACIÓN**. Resultado Promedio: {val_resultado:.4f} {unidad_medida}")
            
        # Registrar en el historial de sesión
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

        # Generar imagen gráfica en buffer para el PDF
        img_buf = generar_imagen_grafica(df_plot, param_nombre) if len(resultados_serie) > 0 else None

        # Generar PDF oficial con estadísticas y gráficos incrustados
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
            stats=stats_corrida,
            img_grafica_bytes=img_buf
        )

        st.markdown("### 📥 Descargar Certificado de Análisis con Análisis Gráfico y Estadístico")
        st.download_button(
            label="📄 Descargar Certificado PDF Oficial",
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
                if file_excel is not None:
                    try:
                        df_ex = pd.read_excel(file_excel)
                        df_ex.columns = df_ex.columns.str.strip().str.lower()
                        st.session_state["productos_db"][nuevo_prod_nombre] = {
                            "especificaciones": [
                                {"parametro": "Ensayo Principal", "tecnica": "Metodología General", "min_hds": 95.0, "max_hds": 105.0, "unidad": "%"}
                            ]
                        }
                        st.success(f"✅ Producto '{nuevo_prod_nombre}' registrado con éxito.")
                    except Exception as e:
                        st.error(f"Error procesando Excel maestro: {e}")
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
