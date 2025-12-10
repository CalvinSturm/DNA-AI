@echo off
call .\venv\Scripts\activate.bat
streamlit run main.py --server.maxUploadSize=2000

pause    
