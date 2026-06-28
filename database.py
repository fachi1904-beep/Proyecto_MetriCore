import sqlite3
import pandas as pd

DB_NAME = "metricore.db"

UNIDADES_POR_TIPO = {
    "Balanza": ["g", "kg", "mg"],
    "Termómetro": ["°C", "°F", "K"],
    "Vernier": ["mm", "cm", "pulg"],
    "Micrómetro": ["mm", "µm", "pulg"],
    "pHmetro": ["pH"],
    "Multímetro": ["V", "mV", "A", "mA", "Ω", "kΩ"],
    "Manómetro": ["Pa", "kPa", "bar", "psi"],
    "Higrómetro": ["%HR"],
    "Luxómetro": ["lux"],
    "Sonómetro": ["dB"],
    "Otro": ["m", "s", "mol", "cd", "otro"]
}

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS equipos (
            id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            tipo TEXT,
            marca TEXT,
            modelo TEXT,
            numero_serie TEXT,
            ubicacion TEXT,
            responsable TEXT,
            rango_max REAL,
            resolucion REAL,
            unidad TEXT,
            tolerancia REAL,
            estado TEXT DEFAULT 'En servicio',
            ultima_calibracion TEXT,
            proxima_calibracion TEXT,
            proveedor TEXT,
            contacto_proveedor TEXT,
            condiciones_ambientales TEXT,
            instrucciones_uso TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS mantenimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipo_id TEXT,
            tipo TEXT,
            fecha TEXT,
            descripcion TEXT,
            responsable TEXT,
            proximo_mantenimiento TEXT,
            FOREIGN KEY (equipo_id) REFERENCES equipos(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS calibraciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipo_id TEXT,
            fecha TEXT,
            proximo_vencimiento TEXT,
            numero_certificado TEXT,
            laboratorio TEXT,
            incertidumbre REAL,
            error REAL,
            unidad TEXT,
            metodo TEXT,
            FOREIGN KEY (equipo_id) REFERENCES equipos(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS condiciones (
            equipo_id TEXT PRIMARY KEY,
            rango_operacion TEXT,
            limitaciones TEXT,
            procedimiento_uso TEXT,
            verificaciones_previas TEXT,
            requisitos_almacenamiento TEXT,
            requisitos_trazabilidad TEXT,
            FOREIGN KEY (equipo_id) REFERENCES equipos(id)
        )
    """)

    conn.commit()
    conn.close()

def get_equipos():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM equipos", conn)
    conn.close()
    return df

def get_equipo_by_id(equipo_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM equipos WHERE id = ?", (equipo_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else {}

def id_existe(equipo_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM equipos WHERE id = ?", (equipo_id,))
    row = c.fetchone()
    conn.close()
    return row is not None

def insert_equipo(data):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO equipos VALUES (
            :id, :nombre, :tipo, :marca, :modelo, :numero_serie,
            :ubicacion, :responsable, :rango_max, :resolucion, :unidad,
            :tolerancia, :estado, :ultima_calibracion, :proxima_calibracion,
            :proveedor, :contacto_proveedor, :condiciones_ambientales, :instrucciones_uso
        )
    """, data)
    conn.commit()
    conn.close()

def update_equipo(data):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE equipos SET
            nombre = :nombre,
            tipo = :tipo,
            marca = :marca,
            modelo = :modelo,
            numero_serie = :numero_serie,
            ubicacion = :ubicacion,
            responsable = :responsable,
            rango_max = :rango_max,
            resolucion = :resolucion,
            unidad = :unidad,
            tolerancia = :tolerancia,
            estado = :estado,
            ultima_calibracion = :ultima_calibracion,
            proxima_calibracion = :proxima_calibracion,
            proveedor = :proveedor,
            contacto_proveedor = :contacto_proveedor,
            condiciones_ambientales = :condiciones_ambientales,
            instrucciones_uso = :instrucciones_uso
        WHERE id = :id
    """, data)
    conn.commit()
    conn.close()

def delete_equipo(equipo_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM equipos WHERE id = ?", (equipo_id,))
    conn.commit()
    conn.close()

def get_mantenimientos(equipo_id=None):
    conn = get_connection()
    if equipo_id:
        df = pd.read_sql_query(
            "SELECT * FROM mantenimientos WHERE equipo_id = ? ORDER BY fecha DESC",
            conn, params=(equipo_id,)
        )
    else:
        df = pd.read_sql_query("SELECT * FROM mantenimientos ORDER BY fecha DESC", conn)
    conn.close()
    return df

def insert_mantenimiento(data):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO mantenimientos (equipo_id, tipo, fecha, descripcion, responsable, proximo_mantenimiento)
        VALUES (:equipo_id, :tipo, :fecha, :descripcion, :responsable, :proximo_mantenimiento)
    """, data)
    conn.commit()
    conn.close()

def get_calibraciones(equipo_id=None):
    conn = get_connection()
    if equipo_id:
        df = pd.read_sql_query(
            "SELECT * FROM calibraciones WHERE equipo_id = ? ORDER BY fecha DESC",
            conn, params=(equipo_id,)
        )
    else:
        df = pd.read_sql_query("SELECT * FROM calibraciones ORDER BY fecha DESC", conn)
    conn.close()
    return df

def insert_calibracion(data):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO calibraciones (equipo_id, fecha, proximo_vencimiento, numero_certificado,
        laboratorio, incertidumbre, error, unidad, metodo)
        VALUES (:equipo_id, :fecha, :proximo_vencimiento, :numero_certificado,
        :laboratorio, :incertidumbre, :error, :unidad, :metodo)
    """, data)
    c.execute("""
        UPDATE equipos SET ultima_calibracion = :fecha, proxima_calibracion = :proximo_vencimiento
        WHERE id = :equipo_id
    """, data)
    conn.commit()
    conn.close()

def get_condiciones(equipo_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM condiciones WHERE equipo_id = ?", (equipo_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else {}

def save_condiciones(data):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO condiciones VALUES (
            :equipo_id, :rango_operacion, :limitaciones, :procedimiento_uso,
            :verificaciones_previas, :requisitos_almacenamiento, :requisitos_trazabilidad
        )
    """, data)
    conn.commit()
    conn.close()