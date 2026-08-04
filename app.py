import streamlit as st
import pandas as pd
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io
from datetime import datetime

st.set_page_config(
    page_title="LIMS QC - Control y Liberación Analítica",
    page_icon="🔬",
    layout="wide"
)

st.title("🔬 Sistema LIMS QC - Control y Aprobación Analítica")
st.caption("Validación Automática de Corridas Analíticas contra Base Maestro de Especificaciones")

# --- ESTADOS DE SESIÓN (PERSISTENCIA VIRTUAL) ---
if 'base_maestro' not in st.session_state:
    # Base Maestro por defecto de ejemplo con Técnicas y Límites
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
tab_maestro, tab_carga, tab_revision, tab_historial = st.tabs([
    "📂 1. Base Maestro (Especificaciones)",
    "📤 2. Carga Resultado de Equipo",
    "🧐 3. Panel de Revisión (Supervisor)",
    "📜 4. Historial & Certificados"
])

# =========================================================
# TAB 1: BASE MAESTRO DE ESPECIFICACIONES
# =========================================================
with tab_maestro:
    st.subheader("⚙️ Gestión de la Base de Datos Principal (Maestro)")
    st.markdown("""
    Carga o actualiza tu archivo **Excel Maestro** con el catálogo de elementos a analizar, 
    sus técnicas asociadas (`HPLC`, `CG`, `Espectrofluorescencia`, `Fisicoquimico`) y sus límites de especificación.
    """)

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
                st.success("✅ Base Maestro cargada y actualizada con éxito.")
            else:
                st.error(f"El archivo debe contener al menos las siguientes columnas: {cols_criticas}")
        except Exception as e:
            st.error(f"Error al leer la Base Maestro: {str(e)}")

    st.markdown("---")
    st.write("### 📋 Registro Oficial de Especificaciones Vigentes")
    st.dataframe(st.session_state.base_maestro, use_container_width=True)

# =========================================================
# TAB 2: CARGA Y CRUCE AUTOMÁTICO DE RESULTADOS DE EQUIPO
# =========================================================
with tab_carga:
    st.subheader("📤 Procesamiento de Resultado del Equipo Analítico")
    
    if st.session_state.base_maestro.empty:
        st.warning("⚠️ Primero debes cargar la Base Maestro en la Pestaña 1.")
    else:
        st.markdown("Sube el archivo Excel exportado por el equipo analítico (`HPLC`, `CG`, `Espectrofluorescencia`, etc.).")
        
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
                if archivo_equipo.name.endswith('.csv'):
                    df_equipo = pd.read_csv(archivo_equipo)
                else:
                    df_equipo = pd.read_excel(archivo_equipo)

                st.write("#### 📊 Vista previa del archivo de equipo:")
                st.dataframe(df_equipo.head(10), use_container_width=True)

                # Identificar columna de correlación
                col_correlacion = st.selectbox(
                    "Selecciona la columna del Excel de Equipo que identifica al Elemento/Muestra:",
                    options=df_equipo.columns.tolist()
                )

                col_resultado = st.selectbox(
                    "Selecciona la columna que contiene el Resultado Final:",
                    options=[c for c in df_equipo.columns if c != col_correlacion]
                )

                if st.button("🔄 PROCESAR Y CORRELACIONAR CON BASE MAESTRO", type="primary"):
                    # Cruce de información
                    df_merged = pd.merge(
                        df_equipo,
                        st.session_state.base_maestro,
                        left_on=col_correlacion,
                        right_on="ID_Elemento",
                        how="inner"
                    )

                    if df_merged.empty:
                        # Intento secundario por nombre de elemento
                        df_merged = pd.merge(
                            df_equipo,
                            st.session_state.base_maestro,
                            left_on=col_correlacion,
                            right_on="Elemento_Muestra",
                            how="inner"
                        )

                    if df_merged.empty:
                        st.error("❌ No se encontraron coincidencias entre la columna seleccionada del equipo y la Base Maestro.")
                    else:
                        # Evaluación automática de cumplimiento
                        def evaluar_cumplimiento(row):
                            val = float(row[col_resultado])
                            lim_min = float(row['Especificacion_Min'])
                            lim_max = float(row['Especificacion_Max'])
                            if lim_min <= val <= lim_max:
                                return "CUMPLE"
                            else:
                                return "OOS (DESVÍO)"

                        df_merged['Dictamen_Tecnico'] = df_merged.apply(evaluar_cumplimiento, axis=1)

                        # Guardar paquete para el Supervisor
                        st.session_state.pendientes[lote_analizado] = {
                            'lote': lote_analizado,
                            'analista': analista_nombre,
                            'fecha_carga': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'datos_evaluados': df_merged,
                            'col_resultado': col_resultado,
                            'col_correlacion': col_correlacion
                        }
                        
                        st.success(f"✅ Corrida {lote_analizado} procesada correctamente. Se enviaron {len(df_merged)} filas al Panel del Supervisor.")
                        st.dataframe(df_merged[[col_correlacion, 'Tecnica', 'Parametro', col_resultado, 'Especificacion_Min', 'Especificacion_Max', 'Dictamen_Tecnico']], use_container_width=True)

            except Exception as e:
                st.error(f"Error procesando el archivo del equipo: {str(e)}")

