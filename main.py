import streamlit as st
import pandas as pd
from src.loader import load_clinvar, load_dna_file
from src.analyzer import analyze_matches
from src.ai_engine import get_ai_response

# --- PAGE CONFIG ---
st.set_page_config(page_title="DNA-AI Analyzer", page_icon="🧬", layout="wide")

# --- SESSION STATE SETUP ---
if "matches" not in st.session_state:
    st.session_state.matches = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- UI HEADER ---
st.title("🧬 DNA-AI: Private Genetic Analyzer")
st.markdown("""
This tool runs **locally**. 
1. It uses **Math** to find exact matches between your DNA and ClinVar.
2. It uses **AI (Llama 3)** to explain what those matches mean.
""")

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/dna-helix.png", width=60) # Optional logo
    st.title("Control Panel")
    
    with st.expander("📂 1. File Uploads", expanded=True):
        clinvar_file = st.file_uploader("ClinVar DB", type=["gz", "txt"], help="Upload variant_summary.txt.gz")
        dna_file = st.file_uploader("Raw DNA", type=["txt", "csv"], help="23andMe or Ancestry text file")

    with st.expander("🤖 2. AI Settings", expanded=True):
        model_name = st.selectbox("LLM Model", ["llama3", "mistral"], help="Requires Ollama running locally")
    
    st.info(f"System Ready: {st.session_state.matches is not None}")


# --- PROCESS LOGIC ---
if clinvar_file and dna_file and st.session_state.matches is None:
    with st.spinner("Processing Genetics..."):
        # 1. Load
        c_df = load_clinvar(clinvar_file)
        u_df = load_dna_file(dna_file)
        
        # 2. Analyze
        results = analyze_matches(u_df, c_df)
        
        st.session_state.matches = results
        if not results.empty:
            st.success(f"✅ Found {len(results)} raw matches!")
        else:
            st.warning("No matches found. Check file formats.")

# --- DISPLAY LOGIC ---
if st.session_state.matches is not None and not st.session_state.matches.empty:
    tab1, tab2 = st.tabs(["📊 Data Report", "💬 Chat with AI Geneticist"])

    # === TAB 1: DATA ===
    with tab1:
        st.markdown("### 🔍 Filter Your Results")
        col1, col2, col3 = st.columns(3)
        with col1:
            show_only_risk = st.checkbox("⚠️ Confirmed Risks Only", value=True)
        with col2:
            strict_mode = st.checkbox("🔥 Strict Mode (No 'Conflicting')", value=True)
        with col3:
            hide_ambiguous = st.checkbox("🧬 Hide Strand Ambiguity", value=True)
        
        # --- BASE FILTERING ---
        display_df = st.session_state.matches.copy()
        
        if show_only_risk:
            display_df = display_df[display_df['MatchStatus'].str.contains("Confirmed")]
        if strict_mode:
            display_df = display_df[~display_df['ClinicalSignificance'].str.contains("Conflicting", case=False)]
        if hide_ambiguous:
            before_count = len(display_df)
            display_df = display_df[~display_df['IsAmbiguous']]
            removed_count = before_count - len(display_df)

        # Sorting: Homozygous first, then Gene Name
        display_df = display_df.sort_values(by=['SortOrder', 'GeneSymbol'])

        # --- DASHBOARD METRICS ---
        col1, col2, col3, col4 = st.columns(4)
        
        # Calculate specific counts
        homozygous_df = display_df[display_df['Zygosity'].str.contains("Homo", case=False, na=False)]
        heterozygous_df = display_df[display_df['Zygosity'].str.contains("Hetero", case=False, na=False)]
        
        col1.metric("Total Risks Found", len(display_df))
        col2.metric("Homozygous (High Risk)", len(homozygous_df), delta="Priority" if len(homozygous_df)>0 else "None", delta_color="inverse")
        col3.metric("Carriers (Heterozygous)", len(heterozygous_df))
        col4.metric("False Positives Hidden", removed_count if 'removed_count' in locals() else 0)
        
        st.divider()

        # --- INTERACTIVE VIEW CONTROLS ---
        st.write("### 📋 Detailed Results")
        
        # 1. The Filter Switch
        filter_choice = st.radio(
            "Show Category:",
            ["All Results", "🔴 Homozygous Only", "🔸 Carriers Only"],
            horizontal=True,
            label_visibility="collapsed"
        )
        
        # 2. Apply the specific filter
        final_view = display_df.copy()
        if "Homozygous" in filter_choice:
            final_view = homozygous_df
        elif "Carriers" in filter_choice:
            final_view = heterozygous_df

        # 3. Prepare Columns (Renaming for readability)
        if not final_view.empty:
            # Prefer 'PhenotypeList' if it exists, otherwise use 'Name'
            condition_col = 'PhenotypeList' if 'PhenotypeList' in final_view.columns else 'Name'
            
            view_df = final_view[['GeneSymbol', condition_col, 'Zygosity', 'ClinicalSignificance', 'DerivedRiskAllele', 'genotype']]
            view_df = view_df.rename(columns={
                'GeneSymbol': 'Gene',
                condition_col: 'Condition',
                'ClinicalSignificance': 'ClinVar Status',
                'DerivedRiskAllele': 'Risk Variant',
                'genotype': 'Your DNA'
            })

            # 4. Color Highlighting (Red for Homozygous, Yellow for Carrier)
            def highlight_rows(row):
                zyg = str(row['Zygosity'])
                if "Homo" in zyg:
                    return ['background-color: #ff4b4b20'] * len(row) # Light Red tint
                elif "Hetero" in zyg:
                    return ['background-color: #ffa50020'] * len(row) # Light Orange tint
                return [''] * len(row)

            st.dataframe(
                view_df.style.apply(highlight_rows, axis=1), # Apply the colors
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Condition": st.column_config.TextColumn("Condition", width="large"),
                    "Zygosity": st.column_config.TextColumn("Zygosity", width="medium"),
                }
            )
            
            # CSV Download
            csv = view_df.to_csv(index=False).encode('utf-8')
            st.download_button("Download Filtered CSV", csv, "my_genetics_filtered.csv", "text/csv")
        else:
            st.info("No results found for this category.")


