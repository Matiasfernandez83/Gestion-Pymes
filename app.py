"""
Sistema de Gestión Operativa para Pymes
Backend: Flask + SQLite (stdlib)
Autor: Sistema BI Consultoría
"""

import os
import csv
import io
import sqlite3
from datetime import datetime, timedelta, date
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import pandas as pd
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, send_file, g
)
from dotenv import load_dotenv

# Cargar variables de entorno desde .env si existe
load_dotenv()

# ══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════

app = Flask(__name__)
# Obtener secret key del entorno o usar una por defecto (sólo para dev local)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secreta-solo-local-12345")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "database.db"))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Tipos de movimiento válidos
TIPOS_VALIDOS = {"ingreso", "egreso", "venta", "compra"}

# ══════════════════════════════════════════════════════════════════
# BASE DE DATOS — Conexión y contexto de aplicación
# ══════════════════════════════════════════════════════════════════

def get_db():
    """Retorna la conexión SQLite del contexto actual de Flask."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row   # acceso por nombre de columna
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Cierra la conexión BD al final de cada request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    """Crea las tablas e inserta datos de demo si la BD está vacía."""
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # ── Tabla: usuarios ────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT    UNIQUE NOT NULL,
            password TEXT    NOT NULL,
            rol      TEXT    NOT NULL DEFAULT 'usuario'
        )
    """)

    # ── Tabla: movimientos ─────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS movimientos (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha     DATE    NOT NULL,
            tipo      TEXT    NOT NULL,       -- ingreso/egreso/venta/compra
            concepto  TEXT    NOT NULL,
            monto     REAL    NOT NULL,
            categoria TEXT    NOT NULL DEFAULT 'General'
        )
    """)

    # ── Tabla: stock ──────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stock (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo       TEXT    UNIQUE NOT NULL,
            descripcion  TEXT    NOT NULL,
            cantidad     INTEGER NOT NULL DEFAULT 0,
            stock_minimo INTEGER NOT NULL DEFAULT 10,
            rubro        TEXT    NOT NULL DEFAULT 'General'
        )
    """)

    conn.commit()

    # ── Seed: usuario admin por defecto ───────────────────────────
    cur.execute("SELECT COUNT(*) FROM usuarios")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO usuarios (username, password, rol) VALUES (?, ?, ?)",
            ("admin", generate_password_hash("admin123"), "admin")
        )
        conn.commit()

    # ── Seed: movimientos de demo (últimos 6 meses) ───────────────
    cur.execute("SELECT COUNT(*) FROM movimientos")
    if cur.fetchone()[0] == 0:
        import random
        random.seed(42)
        hoy = date.today()
        concepto_ing = ["Venta productos cosmética", "Venta logística", "Servicio consultoría",
                        "Cobro factura #", "Venta online", "Ingreso cuota cliente"]
        concepto_egr = ["Compra materia prima", "Pago proveedor Tech Supply SA",
                        "Gasto operativo", "Pago alquiler", "Servicio electricidad",
                        "Compra insumos logística", "Pago nómina"]
        categorias_i = ["Cosmética", "Logística", "Consultoría", "Ventas"]
        categorias_e = ["Proveedores", "Operativo", "Alquiler", "Servicios", "Personal"]

        demo_rows = []
        for i in range(60):
            dia_offset = random.randint(0, 180)
            fecha = hoy - timedelta(days=dia_offset)
            if random.random() > 0.45:   # más ingresos que egresos para saldo positivo
                tipo = random.choice(["ingreso", "venta"])
                concepto = random.choice(concepto_ing) + (str(i) if "factura" in concepto_ing[0] else "")
                monto = round(random.uniform(50_000, 800_000), 2)
                cat = random.choice(categorias_i)
            else:
                tipo = random.choice(["egreso", "compra"])
                concepto = random.choice(concepto_egr)
                monto = round(random.uniform(20_000, 500_000), 2)
                cat = random.choice(categorias_e)
            demo_rows.append((fecha.isoformat(), tipo, concepto, monto, cat))

        cur.executemany(
            "INSERT INTO movimientos (fecha, tipo, concepto, monto, categoria) VALUES (?,?,?,?,?)",
            demo_rows
        )
        conn.commit()

    # ── Seed: stock de demo ───────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM stock")
    if cur.fetchone()[0] == 0:
        stock_demo = [
            ("LOG-001", "Cajas de Cartón Corrugado",       320, 200, "Logística"),
            ("LOG-002", "Cinta de Embalar 48mm",            850, 300, "Logística"),
            ("LOG-003", "Pallet de Madera 100x120",          45,  20, "Logística"),
            ("LOG-004", "Film Stretch 20 micrones",         500, 150, "Logística"),
            ("LOG-005", "Etiquetas Adhesivas Blancas",     1200, 400, "Logística"),
            ("LOG-006", "Bolsas de Polietileno 50x70",      180, 300, "Logística"),   # CRÍTICO
            ("LOG-007", "Esquineros de Cartón",             640, 200, "Logística"),
            ("LOG-008", "Zuncho Plástico PP 16mm",            8,  10, "Logística"),   # CRÍTICO
            ("COS-001", "Crema Hidratante Facial FPS30",    180, 100, "Cosmética"),
            ("COS-002", "Sérum Vitamina C 30ml",             65,  50, "Cosmética"),
            ("COS-003", "Mascarilla Purif. Arcilla 200ml",  120, 100, "Cosmética"),
            ("COS-004", "Ácido Hialurónico 50ml",            40,  30, "Cosmética"),
            ("COS-005", "Tónico Micelar sin Alcohol 250ml",  15, 100, "Cosmética"),   # CRÍTICO
            ("COS-006", "Contorno de Ojos Retinol 15ml",    55,  40, "Cosmética"),
            ("COS-007", "Protector Solar SPF50+",           165,  80, "Cosmética"),
        ]
        cur.executemany(
            "INSERT INTO stock (codigo, descripcion, cantidad, stock_minimo, rubro) VALUES (?,?,?,?,?)",
            stock_demo
        )
        conn.commit()

    conn.close()
    print("  Base de datos inicializada OK.")