# =========================================================
# TAB 3: PANEL DE REVISIÓN Y DICTAMEN (SUPERVISOR)
# =========================================================
with tab_revision:
    st.subheader("🧐 Bandeja de Revisión y Dictamen (Supervisor)")

    if len(st.session_state.pendientes) == 0:
        st.info("No hay corridas ni análisis pendientes de revisión.")
    else:
        lote_sel = st.selectbox("Seleccione Lote / Corrida a Auditar:", list(st.session_state.pendientes.keys()))
        item = st.session_state.pendientes[lote_sel]

        st.markdown(f"**Lote:** `{item['lote']}` | **Analista:** `{item['analista']}` | **Fecha Carga:** `{item['fecha_carga']}`")
        
        df_rev = item['datos_evaluados']
        st.dataframe(df_rev, use_container_width=True)

        # Detectar si hay OOS (Desvíos fuera de especificación)
        tiene_desvios = (df_rev['Dictamen_Tecnico'] == "OOS (DESVÍO)").any()
        if tiene_desvios:
            st.error("⚠️ ATENCIÓN: Esta corrida contiene resultados FUERA DE ESPECIFICACIÓN (OOS).")
        else:
            st.success("✅ Todos los resultados están DENTRO DE ESPECIFICACIÓN.")

        st.markdown("---")
        st.write("### Dictamen Oficial del Supervisor")
        
        observaciones_sup = st.text_area(
            "Observaciones / Comentarios de Auditoría:", 
            value="Corrida revisada y verificada contra los trazados del equipo y especificaciones de la Base Maestro."
        )
        supervisor_nombre = st.text_input("Nombre y Cargo del Supervisor:", value="Q.F.B. Supervisor de Aseguramiento de Calidad")

        col_act1, col_act2 = st.columns(2)

        with col_act1:
            if st.button("✅ APROBAR Y GENERAR CERTIFICADO OFICIAL", type="primary", use_container_width=True):
                # Generación de PDF Oficial en Memoria
                buffer = io.BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
                story = []
                styles = getSampleStyleSheet()

                # Encabezado
                story.append(Paragraph("<b>INFORME OFICIAL DE LIBERACIÓN DE CALIDAD</b>", styles['Title']))
                story.append(Spacer(1, 10))
                
                info_header = f"""
                <b>Lote / Corrida:</b> {item['lote']}<br/>
                <b>Analista:</b> {item['analista']}<br/>
                <b>Fecha de Revisión:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
                <b>Supervisor Responsable:</b> {supervisor_nombre}
                """
                story.append(Paragraph(info_header, styles['Normal']))
                story.append(Spacer(1, 15))

                # Tabla de Datos
                tabla_datos = [["Elemento / Muestra", "Técnica", "Resultado", "Especificación", "Dictamen"]]
                
                for _, r in df_rev.iterrows():
                    elem = str(r.get('Elemento_Muestra', r.get(item['col_correlacion'])))
                    tec = str(r.get('Tecnica', 'N/A'))
                    res = f"{r[item['col_resultado']]} {r.get('Unidad', '')}"
                    espec = f"{r['Especificacion_Min']} - {r['Especificacion_Max']}"
                    dictamen = str(r['Dictamen_Tecnico'])
                    tabla_datos.append([elem, tec, res, espec, dictamen])

                t = Table(tabla_datos, colWidths=[130, 90, 100, 110, 100])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1E293B")),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
                    ('PADDING', (0,0), (-1,-1), 6)
                ]))
                story.append(t)
                story.append(Spacer(1, 20))

                # Bloque de Firma
                firma_block = f"""
                <b>DICTAMEN DE AUTORIZACIÓN:</b><br/>
                <b>Estatus:</b> <font color='green'><b>APROBADO Y LIBERADO</b></font><br/>
                <b>Observaciones:</b> {observaciones_sup}<br/><br/>
                ____________________________________________<br/>
                <b>Firma Digital:</b> {supervisor_nombre}
                """
                story.append(Paragraph(firma_block, styles['Normal']))

                doc.build(story)
                buffer.seek(0)

                # Guardar en Aprobados y remover de pendientes
                st.session_state.aprobados[lote_sel] = {
                    'lote': lote_sel,
                    'pdf_bytes': buffer.getvalue(),
                    'fecha_aprobacion': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'supervisor': supervisor_nombre,
                    'observaciones': observaciones_sup,
                    'datos': df_rev
                }
                del st.session_state.pendientes[lote_sel]
                st.success(f"¡Lote {lote_sel} APROBADO correctamente!")
                st.rerun()

        with col_act2:
            if st.button("❌ RECHAZAR CORRIDA (OOS)", use_container_width=True):
                st.session_state.rechazados[lote_sel] = {
                    'lote': lote_sel,
                    'fecha_rechazo': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'supervisor': supervisor_nombre,
                    'observaciones': observaciones_sup,
                    'datos': df_rev
                }
                del st.session_state.pendientes[lote_sel]
                st.error(f"Lote {lote_sel} marcado como RECHAZADO.")
                st.rerun()

