# -*- coding: utf-8 -*-
"""
Sistema de Gestión de Estacionamiento Vehicular Universitario
Interfaces interactivas (Dash) para cada Caso de Uso especificado:

CU-00 Registrar Usuario y Vehículo en el Sistema
CU-01 Registrar Ingreso de Vehículo
CU-02 Registrar Salida de Vehículo
CU-03 Generar Reportes en Tiempo Real
CU-04 Consultar Disponibilidad de Estacionamiento
CU-05 Actualizar Panel de Disponibilidad en Tiempo Real
CU-06 Asignar Espacio Reservado por Tipo de Usuario
CU-07 Dirigir y Restringir Acceso a Zonas Asignadas
CU-08 Validar Estado de Pago de Reserva
CU-09 Restringir Acceso por Mora o Pago No Registrado

Ejecutar con:  python app.py
Luego abrir:   http://127.0.0.1:8050
"""

import random
from datetime import datetime

import dash
import dash_bootstrap_components as dbc
import plotly.express as px
from dash import Input, Output, State, dcc, html, dash_table, ctx, no_update

# ---------------------------------------------------------------------------
# "BASE DE DATOS" EN MEMORIA (simulada, para fines de demostración académica)
# ---------------------------------------------------------------------------

ZONAS = ["Docentes", "Administrativos", "Estudiantes Reserva", "General", "Visitantes"]

TIPO_A_ZONA = {
    "Docente": "Docentes",
    "Administrativo": "Administrativos",
    "Estudiante Reserva": "Estudiantes Reserva",
    "Estudiante": "General",
    "Visitante": "Visitantes",
}


def construir_espacios():
    espacios = []
    config = [
        ("Docentes", "D", 6, "reservado"),
        ("Administrativos", "A", 6, "reservado"),
        ("Estudiantes Reserva", "ER", 8, "reservado"),
        ("General", "G", 20, "general"),
        ("Visitantes", "V", 6, "general"),
    ]
    for zona, prefijo, cantidad, tipo in config:
        for i in range(1, cantidad + 1):
            espacios.append(
                {
                    "id": f"{prefijo}-{i:02d}",
                    "zona": zona,
                    "tipo": tipo,
                    "estado": "libre",
                    "asignado_a": None,
                }
            )
    # Pre-ocupar algunos espacios al azar para que la demo se vea realista
    random.seed(7)
    for e in espacios:
        if random.random() < 0.25:
            e["estado"] = "ocupado"
    return espacios


def construir_usuarios():
    return {
        "AB1234": {"nombre": "Prof. Elena Ríos", "tipo_usuario": "Docente",
                   "reserva": True, "zona_reservada": "Docentes", "cedula": "8-101-1111"},
        "CD5678": {"nombre": "Marcos Gil (Adm.)", "tipo_usuario": "Administrativo",
                   "reserva": True, "zona_reservada": "Administrativos", "cedula": "8-202-2222"},
        "EF9012": {"nombre": "Ana Pérez", "tipo_usuario": "Estudiante Reserva",
                   "reserva": True, "zona_reservada": "Estudiantes Reserva", "cedula": "8-303-3333"},
        "GH3456": {"nombre": "Luis Bravo", "tipo_usuario": "Estudiante",
                   "reserva": False, "zona_reservada": None, "cedula": "8-404-4444"},
        "IJ7890": {"nombre": "Carla Núñez (Adm.)", "tipo_usuario": "Administrativo",
                   "reserva": True, "zona_reservada": "Administrativos", "cedula": "8-505-5555"},
        "KL1122": {"nombre": "Prof. Iván Soto", "tipo_usuario": "Docente",
                   "reserva": True, "zona_reservada": "Docentes", "cedula": "8-606-6666"},
    }


def construir_pagos():
    return {
        "AB1234": "Al día",
        "CD5678": "Moroso",
        "EF9012": "No registrado",
        "IJ7890": "Al día",
        "KL1122": "Moroso",
    }


# ---------------------------------------------------------------------------
# Actor secundario de CU-00: Servicio Institucional de la UTP (simulado)
# Este "directorio" representa la fuente externa que valida identidad y
# categoría (Estudiante, Docente, Administrativo). El SAE nunca escribe aquí,
# solo consulta: la categoría jamás debe ser editable manualmente por el usuario.
# ---------------------------------------------------------------------------

INSTITUCIONAL_DIRECTORIO = {
    "8-101-1111": {"nombre": "Prof. Elena Ríos", "tipo_usuario": "Docente"},
    "8-202-2222": {"nombre": "Marcos Gil", "tipo_usuario": "Administrativo"},
    "8-303-3333": {"nombre": "Ana Pérez", "tipo_usuario": "Estudiante Reserva"},
    "8-404-4444": {"nombre": "Luis Bravo", "tipo_usuario": "Estudiante"},
    "8-505-5555": {"nombre": "Carla Núñez", "tipo_usuario": "Administrativo"},
    "8-606-6666": {"nombre": "Prof. Iván Soto", "tipo_usuario": "Docente"},
    "8-707-7777": {"nombre": "Sofía Cruz", "tipo_usuario": "Estudiante"},
    "8-808-8888": {"nombre": "Diego Ruiz", "tipo_usuario": "Docente"},
}

LIMITE_VEHICULOS_POR_USUARIO = 3  # límite institucional (flujo alterno A1)


def construir_perfiles(usuarios):
    """Construye los perfiles institucionales (CU-00): un perfil por cada
    usuario del directorio de la UTP, con la lista de vehículos asociados.
    Se pre-cargan algunos vehículos de demo para que CU-01/CU-06/etc. tengan
    datos con los que trabajar desde el inicio."""
    perfiles = {
        cedula: {"nombre": info["nombre"], "tipo_usuario": info["tipo_usuario"], "vehiculos": []}
        for cedula, info in INSTITUCIONAL_DIRECTORIO.items()
    }
    for placa, u in usuarios.items():
        cedula = u.get("cedula")
        if cedula in perfiles:
            perfiles[cedula]["vehiculos"].append(
                {"placa": placa, "marca": "N/D", "modelo": "N/D", "color": "N/D",
                 "fecha_registro": "Registro inicial (demo)"}
            )
    return perfiles


_usuarios_iniciales = construir_usuarios()

DB = {
    "espacios": construir_espacios(),
    "usuarios": _usuarios_iniciales,
    "perfiles": construir_perfiles(_usuarios_iniciales),       # CU-00
    "pendientes_validacion": [],                                 # CU-00 (E2)
    "pagos": construir_pagos(),
    "registros": [],   # ingresos / salidas
    "incidentes": [],  # accesos no autorizados, etc.
    "reloj": datetime.now(),
}


def reset_all():
    usuarios = construir_usuarios()
    DB["espacios"] = construir_espacios()
    DB["usuarios"] = usuarios
    DB["perfiles"] = construir_perfiles(usuarios)
    DB["pendientes_validacion"] = []
    DB["pagos"] = construir_pagos()
    DB["registros"] = []
    DB["incidentes"] = []


def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def vehiculos_dentro():
    return [r for r in DB["registros"] if r["estado"] == "dentro"]


def espacio_por_id(eid):
    for e in DB["espacios"]:
        if e["id"] == eid:
            return e
    return None


def liberar_espacio_de(placa):
    for e in DB["espacios"]:
        if e["asignado_a"] == placa:
            e["estado"] = "libre"
            e["asignado_a"] = None


def log_incidente(tipo, placa, detalle):
    DB["incidentes"].append({"tipo": tipo, "placa": placa, "detalle": detalle, "fecha_hora": ahora()})


# ---------------------------------------------------------------------------
# APP
# ---------------------------------------------------------------------------

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY, "https://use.fontawesome.com/releases/v5.15.4/css/all.css"],
    suppress_callback_exceptions=True,
    title="Estacionamiento UTP",
)
server = app.server

