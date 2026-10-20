import psycopg

#URL exacta de Supabase con el puerto 6543
URL_supabase = "postgresql://postgres.wwtmgbmaxyhklpqwuzbq:Multiservicios@aws-1-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require"

def conectar_bd():
    #Conexión directa a PostgreSQL usando SQL
    try:
        conexion = psycopg.connect(URL_supabase)
        return conexion
    except Exception as e:
        print(f"Error de conexión: {e}")
        return None
