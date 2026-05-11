#!/usr/bin/env python3
"""
Test a single dictionary entry translation to Narsese.
Usage: python test_translation.py [--db DICT.db] [--word-hash HASH] [--word WORD] [--backend ollama|groq] [--output-format text|json]
"""

import os
import sys
import sqlite3
import argparse
import subprocess
import json
import logging
import time
from typing import Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------- Logging (minimal) ----------
logging.basicConfig(level=logging.WARNING)  # only warnings/errors
logger = logging.getLogger(__name__)

# ---------- Configuration ----------
HASH_TO_AVOID = '32aaccb0c4597738cc2fca23b28557802587b9a9fa91d5c8c54beae8aedee5d9'  # see original

# ---------- Backend functions (copied from translator.modular.py) ----------
def call_groq(prompt_full: str) -> Tuple[str, str]:
    from dotenv import load_dotenv
    load_dotenv()  # optional, but safe
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set")
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
    resp = session.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if 'error' in data:
        raise Exception(f"Groq error: {data['error'].get('message', '')}")
    return data['choices'][0]['message']['content'], json.dumps(data)

def call_ollama(prompt_full: str) -> Tuple[str, str]:
    OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
    OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "devstral:24b")
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt_full}],
        "options": {"temperature": 0.0},
        "stream": False
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    if 'error' in data:
        raise Exception(f"Ollama error: {data['error']}")
    return data['message']['content'], json.dumps(data)

# ---------- Helpers ----------
def compute_hash(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def html_to_text(html: str) -> str:
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
        raise RuntimeError(f"Pandoc error: {e.stderr.decode()}")

def get_word_hash_from_word(db_path: str, word: str) -> str:
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT word_hash FROM dictionary WHERE word = ?", (word,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise ValueError(f"Word '{word}' not found in dictionary")
    return row[0]

def get_raw_html_by_hash(db_path: str, word_hash: str) -> str:
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT raw_html FROM dictionary WHERE word_hash = ? AND content_hash != ?",
                       (word_hash, HASH_TO_AVOID)).fetchone()
    conn.close()
    if not row:
        raise ValueError(f"Hash {word_hash} not found or excluded")
    return row[0]

# ---------- Prompt (same as original) ----------
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

# ---------- Main ----------
def main():
    parser = argparse.ArgumentParser(description="Test Narsese translation for a single dictionary entry")
    parser.add_argument("--db", default="latin_portuguese.bkp.db", help="SQLite dictionary database")
    parser.add_argument("--word-hash", help="SHA256 word hash to translate")
    parser.add_argument("--word", help="Latin word to translate (looks up its hash)")
    parser.add_argument("--backend", choices=["ollama", "groq"], default="ollama", help="LLM backend")
    parser.add_argument("--output-format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--delay", type=float, default=0, help="Sleep seconds before query (simulate rate limit)")
    args = parser.parse_args()

    if args.word and args.word_hash:
        print("Error: specify only one of --word or --word-hash", file=sys.stderr)
        sys.exit(1)
    if not (args.word or args.word_hash):
        print("Error: either --word or --word-hash is required", file=sys.stderr)
        sys.exit(1)

    # Determine word_hash
    if args.word:
        try:
            word_hash = get_word_hash_from_word(args.db, args.word)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        word_hash = args.word_hash

    # Fetch raw HTML
    try:
        raw_html = get_raw_html_by_hash(args.db, word_hash)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Convert to plain text
    try:
        input_text = html_to_text(raw_html)
    except Exception as e:
        print(f"Error converting HTML: {e}", file=sys.stderr)
        sys.exit(1)

    # Set backend environment (the call functions read env vars)
    if args.backend == "groq":
        os.environ["TRANSLATE_BACKEND"] = "groq"  # not directly used but for consistency
        translate_func = call_groq
    else:
        os.environ["TRANSLATE_BACKEND"] = "ollama"
        translate_func = call_ollama

    # Optional delay
    if args.delay > 0:
        time.sleep(args.delay)

    # Call LLM
    full_prompt = PROMPT + input_text
    try:
        narsese, raw_response = translate_func(full_prompt)
    except Exception as e:
        print(f"LLM error: {e}", file=sys.stderr)
        sys.exit(1)

    # Output
    if args.output_format == "json":
        out = {
            "word_hash": word_hash,
            "input_text": input_text,
            "narsese": narsese,
            "raw_response": raw_response,
            "backend": args.backend
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(f"Word Hash: {word_hash}")
        print(f"Input Text: {input_text}")
        print("--- Narsese Output ---")
        print(narsese)
        print("--- End ---")

if __name__ == "__main__":
    main()