MENU = [
    ("/", "Inicio", "fa-home"),
    ("/cu00", "CU-00 Registrar Usuario/Vehículo", "fa-id-card"),
    ("/cu01", "CU-01 Registrar Ingreso", "fa-sign-in-alt"),
    ("/cu02", "CU-02 Registrar Salida", "fa-sign-out-alt"),
    ("/cu03", "CU-03 Reportes en Tiempo Real", "fa-chart-bar"),
    ("/cu04", "CU-04 Consultar Disponibilidad", "fa-search-location"),
    ("/cu05", "CU-05 Panel en Tiempo Real", "fa-satellite-dish"),
    ("/cu06", "CU-06 Asignar Espacio Reservado", "fa-parking"),
    ("/cu07", "CU-07 Dirigir / Restringir Zonas", "fa-directions"),
    ("/cu08", "CU-08 Validar Estado de Pago", "fa-money-check-alt"),
    ("/cu09", "CU-09 Restringir por pago no registrado", "fa-ban"),
]

sidebar = html.Div(
    [
        html.Div(
            [
                html.I(className="fas fa-car-side me-2"),
                html.Span("Estacionamiento UTP", style={"fontWeight": "700"}),
            ],
            className="d-flex align-items-center mb-3",
        ),
        html.Hr(),
        dbc.Nav(
            [
                dbc.NavLink(
                    [html.I(className=f"fas {icon} me-2"), label],
                    href=href,
                    active="exact",
                )
                for href, label, icon in MENU
            ],
            vertical=True,
            pills=True,
        ),
        html.Hr(),
        dbc.Button(
            [html.I(className="fas fa-undo me-2"), "Reiniciar datos de demo"],
            id="btn-reset-global",
            color="secondary",
            outline=True,
            size="sm",
            className="w-100",
        ),
        html.Div(id="reset-global-msg", className="small text-muted mt-2"),
    ],
    style={
        "position": "fixed",
        "top": 0,
        "left": 0,
        "bottom": 0,
        "width": "270px",
        "padding": "1.2rem",
        "backgroundColor": "#f8f9fa",
        "overflowY": "auto",
        "borderRight": "1px solid #dee2e6",
    },
)

content = html.Div(
    id="page-content",
    style={"marginLeft": "290px", "padding": "1.5rem 2rem", "maxWidth": "1200px"},
)

app.layout = html.Div([dcc.Location(id="url"), sidebar, content])


# ---------------------------------------------------------------------------
# HELPERS DE UI COMPARTIDOS
# ---------------------------------------------------------------------------

def page_header(codigo, titulo, descripcion):
    return html.Div(
        [
            html.H4([dbc.Badge(codigo, color="primary", className="me-2"), titulo]),
            html.P(descripcion, className="text-muted"),
            html.Hr(),
        ]
    )


def badge_estado(estado):
    colores = {
        "libre": "success",
        "ocupado": "danger",
        "desconocido": "secondary",
        "sensor con falla": "warning",
        "Al día": "success",
        "Moroso": "danger",
        "No registrado": "secondary",
        "no verificado": "warning",
        "dentro": "success",
        "fuera": "secondary",
    }
    return dbc.Badge(estado, color=colores.get(estado, "secondary"), className="me-1")


def tabla_registros():
    regs = DB["registros"]
    if not regs:
        return dbc.Alert("Aún no hay registros de ingreso/salida.", color="light")
    rows = []
    for r in reversed(regs[-15:]):
        rows.append(
            html.Tr(
                [
                    html.Td(r["placa"]),
                    html.Td(r["tipo_usuario"]),
                    html.Td(r["hora_entrada"]),
                    html.Td(r.get("hora_salida") or "—"),
                    html.Td(badge_estado(r["estado"])),
                ]
            )
        )
    return dbc.Table(
        [html.Thead(html.Tr([html.Th("Placa"), html.Th("Tipo Usuario"), html.Th("Entrada"),
                              html.Th("Salida"), html.Th("Estado")]))]
        + [html.Tbody(rows)],
        bordered=True, hover=True, striped=True, size="sm",
    )


def obtener_categoria_institucional(cedula):
    """Simula la llamada al Servicio Institucional de la UTP (actor secundario
    de CU-00). Devuelve None si la cédula no existe en el directorio."""
    return INSTITUCIONAL_DIRECTORIO.get(cedula)


def placa_pertenece_a_otro(cedula, placa):
    """Recorre todos los perfiles (paso 4 del flujo básico de CU-00) y
    devuelve la cédula del dueño si la placa ya está asociada a OTRO usuario."""
    for ced, perfil in DB["perfiles"].items():
        if ced == cedula:
            continue
        if any(v["placa"] == placa for v in perfil["vehiculos"]):
            return ced
    return None


def badge_categoria(categoria):
    colores = {
        "Docente": "primary",
        "Administrativo": "info",
        "Estudiante Reserva": "warning",
        "Estudiante": "secondary",
    }
    return dbc.Badge(categoria, color=colores.get(categoria, "secondary"), className="ms-1")


def tabla_vehiculos_perfil(cedula):
    perfil = DB["perfiles"].get(cedula)
    if not perfil or not perfil["vehiculos"]:
        return dbc.Alert("Este usuario institucional aún no tiene vehículos registrados.", color="light")
    rows = [
        html.Tr([html.Td(v["placa"]), html.Td(v["marca"]), html.Td(v["modelo"]),
                 html.Td(v["color"]), html.Td(v["fecha_registro"])])
        for v in perfil["vehiculos"]
    ]
    return dbc.Table(
        [html.Thead(html.Tr([html.Th("Placa"), html.Th("Marca"), html.Th("Modelo"),
                              html.Th("Color"), html.Th("Registrado")]))]
        + [html.Tbody(rows)],
        bordered=True, hover=True, striped=True, size="sm",
    )


def opciones_vehiculo_select(perfil):
    return [{"label": "➕ Registrar nuevo vehículo", "value": "__nuevo__"}] + [
        {"label": f"{v['placa']} — {v['marca']} {v['modelo']}", "value": v["placa"]}
        for v in perfil["vehiculos"]
    ]


# ===========================================================================
# CU-00 — REGISTRAR USUARIO Y VEHÍCULO EN EL SISTEMA
# ===========================================================================

def layout_cu00():
    opciones_usuarios = [
        {"label": f"{cedula} — {info['nombre']} ({info['tipo_usuario']})", "value": cedula}
        for cedula, info in INSTITUCIONAL_DIRECTORIO.items()
    ]
    return html.Div(
        [
            page_header(
                "CU-00", "Registrar Usuario y Vehículo en el Sistema",
                "Asocia el vehículo (placa) de un usuario institucional a su perfil dentro del SAE, "
                "consultando su categoría en el Servicio Institucional de la UTP (actor secundario), "
                "para que sea reconocido automáticamente en accesos futuros (CU-01) sin ser tratado "
                "como visitante.",
            ),
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H6("Paso 1 — Identificar usuario institucional"),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Label("Cuenta institucional (UTP)"),
                                        dcc.Dropdown(
                                            id="cu00-cedula", options=opciones_usuarios,
                                            placeholder="Seleccione su cuenta institucional",
                                        ),
                                    ],
                                    md=6,
                                ),
                                dbc.Col(
                                    [
                                        dbc.Label("Simulación"),
                                        dbc.Checklist(
                                            options=[{"label": "Simular falla del Servicio Institucional (E2)", "value": "e2"}],
                                            id="cu00-chk-e2", switch=True,
                                        ),
                                    ],
                                    md=6,
                                ),
                            ],
                            className="mb-3",
                        ),
                        dbc.Button(
                            [html.I(className="fas fa-id-badge me-2"), "Consultar categoría"],
                            id="cu00-btn-consultar", color="info",
                        ),
                        html.Div(id="cu00-perfil-info", className="mt-3"),
                    ]
                ),
                className="mb-4",
            ),
            html.Div(id="cu00-form-vehiculo"),
            html.Hr(),
            html.H6("Vehículos registrados del usuario seleccionado"),
            html.Div(id="cu00-tabla-vehiculos"),
        ]
    )