# =========================================================
# TAB 4: HISTORIAL Y CERTIFICADOS
# =========================================================
with tab_historial:
    st.subheader("📜 Historial de Dictámenes y Certificados")

    subtab1, subtab2 = st.tabs(["🟢 Lotes Aprobados", "🔴 Lotes Rechazados"])

    with subtab1:
        if len(st.session_state.aprobados) == 0:
            st.info("No hay lotes aprobados registrados.")
        else:
            for l_id, data in st.session_state.aprobados.items():
                with st.expander(f"✅ Certificado Aprobado - Lote: {l_id}"):
                    st.write(f"**Aprobado por:** {data['supervisor']}")
                    st.write(f"**Fecha:** {data['fecha_aprobacion']}")
                    st.write(f"**Observaciones:** {data['observaciones']}")
                    st.download_button(
                        label=f"📥 Descargar PDF Oficial Lote {l_id}",
                        data=data['pdf_bytes'],
                        file_name=f"Certificado_QC_{l_id}.pdf",
                        mime="application/pdf"
                    )

    with subtab2:
        if len(st.session_state.rechazados) == 0:
            st.info("No hay lotes rechazados.")
        else:
            for l_id, data in st.session_state.rechazados.items():
                with st.expander(f"❌ Registro de Rechazo - Lote: {l_id}"):
                    st.write(f"**Rechazado por:** {data['supervisor']}")
                    st.write(f"**Fecha:** {data['fecha_rechazo']}")
                    st.write(f"**Motivo / Observaciones:** {data['observaciones']}")
                    st.dataframe(data['datos'], use_container_width=True)
