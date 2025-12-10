import pandas as pd
import re

def detect_ambiguity(row) -> bool:
    """
    Detects Strand Flips (Palindromes) by checking Name and Alleles.
    Target: A>T, T>A, C>G, G>C
    """
    name = str(row.get('Name', '')).upper()
    # Regex to find patterns like "A>T" or "C>G" inside the Name
    has_palindrome_name = re.search(r'[0-9](A>T|T>A|C>G|G>C)', name) is not None
    
    # Also check strict columns
    ref = str(row.get('ReferenceAllele', ''))
    alt = str(row.get('DerivedRiskAllele', ''))
    is_palindrome_cols = ({ref, alt} == {'A', 'T'}) or ({ref, alt} == {'C', 'G'})
    
    return has_palindrome_name or is_palindrome_cols

def analyze_matches(user_df: pd.DataFrame, clinvar_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merges User DNA with ClinVar and determines clinical status.
    """
    if user_df.empty or clinvar_df.empty:
        return pd.DataFrame()

    merged = pd.merge(
        user_df, clinvar_df,
        left_on=['chrom', 'pos'],
        right_on=['Chromosome', 'Start']
    )
    
    final_rows = []
    
    # Iterate to apply complex business logic
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

        if status != "No Call":
            row_data = row.to_dict()
            row_data['MatchStatus'] = status
            row_data['DerivedRiskAllele'] = risk_allele
            row_data['Zygosity'] = zygosity
            final_rows.append(row_data)
            
    results = pd.DataFrame(final_rows)
    
    if not results.empty:
        # Pre-calculate Ambiguity
        results['IsAmbiguous'] = results.apply(detect_ambiguity, axis=1)
        # Add Sort Order helper
        results['SortOrder'] = results['MatchStatus'].apply(lambda x: 0 if "Confirmed" in x else 1)
        
    return results