@app.callback(
    Output("cu00-perfil-info", "children"),
    Output("cu00-form-vehiculo", "children"),
    Output("cu00-tabla-vehiculos", "children"),
    Input("cu00-btn-consultar", "n_clicks"),
    State("cu00-cedula", "value"),
    State("cu00-chk-e2", "value"),
    prevent_initial_call=True,
)
def cu00_consultar(n, cedula, e2):
    if not cedula:
        return dbc.Alert("Seleccione una cuenta institucional.", color="danger"), html.Div(), html.Div()

    # E2: falla en la validación con el servicio institucional
    if e2 and "e2" in e2:
        DB["pendientes_validacion"].append({"cedula": cedula, "fecha_hora": ahora()})
        return (
            dbc.Alert(
                [
                    html.B("E2 — Falla en la validación con el Servicio Institucional. "),
                    "La solicitud se guardó como 'pendiente de validación' y el sistema reintentará "
                    "automáticamente al restablecerse la conexión.",
                ],
                color="danger",
            ),
            html.Div(),
            tabla_vehiculos_perfil(cedula),
        )

    # Paso 3 del flujo básico: consultar identidad y categoría (actor secundario)
    info = obtener_categoria_institucional(cedula)
    if not info:
        return dbc.Alert("No se encontró esta cuenta en el Servicio Institucional de la UTP.", color="danger"), html.Div(), html.Div()

    if cedula not in DB["perfiles"]:
        DB["perfiles"][cedula] = {"nombre": info["nombre"], "tipo_usuario": info["tipo_usuario"], "vehiculos": []}
    perfil = DB["perfiles"][cedula]

    perfil_info = dbc.Alert(
        [
            html.B(f"{perfil['nombre']} "),
            "— categoría validada por el Servicio Institucional: ",
            badge_categoria(perfil["tipo_usuario"]),
            html.Span(" (no editable manualmente).", className="text-muted ms-1"),
        ],
        color="success",
    )

    form = dbc.Card(
        dbc.CardBody(
            [
                html.H6("Paso 2 — Datos del vehículo"),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Vehículo (elija 'nuevo' o uno existente para A2)"),
                                dcc.Dropdown(
                                    id="cu00-vehiculo-select",
                                    options=opciones_vehiculo_select(perfil),
                                    value="__nuevo__", clearable=False,
                                ),
                            ],
                            md=6,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Simulación"),
                                dbc.Checklist(
                                    options=[{"label": "Simular placa ya registrada por otro usuario (E1)", "value": "e1"}],
                                    id="cu00-chk-e1", switch=True,
                                ),
                            ],
                            md=6,
                        ),
                    ],
                    className="mb-3",
                ),
                dbc.Row(
                    [
                        dbc.Col([dbc.Label("Placa"), dbc.Input(id="cu00-placa", placeholder="Ej. MN4455")], md=3),
                        dbc.Col([dbc.Label("Marca"), dbc.Input(id="cu00-marca", placeholder="Ej. Toyota")], md=3),
                        dbc.Col([dbc.Label("Modelo"), dbc.Input(id="cu00-modelo", placeholder="Ej. Corolla")], md=3),
                        dbc.Col([dbc.Label("Color"), dbc.Input(id="cu00-color", placeholder="Ej. Gris")], md=3),
                    ],
                    className="mb-3",
                ),
                dbc.Button(
                    [html.I(className="fas fa-save me-2"), "Registrar / Actualizar vehículo"],
                    id="cu00-btn-guardar", color="success",
                ),
                html.Div(id="cu00-resultado", className="mt-3"),
            ]
        ),
        className="mb-4",
    )

    return perfil_info, form, tabla_vehiculos_perfil(cedula)


@app.callback(
    Output("cu00-placa", "value"),
    Output("cu00-marca", "value"),
    Output("cu00-modelo", "value"),
    Output("cu00-color", "value"),
    Input("cu00-vehiculo-select", "value"),
    State("cu00-cedula", "value"),
    prevent_initial_call=True,
)
def cu00_precargar_vehiculo(seleccion, cedula):
    # A2: si el usuario elige un vehículo existente, se precargan sus datos
    if not cedula or not seleccion or seleccion == "__nuevo__":
        return "", "", "", ""
    perfil = DB["perfiles"].get(cedula, {})
    for v in perfil.get("vehiculos", []):
        if v["placa"] == seleccion:
            return v["placa"], v["marca"], v["modelo"], v["color"]
    return "", "", "", ""


@app.callback(
    Output("cu00-resultado", "children"),
    Output("cu00-tabla-vehiculos", "children"),
    Output("cu00-vehiculo-select", "options"),
    Output("cu00-vehiculo-select", "value"),
    Input("cu00-btn-guardar", "n_clicks"),
    State("cu00-cedula", "value"),
    State("cu00-vehiculo-select", "value"),
    State("cu00-placa", "value"),
    State("cu00-marca", "value"),
    State("cu00-modelo", "value"),
    State("cu00-color", "value"),
    State("cu00-chk-e1", "value"),
    prevent_initial_call=True,
)
def cu00_guardar(n, cedula, seleccion, placa, marca, modelo, color, e1):
    if not cedula or cedula not in DB["perfiles"]:
        return dbc.Alert("Primero consulte la categoría del usuario en el Paso 1.", color="danger"), no_update, no_update, no_update
    if not placa or not placa.strip():
        return dbc.Alert("Debe indicar la placa del vehículo.", color="danger"), tabla_vehiculos_perfil(cedula), no_update, no_update

    placa = placa.strip().upper()
    perfil = DB["perfiles"][cedula]
    es_edicion = bool(seleccion) and seleccion != "__nuevo__"

    # E1: placa ya asociada a otro perfil (real, o forzada con el switch de demo)
    dueno = placa_pertenece_a_otro(cedula, placa)
    forzar_e1 = bool(e1) and "e1" in e1
    if (dueno and (not es_edicion or dueno != cedula)) or forzar_e1:
        nombre_otro = DB["perfiles"].get(dueno, {}).get("nombre") if dueno else "otro usuario (simulado)"
        return (
            dbc.Alert(
                [
                    html.B("E1 — Placa ya registrada: "),
                    f"la placa {placa} ya está asociada a {nombre_otro}. Verifique el número de placa "
                    "o contacte al Administrador del SAE.",
                ],
                color="danger",
            ),
            tabla_vehiculos_perfil(cedula), no_update, no_update,
        )

    if es_edicion:
        # A2: actualización de datos de un vehículo ya registrado
        vehiculo = next((v for v in perfil["vehiculos"] if v["placa"] == seleccion), None)
        if vehiculo is None:
            return dbc.Alert("El vehículo seleccionado ya no existe.", color="danger"), tabla_vehiculos_perfil(cedula), no_update, no_update
        placa_anterior = vehiculo["placa"]
        if placa_anterior != placa and placa_anterior in DB["usuarios"]:
            del DB["usuarios"][placa_anterior]
        vehiculo.update({"placa": placa, "marca": marca or "N/D", "modelo": modelo or "N/D", "color": color or "N/D"})
        mensaje = f"Datos del vehículo {placa} actualizados correctamente (A2)."
    else:
        # A1 / flujo básico: registrar un vehículo (adicional o el primero)
        if len(perfil["vehiculos"]) >= LIMITE_VEHICULOS_POR_USUARIO:
            return (
                dbc.Alert(
                    f"Se alcanzó el límite institucional de {LIMITE_VEHICULOS_POR_USUARIO} vehículos por usuario.",
                    color="warning",
                ),
                tabla_vehiculos_perfil(cedula), no_update, no_update,
            )
        perfil["vehiculos"].append(
            {"placa": placa, "marca": marca or "N/D", "modelo": modelo or "N/D", "color": color or "N/D",
             "fecha_registro": ahora()}
        )
        mensaje = f"Vehículo {placa} registrado y asociado exitosamente al perfil de {perfil['nombre']}."

    # Sincroniza con el mapa global de CU-01, para reconocimiento automático futuro
    reserva = perfil["tipo_usuario"] in ("Docente", "Administrativo", "Estudiante Reserva")
    DB["usuarios"][placa] = {
        "nombre": perfil["nombre"],
        "tipo_usuario": perfil["tipo_usuario"],
        "reserva": reserva,
        "zona_reservada": TIPO_A_ZONA.get(perfil["tipo_usuario"]) if reserva else None,
        "cedula": cedula,
    }

    return (
        dbc.Alert([html.B("Registro exitoso. "), mensaje], color="success"),
        tabla_vehiculos_perfil(cedula),
        opciones_vehiculo_select(perfil),
        placa,
    )


