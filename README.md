# Latin → Narsese (NAL) Translator

> Turn a Latin–Portuguese dictionary into Narsese, the language of the Non‑Axiomatic Reasoning System (NARS).

## What is this?

This tool reads entries from a Latin‑Portuguese dictionary (`dicionariolatino.com`) and translates their meanings into [Narsese](https://github.com/opennars/opennars/wiki/OpenNARS-Glossary), the formal language of **NAL** (Non‑Axiomatic Logic).  

The goal is to represent lexical knowledge in a machine‑understandable format that NARS can reason with — inheritance, similarity, implication, and all.

## How it works

1. **Extract** – the dictionary is stored in a SQLite database (`latin_portuguese.bkp.db`), originally scraped from dicionariolatino.com.
2. **Translate** – a Python script (`dumper.modular.py`) sends each entry to an LLM (Groq or Ollama) with a strict Narsese prompt.
3. **Store** – the generated Narsese and the original text are saved in `narseses_latim_portugues.db`.
4. **Output** – the final Narsese statements are also written to plain‑text `.nal` files.

![](https://via.placeholder.com/800x4?text=)

### Example  

**Portuguese meaning**:  
> *"Arena" can mean sand (material) or amphitheatre (place).*

**Generated Narsese**:
```nal
< (arena * {material}) --> areia >.
< (arena * {lugar}) --> anfiteatro >.
```

Each statement is wrapped in `< >`, uses the inheritance copula `-->`, and can include a **context term** (like `{material}`) to handle polysemy cleanly.

## Project structure

```
latin_to_narsese/
├── dumper.modular.py          # Main translator script
├── dicionariolatino.com       # Raw dictionary DB dump
├── narseses.txt.nal           # All extracted Narsese statements
├── narseses.sort.txt.nal      # Sorted version
├── prompt.txt                 # System prompt for the LLM
├── env.groq / env.ollama      # Environment configuration
├── run.sh                     # Quick execution wrapper
├── nix-shell.sh               # Nix environment (optional)
└── LICENSE                    # MIT
```

## Usage

### 1. Clone and set up

```bash
git clone https://github.com/haller33/latin_to_narsese.git
cd latin_to_narsese
```

### 2. Install dependencies

```bash
pip install requests tqdm  # core requirements
sudo apt install pandoc    # for HTML → plain text conversion
```

### 3. Choose a backend

| Backend | Environment variable | Notes |
|---------|----------------------|-------|
| **Ollama** (local) | `TRANSLATE_BACKEND=ollama` | Free, private, requires Ollama running locally |
| **Groq** (cloud) | `TRANSLATE_BACKEND=groq` + `GROQ_API_KEY` | Faster, needs an API key |

Example with ollama:
```bash
export TRANSLATE_BACKEND=ollama
export OLLAMA_MODEL=devstral:24b   # or any other model
python dumper.modular.py
```

### 4. Run the translator

```bash
./run.sh
```

The script will:
- Read unprocessed dictionary entries from `latin_portuguese.bkp.db`.
- Send each definition to the LLM together with the Narsese prompt.
- Save the resulting Narsese into `narseses_latim_portugues.db` and the `.nal` files.
- Wait 80 seconds between requests (to be gentle with free APIs).

## Output format

The generated Narsese follows the rules defined in `prompt.txt`:

- Every statement is delimited by `<` and `>` and ends with `.`, `?`, or `!`.
- Use `-->` for inheritance (“is a” / “has property”).
- Use `<->` only for true equivalence.
- Use `(A * B)` to provide context and disambiguate meanings.
- Truth values (frequency/confidence) are optional but can be appended like `%0.90;0.95%`.

## Why NAL / Narsese?

[NARS](https://cis.temple.edu/~pwang/) is a reasoning system built for **insufficient knowledge and resources** (AIKR).  
Its language, **Narsese**, is a formal, term‑based logic that supports:

- **Inheritance** (`-->`) – the core relation of generalisation/specialisation.  
- **Similarity** (`<->`) – mutual inheritance.  
- **Implication** (`==>`) – for conditional knowledge.  
- **Truth values** (frequency & confidence) – to handle uncertainty.  

Translating a dictionary into Narsese allows a NARS agent to:
- Answer questions about word meanings.
- Reason by analogy and inheritance.
- Learn new meanings from context.

## Status

✅ Basic pipeline working (extract → LLM → store → output).  
🔜 Future ideas:  
- Improve prompt to generate even cleaner Narsese.
- Add support for batch processing.
- Provide a small NARS demo that queries the generated knowledge.

## License

[MIT](LICENSE) – feel free to use, modify, and contribute.

## Author

Made by [haller33](https://github.com/haller33) – because Latin belongs in AI, too.
