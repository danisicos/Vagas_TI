import json
import mysql.connector
from datetime import datetime, date
from dotenv import load_dotenv
import os
import logging
import sys

# Carregar variáveis do .env
load_dotenv()

# Configuração do logging SIMPLIFICADA
def setup_logging():
    logger = logging.getLogger('concursos_db')
    logger.setLevel(logging.INFO)
    
    # Remove handlers existentes para evitar duplicação
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Handler para stdout (que será capturado pelo cron)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    
    # Formato simples
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    stdout_handler.setFormatter(formatter)
    
    logger.addHandler(stdout_handler)
    
    return logger

logger = setup_logging()

# Configuração do banco de dados
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "port": int(os.getenv("DB_PORT", 3306))
}

# Funções principais
def load_data(json_file=None):
    if json_file is None:
        json_file = "/var/www/vagas/data.json"
    
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            logger.info(f"Dados carregados com sucesso do arquivo {json_file}. Total de registros: {len(data)}")
            return data
    except FileNotFoundError:
        logger.error(f"Arquivo {json_file} não encontrado")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON do arquivo {json_file}: {e}")
        raise

def determine_status_and_date(item):
    if "start_date" not in item or item["start_date"] is None:
        logger.info(f"Concurso identificado como Cancelado: '{item.get('title', 'título não informado')}'")
        return None, "Cancelado"
    
    try:
        start_date = datetime.strptime(item["start_date"], "%d/%m/%Y").date()
        status = "Encerrado" if start_date < date.today() else "Aberto"
        return start_date, status
    except Exception:
        logger.warning(f"Data de início inválida para '{item.get('title', 'título não informado')}': {item.get('start_date')} - Marcado como Cancelado")
        return None, "Cancelado"

def insert_data(conn, data):
    cursor = conn.cursor()

    sql = """
    INSERT INTO concursos (title, url, state, job, processed_at, start_date, pdf_url, status)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        title = VALUES(title),
        state = VALUES(state),
        job = VALUES(job),
        processed_at = VALUES(processed_at),
        start_date = VALUES(start_date),
        pdf_url = VALUES(pdf_url),
        status = VALUES(status);
    """

    inserted_count = 0
    updated_count = 0
    
    for item in data:
        try:
            processed_at = datetime.fromisoformat(item["processed_at"])
            start_date, status = determine_status_and_date(item)

            cursor.execute(sql, (
                item["title"],
                item["url"],
                item["state"],
                item.get("job"),
                processed_at,
                start_date,
                item.get("pdf_url"),
                status
            ))
            
            if cursor.rowcount == 1:
                inserted_count += 1
            elif cursor.rowcount == 2:
                updated_count += 1
                
        except Exception as e:
            logger.error(f"Erro ao processar item '{item.get('title', 'título não informado')}': {e}")
            continue

    conn.commit()
    cursor.close()
    
    logger.info(f"Processamento concluído - Inseridos: {inserted_count}, Atualizados: {updated_count}")

def update_expired_concursos(conn):
    cursor = conn.cursor()
    
    sql_update = """
    UPDATE concursos 
    SET status = 'Encerrado'
    WHERE start_date < CURDATE() 
    AND status NOT IN ('Encerrado', 'Cancelado')
    AND start_date IS NOT NULL
    """
    
    try:
        cursor.execute(sql_update)
        rows_affected = cursor.rowcount
        conn.commit()
        
        logger.info(f"Análise de status concluída - {rows_affected} concursos marcados como 'Encerrado'")
        
    except Exception as e:
        logger.error(f"Erro ao atualizar status dos concursos: {e}")
        conn.rollback()
        rows_affected = 0
    finally:
        cursor.close()
    
    return rows_affected

def analyze_and_update_status(conn):
    logger.info("Iniciando análise de registros para atualização de status")
    
    rows_updated = update_expired_concursos(conn)
    
    if rows_updated > 0:
        logger.info(f"Status atualizado com sucesso para {rows_updated} concursos")
    else:
        logger.info("Nenhum concurso precisou ter o status atualizado")
    
    return rows_updated

def get_status_summary(conn):
    cursor = conn.cursor()
    
    sql = """
    SELECT 
        CASE 
            WHEN status IS NULL THEN 'Sem Status'
            ELSE status 
        END as status, 
        COUNT(*) as total
    FROM concursos 
    GROUP BY status
    ORDER BY total DESC
    """
    
    try:
        cursor.execute(sql)
        results = cursor.fetchall()

        logger.info("Resumo dos status dos concursos:")
        for status, count in results:
            logger.info(f"  {status}: {count} concursos")
            
        return results
    except Exception as e:
        logger.error(f"Erro ao obter resumo dos status: {e}")
        return []
    finally:
        cursor.close()
        
def main():
    logger.info("=== INÍCIO DA EXECUÇÃO ===")
    
    try:
        logger.info("Conectando ao banco de dados...")
        conn = mysql.connector.connect(**DB_CONFIG)
        logger.info("Conexão estabelecida com sucesso")
        logger.info("Carregando dados do arquivo JSON...")
        data = load_data()
        logger.info("Inserindo/atualizando dados no banco...")
        insert_data(conn, data)
        analyze_and_update_status(conn)
        get_status_summary(conn)
        logger.info("Processamento concluído com sucesso!")
    except mysql.connector.Error as err:
        logger.error(f"Erro no banco de dados: {err}")
        return False
    except FileNotFoundError:
        logger.error("Arquivo data.json não encontrado!")
        return False
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        return False
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()
            logger.info("Conexão com o banco encerrada")
    
    logger.info("=== FIM DA EXECUÇÃO ===")
    return True

if __name__ == "__main__":
    success = main()