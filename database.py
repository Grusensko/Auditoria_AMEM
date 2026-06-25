import os
import sqlite3
import hashlib
import secrets
from cryptography.fernet import Fernet

# Configurar la clave de cifrado
# Se lee de variables de entorno o de los secrets de Streamlit
def get_encryption_key():
    # 1. Intentar desde variable de entorno
    key = os.environ.get("AMEM_ENCRYPTION_KEY")
    if key:
        return key.encode()
        
    # 2. Intentar desde Streamlit secrets
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "AMEM_ENCRYPTION_KEY" in st.secrets:
            key = st.secrets["AMEM_ENCRYPTION_KEY"]
            if key:
                return key.encode()
    except Exception:
        pass
        
    # 3. Si no hay clave configurada, detener la ejecución por seguridad
    raise ValueError(
        "ERROR CRÍTICO DE SEGURIDAD: La clave criptográfica 'AMEM_ENCRYPTION_KEY' no está configurada. "
        "Debe definirse como variable de entorno o en los secrets de Streamlit (.streamlit/secrets.toml)."
    )

cipher_suite = Fernet(get_encryption_key())

def encrypt_data(data: str) -> bytes:
    if not data:
        return b''
    return cipher_suite.encrypt(data.encode())

def decrypt_data(encrypted_data: bytes) -> str:
    if not encrypted_data:
        return ""
    try:
        return cipher_suite.decrypt(encrypted_data).decode()
    except Exception:
        return "[Error al desencriptar / Clave inválida]"

def hash_cuit(cuit: str) -> str:
    """Genera un hash SHA256 determinista del CUIT para búsquedas rápidas e índices sin desencriptar."""
    if not cuit:
        return ""
    # Normalizar CUIT quitando guiones y espacios
    cuit_clean = "".join(filter(str.isdigit, str(cuit)))
    return hashlib.sha256(cuit_clean.encode()).hexdigest()

def hash_password(password: str, salt: bytes = None) -> tuple[bytes, bytes]:
    """Genera un hash seguro PBKDF2 para contraseñas."""
    if salt is None:
        salt = secrets.token_bytes(16)
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return pwdhash, salt

# Conexión a la base de datos
DB_PATH = os.path.join(os.path.dirname(__file__), "amem_audit.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabla de Usuarios para Login
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE NOT NULL,
        password_hash BLOB NOT NULL,
        salt BLOB NOT NULL,
        rol TEXT NOT NULL CHECK(rol IN ('auditor', 'consulta'))
    )
    """)
    
    # Tabla de Clientes (con CUIT y Razón Social encriptados)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        cuit_hash TEXT PRIMARY KEY, -- Hash SHA256 del CUIT para búsquedas indexadas
        cuit_encrypted BLOB NOT NULL, -- CUIT encriptado para mostrar al humano
        nombre_razon_social_encrypted BLOB NOT NULL, -- Nombre encriptado
        categoria TEXT
    )
    """)
    
    # Tabla de Prestaciones (Excel de Gestión)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prestaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        obra_social_nombre TEXT NOT NULL, -- Nombre corto de OS (ej: OSEP, OSDE)
        paciente TEXT,
        fecha_factura TEXT, -- Fecha de la factura asociada en el Excel
        periodo TEXT, -- Periodo (ej: FEBRERO)
        monto REAL NOT NULL,
        factura_nro TEXT,
        forma_pago TEXT,
        fecha_pago TEXT, -- Fecha de cobro registrada en Excel
        estado_conciliacion TEXT DEFAULT 'PENDIENTE_FACTURA',
        mes_auditoria TEXT NOT NULL -- Formato YYYY-MM
    )
    """)
    
    # Tabla de Facturas Emitidas (ARCA/AFIP)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS facturas (
        comprobante_id TEXT PRIMARY KEY, -- Formato: punto_venta-tipo-numero (ej: 00005-011-00000000000000001959)
        cuit_hash TEXT, -- Relación con Clientes
        cuit_txt TEXT, -- CUIT en texto plano (opcional para control rápido de AFIP, ya que es público)
        fecha_emision TEXT NOT NULL,
        monto_total REAL NOT NULL,
        tipo_comprobante TEXT NOT NULL, -- Código AFIP (011, 013, 015, etc.)
        estado TEXT DEFAULT 'ACTIVO', -- ACTIVO / ANULADO
        mes_auditoria TEXT NOT NULL,
        FOREIGN KEY (cuit_hash) REFERENCES clientes(cuit_hash)
    )
    """)
    
    # Tabla de Movimientos Bancarios (Supervielle)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS movimientos_banco (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        hora TEXT,
        concepto TEXT NOT NULL,
        detalle TEXT,
        debito REAL DEFAULT 0,
        credito REAL DEFAULT 0,
        saldo REAL,
        cuit_hash_asociado TEXT, -- Relación detectada con un cliente
        cuit_txt_asociado TEXT,
        mes_auditoria TEXT NOT NULL,
        FOREIGN KEY (cuit_hash_asociado) REFERENCES clientes(cuit_hash)
    )
    """)
    
    # Tabla de Conciliación de Tres Vías
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conciliaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prestacion_id INTEGER,
        factura_id TEXT,
        movimiento_banco_id INTEGER,
        estado_final TEXT NOT NULL CHECK(estado_final IN ('CONCILIADO', 'PENDIENTE_FACTURA', 'PENDIENTE_COBRO', 'DISCREPANCIA', 'INCONSISTENTE')),
        observaciones TEXT,
        mes_auditoria TEXT NOT NULL,
        FOREIGN KEY (prestacion_id) REFERENCES prestaciones(id),
        FOREIGN KEY (factura_id) REFERENCES facturas(comprobante_id),
        FOREIGN KEY (movimiento_banco_id) REFERENCES movimientos_banco(id)
    )
    """)
    
    # Crear índices para búsquedas veloces
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_prestaciones_cuit ON prestaciones(obra_social_nombre)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_facturas_cuit_hash ON facturas(cuit_hash)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_movimientos_cuit_hash ON movimientos_banco(cuit_hash_asociado)")
    
    # Crear usuario administrador por defecto si la tabla está vacía
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        pwd_hash, salt = hash_password("amem2026")
        cursor.execute("""
        INSERT INTO usuarios (usuario, password_hash, salt, rol)
        VALUES (?, ?, ?, ?)
        """, ("admin", pwd_hash, salt, "auditor"))
        
        pwd_hash_consulta, salt_consulta = hash_password("amemconsulta")
        cursor.execute("""
        INSERT INTO usuarios (usuario, password_hash, salt, rol)
        VALUES (?, ?, ?, ?)
        """, ("consulta", pwd_hash_consulta, salt_consulta, "consulta"))
        
    conn.commit()
    conn.close()
    print("Base de datos inicializada correctamente.")

if __name__ == "__main__":
    init_db()
