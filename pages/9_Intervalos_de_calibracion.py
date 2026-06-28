import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_equipos, get_calibraciones
from utils import aplicar_estilos

COLOR = {
    "verde":       "#23c057",
    "verde_osc":   "#15924a",
    "azul_marino": "#063d7d",
    "teal":        "#238d93",
    "verde_prof":  "#0a453c",
    "azul_med":    "#1469aa",
    "verde_menta": "#15795a",
    "aqua":        "#2dc197",
    "azul_noche":  "#0b2c40",
}

def calcular_intervalo_anios(fecha_ant: date, fecha_act: date) -> float:
    delta = fecha_act - fecha_ant
    return delta.days / 365.25

def fecha_desde_intervalo(fecha_base: date, intervalo_anios: float) -> date:
    dias = int(intervalo_anios * 365.25)
    return fecha_base + timedelta(days=dias)

def escalera_error_medio(error_medio, emp, intervalo_anterior_anios, fue_ajustado):
    if fue_ajustado:
        return {
            "recomendacion": "El equipo fue ajustado recientemente. Use el intervalo recomendado por el fabricante.",
            "intervalo_nuevo": None,
            "tipo": "warn"
        }
    limite_control = 0.80 * emp
    if abs(error_medio) > emp:
        return {
            "recomendacion": "El error medio supera el EMP. Se recomienda ajuste mecánico y calibración inmediata.",
            "intervalo_nuevo": None,
            "tipo": "bad"
        }
    elif abs(error_medio) <= limite_control:
        nuevo = intervalo_anterior_anios * 1.50
        return {
            "recomendacion": f"El error medio ({error_medio:.5f}) está dentro del límite de control ({limite_control:.5f}). Se amplía el intervalo en un 50%.",
            "intervalo_nuevo": nuevo,
            "tipo": "ok"
        }
    else:
        nuevo = intervalo_anterior_anios * 0.50
        return {
            "recomendacion": f"El error medio ({error_medio:.5f}) supera el límite de control ({limite_control:.5f}). Se reduce el intervalo en un 50%.",
            "intervalo_nuevo": nuevo,
            "tipo": "warn"
        }

def escalera_error_incertidumbre(error, incertidumbre, emp, intervalo_anterior_anios, fue_ajustado):
    if fue_ajustado:
        return {
            "recomendacion": "El equipo fue ajustado recientemente. Use el intervalo recomendado por el fabricante.",
            "intervalo_nuevo": None,
            "tipo": "warn"
        }
    limite_control = 0.80 * emp
    error_con_u = abs(error) + incertidumbre
    if error_con_u > emp:
        return {
            "recomendacion": f"El error ± U ({error_con_u:.5f}) supera el EMP ({emp:.5f}). Se recomienda ajuste mecánico y calibración inmediata.",
            "intervalo_nuevo": None,
            "tipo": "bad"
        }
    elif error_con_u <= limite_control:
        nuevo = intervalo_anterior_anios * 1.50
        return {
            "recomendacion": f"El error ± U ({error_con_u:.5f}) está dentro del límite de control ({limite_control:.5f}). Se amplía el intervalo en un 50%.",
            "intervalo_nuevo": nuevo,
            "tipo": "ok"
        }
    else:
        nuevo = intervalo_anterior_anios * 0.50
        return {
            "recomendacion": f"El error ± U ({error_con_u:.5f}) supera el límite de control ({limite_control:.5f}). Se reduce el intervalo en un 50%.",
            "intervalo_nuevo": nuevo,
            "tipo": "warn"
        }

