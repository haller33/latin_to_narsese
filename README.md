# Latin ⟶ Narsese (NAL)

> 🌐 **Turning a Latin–Portuguese dictionary into formal knowledge for NARS.**

This project converts entries from a Latin–Portuguese dictionary (`dicionariolatino.com`) into **Narsese**, the language of the **Non‑Axiomatic Reasoning System (NARS)**. The goal is to represent lexical knowledge in a format that NARS can use to reason, learn, and answer questions.

NARS uses **Non‑Axiomatic Logic (NAL)**, which operates under the assumption of insufficient knowledge and resources (AIKR). This project builds a bridge between natural language and symbolic reasoning, allowing a NARS agent to "understand" Latin concepts and their relationships.

## Table of Contents

- [How It Works](#how-it-works)
- [Repository Structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Usage](#usage)
    - [1. Running the Main Translator](#1-running-the-main-translator)
    - [2. Running with OpenNARS‑for‑Applications](#2-running-with-opennars-for-applications)
    - [3. Pre‑processing Texts with the `project/` Directory](#3-pre-processing-texts-with-the-project-directory)
- [Example Output (Narsese)](#example-output-narsese)
- [License](#license)

---

## How It Works

The process is divided into clear steps:

1.  **Extraction & Translation**: The script `translator.modular.py` reads an SQLite database (`latin_portuguese.bkp.db`) containing dictionary entries. For each entry, it extracts the Portuguese meaning and uses a language model (Groq API or local Ollama) to generate one or more Narsese sentences, following the rules defined in `prompt.txt` and used on the `translator.modular.py`.
2.  **Storage & Organization**: The generated Narsese sentences are saved into:
    *   `narseses_latim_portugues.db`: SQLite database tracking all translations.
    *   `narseses.txt.nal` and `narseses.sort.txt.nal`: Plain‑text files, unsorted and sorted, ready for use.
3.  **Reasoning with OpenNARS**: The repository includes **OpenNARS‑for‑Applications (ONA)** as a submodule. `show_narseses.sh` is a helper script to format the output so it can be loaded directly into ONA, completing the cycle from dictionary to reasoning.

---

## Repository Structure

```
latin_to_narsese/
├── translator.modular.py      # Main translator script
├── show_narseses.sh           # Helper to format output for ONA
├── OpenNARS-for-Applications/ # OpenNARS submodule (reasoner)
├── dicionariolatino.com/      # Submodule with the dictionary database
├── prompt.txt                 # Detailed instructions for generating Narsese
├── env.groq / env.ollama      # Example environment configuration files
├── run.sh / nix-shell.sh      # Utility scripts for execution
├── narseses.latimp.txt.nal    # Output file with Narsese sentences
├── project/                   # Auxiliary tools directory
│   ├── README.md              # Documentation of auxiliary tools
│   ├── extract-paragraphs.js  # Extracts paragraphs from .txt files
│   ├── frequencia_de_termos.js# Generates word frequency lists
│   ├── harrypotter/           # Modern corpus (Portuguese/English)
│   └── virgil/                # Classical corpus (Virgil's Aeneid)
└── LICENSE                    # MIT License
```

---

## Prerequisites

Before starting, make sure you have installed:

-   **Python 3.8+** with `pip`
-   **SQLite3**
-   **Pandoc** (for HTML conversion): `sudo apt install pandoc` (or equivalent)
-   **Node.js** (to use the tools in the `project/` directory)
-   **Git** (to clone submodules)
-   **Ollama** (for local execution) or a **Groq API key** (for cloud execution)

---

## Setup

1.  **Clone the repository and submodules:**
    ```bash
    git clone --recursive https://github.com/haller33/latin_to_narsese.git
    cd latin_to_narsese
    ```
    If you already cloned without `--recursive`, run:
    ```bash
    git submodule update --init --recursive
    ```

2.  **Set up the Python environment:**
    ```bash
    pip install requests tqdm
    ```

3.  **Choose and configure the translation backend (LLM).**

    *   **Option 1: Ollama (Local, free)**
        -   Install and run Ollama.
        -   Pull a model, e.g.: `ollama pull devstral:24b`
        -   Set environment variables:
            ```bash
            export TRANSLATE_BACKEND=ollama
            export OLLAMA_MODEL=devstral:24b
            ```
        -   (Optional) Change the base URL in `OLLAMA_URL` if needed.

    *   **Option 2: Groq API (Cloud, faster)**
        -   Get an API key from [console.groq.com](https://console.groq.com).
        -   Set environment variables:
            ```bash
            export TRANSLATE_BACKEND=groq
            export GROQ_API_KEY="your_key_here"
            export GROQ_MODEL="llama-3.3-70b-versatile"
            ```

---

## Usage

### 1. Running the Main Translator

To process dictionary entries and generate `.nal` files:

```bash
python translator.modular.py

# or

uv run python3 translator.modular.py

# or

sh run.sh
```

-   The script reads the `latin_portuguese.bkp.db` database.
-   It automatically skips already translated entries (using `narseses_latim_portugues.db`).
-   To respect rate limits on free APIs, there is an 80‑second delay between requests.
-   Progress and logs are displayed in the terminal.

### 2. Running with OpenNARS‑for‑Applications (ONA)

To load the generated knowledge into NARS and start interacting:

1.  **Compile ONA**. Follow the instructions in the `OpenNARS-for-Applications/` directory (usually using `make`).
2.  **Format the output** using the helper script:
    ```bash
    ./show_narseses.sh
    ```
    This script processes the translation database and produces output in the format expected by ONA.
3.  **Load into ONA**. For example, pipe the output to the ONA executable:
    ```bash
    ./OpenNARS-for-Applications/NAR shell < $( ./show_narseses.sh ) 
    ```
    You can now ask questions to the system!

### 3. Pre‑processing Texts with the `project/` Directory

The tools in `project/` can be used to analyse word frequencies and prepare new corpora.

-   **Example: Generate a frequency list from the Aeneid**
    ```bash
    cd project/
    node extract-paragraphs.js virgil/aened.shtml.formated.txt > paragraphs.json
    node frequencia_de_termos.js paragraphs.json > frequencies_virgil.txt
    ```
    This produces a list of words and their relative frequencies, sorted from most to least common.

-   **Purpose of the scripts:**
    -   `extract-paragraphs.js`: Converts a `.txt` file into a JSON array of paragraphs.
    -   `frequencia_de_termos.js`: Generates the frequency list from the JSON.
    -   `frequencia_de_termos.trim.js`: Version with Unicode‑aware cleaning, preserving accents.

The included corpora (`harrypotter/`, `virgil/`) serve as examples and bases for testing and analysis.

---

## Example Output (Narsese)

The dictionary often contains multiple meanings for a word, such as "arena" (sand or amphitheatre). The translator resolves this ambiguity using **context terms**, generating sentences like:

```nal
< (arena * {material}) --> sand >.
< (arena * {place}) --> amphitheatre >.
```

Each sentence is a NAL **statement**, delimited by `<` and `>`:
-   `(arena * {material})`: A product term representing the word "arena" in the context "material".
-   `sand`: The term for the meaning.
-   `-->`: The **inheritance** copula, indicating that an instance of "arena" in the "material" context **is a** "sand".
-   `.`: The termination indicates a **belief** (truth statement).

For a more complex phrase like "love is a feeling", the translator could generate:

```nal
< (love * {feeling}) --> friendship >.
```

The prompt in `prompt.txt` includes dozens of rules and examples to ensure high‑quality translation, such as the correct use of `<->` (equivalence), `==>` (implication), and logical operators like `&&` (conjunction).

---

## License

This project is licensed under the terms of the **MIT** license. See the [LICENSE](LICENSE) file for details.

---

## Contributions and Contact

Contributions are welcome! Feel free to open issues and pull requests.

Developed by [haller33](https://github.com/haller33) to make Latin understandable for machines that reason.
