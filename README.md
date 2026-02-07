# Vagas TI - Scraper de Concursos

Este projeto é um pipeline automatizado para coletar, processar e armazenar informações sobre concursos públicos na área de Tecnologia da Informação (TI). Ele busca dados do site "PCI Concursos", filtra por cargos de interesse, limpa dados expirados e armazena as informações relevantes em um banco de dados MySQL.

## 🚀 Funcionalidades

- **Scraper (`scraper.py`)**: Coleta novos concursos do site PCI Concursos, filtrando especificamente por cargos de TI definidos no sistema.
- **Cleaner (`cleaner.py`)**: Remove registros que já expiraram ou que não possuem data de início válida, mantendo a base de dados limpa.
- **Database (`database.py`)**: Insere e atualiza as informações no banco de dados MySQL, gerenciando o status dos concursos (Aberto, Encerrado, Cancelado).
- **Orquestrador (`main.py`)**: Gerencia a execução sequencial dos scripts acima, garantindo o fluxo correto de dados.

## 📋 Pré-requisitos

- Python 3.8 ou superior
- MySQL Server
- **Importante**: O projeto assume a existência do diretório `/var/www/vagas/data/` para armazenar arquivos JSON temporários (`data.json`, `processed.json`). Certifique-se de que este diretório exista e que o usuário que executa o script tenha permissões de escrita nele.

## 🛠️ Instalação

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/seu-usuario/vagas-ti.git
   cd vagas-ti
   ```

2. **Crie um ambiente virtual (recomendado):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/Mac
   # ou
   venv\Scripts\activate  # Windows
   ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Prepare o diretório de dados:**
   ```bash
   sudo mkdir -p /var/www/vagas/data
   sudo chown -R $USER:$USER /var/www/vagas/data
   ```

## ⚙️ Configuração

Crie um arquivo `.env` na raiz do projeto com as credenciais do seu banco de dados MySQL. Você pode usar o modelo abaixo:

```env
DB_HOST=localhost
DB_USER=seu_usuario
DB_PASSWORD=sua_senha
DB_NAME=nome_do_banco
DB_PORT=3306
```

## 🗄️ Estrutura do Banco de Dados

O sistema utiliza uma tabela chamada `concursos`. Execute o seguinte script SQL no seu banco de dados para criá-la:

```sql
CREATE TABLE IF NOT EXISTS concursos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    url VARCHAR(255) UNIQUE NOT NULL,
    state VARCHAR(50),
    job VARCHAR(255),
    processed_at DATETIME,
    start_date DATE,
    pdf_url VARCHAR(255),
    status ENUM('Aberto', 'Encerrado', 'Cancelado') DEFAULT 'Aberto',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

## ▶️ Uso

Para executar o pipeline completo (coleta, limpeza e armazenamento), execute o script principal:

```bash
python main.py
```

O script executará as etapas na seguinte ordem:
1. **Scraper**: Busca novas vagas.
2. **Cleaner**: Limpa vagas expiradas do arquivo local.
3. **Database**: Sincroniza os dados com o banco de dados MySQL.

## 📂 Estrutura do Projeto

```
.
├── core/
│   ├── base.py       # Definições de cargos e constantes
│   ├── cleaner.py    # Limpeza de dados locais
│   ├── database.py   # Interação com o banco de dados
│   └── scraper.py    # Lógica de scraping
├── main.py           # Script principal (entry point)
├── requirements.txt  # Dependências do projeto
├── README.md         # Documentação
└── .env              # Variáveis de ambiente (não versionado)
```

## 🤝 Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou enviar pull requests.

## License

[MIT](https://choosealicense.com/licenses/mit/)
