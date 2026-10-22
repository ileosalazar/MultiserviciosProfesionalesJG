import psycopg


URL_supabase = "postgresql://postgres.wwtmgbmaxyhklpqwuzbq:Multiservicios@aws-1-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require"

def conectar_bd():
    try:
        conexion = psycopg.connect(URL_supabase)
        return conexion
    except Exception as e:
        print(f"Error de conexión: {e}")
        return None
