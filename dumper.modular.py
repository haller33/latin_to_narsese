#!/usr/bin/env python3
"""
Traduz entradas de dicionário (HTML) para Narsese usando LLM.
Suporta Groq API ou Ollama local.
"""

import os
import sys
import sqlite3
import hashlib
import subprocess
import time
import json
import logging
import re
from typing import Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ========== CONFIGURAÇÕES ==========
DB_FILE = "latin_portuguese.bkp.db"
DB_TRANSLATIONS = "narseses_latim_portugues.db"
HASH_TO_AVOID = '32aaccb0c4597738cc2fca23b28557802587b9a9fa91d5c8c54beae8aedee5d9'
SLEEP_SECONDS = 80      # atraso entre requisições
RETRY_DELAY = 180       # atraso base para retentativas

# Backend (variáveis de ambiente)
BACKEND = os.environ.get("TRANSLATE_BACKEND", "ollama").lower()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "devstral:24b")

# Prompt (idêntico ao original)
PROMPT = """Você traduz frases do português para Narsese (lógica NARS). Siga estas regras rigorosamente.

## Sintaxe (resumida)
- Herança: `<A --> B>`   (A é um B / A tem propriedade B)
- Similaridade: `<A <-> B>`    (A é equivalente a B – use com moderação!)
- Implicação: `<P ==> Q>`
- Temporal: `<P =/> Q>`
- Conjunção: `(&&, A, B)`
- Negação: `(--, A)`
- Produto (contexto): `(A * B)`
- Variáveis: `#1`, `$1`
- Valor de verdade: `%freq;conf%` (opcional)
- Terminação: `.` (crença), `?` (pergunta), `!` (objetivo)

## Regras principais (obrigatórias)
1. **Toda declaração deve começar com `<` e terminar com `>.`** – incluindo aquelas que usam produto `(A * B)`.
   Exemplo correto: `< (amor * {sentimento}) --> amizade >.`
   Exemplo incorreto: `(amor * {sentimento}) --> amizade.` (falta `<` e `>`)

2. Saída apenas Narsese, uma declaração por linha, sem texto extra.

3. Use `<->` **apenas** quando dois termos forem verdadeiramente equivalentes em todos os contextos (ex.: "solteiro = homem não casado" em contexto normal).

4. **Para palavras de dicionário com múltiplos significados** (polissemia):
   - **Não** use `<->` para cada significado.
   - Use herança com contexto: `< (palavra * {sentido}) --> significado >.`
   - Exemplo: `< (arena * {material}) --> areia >.`  (e não `<arena <-> areia>`)

5. **Evite tautologias e auto‑referências vazias** – não gere declarações como `< (asilo * {lugar}) --> asilo >.` (o mesmo termo dos dois lados). Isso não acrescenta informação.

6. **Não misture categorias ontológicas** – um lugar não é uma pessoa, um material não é um prédio. Use contextos diferentes.

7. **Comentários**: comece a linha com `//` – nunca depois de uma declaração.

## Exemplos em português (com sintaxe correta)

| Frase em português | Narsese correto (observe os `< >`) |
|-------------------|--------------------------------------|
| A palavra latina "arena" significa areia (sentido material) | `< (arena * {material}) --> areia >.` |
| "Arena" significa anfiteatro (sentido de lugar) | `< (arena * {lugar}) --> anfiteatro >.` |
| "Arena" significa gladiador (metonímia) | `< (arena * {lutador}) --> gladiador >.` |
| Solteiro é um homem não casado (contexto normal) | `< (solteiro * {normal}) <-> (homem & (--, casado)) >.` |
| O Papa não é solteiro (90% de confiança) | `< {papa} --> (homem & (--, casado)) >. < {papa} --> solteiro >. %0.00;0.90%.` |
| Um gato está sobre o tapete | `< ({gato} * {tapete}) --> sobre >.` |
| Se chover, então o chão fica molhado | `< chover ==> < chao --> molhado > >.` |
| Alguém comeu a pizza? | `< (&&, < #1 --> comeu >, < ({pizza} * #1) --> [objeto_de] >) >?` |

## Sua tarefa
Traduza as seguintes frases em português para Narsese. Saída apenas Narsese, uma por linha, **sempre com `<` e `>` delimitando cada declaração**.

"""