# === TAB 2: AI CHAT ===
    with tab2:
        st.info("The AI has access strictly to the 'Confirmed Risk' matches found in Tab 1.")
        
        # 1. Prepare Context
        context_text = ""
        if not display_df.empty:
            for i, row in display_df.head(20).iterrows():
                context_text += (f"- Gene: {row['GeneSymbol']}, Condition: {row.get('PhenotypeList', row['Name'])}, "
                                 f"Genotype: {row['genotype']}, Zygosity: {row.get('Zygosity', 'Unknown')}\n")
        else:
            context_text = "No confirmed pathogenic risks were found."

        # 2. Display Chat History (This runs FIRST so it appears above input)
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # 3. Input Controls (Quick Actions + Text Input)
        st.markdown("---") # Visual separator
        st.caption("Quick Actions:")
        
        # We use a container to group buttons close to the chat input
        col1, col2 = st.columns(2)
        action_1 = col1.button("🧠 Explain my Homozygous risks", use_container_width=True)
        action_2 = col2.button("🥗 Diet/Lifestyle recommendations?", use_container_width=True)
        
        # The Chat Input (Naturally pins to bottom if not inside columns)
        user_input = st.chat_input("Ask about your results...")

        # 4. Processing Logic
        # Determine if we have a query from Buttons OR Input
        user_query = None
        if action_1:
            user_query = "Explain my homozygous risks in simple terms."
        elif action_2:
            user_query = "Based on these genes, are there lifestyle changes I should consider?"
        elif user_input:
            user_query = user_input

        # If a query exists, run the AI and RERUN the app
        if user_query:
            # A. Display User Message Immediately (Visual feedback)
            with st.chat_message("user"):
                st.markdown(user_query)
            
            # B. Generate AI Response
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                message_placeholder.markdown("Consulting medical knowledge...")
                
                response_text = get_ai_response(model_name, context_text, user_query)
                message_placeholder.markdown(response_text)
            
            # C. Save to History
            st.session_state.messages.append({"role": "user", "content": user_query})
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            
            # D. Force Refresh 
            # This makes the new message "stick" in the history loop above, 
            # keeping the input box clean at the bottom.
            st.rerun()