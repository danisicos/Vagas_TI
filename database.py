import json
import mysql.connector
from datetime import datetime, date
from dotenv import load_dotenv
import os
import logging
from logging.handlers import RotatingFileHandler

# Carregar variáveis do .env
load_dotenv()

# Configuração do logging
def setup_logging():

    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    logger = logging.getLogger('concursos_db')
    logger.setLevel(logging.INFO)
    
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'concursos.log'),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=5,
        encoding='utf-8'
    )
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
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
def load_data(json_file):
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
        status = 'Aberto';
    """

    inserted_count = 0
    updated_count = 0
    
    for item in data:
        try:
            processed_at = datetime.fromisoformat(item["processed_at"])

            try:
                start_date = datetime.strptime(item["start_date"], "%d/%m/%Y").date()
            except Exception:
                start_date = None
                logger.warning(f"Data de início inválida para '{item.get('title', 'título não informado')}': {item.get('start_date')}")

            cursor.execute(sql, (
                item["title"],
                item["url"],
                item["state"],
                item.get("job"),
                processed_at,
                start_date,
                item["pdf_url"],
                'Aberto'
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
    """
    Atualiza o status dos concursos para 'Encerrado' quando start_date for menor que a data atual
    """
    cursor = conn.cursor()
    
    sql_update = """
    UPDATE concursos 
    SET status = 'Encerrado'
    WHERE start_date < CURDATE() 
    AND status != 'Encerrado'
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
    """
    Função principal para analisar e atualizar status dos concursos
    """
    logger.info("Iniciando análise de registros para atualização de status")
    
    rows_updated = update_expired_concursos(conn)
    
    if rows_updated > 0:
        logger.info(f"Status atualizado com sucesso para {rows_updated} concursos")
    else:
        logger.info("Nenhum concurso precisou ter o status atualizado")
    
    return rows_updated

def get_status_summary(conn):
    """
    Retorna um resumo dos status dos concursos
    """
    cursor = conn.cursor()
    
    sql = """
    SELECT status, COUNT(*) as total
    FROM concursos 
    GROUP BY status
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
    """
    Função principal do programa
    """
    logger.info("=== INÍCIO DA EXECUÇÃO ===")
    
    try:
        logger.info("Conectando ao banco de dados...")
        conn = mysql.connector.connect(**DB_CONFIG)
        logger.info("Conexão estabelecida com sucesso")
        logger.info("Carregando dados do arquivo JSON...")
        data = load_data("data.json")
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