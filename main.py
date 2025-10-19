import os, re, json, asyncio, aiohttp, unicodedata
from bs4 import BeautifulSoup
from io import BytesIO
from PyPDF2 import PdfReader
from dotenv import load_dotenv
from datetime import datetime
from base import CARGOS

BASE_URL = 'https://www.pciconcursos.com.br'
HOME_URL = f'{BASE_URL}/concursos/'
BASE_DIR = '/var/www/vagas'
DATA_FILE = os.path.join(BASE_DIR, 'data.json')
PROCESSED_FILE = os.path.join(BASE_DIR, 'processed.json')

processed = set()
data_list = []

# Função para normalizar texto
def normalizar_texto(texto):
    if not texto:
        return ""

    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(char for char in texto if unicodedata.category(char) != 'Mn')
    
    texto = texto.lower()
    
    texto = re.sub(r'[^\w\s]', ' ', texto, flags=re.UNICODE)
    texto = re.sub(r'\s+', ' ', texto)
    
    return texto.strip()

def buscar_cargos(texto_edital):

    texto_normalizado = normalizar_texto(texto_edital)
    cargos_encontrados = []
    
    if not hasattr(buscar_cargos, 'cargos_normalizados'):
        buscar_cargos.cargos_normalizados = {
            cargo: normalizar_texto(cargo) for cargo in CARGOS
        }
    
    for cargo_original, cargo_normalizado in buscar_cargos.cargos_normalizados.items():
        if cargo_normalizado in texto_normalizado:
            cargos_encontrados.append(cargo_original)
    
    return list(dict.fromkeys(cargos_encontrados))

