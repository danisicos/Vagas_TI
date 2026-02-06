#!/usr/bin/env python3

import subprocess
import sys
import os
from datetime import datetime

# Pipeline para execução dos scripts de vagas
def run_script(script_name, description):
    print(f"\n{'='*60}")
    print(f"Iniciando: {description}")
    print(f"Script: {script_name}")
    print(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    # Tenta executar o script e mostra informações de erro, caso necessário
    try:
        subprocess.run(
            [sys.executable, script_name],
            check=True,
            capture_output=False,
            text=True,
            cwd=os.path.join(os.path.dirname(os.path.abspath(__file__)), "core")
        )
        
        print(f"\n✓ {description} executado com sucesso!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n✗ ERRO ao executar {description}!")
        print(f"Código de saída: {e.returncode}")
        if e.stderr:
            print(f"Erro: {e.stderr}")
        return False
        
    except FileNotFoundError:
        print(f"\n✗ Arquivo não encontrado: {script_name}")
        return False
        
    except Exception as e:
        print(f"\n✗ Erro inesperado ao executar {description}: {e}")
        return False

# Função principal que executa o pipeline
def main():
    print(f"\n{'#'*70}")
    print("INICIANDO PIPELINE DE PROCESSAMENTO")
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*70}")
    
    # Definição dos scripts na ordem de execução
    scripts = [
        {
            "file": "scraper.py",
            "description": "Scraper - Coleta de concursos do PCI Concursos"
        },
        {
            "file": "cleaner.py", 
            "description": "Cleaner - Limpeza de dados expirados"
        },
        {
            "file": "database.py",
            "description": "Database - Inserção/Atualização no banco de dados"
        }
    ]
    
    # Verifica se todos os scripts existem antes de começar
    missing_scripts = []
    for script in scripts:
        if not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "core", script["file"])):
            missing_scripts.append(script["file"])
    
    if missing_scripts:
        print(f"\n✗ Scripts não encontrados: {', '.join(missing_scripts)}")
        print("Certifique-se de que todos os scripts estão no diretório 'core' em relação ao main.py.")
        return False
    
    # Executa cada script em ordem
    for i, script in enumerate(scripts, 1):
        print(f"\n[Etapa {i}/3] Executando: {script['description']}")
        
        success = run_script(script["file"], script["description"])
        
        if not success:
            print(f"\n{'!'*70}")
            print("PIPELINE INTERROMPIDO!")
            print(f"O script {script['file']} falhou.")
            print("Scripts não executados:")
            for remaining in scripts[i:]:
                print(f"  - {remaining['description']}")
            print(f"{'!'*70}")
            return False
    
    # Pipeline completo executado com sucesso
    print(f"\n{'#'*70}")
    print("PIPELINE CONCLUÍDO COM SUCESSO!")
    print("Todos os scripts foram executados na ordem correta.")
    print(f"Data/Hora final: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*70}")
    
    return True

if __name__ == "__main__":
    # Configura para mostrar todas as saídas dos scripts em tempo real
    success = main()
    sys.exit(0 if success else 1)