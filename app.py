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

st.set_page_config(
    page_title="LIMS AI - Control y Predicción Analítica",
    page_icon="🔬",
    layout="wide"
)

st.title("🔬 LIMS AI - Control, Aprobación y Predicción Analítica")
st.caption("Validación Automática de Corridas, Asistente de Dictamen IA y Análisis Predictivo de Tendencias")

# --- ESTADOS DE SESIÓN ---
if 'base_maestro' not in st.session_state:
    st.session_state.base_maestro = pd.DataFrame([
        {
            "ID_Elemento": "ELE-001",
            "Elemento_Muestra": "Paracetamol Active",
            "Tecnica": "HPLC",
            "Parametro": "Valoración",
            "Especificacion_Min": 95.0,
            "Especificacion_Max": 105.0,
            "Unidad": "%"
        },
        {
            "ID_Elemento": "ELE-002",
            "Elemento_Muestra": "Impureza A",
            "Tecnica": "HPLC",
            "Parametro": "Sustancias Relacionadas",
            "Especificacion_Min": 0.0,
            "Especificacion_Max": 0.5,
            "Unidad": "%"
        },
        {
            "ID_Elemento": "ELE-003",
            "Elemento_Muestra": "Metanol Residual",
            "Tecnica": "CG",
            "Parametro": "Solventes Residuales",
            "Especificacion_Min": 0.0,
            "Especificacion_Max": 3000.0,
            "Unidad": "ppm"
        },
        {
            "ID_Elemento": "ELE-004",
            "Elemento_Muestra": "Marcador Fluorescente",
            "Tecnica": "Espectrofluorescencia",
            "Parametro": "Intensidad Relativa",
            "Especificacion_Min": 80.0,
            "Especificacion_Max": 120.0,
            "Unidad": "UF"
        },
        {
            "ID_Elemento": "ELE-005",
            "Elemento_Muestra": "Muestra Biofertilizante",
            "Tecnica": "Fisicoquimico",
            "Parametro": "pH",
            "Especificacion_Min": 6.5,
            "Especificacion_Max": 7.5,
            "Unidad": "pH"
        }
    ])

if 'pendientes' not in st.session_state:
    st.session_state.pendientes = {}

if 'aprobados' not in st.session_state:
    st.session_state.aprobados = {}

if 'rechazados' not in st.session_state:
    st.session_state.rechazados = {}

# --- PESTAÑAS LIMS ---
tab_maestro, tab_carga, tab_revision, tab_ia, tab_historial = st.tabs([
    "📂 1. Base Maestro",
    "📤 2. Carga Resultado Equipo",
    "🧐 3. Panel de Revisión",
    "🤖 4. Módulo IA & Tendencias",
    "📜 5. Historial & Certificados"
])

# =========================================================
# TAB 1: BASE MAESTRO
# =========================================================
with tab_maestro:
    st.subheader("⚙️ Gestión de la Base Maestro de Especificaciones")
    archivo_maestro_upload = st.file_uploader(
        "Sube tu archivo Excel Maestro (.xlsx / .csv):", 
        type=["xlsx", "csv"], 
        key="uploader_maestro"
    )

    if archivo_maestro_upload is not None:
        try:
            if archivo_maestro_upload.name.endswith('.csv'):
                df_temp = pd.read_csv(archivo_maestro_upload)
            else:
                df_temp = pd.read_excel(archivo_maestro_upload)

            cols_criticas = {'ID_Elemento', 'Tecnica', 'Especificacion_Min', 'Especificacion_Max'}
            if cols_criticas.issubset(df_temp.columns):
                st.session_state.base_maestro = df_temp
                st.success("✅ Base Maestro cargada y actualizada.")
            else:
                st.error(f"El archivo debe contener las columnas: {cols_criticas}")
        except Exception as e:
            st.error(f"Error al leer la Base Maestro: {str(e)}")

    st.markdown("---")
    st.dataframe(st.session_state.base_maestro, use_container_width=True)