# ══════════════════════════════════════════════════════════════════
# DECORADOR DE AUTENTICACIÓN
# ══════════════════════════════════════════════════════════════════

def login_required(f):
    """Decorator: redirige al login si no hay sesión activa."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Debes iniciar sesión para acceder.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ══════════════════════════════════════════════════════════════════
# RUTAS PÚBLICAS — Login / Logout
# ══════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    """Raíz: redirige a dashboard si hay sesión, sino al login."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    """Vista de login. POST verifica credenciales y crea sesión."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db  = get_db()
        row = db.execute(
            "SELECT * FROM usuarios WHERE username = ?", (username,)
        ).fetchone()

        if row and check_password_hash(row["password"], password):
            session["user_id"]  = row["id"]
            session["username"] = row["username"]
            session["rol"]      = row["rol"]
            return redirect(url_for("dashboard"))
        else:
            flash("Usuario o contraseña incorrectos.", "error")

    return render_template("login.html")

@app.route("/logout")
def logout():
    """Cierra la sesión y redirige al login."""
    session.clear()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("login"))

# ══════════════════════════════════════════════════════════════════
# RUTAS PROTEGIDAS — Vistas principales
# ══════════════════════════════════════════════════════════════════

@app.route("/dashboard")
@login_required
def dashboard():
    """Dashboard principal con tarjetas de KPIs."""
    return render_template("index.html")

@app.route("/detalle")
@login_required
def detalle():
    """Vista de detalle/tabla de movimientos con filtros."""
    tipo      = request.args.get("tipo", "")
    fecha_ini = request.args.get("fecha_ini", "")
    fecha_fin = request.args.get("fecha_fin", "")

    db  = get_db()
    sql = "SELECT * FROM movimientos WHERE 1=1"
    params = []

    if tipo and tipo in TIPOS_VALIDOS:
        sql += " AND tipo = ?"
        params.append(tipo)
    if fecha_ini:
        sql += " AND fecha >= ?"
        params.append(fecha_ini)
    if fecha_fin:
        sql += " AND fecha <= ?"
        params.append(fecha_fin)

    sql += " ORDER BY fecha DESC"
    movs = db.execute(sql, params).fetchall()

    return render_template("detalle.html",
                           movimientos=movs,
                           tipo=tipo,
                           fecha_ini=fecha_ini,
                           fecha_fin=fecha_fin)

@app.route("/stock-view")
@login_required
def stock_view():
    """Vista de gestión de stock."""
    db    = get_db()
    items = db.execute("SELECT * FROM stock ORDER BY rubro, descripcion").fetchall()
    return render_template("stock.html", items=items)

