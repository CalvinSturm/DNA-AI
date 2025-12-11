import pandas as pd
import streamlit as st

@st.cache_data(show_spinner=False)
def load_clinvar(file) -> pd.DataFrame:
    """
    Loads ClinVar data with aggressive cleaning.
    """
    try:
        file.seek(0)
        first_two = file.read(2)
        file.seek(0)
        is_gzip = (first_two == b'\x1f\x8b')
        comp = 'gzip' if is_gzip else None

        cols = ['GeneSymbol', 'Name', 'ClinicalSignificance', 'PhenotypeList', 
                'Assembly', 'Chromosome', 'Start', 'ReferenceAllele', 'AlternateAllele']
        
        df = pd.read_csv(
            file, sep='\t', compression=comp, usecols=cols, low_memory=False,
            dtype={'Chromosome': str, 'Start': int}
        )
    except Exception as e:
        st.error(f"Error loading ClinVar: {e}")
        return pd.DataFrame()

    # FILTER: Assembly GRCh37
    if 'Assembly' in df.columns:
        df = df[df['Assembly'].astype(str).str.contains('GRCh37', na=False)]
    
    # FILTER: Pathogenic Only
    if 'ClinicalSignificance' in df.columns:
        df = df[df['ClinicalSignificance'].str.contains('Pathogenic', na=False, case=False)]

    # CLEAN: Chromosome
    df['Chromosome'] = df['Chromosome'].astype(str).str.replace('chr', '', case=False).str.strip()
    return df

def load_dna_file(dna_file) -> pd.DataFrame:
    """
    Parses user raw DNA file (23andMe/Ancestry format).
    """
    try:
        # Read with flexible columns
        user_df = pd.read_csv(
            dna_file, 
            sep=r'\s+', 
            comment='#', 
            header=None,
            dtype=str, 
            on_bad_lines='skip'
        )

        # Check for 5-column AncestryDNA format
        if len(user_df.columns) == 5:
            user_df.columns = ['rsid', 'chrom', 'pos', 'allele1', 'allele2']
            user_df['genotype'] = user_df['allele1'].fillna('') + user_df['allele2'].fillna('')
            user_df = user_df.drop(columns=['allele1', 'allele2'])
        
        # Assume 4-column format (23andMe)
        elif len(user_df.columns) == 4:
            user_df.columns = ['rsid', 'chrom', 'pos', 'genotype']

        else:
            st.error("Invalid file format. Please upload a valid 23andMe or AncestryDNA file.")
            return pd.DataFrame()

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
    
    return user_df