# =========================================================
# TAB 2: CARGA Y CRUCE AUTOMÁTICO
# =========================================================
with tab_carga:
    st.subheader("📤 Carga y Evaluación de Corrida Analítica")
    
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        lote_analizado = st.text_input("Número de Lote / Corrida:", value=f"LOTE-{datetime.now().strftime('%Y%m%d')}-01")
    with col_m2:
        analista_nombre = st.text_input("Nombre del Analista:", value="Analista de Control de Calidad")

    archivo_equipo = st.file_uploader(
        "Selecciona el Excel del Equipo Analítico:", 
        type=["xlsx", "csv"], 
        key="uploader_equipo"
    )

    if archivo_equipo is not None:
        try:
            df_equipo = pd.read_csv(archivo_equipo) if archivo_equipo.name.endswith('.csv') else pd.read_excel(archivo_equipo)

            col_correlacion = st.selectbox("Columna que identifica el Elemento/Muestra:", options=df_equipo.columns.tolist())
            col_resultado = st.selectbox("Columna con el Resultado Final:", options=[c for c in df_equipo.columns if c != col_correlacion])

            if st.button("🔄 PROCESAR Y EVALUAR RANGOS", type="primary"):
                df_merged = pd.merge(df_equipo, st.session_state.base_maestro, left_on=col_correlacion, right_on="ID_Elemento", how="inner")
                if df_merged.empty:
                    df_merged = pd.merge(df_equipo, st.session_state.base_maestro, left_on=col_correlacion, right_on="Elemento_Muestra", how="inner")

                if df_merged.empty:
                    st.error("❌ No se encontraron coincidencias con la Base Maestro.")
                else:
                    def evaluar(row):
                        val = float(row[col_resultado])
                        return "CUMPLE" if float(row['Especificacion_Min']) <= val <= float(row['Especificacion_Max']) else "OOS (DESVÍO)"

                    df_merged['Dictamen_Tecnico'] = df_merged.apply(evaluar, axis=1)

                    st.session_state.pendientes[lote_analizado] = {
                        'lote': lote_analizado,
                        'analista': analista_nombre,
                        'fecha_carga': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'datos_evaluados': df_merged,
                        'col_resultado': col_resultado,
                        'col_correlacion': col_correlacion
                    }
                    st.success(f"✅ Corrida {lote_analizado} lista para revisión.")
                    st.dataframe(df_merged, use_container_width=True)

        except Exception as e:
            st.error(f"Error procesando archivo: {str(e)}")

# =========================================================
# TAB 3: REVISIÓN Y DICTAMEN
# =========================================================
with tab_revision:
    st.subheader("🧐 Panel de Revisión")

    if not st.session_state.pendientes:
        st.info("No hay corridas pendientes de revisión.")
    else:
        lote_sel = st.selectbox("Seleccione Lote / Corrida:", list(st.session_state.pendientes.keys()))
        item = st.session_state.pendientes[lote_sel]
        df_rev = item['datos_evaluados']

        st.dataframe(df_rev, use_container_width=True)

        # Sugerencia automática de justificación técnica
        oos_count = (df_rev['Dictamen_Tecnico'] == "OOS (DESVÍO)").sum()
        if oos_count == 0:
            obs_defecto = "Análisis auditado. Todos los parámetros evaluados se encuentran dentro de las especificaciones oficiales vigentes."
        else:
            obs_defecto = f"ALERTA QC: Se detectaron {oos_count} parámetros fuera de especificación (OOS). Se requiere investigación de laboratorio."

        observaciones_sup = st.text_area("Observaciones de Auditoría:", value=obs_defecto)
        supervisor_nombre = st.text_input("Nombre del Supervisor:", value="Q.F.B. Supervisor de Calidad")

        col_act1, col_act2 = st.columns(2)
        with col_act1:
            if st.button("✅ APROBAR Y EMITIR PDF", type="primary", use_container_width=True):
                # Generación de PDF
                buffer = io.BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
                story = []
                styles = getSampleStyleSheet()

                story.append(Paragraph("<b>INFORME DE LIBERACIÓN DE CALIDAD</b>", styles['Title']))
                story.append(Spacer(1, 10))
                story.append(Paragraph(f"<b>Lote:</b> {item['lote']}<br/><b>Analista:</b> {item['analista']}<br/><b>Supervisor:</b> {supervisor_nombre}", styles['Normal']))
                story.append(Spacer(1, 15))

                tabla_datos = [["Muestra", "Técnica", "Resultado", "Rango", "Dictamen"]]
                for _, r in df_rev.iterrows():
                    tabla_datos.append([
                        str(r.get('Elemento_Muestra', r.get(item['col_correlacion']))),
                        str(r.get('Tecnica', 'N/A')),
                        f"{r[item['col_resultado']]} {r.get('Unidad', '')}",
                        f"{r['Especificacion_Min']} - {r['Especificacion_Max']}",
                        str(r['Dictamen_Tecnico'])
                    ])

                t = Table(tabla_datos, colWidths=[130, 90, 100, 110, 100])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1E293B")),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
                    ('PADDING', (0,0), (-1,-1), 6)
                ]))
                story.append(t)

                doc.build(story)
                buffer.seek(0)

                st.session_state.aprobados[lote_sel] = {
                    'lote': lote_sel,
                    'pdf_bytes': buffer.getvalue(),
                    'fecha_aprobacion': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'supervisor': supervisor_nombre,
                    'datos': df_rev
                }
                del st.session_state.pendientes[lote_sel]
                st.success(f"Lote {lote_sel} APROBADO.")
                st.rerun()

        with col_act2:
            if st.button("❌ RECHAZAR CORRIDA", use_container_width=True):
                st.session_state.rechazados[lote_sel] = {
                    'lote': lote_sel,
                    'fecha_rechazo': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'supervisor': supervisor_nombre,
                    'datos': df_rev
                }
                del st.session_state.pendientes[lote_sel]
                st.error(f"Lote {lote_sel} RECHAZADO.")
                st.rerun()

