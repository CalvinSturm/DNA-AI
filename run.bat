@echo off
call .\venv\Scripts\activate.bat
streamlit run dna_chat_app.py --server.maxUploadSize=2000
pause    
