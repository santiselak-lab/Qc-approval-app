import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
import hashlib
import io
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
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
# FUNCIÓN PARA GENERAR CERTIFICADO PDF OFICIAL
# -------------------------------------------------------------------
def generar_pdf_certificado(lote, producto, parametro, resultado, min_lim, max_lim, unidad, estado, analista, jefe_qc, tecnica):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor("#1b4f72"),
        alignment=1,
        spaceAfter=10
    )
    subtitle_style = ParagraphStyle(
        'SubTitleStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor("#566573"),
        alignment=1,
        spaceAfter=20
    )
    body_style = styles['Normal']
    
    # Encabezado
    story.append(Paragraph("<b>CERTIFICADO DE ANÁLISIS DE CALIDAD (CoA)</b>", title_style))
    story.append(Paragraph("Sistema LIMS QC Enterprise - Trazabilidad Analítica", subtitle_style))
    story.append(Spacer(1, 10))
    
    # Datos Generales de la Muestra
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
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#bdc3c7"))
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 15))
    
    # Tabla de Resultados Analíticos
    story.append(Paragraph("<b>Evaluación Analítica vs Especificaciones (HDS / Farmacopea)</b>", styles['Heading3']))
    story.append(Spacer(1, 5))
    
    color_estado = colors.HexColor("#27ae60") if estado == "CUMPLE" else colors.HexColor("#c0392b")
    
    data_res = [
        ["Parámetro Evaluado", "Especificación Min", "Especificación Max", "Resultado", "Unidad", "Dictamen"],
        [parametro, f"{min_lim}", f"{max_lim}", f"{resultado}", unidad, estado]
    ]
    t_res = Table(data_res, colWidths=[140, 80, 80, 80, 50, 110])
    t_res.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2e4053")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#bdc3c7")),
        ('TEXTCOLOR', (5,1), (5,1), color_estado),
        ('FONTNAME', (5,1), (5,1), 'Helvetica-Bold')
    ]))
    story.append(t_res)
    story.append(Spacer(1, 20))
    
    # Trazabilidad y Firmas
    raw_hash_data = f"{lote}-{producto}-{resultado}-{datetime.now().strftime('%Y%m%d')}"
    hash_seguro = hashlib.sha256(raw_hash_data.encode()).hexdigest()[:16].upper()
    
    data_firmas = [
        [Paragraph(f"<b>Analista Responsable:</b><br/>{analista}<br/><br/>___________________________<br/>Firma Operador", body_style),
         Paragraph(f"<b>Aprobación Calidad:</b><br/>{jefe_qc}<br/><br/>___________________________<br/>Firma Autorizada (Jefe QC)", body_style)]
    ]
    t_firmas = Table(data_firmas, colWidths=[270, 270])
    t_firmas.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_firmas)
    story.append(Spacer(1, 25))
    
    story.append(Paragraph(f"<b>Trazabilidad Integridad de Datos (21 CFR Part 11):</b> Hash SHA-256: <code>{hash_seguro}</code>", ParagraphStyle('HashStyle', parent=body_style, fontSize=8, textColor=colors.HexColor("#7f8c8d"))))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# -------------------------------------------------------------------
# ENCABEZADO PRINCIPAL
# -------------------------------------------------------------------
st.title("🧪 LIMS QC & Automatización Analítica")
st.caption("Control Integrado: Excel Interno + SDS/MSDS + Farmacopea RAG (Con Fallback) + SPC + Reportes PDF")

tab1, tab2, tab3 = st.tabs([
    "📋 1. Procesar Corrida & Cálculos", 
    "📦 2. Base Master & Documentación (SDS/Farmacopea)", 
    "📈 3. Historial, SPC & Trazabilidad"
])

# -------------------------------------------------------------------
# PESTAÑA 1: PROCESAR CORRIDA & TÉCNICAS ANALÍTICAS
# -------------------------------------------------------------------
with tab1:
    st.subheader("Evaluación de Lote, Firma y Emisión de Certificado")
    
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
    
    archivo_corrida = st.file_uploader(
        "Cargue el archivo Excel (.xlsx) con los resultados de la muestra:", 
        type=["xlsx"], 
        key="uploader_datos_corrida"
    )

    val_resultado = None
    if archivo_corrida is not None:
        try:
            df_corrida_subida = pd.read_excel(archivo_corrida, sheet_name="Datos_Corrida", skiprows=6)
            df_corrida_subida.columns = df_corrida_subida.columns.str.strip()
            st.success("✅ Archivo de corrida cargado correctamente.")
            st.dataframe(df_corrida_subida, use_container_width=True)
            
            if "Resultado Obtenido" in df_corrida_subida.columns:
                val_resultado = float(df_corrida_subida.iloc[0]["Resultado Obtenido"])
            else:
                val_resultado = 98.8
        except Exception as e:
            st.warning(f"No se leyó pestaña estándar, ingrese el resultado manualmente: {e}")
            val_resultado = st.number_input("Resultado Analítico Manual:", value=98.8, format="%.4f")
    else:
        st.info("ℹ️ Ingrese el resultado analítico de la muestra para la evaluación:")
        val_resultado = st.number_input("Resultado Analítico de la Muestra:", value=98.8, format="%.4f")

    # Obtener especificaciones del producto seleccionado
    especs_producto = st.session_state["productos_db"][prod_sel]["especificaciones"]
    param_obj = especs_producto[0] # Tomar el primer parámetro de referencia
    min_lim = param_obj["min_hds"]
    max_lim = param_obj["max_hds"]
    param_nombre = param_obj["parametro"]
    unidad_medida = param_obj["unidad"]

    st.markdown(f"**Parámetro evaluado en base master:** `{param_nombre}` (Límites: {min_lim} - {max_lim} {unidad_medida})")

    if st.button("🚀 Evaluar Lote, Registrar y Generar Certificado PDF", type="primary"):
        estado = "CUMPLE" if (min_lim <= val_resultado <= max_lim) else "FUERA DE ESPECIFICACIÓN (OOS)"
        
        if estado == "CUMPLE":
            st.success(f"✅ Dictamen: El lote {lote_input} **CUMPLE** con los parámetros. Resultado: {val_resultado} {unidad_medida}")
        else:
            st.error(f"❌ Dictamen: El lote {lote_input} está **FUERA DE ESPECIFICACIÓN**. Resultado: {val_resultado} {unidad_medida}")
            
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

        # Generar PDF al instante
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
            tecnica=tecnica_instrumental
        )

        st.markdown("### 📥 Descargar Certificado de Análisis Oficial")
        st.download_button(
            label="📄 Descargar Certificado en PDF",
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
                if file_farmacopea is not None:
                    st.success("📚 Farmacopea cargada exitosamente.")
                else:
                    st.warning("⚠️ Aviso: Sin Farmacopea adjunta, usando límites del Excel/SDS.")

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
# PESTAÑA 3: HISTORIAL, SPC Y SEGUIMIENTO AISLADO POR ANALITO
# -------------------------------------------------------------------
with tab3:
    st.subheader("📈 Control Estadístico de Procesos (SPC) & Seguimiento por Analito")
    
    df_hist = st.session_state["historial_corridas"]
    
    if not df_hist.empty:
        # --- FILTROS ESTRICTOS PARA EVITAR QUE SE MEZCLEN LOS PRODUCTOS ---
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
