import streamlit as st
import pandas as pd
import re
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import PromptTemplate

# --- PAGE CONFIG ---
st.set_page_config(page_title="DNA-AI Analyzer", page_icon="🧬", layout="wide")

st.title("🧬 DNA-AI: Private Genetic Analyzer")
st.markdown("""
This tool runs **locally**. 
1. It uses **Math** to find exact matches between your DNA and ClinVar.
2. It uses **AI (Llama 3)** to explain what those matches mean.
""")

# --- SIDEBAR ---
with st.sidebar:
    st.header("1. Upload Data")
    clinvar_file = st.file_uploader("Upload ClinVar DB (variant_summary.txt.gz)", type=["gz", "txt"])
    dna_file = st.file_uploader("Upload Raw DNA (txt/csv)", type=["txt", "csv"])
    
    st.markdown("---")
    st.header("2. AI Settings")
    model_name = st.selectbox("Model", ["llama3", "mistral"])
    
    if "matches" not in st.session_state:
        st.session_state.matches = None
    if "messages" not in st.session_state:
        st.session_state.messages = []

# --- FUNCTIONS ---

@st.cache_resource
def load_clinvar(file):
    """Loads ClinVar with aggressive cleaning."""
    file.seek(0)
    first_two = file.read(2)
    file.seek(0)
    is_gzip = (first_two == b'\x1f\x8b')
    comp = 'gzip' if is_gzip else None

    cols = ['GeneSymbol', 'Name', 'ClinicalSignificance', 'PhenotypeList', 
            'Assembly', 'Chromosome', 'Start', 'ReferenceAllele', 'AlternateAllele']
    
    try:
        df = pd.read_csv(
            file, sep='\t', compression=comp, usecols=cols, low_memory=False,
            dtype={'Chromosome': str, 'Start': int}
        )
    except Exception as e:
        st.error(f"Error loading ClinVar: {e}")
        st.stop()

    # FILTER & CLEAN
    if 'Assembly' in df.columns:
        df = df[df['Assembly'].astype(str).str.contains('GRCh37', na=False)]
    
    if 'ClinicalSignificance' in df.columns:
        df = df[df['ClinicalSignificance'].str.contains('Pathogenic', na=False, case=False)]

    df['Chromosome'] = df['Chromosome'].astype(str).str.replace('chr', '', case=False).str.strip()
    return df

def process_dna(dna_file, clinvar_df):
    """Loads User DNA, Smart Matches, and Calculates Zygosity."""
    try:
        user_df = pd.read_csv(
            dna_file, 
            sep=r'\s+', 
            comment='#', 
            header=None,
            names=['rsid', 'chrom', 'pos', 'genotype'],
            dtype=str, 
            on_bad_lines='skip'
        )
    except Exception as e:
        st.error(f"Error reading DNA file: {e}")
        return pd.DataFrame()

    # CLEAN DATA
    user_df['pos'] = pd.to_numeric(user_df['pos'], errors='coerce')
    user_df = user_df.dropna(subset=['pos'])
    user_df['pos'] = user_df['pos'].astype(int)
    
    user_df['chrom'] = user_df['chrom'].astype(str).str.replace('chr', '', case=False).str.strip()
    user_df['chrom'] = user_df['chrom'].replace({'23': 'X', '24': 'Y', '25': 'MT', 'M': 'MT'})
    user_df['genotype'] = user_df['genotype'].astype(str).str.upper().str.strip()

    # MERGE
    merged = pd.merge(
        user_df, clinvar_df,
        left_on=['chrom', 'pos'],
        right_on=['Chromosome', 'Start']
    )
    
    final_rows = []
    for _, row in merged.iterrows():
        user_gt = row['genotype']
        
        # 1. Get Risk Allele (From Column OR Name)
        risk_allele = str(row['AlternateAllele']).strip().upper()
        if risk_allele in ['NAN', 'NA', '-', '.', 'NONE']:
            match = re.search(r'>([ACGT])', str(row['Name']))
            if match:
                risk_allele = match.group(1)
        
        # 2. Determine Status & Zygosity
        status = "Unknown"
        zygosity = "Unknown"
        
        if user_gt in ['--', 'NAN', '']:
            status = "No Call"
        elif risk_allele in user_gt:
            status = "🔴 Confirmed Risk"
            
            # Zygosity Logic
            if len(user_gt) == 2:
                if user_gt[0] == risk_allele and user_gt[1] == risk_allele:
                    zygosity = "Homozygous (2 Copies) ⚠️"
                else:
                    zygosity = "Heterozygous (1 Copy / Carrier)"
            else:
                zygosity = "Hemizygous/Other"
        else:
            status = "🔸 Position Match (Allele Mismatch)"

        row_data = row.to_dict()
        row_data['MatchStatus'] = status
        row_data['DerivedRiskAllele'] = risk_allele
        row_data['Zygosity'] = zygosity
        
        if status != "No Call":
            final_rows.append(row_data)
            
    return pd.DataFrame(final_rows)

# --- MAIN LOGIC ---

