# Project — Corpus Processing Tools

This folder contains supplementary scripts and sample text corpora used to prepare raw text for the **Latin → Narsese** pipeline.  
The main goal is to extract sentences, count word frequencies, and produce ranked vocabulary lists that can later inform which Latin terms to prioritise when building a Narsese lexicon.

## Directory Structure

```
project/
├── extract-paragraphs.js          # Extract paragraphs from .txt files (sentence boundaries)
├── frequencia_de_termos.js        # Count word frequencies (basic punctuation removal)
├── frequencia_de_termos.trim.js   # Same, but with Unicode‑aware trimming of punctuation
├── harrypotter/                   # Portuguese & English Harry Potter text + frequency lists
└── virgil/                        # Virgil’s Aeneid (Latin) + frequency lists
```

## What’s Inside Each Subfolder?

### `harrypotter/`
Contains the first Harry Potter book in both **Portuguese** (`harrypotter-e-a-pedra-filosofal.epub.txt`) and **English** (`harrypotter-the-sourcerer-stone.epub.txt`), plus a word frequency file (`harrypotter-frequencia_termos.txt`) derived from the Portuguese version.  
These are used as modern‑language baselines for evaluating coverage and to help prioritise vocabulary that appears frequently in everyday narrative text.

### `virgil/`
Holds the complete **Aeneid** in Latin (HTML files `aen1.shtml` – `aen12.shtml`), a cleaned plain‑text version (`aened.shtml.formated.txt`), and the corresponding frequency list (`aened.frequencia_termos.txt`).  
This serves as the primary Latin corpus: by extracting and ranking word frequencies, the system can focus its Narsese lexicon on the most common Latin vocabulary first.

## Script Overview

| Script | Purpose |
|--------|---------|
| `extract-paragraphs.js` | Reads a `.txt` file and splits it into paragraph objects. Paragraph boundaries are detected by `[!.?]\n\n`. Output is a JSON array, e.g. `[{"index":1,"paragrafo":"..."}, ...]`. |
| `frequencia_de_termos.js` | Counts word frequency from a JSON array (the output of `extract-paragraphs.js`). Punctuation is stripped, words are lowercased, and the result is a sorted list of `percentual palavra` pairs. |
| `frequencia_de_termos.trim.js` | Same as above, but uses Unicode‑aware trimming (`\p{L}\p{N}`) to keep accented letters intact – useful for Portuguese and Latin. |

All scripts are **Node.js** tools and expect to be called from the command line.

## Typical Workflow

1. **Convert original text** (`.epub` or `.shtml`) into a plain `.txt` file.
2. **Extract paragraphs** – this creates a structured JSON file:
   ```bash
   node extract-paragraphs.js arquivo.txt > paragrafos.json
   ```
3. **Generate frequency list** from the JSON:
   ```bash
   node frequencia_de_termos.js paragrafos.json > frequencias.txt
   ```
   The output is a simple list where each line is `%freq palavra`, sorted from most to least frequent.

## Why Word Frequencies?

In the main Latin‑to‑Narsese pipeline, the dictionary has tens of thousands of entries. By first building a frequency list from a representative Latin corpus (the Aeneid) and a comparable modern corpus (Harry Potter), the system can:
- Prioritise translation of high‑frequency Latin words into Narsese first.
- Validate that common Portuguese/English concepts have a counterpart in the Latin dictionary.
- Identify gaps where a Latin term is needed but missing from the current dictionary.

The frequency lists are also useful for **data‑driven ordering** of the `.nal` files – for example, sorting the final Narsese statements so that the most common words are loaded first into the NARS memory.

## Integration with the Main Pipeline

The scripts here are *not* part of the main `dumper.modular.py` translator. Instead, they are **pre‑processing tools** used to:
- Prepare the raw corpora that eventually feed into the Narsese generation logic.
- Generate frequency data that can be consulted when filtering or sorting dictionary entries.

If you want to extend the pipeline with a frequency‑aware translation mode, the output of `frequencia_de_termos.js` (or `.trim.js`) can be read by a Python script and used to assign priority levels to each Latin lemma.

## Dependencies

- [Node.js](https://nodejs.org/) (v12 or later) – to run the JavaScript scripts.
- No external npm packages are required – only the built‑in `fs` module.

## License

Same as the main repository – see the [LICENSE](../LICENSE) file at the root.