# =========================================================
# TAB 4: MÓDULO IA & TENDENCIAS PREDICTIVAS
# =========================================================
with tab_ia:
    st.subheader("🤖 Análisis Predictivo y Detección Precoz de Desvíos (IA)")
    st.markdown("Este módulo evalúa la **estabilidad estadística** y predice el riesgo de desvíos futuros utilizando regresión lineal de tendencias.")

    # Simulación/Carga de serie temporal de lotes anteriores
    st.write("### 📉 Proyección de Tendencia por Parámetro")
    
    param_sel = st.selectbox("Seleccione Parámetro a Analizar:", st.session_state.base_maestro['Elemento_Muestra'].unique())
    
    # Extraer especificaciones
    row_spec = st.session_state.base_maestro[st.session_state.base_maestro['Elemento_Muestra'] == param_sel].iloc[0]
    spec_min = float(row_spec['Especificacion_Min'])
    spec_max = float(row_spec['Especificacion_Max'])

    # Generar serie de lotes históricos para demostración analítica
    np.random.seed(42)
    lotes_hist = [f"LOTE-2026-{i:03d}" for i in range(1, 11)]
    
    # Generar datos simulados con leve deriva
    base_val = (spec_min + spec_max) / 2
    deriva = np.linspace(0, (spec_max - base_val) * 0.8, 10)
    ruido = np.random.normal(0, (spec_max - spec_min) * 0.05, 10)
    valores_hist = base_val + deriva + ruido

    df_tendencia = pd.DataFrame({
        'Lote': lotes_hist,
        'Resultado': valores_hist,
        'Orden': np.arange(1, 11)
    })

    st.line_chart(df_tendencia.set_index('Lote')['Resultado'])

    # Regresión Lineal de Predicción
    slope, intercept, r_value, p_value, std_err = linregress(df_tendencia['Orden'], df_tendencia['Resultado'])
    
    # Proyección a 5 lotes futuros
    lote_futuro_num = 15
    prediccion_futura = slope * lote_futuro_num + intercept

    col_ia1, col_ia2, col_ia3 = st.columns(3)
    col_ia1.metric("Pendiente de Deriva (Slope)", f"{slope:.4f}")
    col_ia2.metric("Correlación R²", f"{r_value**2:.4f}")
    col_ia3.metric("Proyección a Lote #15", f"{prediccion_futura:.2f} {row_spec['Unidad']}")

    if prediccion_futura > spec_max or prediccion_futura < spec_min:
        st.error(f"⚠️ **DIAGNÓSTICO PREDICTIVO IA:** Si la tendencia continúa, el proceso caerá en **OOS** en el Lote #15 (Límite: {spec_min} - {spec_max}).")
    else:
        st.success("✅ **DIAGNÓSTICO PREDICTIVO IA:** Proceso estable. No se proyectan desvíos en las próximas 5 corridas.")

# =========================================================
# TAB 5: HISTORIAL Y CERTIFICADOS
# =========================================================
with tab_historial:
    st.subheader("📜 Historial de Certificados")
    if not st.session_state.aprobados:
        st.info("No hay certificados emitidos.")
    else:
        for l_id, data in st.session_state.aprobados.items():
            st.write(f"✅ **Lote:** {l_id} | **Aprobó:** {data['supervisor']} | **Fecha:** {data['fecha_aprobacion']}")
            st.download_button(
                label=f"📥 Descargar PDF Lote {l_id}",
                data=data['pdf_bytes'],
                file_name=f"Certificado_QC_{l_id}.pdf",
                mime="application/pdf"
            )
