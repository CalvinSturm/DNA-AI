# 🧬 DNA-AI: Private Genetic Analyzer

**DNA-AI** is a local, privacy-focused bioinformatics tool that analyzes raw DNA data (from 23andMe, AncestryDNA, etc.) against the NCBI ClinVar database. It combines deterministic data matching with a local Large Language Model (Llama 3) to explain health risks in plain English.

**⚠️ DISCLAIMER: This tool is for educational and research purposes only. It is NOT a medical device. Always consult a genetic counselor or doctor for medical advice.**

## 🚀 Features

*   **100% Private & Offline:** Your DNA data never leaves your computer. The AI runs locally.
*   **Robust Matching:** Matches user DNA against the ClinVar database using Chromosome and Position.
*   **Smart Filtering:**
    *   **Zygosity Detection:** Distinguishes between Carriers (1 Copy) and Affected (2 Copies).
    *   **Strand Flip Protection:** Automatically detects and hides ~90% of false positives caused by reverse-strand sequencing errors (e.g., A>T or C>G palindromes).
    *   **Strict Mode:** Hides variants with "Conflicting interpretations" among scientists.
*   **AI Geneticist:** Chat with a local Llama 3 AI to ask questions about your specific results.
*   **Universal Loader:** Handles `.txt`, `.csv`, `.zip`, and `.gz` files automatically.

---

## 🛠️ Prerequisites

Before running the program, ensure you have the following installed:

1.  **Python 3.10+**
2.  **Ollama:** (Required for the AI features). [Download here](https://ollama.com/).

### 1. Setup the AI Model
Open your terminal/command prompt and run:
```bash
ollama pull llama3
```

### 2. Install Python Libraries
It is recommended to use a virtual environment.
```bash
# Create venv
python -m venv venv

# Activate venv (Windows)
venv\Scripts\activate

# Install requirements
pip install streamlit pandas langchain langchain-community langchain-chroma langchain-ollama pypdf
```

---

## 📂 Data Setup

You need two files to run this program.

### 1. The Database (ClinVar)
You need the "Variant Summary" file from NCBI.
*   **Download Link:** [variant_summary.txt.gz](https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz)
*   **Location:** [NCBI FTP Site](https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/)
*   **Note:** Do **NOT** unzip this file. The program reads the `.gz` directly to save space.

### 2. Your DNA Data
*   Download your "Raw Data" from 23andMe, AncestryDNA, or MyHeritage.
*   The file should look like a text list of `rsid`, `chromosome`, `position`, `genotype`.

---

## ▶️ How to Run

1.  Open your terminal in the project folder.
2.  Activate your virtual environment (if used).
3.  Run the Streamlit app:

```bash
streamlit run main.py --server.maxUploadSize=2000
```

---

## 🔍 How to Interpret Results

### The Filters
*   **⚠️ Confirmed Risks Only:** Hides "Benign" and "Uncertain" results.
*   **🔥 Strict Mode:** Hides results where labs disagree (e.g., one lab says "Pathogenic" but another says "Benign").
*   **🧬 Hide Strand Ambiguity:** (Recommended: ON). Hides ambiguous "Palindrome" mutations (A↔T, C↔G) which are often technical errors in 23andMe data.

### Zygosity (The most important column)
*   **Heterozygous (1 Copy / Carrier):** You have one normal gene and one mutated gene. For recessive conditions, you are usually healthy but can pass it on.
*   **Homozygous (2 Copies) ⚠️:** You have two mutated genes. This is a significant finding and warrants further investigation or discussion with a professional.

---

## 🐛 Troubleshooting

**"Found 0 matches"**
*   Ensure your DNA file uses **Build 37 (GRCh37/hg19)** coordinates (standard for 23andMe/Ancestry).
*   If using very new clinical data (Build 38), the positions will not match ClinVar.

**"Found 30,000 matches"**
*   This is normal before filtering. Turn on **"Confirmed Risks Only"** and **"Hide Strand Ambiguity"**.

**"The AI isn't responding"**
*   Make sure Ollama is running in the background. Open a separate terminal and type `ollama serve`.

---

## 📜 License
This project is open-source.
Data provided by [NCBI ClinVar](https://www.ncbi.nlm.nih.gov/clinvar/).
Public domain test data provided by [Harvard Personal Genome Project](https://pgp.med.harvard.edu/).