def load_json_set(path):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_json_set(data_set, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(list(data_set), f, ensure_ascii=False, indent=2)

def load_json_list(path):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_json_list(lst, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(lst, f, ensure_ascii=False, indent=2)

def init_state():
    global processed, data_list
    processed = load_json_set(PROCESSED_FILE)
    data_list = load_json_list(DATA_FILE)
    print(f"[init_state] processed={len(processed)}, data_list={len(data_list)}")

def persist_state():
    save_json_set(processed, PROCESSED_FILE)
    save_json_list(data_list, DATA_FILE)
    print(f"[persist_state] saved processed={len(processed)}, data_list={len(data_list)}")

def parse_date_range(raw_date: str):
    m = re.search(r"(\d{2}/\d{2}/\d{4})\s*a\s*(\d{2}/\d{2}/\d{4})", raw_date)
    if m:
        return m.group(1), m.group(2)
    m2 = re.search(r"(\d{2}/\d{2}/\d{4})", raw_date)
    if m2:
        return m2.group(1), None
    return None, None

def str_to_date(date_str: str):
    return datetime.strptime(date_str, "%d/%m/%Y").date()

def is_expired(start: str, end: str):
    today = datetime.today().date()
    try:
        if end:
            return str_to_date(end) < today
        elif start:
            return str_to_date(start) < today
    except Exception:
        pass
    return False

async def fetch(session, url: str) -> bytes:
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
        resp.raise_for_status()
        return await resp.read()

async def parse_homepage(session) -> list:
    html = await fetch(session, HOME_URL)
    soup = BeautifulSoup(html, 'html.parser')
    contests = []
    for div in soup.find_all('div', attrs={'data-url': True}):
        rel = div['data-url']
        url = rel if rel.startswith('http') else BASE_URL + rel
        a = div.find('a')
        title = a.get('title', '').strip() if a else 'Sem título'
        state = div.find('div', class_='cc').get_text(strip=True) or 'NACIONAL'
        ce = div.find('div', class_='ce')
        date = 'Em breve'
        if ce and ce.find('span'):
            raw = ''.join(ce.find('span').strings)
            date = raw.replace('Até', '').strip()
        contests.append({'title': title, 'url': url, 'state': state, 'date': date})
    return contests

async def extract_pdf_urls(session, contest_url: str) -> list[str]:
    html = await fetch(session, contest_url)
    soup = BeautifulSoup(html, 'html.parser')
    links = soup.find_all('a', title=re.compile(r'EDITAL DE ABERTURA', re.I))
    pdf_urls = []
    for a in links:
        href = a.get('href')
        if href:
            pdf_urls.append(href if href.startswith('http') else BASE_URL + href)
    if not pdf_urls:
        for a in soup.find_all('a', href=re.compile(r'\.pdf$', re.I)):
            href = a['href']
            pdf_urls.append(href if href.startswith('http') else BASE_URL + href)
    seen = set()
    unique = []
    for u in pdf_urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique

async def search_pdf(session, pdf_url: str) -> dict | None:
    try:
        data = await fetch(session, pdf_url)
        reader = PdfReader(BytesIO(data))
        raw_text = ''.join(page.extract_text() or '' for page in reader.pages)
        
        found_cargos = buscar_cargos(raw_text)
        
        print(f"[DEBUG] PDF {pdf_url} -> cargos encontrados: {found_cargos}")
        
        if found_cargos:
            return {"cargos": found_cargos}
    except Exception as e:
        print(f"[search_pdf] Erro ao ler PDF {pdf_url}: {e}")
    return None

async def process_contest(session, c, i, total):
    url = c['url']
    print(f"Processando {i}/{total}: {c['title']}")

    if url in processed:
        print("  -> Já processado anteriormente")
        return False

    processed.add(url)
    persist_state()

    try:
        pdf_urls = await extract_pdf_urls(session, url)
        print(f"  -> Encontrados {len(pdf_urls)} PDFs")

        chosen_pdf, edital_data = await find_first_relevant_pdf(session, pdf_urls)

        job_title, all_jobs = extract_job_info(edital_data)

        if not job_title:
            print("  -> Ignorado: sem dados relevantes de TI")
            return False

        start_date, end_date = parse_date_range(c['date'])
        if is_expired(start_date, end_date):
            print("  -> Ignorado: concurso expirado")
            return False

        entry = build_entry(c, job_title, all_jobs, start_date, end_date, chosen_pdf)
        data_list.append(entry)
        persist_state()

        print(f"  -> ADICIONADO: {job_title} (total: {len(all_jobs)} cargos de TI)")
        return True

    except Exception as e:
        print(f"  -> Erro ao processar concurso: {e}")
        return False

async def find_first_relevant_pdf(session, pdf_urls):
    for pdf_url in pdf_urls:
        result = await search_pdf(session, pdf_url)
        if result:
            return pdf_url, result
    return None, None

def extract_job_info(edital_data):
    if edital_data and edital_data.get('cargos'):
        all_jobs = edital_data['cargos']
        job_title = all_jobs[0]
        return job_title, all_jobs
    return None, []

def build_entry(c, job_title, all_jobs, start_date, end_date, chosen_pdf):
    entry = {
        'title': c['title'],
        'url': c['url'],
        'state': c['state'],
        'job': job_title,
        'all_jobs': all_jobs,
        'processed_at': datetime.now().isoformat()
    }
    if start_date:
        entry['start_date'] = start_date
    if end_date:
        entry['end_date'] = end_date
    if chosen_pdf:
        entry['pdf_url'] = chosen_pdf
    return entry

async def check_and_process():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iniciando verificação de concursos...")

    async with aiohttp.ClientSession() as session:
        try:
            contests = await parse_homepage(session)
            print(f"Encontrados {len(contests)} concursos na página inicial")

            new_contests = 0
            total = len(contests)
            for i, c in enumerate(contests, 1):
                added = await process_contest(session, c, i, total)
                if added:
                    new_contests += 1
            print(f"Processamento finalizado! {new_contests} novos concursos adicionados.")

        except Exception as e:
            print(f"Erro durante o processamento: {e}")

def run_once():
    asyncio.run(check_and_process())

if __name__ == '__main__':
    init_state()
    run_once()