@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    """Formulario de carga masiva CSV/Excel. POST procesa e inserta en BD."""
    if request.method == "GET":
        return render_template("upload.html")

    archivo = request.files.get("archivo_csv")
    if not archivo or archivo.filename == "":
        flash("No se seleccionó ningún archivo.", "error")
        return redirect(url_for("upload"))

    fname = archivo.filename.lower()
    if not (fname.endswith(".csv") or fname.endswith(".xlsx")):
        flash("Solo se aceptan archivos .csv o .xlsx", "error")
        return redirect(url_for("upload"))

    db = get_db()
    ok_movs, err_movs = 0, 0
    ok_stock, err_stock = 0, 0

    try:
        if fname.endswith(".csv"):
            # Lógica CSV anterior (sólo movimientos)
            contenido = archivo.stream.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(contenido))
            req_movs = {"fecha", "tipo", "concepto", "monto", "categoria"}
            headers = {h.strip().lower() for h in (reader.fieldnames or [])}
            if not req_movs.issubset(headers):
                faltantes = req_movs - headers
                flash(f"Faltan columnas en el CSV: {', '.join(faltantes)}", "error")
                return redirect(url_for("upload"))

            rows = []
            for linea in reader:
                row = {k.strip().lower(): v.strip() for k, v in linea.items()}
                tipo = row.get("tipo", "").lower()
                if tipo not in TIPOS_VALIDOS:
                    err_movs += 1
                    continue
                try:
                    fecha = datetime.strptime(row["fecha"], "%Y-%m-%d").date().isoformat()
                    monto = float(row["monto"].replace(",", ".").replace("$", "").strip())
                    rows.append((fecha, tipo, row.get("concepto", "")[:200], monto, row.get("categoria", "General")[:100]))
                    ok_movs += 1
                except:
                    err_movs += 1
            if rows:
                db.executemany("INSERT INTO movimientos (fecha,tipo,concepto,monto,categoria) VALUES (?,?,?,?,?)", rows)

        elif fname.endswith(".xlsx"):
            # Lógica Excel (múltiples hojas: Movimientos y/o Stock)
            hojas = pd.read_excel(archivo, sheet_name=None, dtype=str)
            
            # --- Procesar hoja Movimientos ---
            if "Movimientos" in hojas:
                df_m = hojas["Movimientos"].dropna(how="all")
                df_m.columns = [str(c).strip().lower() for c in df_m.columns]
                req_movs = {"fecha", "tipo", "concepto", "monto", "categoria"}
                
                if req_movs.issubset(set(df_m.columns)):
                    rows_m = []
                    for _, row in df_m.iterrows():
                        tipo = str(row.get("tipo", "")).strip().lower()
                        if tipo not in TIPOS_VALIDOS:
                            err_movs += 1; continue
                        try:
                            # Pandas lee fechas de varias formas, intentamos normalizar
                            fecha_val = pd.to_datetime(row["fecha"]).date().isoformat()
                            monto_val = float(str(row["monto"]).replace(",", ".").replace("$", "").strip())
                            rows_m.append((fecha_val, tipo, str(row.get("concepto", ""))[:200], monto_val, str(row.get("categoria", "General"))[:100]))
                            ok_movs += 1
                        except:
                            err_movs += 1
                    if rows_m:
                        db.executemany("INSERT INTO movimientos (fecha,tipo,concepto,monto,categoria) VALUES (?,?,?,?,?)", rows_m)
            
            # --- Procesar hoja Stock ---
            if "Stock" in hojas:
                df_s = hojas["Stock"].dropna(how="all")
                df_s.columns = [str(c).strip().lower().replace(" ", "_") for c in df_s.columns]
                req_stock = {"codigo", "descripcion", "cantidad", "stock_minimo", "rubro"}
                
                if req_stock.issubset(set(df_s.columns)):
                    for _, row in df_s.iterrows():
                        codigo = str(row.get("codigo", "")).strip()
                        if not codigo or codigo.lower() == "nan":
                            err_stock += 1; continue
                        try:
                            cant = int(float(str(row["cantidad"]).replace(",", ".")))
                            minimo = int(float(str(row["stock_minimo"]).replace(",", ".")))
                            desc = str(row.get("descripcion", ""))[:200]
                            rubro = str(row.get("rubro", "General"))[:100]
                            
                            # Insertar ignorando si ya existe el código, o idealmente actualizar
                            # Optamos por INSERT OR REPLACE para que sirva de actualización masiva
                            db.execute("""
                                INSERT INTO stock (codigo, descripcion, cantidad, stock_minimo, rubro) 
                                VALUES (?, ?, ?, ?, ?)
                                ON CONFLICT(codigo) DO UPDATE SET 
                                descripcion=excluded.descripcion,
                                cantidad=excluded.cantidad,
                                stock_minimo=excluded.stock_minimo,
                                rubro=excluded.rubro
                            """, (codigo, desc, cant, minimo, rubro))
                            ok_stock += 1
                        except:
                            err_stock += 1

        db.commit()
        msg = f"Importación exitosa. "
        if ok_movs > 0 or err_movs > 0: msg += f"Movimientos: {ok_movs} OK, {err_movs} Error. "
        if ok_stock > 0 or err_stock > 0: msg += f"Stock: {ok_stock} OK, {err_stock} Error."
        flash(msg, "success")

    except Exception as e:
        flash(f"Error al procesar el archivo: {str(e)}", "error")

    return redirect(url_for("upload"))