if clinvar_file and dna_file:
    # 1. PROCESSING
    if st.session_state.matches is None:
        with st.spinner("Processing..."):
            c_df = load_clinvar(clinvar_file)
            results = process_dna(dna_file, c_df)
            st.session_state.matches = results
            
            if not results.empty:
                st.success(f"✅ Found {len(results)} raw matches!")

    # 2. DISPLAY
    if st.session_state.matches is not None and not st.session_state.matches.empty:
        tab1, tab2 = st.tabs(["📊 Data Report", "💬 Chat with AI Geneticist"])

        with tab1:
            # --- 1. ENHANCED DATA PREP (AGGRESSIVE AMBIGUITY CHECK) ---
            def is_ambiguous(row):
                """
                Detects Strand Flips (Palindromes) by checking Name.
                Target: A>T, T>A, C>G, G>C
                """
                name = str(row.get('Name', '')).upper()
                # Regex to find patterns like "A>T" or "C>G" inside the Name
                has_palindrome_name = re.search(r'[0-9](A>T|T>A|C>G|G>C)\W', name) is not None
                
                # Also check strict columns
                ref = str(row.get('ReferenceAllele', ''))
                alt = str(row.get('DerivedRiskAllele', ''))
                is_palindrome_cols = ({ref, alt} == {'A', 'T'}) or ({ref, alt} == {'C', 'G'})
                
                return has_palindrome_name or is_palindrome_cols

            st.session_state.matches['IsAmbiguous'] = st.session_state.matches.apply(is_ambiguous, axis=1)

            # Sort Order
            st.session_state.matches['SortOrder'] = st.session_state.matches['MatchStatus'].apply(
                lambda x: 0 if "Confirmed" in x else 1
            )
            sorted_df = st.session_state.matches.sort_values(by=['SortOrder', 'GeneSymbol'])
            
            # --- 2. FILTER WIDGETS ---
            st.markdown("### 🔍 Filter Your Results")
            col1, col2, col3 = st.columns(3)
            with col1:
                show_only_risk = st.checkbox("⚠️ Confirmed Risks Only", value=True)
            with col2:
                strict_mode = st.checkbox("🔥 Strict Mode (No 'Conflicting')", value=True)
            with col3:
                hide_ambiguous = st.checkbox("🧬 Hide Strand Ambiguity (Fix C/G Errors)", value=True)
            
            # --- 3. APPLY FILTERS ---
            display_df = sorted_df.copy()

            if show_only_risk:
                display_df = display_df[display_df['MatchStatus'].str.contains("Confirmed")]
            
            if strict_mode:
                display_df = display_df[~display_df['ClinicalSignificance'].str.contains("Conflicting", case=False)]
                
            if hide_ambiguous:
                before_count = len(display_df)
                display_df = display_df[~display_df['IsAmbiguous']]
                removed_count = before_count - len(display_df)
                if removed_count > 0:
                    st.success(f"🛡️ Active Protection: Removed {removed_count} False Positives (Strand Flip Errors).")

            st.markdown(f"**Showing {len(display_df)} High-Confidence Matches**")

            # --- 4. DISPLAY TABLE ---
            display_cols = ['MatchStatus', 'Zygosity', 'GeneSymbol', 'Name', 'genotype', 'DerivedRiskAllele', 'ClinicalSignificance']
            valid_cols = [c for c in display_cols if c in display_df.columns]
            
            st.dataframe(
                display_df[valid_cols], 
                use_container_width=True,
                hide_index=True
            )
            
            csv = display_df.to_csv(index=False).encode('utf-8')
            st.download_button("Download Filtered CSV", csv, "my_genetics_filtered.csv", "text/csv")

        with tab2:
            st.info("The AI has access strictly to the 'Confirmed Risk' matches found in Tab 1.")
            
            # Context generation based on current FILTERS
            # (We use display_df so the AI only sees what you see)
            context_text = ""
            if not display_df.empty:
                # Limit to top 20 rows to prevent AI overload
                for i, row in display_df.head(20).iterrows():
                    context_text += f"- Gene: {row['GeneSymbol']}, Condition: {row['Name']}, Your Genotype: {row['genotype']}, Zygosity: {row.get('Zygosity', 'Unknown')}\n"
            else:
                context_text = "No confirmed pathogenic risks were found."
            
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
            
            if prompt := st.chat_input("Ask about your results..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                with st.chat_message("assistant"):
                    message_placeholder = st.empty()
                    message_placeholder.markdown("Consulting medical knowledge...")
                    
                    llm = ChatOllama(model=model_name)
                    
                    template = """
                    You are a helpful genetic assistant. 
                    
                    USER'S CONFIRMED RISKS:
                    {context}
                    
                    USER QUESTION: 
                    {question}
                    
                    INSTRUCTIONS:
                    1. Focus ONLY on the "Confirmed Risks" listed above.
                    2. Explain what the gene/condition is in simple terms.
                    3. Pay attention to "Zygosity". If it is "Heterozygous", remind the user they are likely just a Carrier (Healthy).
                    4. If it is "Homozygous", this is more significant.
                    """
                    
                    prompt_template = PromptTemplate(template=template, input_variables=["context", "question"])
                    chain = prompt_template | llm
                    response_obj = chain.invoke({"context": context_text, "question": prompt})
                    response_text = response_obj.content
                    
                    message_placeholder.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})

else:
    st.info("Please upload both files to begin.")