def cartas_control(fechas, errores, emp, fue_ajustado, fecha_ajuste=None):
    if len(fechas) < 2:
        return {
            "recomendacion": "Se necesitan al menos 2 fechas de calibración.",
            "intervalo_nuevo": None,
            "tipo": "warn",
            "deriva_anual": None,
            "datos_grafica": None
        }
    fecha_ref = fechas[0]
    tiempos_anios = [(f - fecha_ref).days / 365.25 for f in fechas]
    if fue_ajustado and fecha_ajuste:
        datos_filtrados = [
            (t, e) for t, e, f in zip(tiempos_anios, errores, fechas)
            if f >= fecha_ajuste
        ]
        if len(datos_filtrados) < 2:
            return {
                "recomendacion": "Con ajuste reciente, se necesitan al menos 2 calibraciones post-ajuste.",
                "intervalo_nuevo": None,
                "tipo": "warn",
                "deriva_anual": None,
                "datos_grafica": None
            }
        tiempos_anios = [d[0] for d in datos_filtrados]
        errores_calc = [d[1] for d in datos_filtrados]
        tiempos_anios = [0.0] + tiempos_anios
        errores_calc = [0.0] + errores_calc
    else:
        errores_calc = errores
    t = np.array(tiempos_anios)
    e = np.array(errores_calc)
    if len(t) < 2:
        return {
            "recomendacion": "Datos insuficientes para calcular deriva.",
            "intervalo_nuevo": None,
            "tipo": "warn",
            "deriva_anual": None,
            "datos_grafica": None
        }
    pendiente, intercepto = np.polyfit(t, e, 1)
    deriva_anual = abs(pendiente)
    limite_control = 0.80 * emp
    if deriva_anual == 0:
        return {
            "recomendacion": "No se detectó deriva entre las calibraciones. Use el intervalo recomendado por el fabricante.",
            "intervalo_nuevo": None,
            "tipo": "warn",
            "deriva_anual": 0,
            "datos_grafica": {
                "tiempos": list(t), "errores": list(e),
                "pendiente": pendiente, "intercepto": intercepto,
                "limite_control": limite_control, "emp": emp
            }
        }
    error_actual = abs(intercepto + pendiente * t[-1])
    margen = limite_control - error_actual
    if margen <= 0:
        return {
            "recomendacion": f"La deriva ({deriva_anual:.5f}/año) ya supera el 80% del EMP. Se recomienda calibración inmediata.",
            "intervalo_nuevo": None,
            "tipo": "bad",
            "deriva_anual": deriva_anual,
            "datos_grafica": {
                "tiempos": list(t), "errores": list(e),
                "pendiente": pendiente, "intercepto": intercepto,
                "limite_control": limite_control, "emp": emp
            }
        }
    intervalo = margen / deriva_anual
    return {
        "recomendacion": f"Deriva estimada: {deriva_anual:.5f}/año. El instrumento alcanzará el 80% del EMP en {intervalo:.2f} años.",
        "intervalo_nuevo": intervalo,
        "tipo": "ok",
        "deriva_anual": deriva_anual,
        "datos_grafica": {
            "tiempos": list(t), "errores": list(e),
            "pendiente": pendiente, "intercepto": intercepto,
            "limite_control": limite_control, "emp": emp
        }
    }

def grafica_escalera(error_val, emp, unidad, con_incertidumbre=False, incertidumbre=0.0):
    fig, ax = plt.subplots(figsize=(7, 4))
    fig.patch.set_facecolor("#0b2c40")
    ax.set_facecolor("#0b2c40")
    limite = 0.80 * emp
    x_centro = 0
    ax.axhspan(-emp, -limite, alpha=0.15, color="#f44336")
    ax.axhspan(-limite, limite, alpha=0.15, color="#23c057")
    ax.axhspan(limite, emp, alpha=0.15, color="#f44336")
    ax.axhline(y=emp,    color="#f44336", linestyle="--", linewidth=1.2, label=f"+EMP ({emp:.4f})")
    ax.axhline(y=-emp,   color="#f44336", linestyle="--", linewidth=1.2, label=f"−EMP (−{emp:.4f})")
    ax.axhline(y=limite, color="#ff9800", linestyle=":",  linewidth=1.2, label=f"+80% EMP ({limite:.4f})")
    ax.axhline(y=-limite,color="#ff9800", linestyle=":",  linewidth=1.2, label=f"−80% EMP (−{limite:.4f})")
    ax.axhline(y=0,      color="white",   linestyle="-",  linewidth=0.5, alpha=0.3)
    color_punto = COLOR["verde"] if abs(error_val) <= limite else ("#ff9800" if abs(error_val) <= emp else "#f44336")
    if con_incertidumbre and incertidumbre > 0:
        ax.errorbar(x_centro, error_val, yerr=incertidumbre,
                    fmt="o", color=color_punto, markersize=10,
                    capsize=6, capthick=2, elinewidth=2, label="Error ± U")
    else:
        ax.scatter(x_centro, error_val, color=color_punto, s=120, zorder=5, label="Error medio")
    ax.set_xlim(-1, 1)
    ax.set_xticks([])
    ax.set_ylabel(f"Error ({unidad})", color="white")
    ax.tick_params(colors="white")
    ax.spines[:].set_color("#2dc19733")
    ax.legend(loc="upper right", fontsize=7.5, framealpha=0.2, labelcolor="white", facecolor="#0a453c")
    ax.set_title("Evaluación — Método de Escalera", color="white", fontsize=11, pad=10)
    fig.tight_layout()
    return fig

