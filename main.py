import os
import re
import json
import asyncio
import aiohttp
import discord
from discord.ext import commands, tasks
from bs4 import BeautifulSoup
from io import BytesIO
from PyPDF2 import PdfReader
from dotenv import load_dotenv
from datetime import datetime

# Carrega variáveis de ambiente
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID', '0'))

# URLs base
BASE_URL = 'https://www.pciconcursos.com.br'
HOME_URL = f'{BASE_URL}/concursos/'

# Arquivos locais
PROCESSED_FILE = 'processed.json'
DATA_FILE = r'C:\Users\luisg\Documents\GitHub\Vagas_TI\data.json'

# Palavras-chave TI
CARGOS = [
    'analista de banco de dados', 'analista desenvolvedor', 'analista de desenvolvimento',
    'analista de tecnologia da informação', 'técnico de tecnologia da informação',
    'analista de suporte', 'analista de redes', 'analista de sistemas',
    'analista de informática', 'analista em sistemas de informação',
    'desenvolvedor de software', 'programador', 'técnico de informática',
    'tecnologista da informação', 'operador de sistemas', 'analista de ti',
    'técnico bancário iii', 'técnico bancário novo tecnologia da informação – tbn/ti',
    'agente de tecnologia', 'gerência de ti'
]

MATERIAS = [
    'arquitetura cliente-servidor', 'arquitetura de software', 'arquitetura mvc',
    'ci/cd', 'cmmi', 'clean code', 'cobit', 'codificação limpa', 'data lake',
    'data mining', 'data warehouse', 'design patterns', 'devops', 'engenharia de requisitos',
    'engenharia de software', 'entidade-relacionamento', 'extreme programming', 'html/css',
    'html5', 'hibernate', 'infraestrutura de ti', 'inteligência artificial', 'itil', 'jakartaee', 'java',
    'javaee', 'javascript', 'junit', 'low-code', 'machine learning', 'mps-br',
    'microsserviços', 'mysql', 'no-code', 'nosql', 'owasp', 'oracle',
    'pl/sql', 'pmbok', 'postgresql', 'qualidade de software', 'react', 'ruby',
    'scrum', 'sgd/me nº 94', 'soap', 'sql', 'sql server', 'springboot', 'story points',
    'stored procedure', 'swagger', 'tcp', 'tcp/ip', 'tdd', 'testes de software', 'trigger',
    'typescript', 'vue.js', 'web services', 'webapi', 'aprendizado de máquina',
    'governança de ti', 'node.js', 'docker', 'kubernetes', 'orientação a objetos', 'middleware', 'apis rest',
    'api rest', 'rest/graphql', 'sonarqube', 'single sign-on', 'oauth', 'containers'
]

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

processed = set()
data_list = []

# Funções de persistência JSON
def load_json_set(path):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except:
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
        except:
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
    except:
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

def normalize(text: str) -> str:
    text = re.sub(r'[^\w\s]', ' ', text, flags=re.UNICODE)
    text = re.sub(r'\s+', ' ', text)
    return text.lower()

async def search_pdf(session, pdf_url: str) -> dict | None:
    data = await fetch(session, pdf_url)
    try:
        reader = PdfReader(BytesIO(data))
        raw_text = ''.join(page.extract_text() or '' for page in reader.pages)
        text = normalize(raw_text)
        found_cargos = [kw for kw in CARGOS if normalize(kw) in text]
        found_materias = [kw for kw in MATERIAS if normalize(kw) in text]
        print(f"[DEBUG] PDF {pdf_url} -> cargos encontrados: {found_cargos}")
        print(f"[DEBUG] PDF {pdf_url} -> matérias encontradas: {found_materias}")
        found_cargos = list(dict.fromkeys(found_cargos))
        found_materias = list(dict.fromkeys(found_materias))
        if len(found_materias) >= 3 or found_cargos:
            return {"materias": found_materias, "cargos": found_cargos}
    except Exception as e:
        print(f"[search_pdf] Erro ao ler PDF {pdf_url}: {e}")
    return None

@tasks.loop(minutes=60)
async def check_and_notify():
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        return
    async with aiohttp.ClientSession() as session:
        contests = await parse_homepage(session)
        for c in contests:
            url = c['url']
            if url in processed:
                continue
            processed.add(url)
            persist_state()
            pdf_urls = await extract_pdf_urls(session, url)
            chosen_pdf = None
            edital_data = None
            for pdf_url in pdf_urls:
                result = await search_pdf(session, pdf_url)
                if result:
                    chosen_pdf = pdf_url
                    edital_data = result
                    break
            job_title = None
            materias_list = None
            if edital_data:
                if edital_data.get('cargos'):
                    job_title = edital_data['cargos'][0]
                elif len(edital_data.get('materias', [])) >= 3:
                    job_title = "Cargo não encontrado"
                materias_list = edital_data['materias']
            if not job_title:
                print(f"[DEBUG] Ignorado: sem dados relevantes no edital de {c['title']}")
                continue
            start_date, end_date = parse_date_range(c['date'])
            if is_expired(start_date, end_date):
                continue
            entry = {
                'title': c['title'], 'url': url, 'state': c['state'], 'job': job_title
            }
            if start_date:
                entry['start_date'] = start_date
            if end_date:
                entry['end_date'] = end_date
            if materias_list:
                entry['materias'] = materias_list
            if chosen_pdf:
                entry['pdf_url'] = chosen_pdf
            data_list.append(entry)
            persist_state()
            mat_str = ', '.join(materias_list) if materias_list else "N/D"
            msg = f"## {c['title']}\n"
            msg += f"----------------------------------------\n"
            msg += f"**📜 Estado:** {c['state']}\n"
            msg += f"----------------------------------------\n"
            if start_date and end_date:
                msg += f"**🗓️ Inscrições:** de {start_date} até {end_date}\n"
            elif start_date:
                msg += f"**🗓️ Inscrições até:** {start_date}\n"
            else:
                msg += f"**🗓️ Inscrições:** Data indefinida\n"
            msg += f"----------------------------------------\n"
            msg += f"**💼 Cargo:** {job_title}\n"
            msg += f"----------------------------------------\n"
            if materias_list:
                msg += f"**📚 Matérias:** {mat_str}\n"
                msg += f"----------------------------------------\n"
            if chosen_pdf:
                msg += f"**📒 Edital:** {chosen_pdf}\n"
                msg += f"----------------------------------------\n"
            msg += f"**💻 Link do concurso:** {url}\n"
            msg += f"----------------------------------------\n"
            await channel.send(msg)

@bot.event
async def on_ready():
    init_state()
    check_and_notify.start()

if __name__ == '__main__':
    bot.run(TOKEN)