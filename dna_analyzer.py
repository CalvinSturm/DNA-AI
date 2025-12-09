import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import pandas as pd
import os

class DnaHealthTool:
    def __init__(self, root):
        self.root = root
        self.root.title("My Genome Analyzer")
        self.root.geometry("1000x600")
        
        # Data storage
        self.clinvar_df = None
        self.dna_df = None
        
        # --- GUI LAYOUT ---
        
        # Top Frame: Controls
        control_frame = tk.Frame(root, pady=10)
        control_frame.pack(side=tk.TOP, fill=tk.X)
        
        # Buttons
        self.btn_load_db = tk.Button(control_frame, text="1. Load ClinVar DB (variant_summary.txt.gz)", command=self.load_clinvar_db, bg="#e1f5fe")
        self.btn_load_db.pack(side=tk.LEFT, padx=10)
        
        self.btn_load_dna = tk.Button(control_frame, text="2. Load DNA Raw Data (txt/csv)", command=self.load_dna_file, state=tk.DISABLED, bg="#e1f5fe")
        self.btn_load_dna.pack(side=tk.LEFT, padx=10)
        
        self.lbl_status = tk.Label(control_frame, text="Status: Waiting for Database...", fg="gray")
        self.lbl_status.pack(side=tk.LEFT, padx=20)
        
        # Middle Frame: Results Table
        tree_frame = tk.Frame(root)
        tree_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview (The Table)
        columns = ("Gene", "Condition", "Significance", "User Genotype", "Risk Allele", "RSID")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", yscrollcommand=scrollbar.set)
        
        # Define Headings
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)
            
        self.tree.pack(expand=True, fill=tk.BOTH)
        scrollbar.config(command=self.tree.yview)

    def update_status(self, message, color="black"):
        self.lbl_status.config(text=f"Status: {message}", fg=color)
        self.root.update()

    def load_clinvar_db(self):
        """Loads the ClinVar database file."""
        file_path = filedialog.askopenfilename(filetypes=[("GZIP Files", "*.gz"), ("Text Files", "*.txt")])
        if not file_path:
            return

        try:
            self.update_status("Loading ClinVar DB... (this takes ~10-20s)", "blue")
            
            # Columns to load to save memory
            cols = ['GeneSymbol', 'Name', 'ClinicalSignificance', 'PhenotypeList', 
                    'Assembly', 'Chromosome', 'Start', 'ReferenceAllele', 'AlternateAllele']
            
            # Load and filter chunks (Optimized for speed)
            self.clinvar_df = pd.read_csv(
                file_path, 
                sep='\t', 
                compression='gzip', 
                usecols=cols, 
                low_memory=False
            )
            
            # FILTER 1: Genome Build (23andMe uses GRCh37/hg19)
            self.clinvar_df = self.clinvar_df[self.clinvar_df['Assembly'] == 'GRCh37']
            
            # FILTER 2: Only Pathogenic variants
            self.clinvar_df = self.clinvar_df[
                self.clinvar_df['ClinicalSignificance'].str.contains('Pathogenic', na=False, case=False) & 
                ~self.clinvar_df['ClinicalSignificance'].str.contains('Conflicting', na=False, case=False)
            ]
            
            # Normalize Chromosome names (remove 'chr' prefix if present)
            self.clinvar_df['Chromosome'] = self.clinvar_df['Chromosome'].astype(str).str.replace('chr', '')
            
            self.btn_load_dna.config(state=tk.NORMAL)
            self.update_status(f"Database Loaded! ({len(self.clinvar_df)} pathogenic records)", "green")
            
        except Exception as e:
            self.update_status(f"Error: {str(e)}", "red")
            messagebox.showerror("Error", str(e))

    def load_dna_file(self):
        """Loads the User's DNA file (23andMe/Ancestry format)."""
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("CSV Files", "*.csv")])
        if not file_path:
            return
            
        try:
            self.update_status("Processing DNA file...", "blue")
            
            # 23andMe files usually have comment lines starting with '#'
            # We try to detect the header automatically or skip comments
            self.dna_df = pd.read_csv(
                file_path, 
                sep='\t', 
                comment='#', 
                header=None,
                names=['rsid', 'chrom', 'pos', 'genotype'], # Standard 23andMe columns
                dtype={'chrom': str, 'pos': int, 'genotype': str}
            )
            
            # Clean Chromosome column (handle '23' -> 'X', '24' -> 'Y', '25' -> 'MT')
            # Note: ClinVar uses X, Y, MT. 23andMe usually uses 1-22, X, Y, MT.
            self.dna_df['chrom'] = self.dna_df['chrom'].astype(str).replace({'23': 'X', '24': 'Y', '25': 'MT'})
            
            self.run_analysis()
            
        except Exception as e:
            self.update_status(f"Error parsing DNA file: {str(e)}", "red")

    def run_analysis(self):
        """Merges DNA data with ClinVar data."""
        self.update_status("Comparing Genomes...", "blue")
        
        # Merge datasets on Chromosome and Position
        # This is the "Magic" step
        merged = pd.merge(
            self.dna_df,
            self.clinvar_df,
            left_on=['chrom', 'pos'],
            right_on=['Chromosome', 'Start']
        )
        
        # Clear previous results
        for row in self.tree.get_children():
            self.tree.delete(row)
            
        count = 0
        for index, row in merged.iterrows():
            user_gt = str(row['genotype'])
            risk_allele = str(row['AlternateAllele'])
            
            # LOGIC: Check if the User's Genotype contains the Risk Allele
            # e.g., if Risk is 'A' and user is 'AG', that's a match.
            if risk_allele in user_gt and user_gt != '--':
                self.tree.insert("", "end", values=(
                    row['GeneSymbol'],
                    row['PhenotypeList'],
                    row['ClinicalSignificance'],
                    user_gt,
                    risk_allele,
                    row['rsid']
                ))
                count += 1
        
        self.update_status(f"Analysis Complete. Found {count} matches.", "green")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    root = tk.Tk()
    app = DnaHealthTool(root)
    root.mainloop()