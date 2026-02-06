import json
from datetime import datetime

DATA_FILE = '/var/www/vagas/data/data.json'

def str_to_date(date_str: str):
    return datetime.strptime(date_str, "%d/%m/%Y").date()

def clean_data():
    """Remove registros sem start_date ou com datas expiradas"""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data_list = json.load(f)
    except FileNotFoundError:
        print(f"Arquivo {DATA_FILE} não encontrado")
        return
    
    today = datetime.today().date()
    original_count = len(data_list)
    
    cleaned_list = []
    removed_empty = 0
    removed_expired = 0
    
    for entry in data_list:
        start_date = entry.get('start_date')
        
        # Remove se não tiver start_date
        if not start_date:
            removed_empty += 1
            continue
            
        # Remove se a data já passou
        try:
            if str_to_date(start_date) < today:
                removed_expired += 1
                continue
        except Exception as e:
            print(f"Erro ao processar data '{start_date}': {e}")
            # Em caso de erro, mantém o registro
            cleaned_list.append(entry)
            continue
            
        cleaned_list.append(entry)
    
    # Salva dados limpos
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(cleaned_list, f, ensure_ascii=False, indent=2)
    
    print("\n=== Limpeza Concluída ===")
    print(f"Registros originais: {original_count}")
    print(f"Removidos sem data: {removed_empty}")
    print(f"Removidos expirados: {removed_expired}")
    print(f"Total removidos: {removed_empty + removed_expired}")
    print(f"Registros restantes: {len(cleaned_list)}")

if __name__ == '__main__':
    clean_data()