@app.route("/descargar-plantilla")
@login_required
def descargar_plantilla():
    """Genera y descarga un Excel con hojas para Movimientos y Stock."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # Template Movimientos
        df_movs = pd.DataFrame([{
            "Fecha": date.today().strftime("%Y-%m-%d"),
            "Tipo": "ingreso",  # o egreso, venta, compra
            "Concepto": "Ejemplo de ingreso de sistema",
            "Monto": 15000.50,
            "Categoria": "Ventas"
        }])
        df_movs.to_excel(writer, index=False, sheet_name="Movimientos")
        
        # Template Stock
        df_stock = pd.DataFrame([{
            "Codigo": "PROD-001",
            "Descripcion": "Producto de Ejemplo",
            "Cantidad": 150,
            "Stock_Minimo": 50,
            "Rubro": "General"
        }])
        df_stock.to_excel(writer, index=False, sheet_name="Stock")
        
        # Ajustar anchos automáticamente
        for sheetname in writer.sheets:
            worksheet = writer.sheets[sheetname]
            worksheet.autofit()

    output.seek(0)
    return send_file(
        output,
        download_name="Plantilla_Carga_Masiva.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ══════════════════════════════════════════════════════════════════
# API JSON — Endpoints para alimentar el dashboard
# ══════════════════════════════════════════════════════════════════

@app.route("/api/datos")
@login_required
def api_datos():
    """
    Devuelve JSON con todos los KPIs y datos para el dashboard.
    Usado por el frontend JS para renderizar tarjetas y gráficos.
    """
    db = get_db()

    # ── KPIs principales ──────────────────────────────────────────
    ingresos = db.execute(
        "SELECT COALESCE(SUM(monto),0) as total FROM movimientos WHERE tipo IN ('ingreso','venta')"
    ).fetchone()["total"]

    egresos = db.execute(
        "SELECT COALESCE(SUM(monto),0) as total FROM movimientos WHERE tipo IN ('egreso','compra')"
    ).fetchone()["total"]

    stock_critico = db.execute(
        "SELECT COUNT(*) as n FROM stock WHERE cantidad <= stock_minimo"
    ).fetchone()["n"]

    # ── Movimientos por mes (últimos 6 meses) ─────────────────────
    filas_mes = db.execute("""
        SELECT
            strftime('%Y-%m', fecha) AS mes,
            SUM(CASE WHEN tipo IN ('ingreso','venta') THEN monto ELSE 0 END) AS ingresos,
            SUM(CASE WHEN tipo IN ('egreso','compra')  THEN monto ELSE 0 END) AS egresos
        FROM movimientos
        WHERE fecha >= date('now', '-6 months')
        GROUP BY mes
        ORDER BY mes ASC
    """).fetchall()

    meses_es = {"01":"Ene","02":"Feb","03":"Mar","04":"Abr","05":"May","06":"Jun",
                "07":"Jul","08":"Ago","09":"Sep","10":"Oct","11":"Nov","12":"Dic"}
    por_mes = []
    for r in filas_mes:
        y, m = r["mes"].split("-")
        por_mes.append({
            "mes":      f"{meses_es[m]} {y[2:]}",
            "ingresos": round(r["ingresos"], 2),
            "egresos":  round(r["egresos"],  2),
        })

    # ── Últimos 8 movimientos ─────────────────────────────────────
    ultimos = db.execute(
        "SELECT * FROM movimientos ORDER BY fecha DESC, id DESC LIMIT 8"
    ).fetchall()
    movs_recientes = [dict(m) for m in ultimos]

    # ── Distribución por categoría (ingresos) ─────────────────────
    cats = db.execute("""
        SELECT categoria, SUM(monto) as total
        FROM movimientos WHERE tipo IN ('ingreso','venta')
        GROUP BY categoria ORDER BY total DESC LIMIT 5
    """).fetchall()
    por_categoria = [{"categoria": r["categoria"], "total": round(r["total"], 2)} for r in cats]

    return jsonify({
        "ingresos":       round(ingresos, 2),
        "egresos":        round(egresos,  2),
        "saldo":          round(ingresos - egresos, 2),
        "stock_critico":  stock_critico,
        "por_mes":        por_mes,
        "por_categoria":  por_categoria,
        "recientes":      movs_recientes,
        "ultima_actualizacion": datetime.now().strftime("%d/%m/%Y %H:%M"),
    })

@app.route("/api/stock")
@login_required
def api_stock():
    """Devuelve JSON con todos los ítems de stock."""
    db    = get_db()
    items = db.execute("SELECT * FROM stock ORDER BY rubro, descripcion").fetchall()
    return jsonify([dict(i) for i in items])

# ══════════════════════════════════════════════════════════════════
# EXPORTAR — Descarga Excel / CSV
# ══════════════════════════════════════════════════════════════════

@app.route("/exportar")
@login_required
def exportar():
    """
    Exporta movimientos o stock a Excel (.xlsx).
    Parámetro: ?tabla=movimientos (default) | stock
    """
    tabla = request.args.get("tabla", "movimientos")

    db = get_db()
    if tabla == "stock":
        rows  = db.execute("SELECT * FROM stock").fetchall()
        cols  = ["id", "codigo", "descripcion", "cantidad", "stock_minimo", "rubro"]
        fname = "stock_export.xlsx"
    else:
        rows  = db.execute("SELECT * FROM movimientos ORDER BY fecha DESC").fetchall()
        cols  = ["id", "fecha", "tipo", "concepto", "monto", "categoria"]
        fname = "movimientos_export.xlsx"

    # Construir DataFrame con pandas y exportar
    data = [dict(zip(cols, [r[c] for c in cols])) for r in rows]
    df   = pd.DataFrame(data, columns=cols)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=tabla.capitalize())
        
        # Ajustar anchos
        for sheetname in writer.sheets:
            worksheet = writer.sheets[sheetname]
            worksheet.autofit()
            
    output.seek(0)

    return send_file(
        output,
        download_name=fname,
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ══════════════════════════════════════════════════════════════════
# STOCK CRUD — Agregar/Actualizar rápido
# ══════════════════════════════════════════════════════════════════

@app.route("/stock/actualizar/<int:item_id>", methods=["POST"])
@login_required
def actualizar_stock(item_id):
    """Actualiza la cantidad de un ítem de stock."""
    nueva_cantidad = request.form.get("cantidad", type=int)
    if nueva_cantidad is None or nueva_cantidad < 0:
        flash("Cantidad inválida.", "error")
        return redirect(url_for("stock_view"))

    get_db().execute(
        "UPDATE stock SET cantidad = ? WHERE id = ?", (nueva_cantidad, item_id)
    )
    get_db().commit()
    flash("Stock actualizado correctamente.", "success")
    return redirect(url_for("stock_view"))

@app.route("/movimiento/nuevo", methods=["POST"])
@login_required
def nuevo_movimiento():
    """Agrega un movimiento manual desde el formulario del detalle."""
    fecha     = request.form.get("fecha")
    tipo      = request.form.get("tipo", "").lower()
    concepto  = request.form.get("concepto", "")
    monto_str = request.form.get("monto", "0").replace(",", ".")
    categoria = request.form.get("categoria", "General")

    try:
        monto = float(monto_str)
        datetime.strptime(fecha, "%Y-%m-%d")
        if tipo not in TIPOS_VALIDOS:
            raise ValueError("Tipo inválido")
    except ValueError as e:
        flash(f"Error en el formulario: {e}", "error")
        return redirect(url_for("detalle"))

    get_db().execute(
        "INSERT INTO movimientos (fecha, tipo, concepto, monto, categoria) VALUES (?,?,?,?,?)",
        (fecha, tipo, concepto, monto, categoria)
    )
    get_db().commit()
    flash("Movimiento registrado correctamente.", "success")
    return redirect(url_for("detalle"))

# ══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 55)
    print("  Sistema de Gestión Operativa para Pymes")
    print("  http://localhost:5000")
    print("  Usuario: admin  |  Contraseña: admin123")
    print("=" * 55)
    init_db()
    app.run(debug=True, port=5000, host="0.0.0.0")