# ===========================================================================
# CU-01 — REGISTRAR INGRESO DE VEHÍCULO
# ===========================================================================

def layout_cu01():
    return html.Div(
        [
            page_header("CU-01", "Registrar Ingreso de Vehículo",
                        "El Sistema de Reconocimiento de Placas (ANPR) o el guardia registran "
                        "la entrada de un vehículo, identifican el tipo de usuario y autorizan la barrera."),
            dbc.Card(
                dbc.CardBody(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Label("Placa del vehículo"),
                                        dbc.Input(id="cu01-placa", placeholder="Ej. AB1234", type="text"),
                                    ],
                                    md=4,
                                ),
                                dbc.Col(
                                    [
                                        dbc.Label("Acciones"),
                                        html.Div(
                                            dbc.Button(
                                                [html.I(className="fas fa-camera me-2"), "Simular lectura ANPR"],
                                                id="cu01-btn-anpr", color="info", className="me-2",
                                            )
                                        ),
                                    ],
                                    md=4,
                                ),
                                dbc.Col(
                                    [
                                        dbc.Checklist(
                                            options=[{"label": "Fallo de cámara (A1: digitar manualmente)", "value": "fallo"}],
                                            id="cu01-chk-fallo", switch=True,
                                        ),
                                        dbc.Checklist(
                                            options=[{"label": "Simular falla de conexión con BD (E1)", "value": "e1"}],
                                            id="cu01-chk-e1", switch=True, className="mt-2",
                                        ),
                                    ],
                                    md=4,
                                ),
                            ],
                            className="mb-3",
                        ),
                        html.Div(id="cu01-visitante-form"),
                        dbc.Button(
                            [html.I(className="fas fa-check me-2"), "Registrar Ingreso"],
                            id="cu01-btn-registrar", color="success",
                        ),
                        html.Div(id="cu01-resultado", className="mt-3"),
                    ]
                ),
                className="mb-4",
            ),
            html.H5("Vehículos actualmente dentro del campus"),
            html.Div(id="cu01-tabla", children=tabla_registros()),
        ]
    )


@app.callback(Output("cu01-placa", "value"), Input("cu01-btn-anpr", "n_clicks"), prevent_initial_call=True)
def cu01_simular_anpr(n):
    # A veces simula una placa registrada, a veces una desconocida (visitante)
    placas = list(DB["usuarios"].keys()) + ["ZZ0000", "QQ9999"]
    return random.choice(placas)


@app.callback(
    Output("cu01-visitante-form", "children"),
    Input("cu01-placa", "value"),
)
def cu01_mostrar_form_visitante(placa):
    if placa and placa.strip().upper() not in DB["usuarios"]:
        return dbc.Card(
            dbc.CardBody(
                [
                    dbc.Alert(
                        "Placa no encontrada en la base de datos (A2). Ingrese los datos del visitante.",
                        color="warning",
                    ),
                    dbc.Row(
                        [
                            dbc.Col(dbc.Input(id="cu01-vis-nombre", placeholder="Nombre completo"), md=4),
                            dbc.Col(dbc.Input(id="cu01-vis-cedula", placeholder="Cédula"), md=4),
                            dbc.Col(dbc.Input(id="cu01-vis-motivo", placeholder="Motivo de la visita"), md=4),
                        ]
                    ),
                ]
            ),
            className="mb-3 border-warning",
        )
    return html.Div(
        [dbc.Input(id="cu01-vis-nombre", style={"display": "none"}),
         dbc.Input(id="cu01-vis-cedula", style={"display": "none"}),
         dbc.Input(id="cu01-vis-motivo", style={"display": "none"})]
    )


@app.callback(
    Output("cu01-resultado", "children"),
    Output("cu01-tabla", "children"),
    Input("cu01-btn-registrar", "n_clicks"),
    State("cu01-placa", "value"),
    State("cu01-chk-fallo", "value"),
    State("cu01-chk-e1", "value"),
    State("cu01-vis-nombre", "value"),
    State("cu01-vis-cedula", "value"),
    State("cu01-vis-motivo", "value"),
    prevent_initial_call=True,
)
def cu01_registrar(n, placa, fallo, e1, vis_nombre, vis_cedula, vis_motivo):
    if not placa:
        return dbc.Alert("Debe indicar o capturar una placa.", color="danger"), tabla_registros()
    placa = placa.strip().upper()

    if e1:
        return (
            dbc.Alert(
                [html.B("E1 — Falla de conexión con la BD: "),
                 "el guardia habilita registro manual en modo local (offline). "
                 "Los datos se sincronizarán al restablecerse la conexión."],
                color="warning",
            ),
            tabla_registros(),
        )

    # E2: ingreso duplicado
    if any(r["placa"] == placa and r["estado"] == "dentro" for r in DB["registros"]):
        log_incidente("Ingreso duplicado", placa, "El vehículo ya figuraba dentro del campus")
        return (
            dbc.Alert(
                [html.B("E2 — Registro de ingreso duplicado: "),
                 f"la placa {placa} ya figura como 'dentro del campus'. Se generó una alerta de inconsistencia."],
                color="danger",
            ),
            tabla_registros(),
        )

    usuario = DB["usuarios"].get(placa)
    if usuario is None:
        # A2: registrar visitante nuevo
        nombre = vis_nombre or "Visitante sin nombre"
        DB["usuarios"][placa] = {
            "nombre": nombre, "tipo_usuario": "Visitante",
            "reserva": False, "zona_reservada": None, "cedula": vis_cedula or "N/D",
        }
        tipo_usuario = "Visitante"
        aviso_extra = dbc.Alert(
            f"A2: vehículo no registrado — se creó un registro temporal de visitante ({nombre}, motivo: {vis_motivo or 'N/D'}).",
            color="info",
        )
    else:
        tipo_usuario = usuario["tipo_usuario"]
        aviso_extra = None

    metodo = "manual (fallo de cámara A1)" if fallo else "automática (ANPR)"
    DB["registros"].append(
        {"placa": placa, "tipo_usuario": tipo_usuario, "hora_entrada": ahora(),
         "hora_salida": None, "estado": "dentro"}
    )

    resultado = html.Div(
        [
            aviso_extra,
            dbc.Alert(
                [
                    html.B("Ingreso registrado exitosamente. "),
                    f"Placa {placa} · Tipo de usuario: {tipo_usuario} · Captura {metodo} · "
                    f"Barrera de acceso autorizada.",
                ],
                color="success",
            ),
        ]
    )
    return resultado, tabla_registros()


# ===========================================================================
# CU-02 — REGISTRAR SALIDA DE VEHÍCULO
# ===========================================================================