# ========== LOGGING ==========
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ========== FUNÇÕES AUXILIARES ==========
def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def html_to_text(html: str) -> str:
    """Converte HTML para texto puro usando pandoc."""
    try:
        proc = subprocess.run(
            ['pandoc', '-f', 'html', '-t', 'plain'],
            input=html.encode('utf-8'),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return proc.stdout.decode('utf-8').replace('\n', ' ').strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Pandoc error: {e.stderr.decode()}")
        raise

def create_tables():
    """Cria tabela translations se não existir."""
    with sqlite3.connect(DB_TRANSLATIONS) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS translations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word_hash TEXT UNIQUE NOT NULL,
                input_hash TEXT UNIQUE NOT NULL,
                input_text TEXT NOT NULL,
                narsese_output TEXT,
                narsese_hash TEXT,
                model TEXT,
                raw_output TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
def get_unprocessed_words() -> list:
    """
    Retorna lista de word_hash que precisam ser processados.
    Separa as consultas: primeiro pega todos os candidatos do dicionário,
    depois remove os que já existem na tabela translations (outro banco).
    """
    # 1. Obtém todos os word_hash do dicionário (exceto o hash a evitar)
    with sqlite3.connect(DB_FILE) as conn_dict:
        cursor = conn_dict.execute(
            "SELECT word_hash FROM dictionary WHERE content_hash != ?",
            (HASH_TO_AVOID,)
        )
        candidate_hashes = {row[0] for row in cursor.fetchall()}

    # 2. Obtém todos os word_hash já traduzidos (do banco de traduções)
    with sqlite3.connect(DB_TRANSLATIONS) as conn_trans:
        cursor = conn_trans.execute("SELECT word_hash FROM translations")
        processed_hashes = {row[0] for row in cursor.fetchall()}

    # 3. Retorna a diferença (candidatos não processados)
    unprocessed = list(candidate_hashes - processed_hashes) # não preserva ordem, mas faz a diferença entre dois sets, o que está otimo.
    logger.info(f"Candidatos totais: {len(candidate_hashes)}, já processados: {len(processed_hashes)}, a processar: {len(unprocessed)}")
    return unprocessed

def get_raw_html(word_hash: str) -> str:
    with sqlite3.connect(DB_FILE) as conn:
        row = conn.execute("SELECT raw_html FROM dictionary WHERE word_hash = ?", (word_hash,)).fetchone()
        if not row:
            raise ValueError(f"Word hash {word_hash} not found")
        return row[0]

def save_translation(word_hash: str, input_text: str, narsese_output: str, model: str, raw_response: str):
    input_hash = compute_hash(input_text)
    narsese_hash = compute_hash(narsese_output)
    with sqlite3.connect(DB_TRANSLATIONS) as conn:
        conn.execute("""
            INSERT INTO translations (word_hash, input_hash, input_text, narsese_output, narsese_hash, model, raw_output)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (word_hash, input_hash, input_text, narsese_output, narsese_hash, model, raw_response))

# ========== BACKENDS ==========
def call_groq(prompt_full: str) -> Tuple[str, str]:
    """Retorna (narsese_output, raw_json_response)."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY não definida")
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt_full}],
        "stream": False,
        "temperature": 0.0
    }
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500,502,503,504])
    session.mount('https://', HTTPAdapter(max_retries=retries))

    while True:
        try:
            resp = session.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if 'error' in data:
                msg = data['error'].get('message', '')
                if 'rate limit' in msg.lower():
                    match = re.search(r'(\d+)m([\d.]+)s', msg)
                    if match:
                        wait = int(match.group(1))*60 + float(match.group(2))
                        logger.warning(f"Rate limit: aguardando {wait:.0f}s")
                        time.sleep(wait)
                        continue
                    else:
                        logger.warning("Rate limit: aguardando 60s")
                        time.sleep(60)
                        continue
                raise Exception(f"Erro Groq: {msg}")
            return data['choices'][0]['message']['content'], json.dumps(data)
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro rede: {e}. Tentando novamente em {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)
        except Exception as e:
            logger.error(f"Erro permanente: {e}")
            raise
        
def call_ollama(prompt_full: str) -> Tuple[str, str]:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt_full}],
        "options": {"temperature": 0.0},
        "stream": False
    }
    while True:
        try:
            # Remove o timeout (None) ou define um valor alto, ex: 600 segundos
            resp = requests.post(OLLAMA_URL, json=payload, timeout=None)
            resp.raise_for_status()
            data = resp.json()
            if 'error' in data:
                raise Exception(f"Erro Ollama: {data['error']}")
            return data['message']['content'], json.dumps(data)
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro conexão Ollama: {e}. Tentando em {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)
        except Exception as e:
            logger.error(f"Erro permanente: {e}")
            raise
        
def call_ollama_old(prompt_full: str) -> Tuple[str, str]:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt_full}],
        "options": {"temperature": 0.0},
        "stream": False
    }
    while True:
        try:
            resp = requests.post(OLLAMA_URL, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            if 'error' in data:
                raise Exception(f"Erro Ollama: {data['error']}")
            return data['message']['content'], json.dumps(data)
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro conexão Ollama: {e}. Tentando em {RETRY_DELAY}s...")
            time.sleep(RETRY_DELAY)
        except Exception as e:
            logger.error(f"Erro permanente: {e}")
            raise

def translate_text(input_text: str) -> Tuple[str, str]:
    full_prompt = PROMPT + input_text
    if BACKEND == 'groq':
        return call_groq(full_prompt)
    elif BACKEND == 'ollama':
        return call_ollama(full_prompt)
    else:
        raise ValueError(f"Backend desconhecido: {BACKEND}")

# ========== MAIN ==========
def main():
    create_tables()
    words = get_unprocessed_words()
    logger.info(f"Total de palavras a processar: {len(words)}")

    for idx, w_hash in enumerate(words, 1):
        logger.info(f"Processando {idx}/{len(words)}: {w_hash}")
        try:
            # Evita duplicata (caso outro processo tenha inserido)
            with sqlite3.connect(DB_TRANSLATIONS) as conn:
                if conn.execute("SELECT 1 FROM translations WHERE word_hash = ?", (w_hash,)).fetchone():
                    logger.info(f"Palavra {w_hash} já processada, ignorando")
                    continue

            raw_html = get_raw_html(w_hash)
            input_text = html_to_text(raw_html)
            logger.info(f"Texto de entrada: {input_text[:100]}...")

            narsese, raw_resp = translate_text(input_text)
            logger.info(f"Narsese gerado: {narsese[:200]}...")

            model_name = GROQ_MODEL if BACKEND == 'groq' else OLLAMA_MODEL
            save_translation(w_hash, input_text, narsese, model_name, raw_resp)
            logger.info(f"Tradução salva para {w_hash}")

            if idx < len(words):
                logger.info(f"Aguardando {SLEEP_SECONDS}s antes da próxima...")
                time.sleep(SLEEP_SECONDS)
        except Exception as e:
            logger.error(f"Falha ao processar {w_hash}: {e}", exc_info=True)
            time.sleep(SLEEP_SECONDS)

if __name__ == "__main__":
    main()