def grafica_cartas_control(datos, unidad):
    if not datos:
        return None
    fig, ax = plt.subplots(figsize=(8, 4))
    fig.patch.set_facecolor("#0b2c40")
    ax.set_facecolor("#0b2c40")
    t = np.array(datos["tiempos"])
    e = np.array(datos["errores"])
    m = datos["pendiente"]
    b = datos["intercepto"]
    lc = datos["limite_control"]
    emp = datos["emp"]
    t_ext = np.linspace(0, max(t) * 1.5, 200)
    ax.axhspan(-emp, -lc, alpha=0.12, color="#f44336")
    ax.axhspan(-lc,   lc, alpha=0.12, color="#23c057")
    ax.axhspan( lc,  emp, alpha=0.12, color="#f44336")
    ax.axhline(y=emp,  color="#f44336", linestyle="--", lw=1.2, label=f"+EMP ({emp:.4f})")
    ax.axhline(y=-emp, color="#f44336", linestyle="--", lw=1.2, label="−EMP")
    ax.axhline(y=lc,   color="#ff9800", linestyle=":",  lw=1.2, label=f"+80% EMP ({lc:.4f})")
    ax.axhline(y=-lc,  color="#ff9800", linestyle=":",  lw=1.2, label="−80% EMP")
    ax.plot(t_ext, m * t_ext + b, color=COLOR["aqua"], lw=1.8, linestyle="-.", label="Tendencia (deriva)")
    ax.scatter(t, e, color=COLOR["verde"], s=80, zorder=5, label="Calibraciones")
    ax.plot(t, e, color=COLOR["verde"], lw=1, alpha=0.5)
    ax.set_xlabel("Tiempo desde primera calibración (años)", color="white")
    ax.set_ylabel(f"Error ({unidad})", color="white")
    ax.tick_params(colors="white")
    ax.spines[:].set_color("#2dc19733")
    ax.legend(loc="upper left", fontsize=7.5, framealpha=0.2, labelcolor="white", facecolor="#0a453c")
    ax.set_title("Cartas de Control — Deriva del error", color="white", fontsize=11, pad=10)
    fig.tight_layout()
    return fig