def layout_cu02():
    return html.Div(
        [
            page_header("CU-02", "Registrar Salida de Vehículo",
                        "Registra la salida de un vehículo, libera su espacio de estacionamiento asignado "
                        "y actualiza el panel de disponibilidad."),
            dbc.Card(
                dbc.CardBody(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Label("Vehículo dentro del campus"),
                                        dcc.Dropdown(id="cu02-placa", placeholder="Seleccione una placa"),
                                    ],
                                    md=6,
                                ),
                                dbc.Col(
                                    [
                                        dbc.Label("Simulación"),
                                        dbc.Checklist(
                                            options=[{"label": "Fallo de cámara ANPR (A1)", "value": "fallo"}],
                                            id="cu02-chk-fallo", switch=True,
                                        ),
                                        dbc.Checklist(
                                            options=[{"label": "Simular falla de conexión BD (E1)", "value": "e1"}],
                                            id="cu02-chk-e1", switch=True, className="mt-2",
                                        ),
                                    ],
                                    md=6,
                                ),
                            ],
                            className="mb-3",
                        ),
                        dbc.Button(
                            [html.I(className="fas fa-door-open me-2"), "Registrar Salida"],
                            id="cu02-btn-registrar", color="success",
                        ),
                        html.Div(id="cu02-resultado", className="mt-3"),
                    ]
                ),
                className="mb-4",
            ),
            html.H5("Vehículos actualmente dentro del campus"),
            html.Div(id="cu02-tabla", children=tabla_registros()),
        ]
    )


@app.callback(Output("cu02-placa", "options"), Input("url", "pathname"))
def cu02_opciones(pathname):
    return [{"label": f"{r['placa']} ({r['tipo_usuario']})", "value": r["placa"]} for r in vehiculos_dentro()]


@app.callback(
    Output("cu02-resultado", "children"),
    Output("cu02-tabla", "children"),
    Input("cu02-btn-registrar", "n_clicks"),
    State("cu02-placa", "value"),
    State("cu02-chk-e1", "value"),
    prevent_initial_call=True,
)
def cu02_registrar_salida(n, placa, e1):
    if not placa:
        return dbc.Alert("Seleccione un vehículo dentro del campus.", color="danger"), tabla_registros()

    if e1:
        return (
            dbc.Alert(
                [html.B("E1 — Falla de conexión con la BD: "),
                 "se permite el registro manual offline; se sincronizará posteriormente."],
                color="warning",
            ),
            tabla_registros(),
        )

    registro = next((r for r in DB["registros"] if r["placa"] == placa and r["estado"] == "dentro"), None)
    if registro is None:
        return dbc.Alert("No existe un ingreso previo sin salida para esta placa.", color="danger"), tabla_registros()

    registro["hora_salida"] = ahora()
    registro["estado"] = "fuera"
    liberar_espacio_de(placa)

    return (
        dbc.Alert(
            [html.B("Salida registrada. "),
             f"Placa {placa} · Barrera de salida autorizada · Espacio de estacionamiento liberado."],
            color="success",
        ),
        tabla_registros(),
    )


# ===========================================================================
# CU-03 — GENERAR REPORTES EN TIEMPO REAL
# ===========================================================================

def layout_cu03():
    return html.Div(
        [
            page_header("CU-03", "Generar Reportes en Tiempo Real",
                        "El administrador visualiza estadísticas de ocupación por zona y tipo de usuario, "
                        "con actualización automática y opción de exportar."),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Label("Filtrar por zona"),
                            dcc.Dropdown(
                                id="cu03-filtro-zona",
                                options=[{"label": "Todas", "value": "Todas"}] + [{"label": z, "value": z} for z in ZONAS],
                                value="Todas",
                            ),
                        ],
                        md=4,
                    ),
                    dbc.Col(
                        [
                            dbc.Label("Filtrar por tipo de usuario"),
                            dcc.Dropdown(
                                id="cu03-filtro-tipo",
                                options=[{"label": "Todos", "value": "Todos"}]
                                + [{"label": t, "value": t} for t in
                                   sorted(set(u["tipo_usuario"] for u in DB["usuarios"].values()))],
                                value="Todos",
                            ),
                        ],
                        md=4,
                    ),
                    dbc.Col(
                        [
                            dbc.Label("Exportar"),
                            html.Div(
                                dbc.Button([html.I(className="fas fa-file-export me-2"), "Enviar Reporte (PDF/Excel simulado)"],
                                           id="cu03-btn-exportar", color="secondary")
                            ),
                            dcc.Download(id="cu03-descarga"),
                        ],
                        md=4,
                    ),
                ],
                className="mb-3",
            ),
            dcc.Interval(id="cu03-interval", interval=5000, n_intervals=0),
            html.Div(id="cu03-alerta"),
            dcc.Graph(id="cu03-grafico"),
            html.H5("Vehículos activos en el campus"),
            html.Div(id="cu03-tabla"),
        ]
    )


@app.callback(
    Output("cu03-grafico", "figure"),
    Output("cu03-alerta", "children"),
    Output("cu03-tabla", "children"),
    Input("cu03-interval", "n_intervals"),
    Input("cu03-filtro-zona", "value"),
    Input("cu03-filtro-tipo", "value"),
)
def cu03_actualizar(n_intervals, zona, tipo):
    conteo = {z: {"libre": 0, "ocupado": 0} for z in ZONAS}
    for e in DB["espacios"]:
        if zona != "Todas" and e["zona"] != zona:
            continue
        conteo[e["zona"]][e["estado"] if e["estado"] in ("libre", "ocupado") else "ocupado"] += 1

    data = []
    for z, vals in conteo.items():
        if zona != "Todas" and z != zona:
            continue
        data.append({"Zona": z, "Estado": "Libre", "Cantidad": vals["libre"]})
        data.append({"Zona": z, "Estado": "Ocupado", "Cantidad": vals["ocupado"]})

    fig = px.bar(
        data, x="Zona", y="Cantidad", color="Estado", barmode="group",
        color_discrete_map={"Libre": "#2ecc71", "Ocupado": "#e74c3c"},
        title=f"Ocupación por zona — actualizado {datetime.now().strftime('%H:%M:%S')}",
    )
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20), height=380)

    activos = vehiculos_dentro()
    if tipo != "Todos":
        activos = [r for r in activos if r["tipo_usuario"] == tipo]

    if not activos:
        alerta = dbc.Alert("A2: no hay vehículos activos que coincidan con el filtro (mapa vacío).", color="light")
        tabla = None
    else:
        alerta = None
        rows = [
            html.Tr([html.Td(r["placa"]), html.Td(r["tipo_usuario"]), html.Td(r["hora_entrada"])])
            for r in reversed(activos)
        ]
        tabla = dbc.Table(
            [html.Thead(html.Tr([html.Th("Placa"), html.Th("Tipo"), html.Th("Hora de ingreso")]))]
            + [html.Tbody(rows)],
            bordered=True, hover=True, striped=True, size="sm",
        )
    return fig, alerta, tabla


@app.callback(
    Output("cu03-descarga", "data"),
    Input("cu03-btn-exportar", "n_clicks"),
    prevent_initial_call=True,
)
def cu03_exportar(n):
    lineas = ["placa,tipo_usuario,hora_entrada,hora_salida,estado"]
    for r in DB["registros"]:
        lineas.append(f"{r['placa']},{r['tipo_usuario']},{r['hora_entrada']},{r.get('hora_salida') or ''},{r['estado']}")
    contenido = "\n".join(lineas)
    return dict(content=contenido, filename="reporte_estacionamiento.csv")


# ===========================================================================
# CU-04 — CONSULTAR DISPONIBILIDAD DE ESTACIONAMIENTO
# ===========================================================================

