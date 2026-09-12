FROM python:3.13-slim

WORKDIR /app

# COPY explícito do requirements primeiro pra cachear a camada de instalação
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# COPY explícito: só o que o pipeline precisa. O .env NUNCA entra na imagem.
COPY main.py ./
COPY core/ ./core/

# scraper.py/cleaner.py/database.py leem/escrevem em /var/www/vagas/data;
# criado aqui pra não depender de root no volume montado.
RUN mkdir -p /var/www/vagas/data

CMD ["python", "main.py"]
