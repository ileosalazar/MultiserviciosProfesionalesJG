import psycopg

# Mantén tu misma URL exacta de Supabase (con el puerto 6543 y el password seguro)
URL_BASE_DATOS = "postgresql://postgres.wwtmgbmaxyhklpqwuzbq:Multiservicios@aws-1-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require"

def conectar_bd():
    """Crea y devuelve una conexión directa a PostgreSQL usando SQL puro"""
    try:
        conexion = psycopg.connect(URL_BASE_DATOS)
        return conexion
    except Exception as e:
        print(f"Error de conexión: {e}")
        return None

# Prueba rápida
if __name__ == "__main__":
    conn = conectar_bd()
    if conn:
        print("¡Conexión directa para SQL crudo exitosa! 🚀")
        conn.close()