def grid_espacios(zona, tipo_filtro):
    espacios = [e for e in DB["espacios"] if e["zona"] == zona]
    if tipo_filtro and tipo_filtro != "todos":
        espacios = [e for e in espacios if e["tipo"] == tipo_filtro]

    colores = {"libre": "#2ecc71", "ocupado": "#e74c3c", "desconocido": "#95a5a6", "sensor con falla": "#f39c12"}
    celdas = []
    for e in espacios:
        celdas.append(
            html.Div(
                e["id"],
                title=f"Zona: {e['zona']} | Tipo: {e['tipo']} | Estado: {e['estado']}",
                style={
                    "backgroundColor": colores.get(e["estado"], "#bdc3c7"),
                    "color": "white", "fontSize": "11px", "fontWeight": "bold",
                    "width": "56px", "height": "42px", "display": "flex",
                    "alignItems": "center", "justifyContent": "center",
                    "borderRadius": "6px", "margin": "3px",
                },
            )
        )
    return html.Div(celdas, style={"display": "flex", "flexWrap": "wrap"})


def layout_cu04():
    return html.Div(
        [
            page_header("CU-04", "Consultar Disponibilidad de Estacionamiento",
                        "El usuario consulta, por zona, los espacios libres/ocupados en tiempo real."),
            dbc.Row(
                [
                    dbc.Col(
                        [dbc.Label("Zona de interés"),
                         dcc.Dropdown(id="cu04-zona", options=[{"label": z, "value": z} for z in ZONAS], value=ZONAS[3])],
                        md=5,
                    ),
                    dbc.Col(
                        [dbc.Label("Filtrar por tipo de espacio (A1)"),
                         dbc.RadioItems(
                             id="cu04-tipo",
                             options=[{"label": "Todos", "value": "todos"},
                                      {"label": "General", "value": "general"},
                                      {"label": "Reservado", "value": "reservado"}],
                             value="todos", inline=True,
                         )],
                        md=5,
                    ),
                    dbc.Col(
                        dbc.Button([html.I(className="fas fa-satellite me-2"), "Simular sensor sin respuesta (E1)"],
                                   id="cu04-btn-sensor-falla", color="warning", outline=True, size="sm"),
                        md=2, className="d-flex align-items-end",
                    ),
                ],
                className="mb-3",
            ),
            html.Div(id="cu04-mensaje"),
            html.Div(
                [
                    html.Small("🟩 Libre   🟥 Ocupado   ⬜ Desconocido (sensor sin respuesta)", className="text-muted"),
                    html.Div(id="cu04-grid", className="mt-2"),
                ]
            ),
        ]
    )


@app.callback(
    Output("cu04-grid", "children"),
    Output("cu04-mensaje", "children"),
    Input("cu04-zona", "value"),
    Input("cu04-tipo", "value"),
    Input("cu04-btn-sensor-falla", "n_clicks"),
)
def cu04_actualizar(zona, tipo, n_clicks):
    mensaje = None
    if ctx.triggered_id == "cu04-btn-sensor-falla":
        candidatos = [e for e in DB["espacios"] if e["zona"] == zona]
        if candidatos:
            e = random.choice(candidatos)
            e["estado"] = "desconocido"
            mensaje = dbc.Alert(
                f"E1: el sensor del espacio {e['id']} no respondió a tiempo; se muestra como 'desconocido'.",
                color="warning",
            )
    espacios_libres = sum(1 for e in DB["espacios"] if e["zona"] == zona and e["estado"] == "libre")
    resumen = dbc.Alert(f"Espacios libres más cercanos en '{zona}': {espacios_libres}", color="info")
    return grid_espacios(zona, tipo), html.Div([resumen, mensaje] if mensaje else resumen)


# ===========================================================================
# CU-05 — ACTUALIZAR PANEL DE DISPONIBILIDAD EN TIEMPO REAL
# ===========================================================================

def layout_cu05():
    return html.Div(
        [
            page_header("CU-05", "Actualizar Panel de Disponibilidad en Tiempo Real",
                        "Simula los sensores de estacionamiento notificando cambios de estado, "
                        "que se propagan al panel en menos de 5 segundos."),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Button([html.I(className="fas fa-bolt me-2"), "Simular cambio de sensor (1 espacio)"],
                                   id="cu05-btn-cambio", color="primary"),
                        md=4,
                    ),
                    dbc.Col(
                        dbc.Button([html.I(className="fas fa-bolt me-2"), "Simular cambios simultáneos (A1)"],
                                   id="cu05-btn-multi", color="primary", outline=True),
                        md=4,
                    ),
                    dbc.Col(
                        dbc.Button([html.I(className="fas fa-exclamation-triangle me-2"), "Simular señal incompleta (E1)"],
                                   id="cu05-btn-error", color="danger", outline=True),
                        md=4,
                    ),
                ],
                className="mb-3",
            ),
            dbc.Checklist(
                options=[{"label": "Auto-actualizar cada 5s (según requerimiento especial)", "value": "on"}],
                id="cu05-auto", switch=True, value=["on"],
            ),
            dcc.Interval(id="cu05-interval", interval=5000, n_intervals=0),
            html.Div(id="cu05-mensaje", className="my-3"),
            html.Div(id="cu05-grid-todas"),
            html.Small(id="cu05-ultima-actualizacion", className="text-muted"),
        ]
    )


def grid_todas_las_zonas():
    bloques = []
    for z in ZONAS:
        bloques.append(html.H6(z, className="mt-2"))
        bloques.append(grid_espacios(z, "todos"))
    return html.Div(bloques)


@app.callback(
    Output("cu05-mensaje", "children"),
    Output("cu05-grid-todas", "children"),
    Output("cu05-ultima-actualizacion", "children"),
    Input("cu05-btn-cambio", "n_clicks"),
    Input("cu05-btn-multi", "n_clicks"),
    Input("cu05-btn-error", "n_clicks"),
    Input("cu05-interval", "n_intervals"),
    State("cu05-auto", "value"),
    prevent_initial_call=False,
)
def cu05_actualizar(n1, n2, n3, n_int, auto):
    trig = ctx.triggered_id
    mensaje = None

    if trig == "cu05-btn-cambio":
        e = random.choice(DB["espacios"])
        e["estado"] = "ocupado" if e["estado"] == "libre" else "libre"
        mensaje = dbc.Alert(f"Sensor del espacio {e['id']} ({e['zona']}) reportó cambio → ahora '{e['estado']}'.", color="success")
    elif trig == "cu05-btn-multi":
        elegidos = random.sample(DB["espacios"], k=min(4, len(DB["espacios"])))
        for e in elegidos:
            e["estado"] = "ocupado" if e["estado"] == "libre" else "libre"
        mensaje = dbc.Alert(
            "A1: cambios simultáneos procesados en cola para: " + ", ".join(e["id"] for e in elegidos), color="info"
        )
    elif trig == "cu05-btn-error":
        e = random.choice(DB["espacios"])
        e["estado"] = "sensor con falla"
        mensaje = dbc.Alert(f"E1: señal incompleta del sensor {e['id']}; se marca como 'sensor con falla' y se genera alerta de mantenimiento.", color="danger")
    elif trig == "cu05-interval" and not auto:
        return no_update, no_update, no_update

    return mensaje, grid_todas_las_zonas(), f"Última actualización del panel: {datetime.now().strftime('%H:%M:%S')}"


# ===========================================================================
# CU-06 — ASIGNAR ESPACIO RESERVADO POR TIPO DE USUARIO
# ===========================================================================

def validar_pago(placa):
    return DB["pagos"].get(placa, "No registrado")


def layout_cu06():
    opciones = [
        {"label": f"{p} — {u['nombre']} ({u['tipo_usuario']})", "value": p}
        for p, u in DB["usuarios"].items() if u["reserva"]
    ]
    return html.Div(
        [
            page_header("CU-06", "Asignar Espacio Reservado por Tipo de Usuario",
                        "Asigna automáticamente al usuario con reserva vigente el espacio libre más cercano "
                        "dentro de la zona que le corresponde según su categoría."),
            dbc.Row(
                [
                    dbc.Col(
                        [dbc.Label("Usuario con reserva que ingresa"),
                         dcc.Dropdown(id="cu06-usuario", options=opciones, value=opciones[0]["value"] if opciones else None)],
                        md=8,
                    ),
                    dbc.Col(
                        dbc.Button([html.I(className="fas fa-play me-2"), "Iniciar Asignación"],
                                   id="cu06-btn-asignar", color="success", className="mt-4"),
                        md=4,
                    ),
                ],
                className="mb-3",
            ),
            html.Div(id="cu06-resultado"),
        ]
    )