def mostrar_intervalos():
    aplicar_estilos()

    if "premium_activo" not in st.session_state or not st.session_state.premium_activo:
        with st.container(border=True):
            st.warning("🔒 Este módulo requiere el Plan Premium.")
            st.caption("Ve a **Acceso a Plan Premium** en el menú lateral para activarlo.")
        st.stop()

    st.markdown("""
    <div style="background: linear-gradient(135deg, #063d7d 0%, #238d93 100%);
    border-radius: 12px; padding: 1.4rem 2rem; margin-bottom: 1.5rem; color: white;">
        <h1 style="margin:0; font-size:1.6rem; color:white;">📐 Intervalos de Calibración</h1>
        <p style="margin:0.3rem 0 0; opacity:0.85; font-size:0.9rem;">
        Determinación y ajuste del intervalo de calibración según ILAC-G24 / OIML D10:2007</p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("1 · Equipo a evaluar")

    modo = st.radio(
        "Modo de ingreso:",
        ["Seleccionar equipo registrado", "Ingresar datos manualmente"],
        horizontal=True
    )

    equipo = None

    if modo == "Seleccionar equipo registrado":
        df_equipos = get_equipos()
        df_cal = get_calibraciones()

        if df_equipos.empty:
            st.warning("No hay equipos registrados. Primero agrega equipos en Ficha de equipo.")
            st.stop()

        equipos_disponibles = []
        for _, row in df_equipos.iterrows():
            cals = df_cal[df_cal["equipo_id"] == row["id"]].sort_values("fecha")
            historial = []
            for _, cal in cals.iterrows():
                historial.append({
                    "fecha": cal["fecha"],
                    "fue_ajustado": False,
                    "errores_por_punto": [
                        {"valor_nominal": 0.0, "error": cal["error"], "incertidumbre": cal["incertidumbre"]}
                    ],
                    "metodo_ic_usado": cal["metodo"],
                    "intervalo_calculado_anios": None,
                    "fecha_proxima_calibracion": cal["proximo_vencimiento"],
                    "calculado_por": cal["laboratorio"]
                })
            equipos_disponibles.append({
                "id": row["id"],
                "nombre": row["nombre"],
                "tipo": row["tipo"],
                "marca": row.get("marca", ""),
                "modelo": row.get("modelo", ""),
                "serie": row.get("numero_serie", ""),
                "unidad": row["unidad"],
                "tolerancia_emp": row["tolerancia"],
                "intervalo_fabricante_anios": 1.0,
                "area": row.get("ubicacion", ""),
                "responsable": row.get("responsable", ""),
                "clase_metrologica": "",
                "estado": row["estado"],
                "historial_calibraciones": historial
            })

        opciones = {f"[{e['id']}] {e['nombre']}": e for e in equipos_disponibles}
        seleccion = st.selectbox("Seleccione el equipo:", list(opciones.keys()))
        equipo = opciones[seleccion]

        st.markdown(f"""
        <div style="background:#0a453c33; border-left:4px solid #23c057;
        border-radius:8px; padding:0.9rem 1.2rem; margin-bottom:1rem;">
            <strong>{equipo['nombre']}</strong> &nbsp;|&nbsp;
            Tipo: {equipo.get('tipo','—')} &nbsp;|&nbsp;
            Área: {equipo.get('area','—')} &nbsp;|&nbsp;
            Estado: {equipo.get('estado','—')}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("**Parámetros del instrumento:**")
    col1, col2, col3 = st.columns(3)

    with col1:
        unidad_default = equipo.get("unidad", "") if equipo else ""
        unidad = st.text_input("Unidad de medida", value=unidad_default, placeholder="mm, kg, °C…")

    with col2:
        emp_default = equipo.get("tolerancia_emp") if equipo else None
        emp = st.number_input(
            f"Tolerancia / EMP ({unidad or 'unidad'})",
            min_value=0.0, value=float(emp_default) if emp_default else 0.02,
            format="%.5f", step=0.001
        )
        if emp <= 0:
            st.error("La tolerancia debe ser mayor que cero.")
            return

    with col3:
        fab_default = equipo.get("intervalo_fabricante_anios") if equipo else None
        intervalo_fabricante = st.number_input(
            "Intervalo fabricante (años)",
            min_value=0.1, value=float(fab_default) if fab_default else 1.0,
            format="%.2f", step=0.25
        )

    st.divider()

    st.subheader("2 · Método de evaluación")

    METODOS = {
        "Escalera — Error medio":
            "Compara el **error medio** del punto con el 80% del EMP.",
        "Escalera — Error con incertidumbre":
            "Compara el **error ± incertidumbre expandida** con el 80% del EMP.",
        "Cartas de control":
            "Analiza la **deriva del error** a lo largo de varias calibraciones. Requiere historial de al menos 2 fechas."
    }

    metodo = st.selectbox("Seleccione el método:", list(METODOS.keys()))
    st.info(METODOS[metodo])

    st.divider()

    st.subheader("3 · Datos de calibración")

    resultado_calculo = None
    fecha_cal_actual = None

    if metodo in ("Escalera — Error medio", "Escalera — Error con incertidumbre"):
        fue_ajustado = st.selectbox(
            "¿El equipo fue ajustado mecánicamente en la última calibración?",
            ["No", "Sí"]
        ) == "Sí"

        col_a, col_b = st.columns(2)
        with col_a:
            fecha_cal_ant = st.date_input("Fecha calibración anterior",
                                          value=date.today().replace(year=date.today().year - 1))
        with col_b:
            fecha_cal_actual = st.date_input("Fecha calibración actual (vigente)", value=date.today())

        if fecha_cal_actual <= fecha_cal_ant:
            st.error("La fecha actual debe ser posterior a la anterior.")
            return

        intervalo_anterior = calcular_intervalo_anios(fecha_cal_ant, fecha_cal_actual)
        st.caption(f"Intervalo anterior calculado: **{intervalo_anterior:.3f} años**")

        error_medio = st.number_input(
            f"Error medio del punto ({unidad})",
            value=0.01, format="%.5f", step=0.001
        )

        incertidumbre = 0.0
        if metodo == "Escalera — Error con incertidumbre":
            incertidumbre = st.number_input(
                f"Incertidumbre expandida U ({unidad})",
                min_value=0.0, value=0.002, format="%.5f", step=0.001
            )

        if st.button("Calcular intervalo", type="primary"):
            if metodo == "Escalera — Error medio":
                resultado_calculo = escalera_error_medio(error_medio, emp, intervalo_anterior, fue_ajustado)
                fig = grafica_escalera(error_medio, emp, unidad or "unidad")
            else:
                resultado_calculo = escalera_error_incertidumbre(error_medio, incertidumbre, emp, intervalo_anterior, fue_ajustado)
                fig = grafica_escalera(error_medio, emp, unidad or "unidad",
                                       con_incertidumbre=True, incertidumbre=incertidumbre)

            st.session_state["ic_resultado"] = resultado_calculo
            st.session_state["ic_fecha_base"] = fecha_cal_actual
            st.session_state["ic_metodo"] = metodo
            st.session_state["ic_fig"] = fig

    else:
        fue_ajustado_cc = st.selectbox(
            "¿El equipo fue ajustado en alguna de las calibraciones del historial?",
            ["No", "Sí"]
        ) == "Sí"

        fecha_ajuste_cc = None
        if fue_ajustado_cc:
            fecha_ajuste_cc = st.date_input("Fecha del ajuste mecánico")

        n_puntos = st.number_input("Cantidad de puntos críticos a evaluar",
                                    min_value=1, max_value=10, value=1, step=1)
        n_fechas = st.number_input("Cantidad de calibraciones en el historial",
                                    min_value=2, max_value=20, value=3, step=1)

        st.markdown("**Fechas de calibración:**")
        fechas_cc = []
        cols_fechas = st.columns(min(int(n_fechas), 4))
        for i in range(int(n_fechas)):
            with cols_fechas[i % 4]:
                default_f = date.today().replace(year=date.today().year - int(n_fechas) + i)
                f = st.date_input(f"Fecha {i+1}", value=default_f, key=f"cc_fecha_{i}")
                fechas_cc.append(f)

        if fechas_cc != sorted(fechas_cc):
            st.error("Las fechas deben estar en orden cronológico.")
            return

        fecha_cal_actual = fechas_cc[-1]

        st.markdown("**Errores por punto crítico:**")
        errores_por_punto = []

        for p in range(int(n_puntos)):
            with st.expander(f"Punto {p+1}", expanded=(p == 0)):
                val_nominal = st.number_input(
                    f"Valor nominal P{p+1} ({unidad})",
                    min_value=0.0001, value=10.0, format="%.4f", key=f"vn_{p}"
                )
                errores_p = []
                for i, f in enumerate(fechas_cc):
                    es_ajuste = fue_ajustado_cc and fecha_ajuste_cc and f == fecha_ajuste_cc
                    if es_ajuste:
                        st.caption(f"  Fecha {i+1} ({f}) — Ajuste: error = 0.00000 (automático)")
                        errores_p.append(0.0)
                    else:
                        err = st.number_input(
                            f"Error en {f} ({unidad})",
                            value=0.0, format="%.5f", step=0.001, key=f"err_{p}_{i}"
                        )
                        errores_p.append(err)
                errores_por_punto.append({"nominal": val_nominal, "errores": errores_p})

        if st.button("Calcular intervalo", type="primary"):
            resultados_puntos = []
            for p_data in errores_por_punto:
                res = cartas_control(fechas_cc, p_data["errores"], emp, fue_ajustado_cc, fecha_ajuste_cc)
                resultados_puntos.append({"nominal": p_data["nominal"], **res})

            intervalos_validos = [r["intervalo_nuevo"] for r in resultados_puntos if r["intervalo_nuevo"] is not None]

            if intervalos_validos:
                intervalo_final = min(intervalos_validos)
                tipo_final = "ok"
            else:
                intervalo_final = None
                tipo_final = "bad" if any(r["tipo"] == "bad" for r in resultados_puntos) else "warn"

            resultado_calculo = {
                "recomendacion": f"Intervalo más restrictivo entre {int(n_puntos)} punto(s): {intervalo_final:.2f} años." if intervalo_final else "No se pudo calcular un intervalo válido.",
                "intervalo_nuevo": intervalo_final,
                "tipo": tipo_final,
                "por_punto": resultados_puntos
            }

            if resultados_puntos and resultados_puntos[0].get("datos_grafica"):
                fig = grafica_cartas_control(resultados_puntos[0]["datos_grafica"], unidad or "unidad")
            else:
                fig = None

            st.session_state["ic_resultado"] = resultado_calculo
            st.session_state["ic_fecha_base"] = fecha_cal_actual
            st.session_state["ic_metodo"] = metodo
            st.session_state["ic_fig"] = fig

    if "ic_resultado" in st.session_state and st.session_state["ic_resultado"]:
        st.divider()
        st.subheader("4 · Resultados")

        res = st.session_state["ic_resultado"]
        fig_res = st.session_state.get("ic_fig")
        fecha_base = st.session_state.get("ic_fecha_base")
        met_usado = st.session_state.get("ic_metodo", metodo)

        color_box = {"ok": "#23c05722", "warn": "#ff980022", "bad": "#f4433622"}.get(res["tipo"], "#ff980022")
        border_box = {"ok": "#23c057", "warn": "#ff9800", "bad": "#f44336"}.get(res["tipo"], "#ff9800")
        icono = {"ok": "✅", "warn": "⚠️", "bad": "🚨"}.get(res["tipo"], "ℹ️")

        st.markdown(f"""
        <div style="background:{color_box}; border-left:4px solid {border_box};
        border-radius:10px; padding:1rem 1.4rem; margin-top:0.8rem;">
            <strong>{icono} {res['recomendacion']}</strong>
        </div>
        """, unsafe_allow_html=True)

        if res["intervalo_nuevo"] is not None and fecha_base:
            intervalo_r = res["intervalo_nuevo"]
            fecha_proxima = fecha_desde_intervalo(fecha_base, intervalo_r)
            col_r1, col_r2 = st.columns(2)
            col_r1.metric("Intervalo recomendado", f"{intervalo_r:.2f} años")
            col_r2.metric("Próxima calibración", fecha_proxima.strftime("%d/%m/%Y"))

        if res.get("por_punto"):
            st.markdown("**Detalle por punto:**")
            filas = []
            for p in res["por_punto"]:
                filas.append({
                    "Nominal": p["nominal"],
                    "Deriva/año": f"{p.get('deriva_anual', 0):.5f}" if p.get("deriva_anual") else "—",
                    "IC recomendado (años)": f"{p['intervalo_nuevo']:.2f}" if p["intervalo_nuevo"] else "—",
                    "Estado": {"ok": "✅ OK", "warn": "⚠️ Atención", "bad": "🚨 Crítico"}.get(p["tipo"], "—")
                })
            st.dataframe(pd.DataFrame(filas), use_container_width=True)

        if fig_res:
            st.markdown("**Visualización:**")
            st.pyplot(fig_res)
            plt.close(fig_res)

        st.divider()
        st.subheader("5 · Exportar reporte")

        if res["intervalo_nuevo"] is not None and fecha_base:
            fecha_proxima = fecha_desde_intervalo(fecha_base, res["intervalo_nuevo"])
            reporte_txt = f"""REPORTE DE INTERVALO DE CALIBRACIÓN
====================================
Equipo       : {equipo['nombre'] if equipo else 'Ingreso manual'}
ID           : {equipo['id'] if equipo else '—'}
Unidad       : {unidad}
EMP          : {emp}
Método       : {met_usado}
Fecha cálculo: {date.today().strftime('%d/%m/%Y')}

RESULTADO
---------
Intervalo recomendado : {res['intervalo_nuevo']:.2f} años
Próxima calibración   : {fecha_proxima.strftime('%d/%m/%Y')}
Recomendación         : {res['recomendacion']}

Generado por MetriCore — Módulo de Intervalos de Calibración (ILAC-G24)
"""
            st.download_button(
                label="📄 Descargar reporte (.txt)",
                data=reporte_txt,
                file_name=f"IC_{equipo['id'] if equipo else 'manual'}_{date.today()}.txt",
                mime="text/plain"
            )

        if equipo and equipo.get("historial_calibraciones"):
            st.divider()
            st.subheader("6 · Historial de calibraciones")
            hist = equipo["historial_calibraciones"]
            filas_hist = []
            for h in hist:
                filas_hist.append({
                    "Fecha": h.get("fecha", "—"),
                    "Método IC": h.get("metodo_ic_usado") or "—",
                    "IC calculado (años)": h.get("intervalo_calculado_anios") or "—",
                    "Próxima calibración": h.get("fecha_proxima_calibracion") or "—",
                    "Registrado por": h.get("calculado_por", "—")
                })
            st.dataframe(pd.DataFrame(filas_hist), use_container_width=True)


mostrar_intervalos()