@app.callback(
    Output("cu06-resultado", "children"),
    Input("cu06-btn-asignar", "n_clicks"),
    State("cu06-usuario", "value"),
    prevent_initial_call=True,
)
def cu06_asignar(n, placa):
    if not placa:
        return dbc.Alert("Seleccione un usuario con reserva.", color="danger")

    estado_pago = validar_pago(placa)
    if estado_pago != "Al día":
        log_incidente("Bloqueo por pago", placa, f"Estado de pago: {estado_pago}")
        return dbc.Alert(
            [html.B("CU-08/CU-09: acceso restringido. "),
             f"El estado de pago de {placa} es '{estado_pago}'. No se asignará espacio reservado "
             "(ver Restringir Acceso por Mora, CU-09)."],
            color="danger",
        )

    usuario = DB["usuarios"][placa]
    zona = usuario["zona_reservada"]
    libres = [e for e in DB["espacios"] if e["zona"] == zona and e["estado"] == "libre"]

    if not libres:
        alterna = next((z for z in ZONAS if z != zona and any(e["estado"] == "libre" for e in DB["espacios"] if e["zona"] == z)), None)
        if alterna:
            return dbc.Alert(
                [html.B("A1 — Sin espacios libres en la zona asignada. "),
                 f"Se sugiere la zona alterna más cercana con disponibilidad: '{alterna}'."],
                color="warning",
            )
        return dbc.Alert("A1: no hay espacios libres en ninguna zona. Usuario colocado en lista de espera.", color="warning")

    espacio = libres[0]
    espacio["estado"] = "ocupado"
    espacio["asignado_a"] = placa

    return dbc.Alert(
        [
            html.B("Espacio asignado y bloqueado temporalmente. "),
            f"Usuario: {usuario['nombre']} ({usuario['tipo_usuario']}) · Zona: {zona} · "
            f"Espacio asignado: {espacio['id']}.",
        ],
        color="success",
    )


# ===========================================================================
# CU-07 — DIRIGIR Y RESTRINGIR ACCESO A ZONAS ASIGNADAS
# ===========================================================================

def layout_cu07():
    opciones = [
        {"label": f"{p} — {u['nombre']}", "value": p}
        for p, u in DB["usuarios"].items() if u["reserva"]
    ]
    return html.Div(
        [
            page_header("CU-07", "Dirigir y Restringir Acceso a Zonas Asignadas",
                        "Dirige al usuario hacia su zona asignada y bloquea intentos de acceso a zonas no autorizadas."),
            dbc.Row(
                [
                    dbc.Col(
                        [dbc.Label("Usuario con zona asignada (ver CU-06)"),
                         dcc.Dropdown(id="cu07-usuario", options=opciones, value=opciones[0]["value"] if opciones else None)],
                        md=6,
                    ),
                    dbc.Col(
                        [dbc.Label("Zona a la que intenta ingresar el vehículo"),
                         dcc.Dropdown(id="cu07-zona-real", options=[{"label": z, "value": z} for z in ZONAS])],
                        md=6,
                    ),
                ],
                className="mb-3",
            ),
            dbc.Checklist(
                options=[{"label": "Simular barrera de zona que no responde (E2)", "value": "e2"}],
                id="cu07-chk-e2", switch=True, className="mb-3",
            ),
            dbc.Button([html.I(className="fas fa-route me-2"), "Verificar Acceso"], id="cu07-btn-verificar", color="primary"),
            html.Div(id="cu07-resultado", className="mt-3"),
            html.H6("Registro de intentos no autorizados", className="mt-4"),
            html.Div(id="cu07-incidentes"),
        ]
    )


def tabla_incidentes():
    if not DB["incidentes"]:
        return dbc.Alert("Sin incidentes registrados.", color="light")
    rows = [
        html.Tr([html.Td(i["fecha_hora"]), html.Td(i["tipo"]), html.Td(i["placa"]), html.Td(i["detalle"])])
        for i in reversed(DB["incidentes"][-10:])
    ]
    return dbc.Table(
        [html.Thead(html.Tr([html.Th("Fecha/Hora"), html.Th("Tipo"), html.Th("Placa"), html.Th("Detalle")]))]
        + [html.Tbody(rows)],
        bordered=True, hover=True, size="sm",
    )


@app.callback(
    Output("cu07-resultado", "children"),
    Output("cu07-incidentes", "children"),
    Input("cu07-btn-verificar", "n_clicks"),
    State("cu07-usuario", "value"),
    State("cu07-zona-real", "value"),
    State("cu07-chk-e2", "value"),
    prevent_initial_call=True,
)
def cu07_verificar(n, placa, zona_real, e2):
    if not placa or not zona_real:
        return dbc.Alert("Seleccione usuario y zona de ingreso.", color="danger"), tabla_incidentes()

    if e2:
        return (
            dbc.Alert(
                [html.B("E2 — Barrera de zona no responde: "),
                 "se notifica al personal de seguridad para intervención manual."],
                color="warning",
            ),
            tabla_incidentes(),
        )

    usuario = DB["usuarios"][placa]
    zona_asignada = usuario["zona_reservada"] or "General"

    if zona_real == zona_asignada:
        return (
            dbc.Alert(
                f"Acceso correcto: {usuario['nombre']} ingresó a la zona autorizada '{zona_asignada}'.",
                color="success",
            ),
            tabla_incidentes(),
        )

    log_incidente("Acceso no autorizado", placa, f"Intentó ingresar a '{zona_real}', zona autorizada: '{zona_asignada}'")
    return (
        dbc.Alert(
            [html.B("E1 — Intento de acceso a zona no autorizada. "),
             f"La barrera permanece cerrada. Zona correcta para {usuario['nombre']}: '{zona_asignada}'."],
            color="danger",
        ),
        tabla_incidentes(),
    )


# ===========================================================================
# CU-08 — VALIDAR ESTADO DE PAGO DE RESERVA
# ===========================================================================

def layout_cu08():
    opciones = [{"label": f"{p} — {u['nombre']}", "value": p} for p, u in DB["usuarios"].items() if u["reserva"]]
    return html.Div(
        [
            page_header("CU-08", "Validar Estado de Pago de Reserva",
                        "Consulta al Departamento de Finanzas la vigencia del pago/suscripción asociada a la reserva."),
            dbc.Row(
                [
                    dbc.Col(
                        [dbc.Label("Usuario con reserva"),
                         dcc.Dropdown(id="cu08-usuario", options=opciones, value=opciones[0]["value"] if opciones else None)],
                        md=6,
                    ),
                    dbc.Col(
                        [dbc.Label("Simulación"),
                         dbc.Checklist(
                             options=[{"label": "Servicio de Finanzas no disponible temporalmente (A1)", "value": "a1"},
                                      {"label": "Servicio de Finanzas caído tras reintentos (E1)", "value": "e1"}],
                             id="cu08-chk", switch=True,
                         )],
                        md=6,
                    ),
                ],
                className="mb-3",
            ),
            dbc.Button([html.I(className="fas fa-search-dollar me-2"), "Validar Pago"], id="cu08-btn-validar", color="primary"),
            html.Div(id="cu08-resultado", className="mt-3"),
            html.H6("Estado de pago registrado por usuario", className="mt-4"),
            html.Div(id="cu08-tabla-pagos"),
        ]
    )


def tabla_pagos():
    rows = []
    for p, estado in DB["pagos"].items():
        nombre = DB["usuarios"].get(p, {}).get("nombre", "—")
        rows.append(html.Tr([html.Td(p), html.Td(nombre), html.Td(badge_estado(estado))]))
    return dbc.Table(
        [html.Thead(html.Tr([html.Th("Placa"), html.Th("Usuario"), html.Th("Estado de pago")]))]
        + [html.Tbody(rows)],
        bordered=True, hover=True, size="sm",
    )


@app.callback(
    Output("cu08-resultado", "children"),
    Output("cu08-tabla-pagos", "children"),
    Input("cu08-btn-validar", "n_clicks"),
    State("cu08-usuario", "value"),
    State("cu08-chk", "value"),
    prevent_initial_call=True,
)
def cu08_validar(n, placa, opciones):
    opciones = opciones or []
    if not placa:
        return dbc.Alert("Seleccione un usuario.", color="danger"), tabla_pagos()

    if "e1" in opciones:
        return (
            dbc.Alert(
                [html.B("E1 — Servicio de Finanzas no disponible tras reintentos. "),
                 "Se aplica la política de acceso restringido temporal (ver CU-09)."],
                color="danger",
            ),
            tabla_pagos(),
        )

    if "a1" in opciones:
        estado_previo = DB["pagos"].get(placa, "No registrado")
        return (
            dbc.Alert(
                [html.B("A1 — Sin respuesta inmediata de Finanzas. "),
                 f"Se utiliza el último estado registrado: '{estado_previo}', marcado como 'no verificado'."],
                color="warning",
            ),
            tabla_pagos(),
        )

    estado = validar_pago(placa)
    color = "success" if estado == "Al día" else "danger" if estado == "Moroso" else "secondary"
    texto = "habilitando la asignación del espacio reservado (CU-06)." if estado == "Al día" \
        else "por lo que se aplicará la restricción de acceso (CU-09)."
    return (
        dbc.Alert([html.B(f"Estado de pago: {estado}. "), texto], color=color),
        tabla_pagos(),
    )


# ===========================================================================
# CU-09 — RESTRINGIR ACCESO POR MORA O PAGO NO REGISTRADO
# ===========================================================================

def layout_cu09():
    morosos = [p for p, e in DB["pagos"].items() if e in ("Moroso", "No registrado")]
    opciones = [{"label": f"{p} — {DB['usuarios'][p]['nombre']} ({DB['pagos'][p]})", "value": p} for p in morosos]
    return html.Div(
        [
            page_header("CU-09", "Restringir Acceso por Mora o Pago No Registrado",
                        "Bloquea automáticamente la asignación de un espacio reservado cuando el pago está en mora "
                        "o no registrado, y permite regularizar el pago."),
            dbc.Row(
                [
                    dbc.Col(
                        [dbc.Label("Usuario con estado Moroso / No registrado"),
                         dcc.Dropdown(id="cu09-usuario", options=opciones, value=opciones[0]["value"] if opciones else None)],
                        md=8,
                    ),
                    dbc.Col(
                        dbc.Button([html.I(className="fas fa-lock me-2"), "Aplicar Restricción"],
                                   id="cu09-btn-bloquear", color="danger", className="mt-4"),
                        md=4,
                    ),
                ],
                className="mb-3",
            ),
            html.Div(id="cu09-resultado"),
            html.Hr(),
            html.H6("Historial de incidentes"),
            html.Div(id="cu09-incidentes", children=tabla_incidentes()),
        ]
    )


@app.callback(
    Output("cu09-resultado", "children"),
    Output("cu09-incidentes", "children"),
    Output("cu09-usuario", "options"),
    Input("cu09-btn-bloquear", "n_clicks"),
    Input({"type": "cu09-regularizar", "placa": dash.ALL}, "n_clicks"),
    State("cu09-usuario", "value"),
    prevent_initial_call=True,
)
def cu09_bloquear(n_bloquear, n_regularizar_list, placa):
    trig = ctx.triggered_id

    # Regularizar pago desde un botón dinámico
    if isinstance(trig, dict) and trig.get("type") == "cu09-regularizar":
        placa_reg = trig["placa"]
        if any(n_regularizar_list):
            DB["pagos"][placa_reg] = "Al día"
            morosos = [p for p, e in DB["pagos"].items() if e in ("Moroso", "No registrado")]
            opciones = [{"label": f"{p} — {DB['usuarios'][p]['nombre']} ({DB['pagos'][p]})", "value": p} for p in morosos]
            return (
                dbc.Alert(
                    [html.B("Pago regularizado. "),
                     f"El estado de {placa_reg} ahora es 'Al día'. Puede procederse con CU-06 (Asignar Espacio Reservado)."],
                    color="success",
                ),
                tabla_incidentes(),
                opciones,
            )

    if not placa:
        return dbc.Alert("Seleccione un usuario en mora o sin pago registrado.", color="danger"), tabla_incidentes(), no_update

    usuario = DB["usuarios"][placa]
    estado = DB["pagos"].get(placa, "No registrado")
    log_incidente("Restricción por pago", placa, f"Estado: {estado}")

    resultado = html.Div(
        [
            dbc.Alert(
                [
                    html.B("Acceso restringido. "),
                    f"{usuario['nombre']} ({placa}) tiene estado '{estado}'. "
                    "No se asignará espacio reservado.",
                ],
                color="danger",
            ),
            html.P("Opciones disponibles para el usuario:"),
            dbc.Button("Estacionarse en zona General", color="secondary", outline=True, className="me-2", disabled=True),
            dbc.Button(
                "Regularizar pago ahora",
                id={"type": "cu09-regularizar", "placa": placa},
                color="success",
            ),
        ]
    )
    return resultado, tabla_incidentes(), no_update


# ===========================================================================
# INICIO
# ===========================================================================

def layout_inicio():
    total_espacios = len(DB["espacios"])
    libres = sum(1 for e in DB["espacios"] if e["estado"] == "libre")
    dentro = len(vehiculos_dentro())
    return html.Div(
        [
            html.H3("Sistema de Gestión de Estacionamiento Vehicular Universitario"),
            html.P(
                "Interfaces de demostración para los 9 casos de uso especificados en el documento de "
                "Especificación de Casos de Uso (UTP). Seleccione un caso de uso en el menú lateral.",
                className="text-muted",
            ),
            dbc.Row(
                [
                    dbc.Col(dbc.Card(dbc.CardBody([html.H2(f"{libres}/{total_espacios}"), html.Small("Espacios libres")])), md=4),
                    dbc.Col(dbc.Card(dbc.CardBody([html.H2(dentro), html.Small("Vehículos dentro del campus")])), md=4),
                    dbc.Col(dbc.Card(dbc.CardBody([html.H2(len(DB["incidentes"])), html.Small("Incidentes registrados")])), md=4),
                ],
                className="mb-4 text-center",
            ),
            dbc.Table(
                [
                    html.Thead(html.Tr([html.Th("ID"), html.Th("Caso de Uso")])),
                    html.Tbody(
                        [
                            html.Tr([html.Td(cu), html.Td(nombre)])
                            for cu, nombre, _ in MENU[1:]
                        ]
                    ),
                ],
                bordered=True, hover=True, size="sm",
            ),
        ]
    )


PAGINAS = {
    "/": layout_inicio,
    "/cu00": layout_cu00,
    "/cu01": layout_cu01,
    "/cu02": layout_cu02,
    "/cu03": layout_cu03,
    "/cu04": layout_cu04,
    "/cu05": layout_cu05,
    "/cu06": layout_cu06,
    "/cu07": layout_cu07,
    "/cu08": layout_cu08,
    "/cu09": layout_cu09,
}


@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def render_page(pathname):
    layout_fn = PAGINAS.get(pathname, layout_inicio)
    return layout_fn()


@app.callback(Output("reset-global-msg", "children"), Input("btn-reset-global", "n_clicks"), prevent_initial_call=True)
def reset_global(n):
    reset_all()
    return f"Datos reiniciados a las {datetime.now().strftime('%H:%M:%S')}."


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=8050)
