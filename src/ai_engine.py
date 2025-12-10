from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import PromptTemplate
import streamlit as st

def get_ai_response(model_name: str, context: str, user_question: str) -> str:

    try:
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
        
        response_obj = chain.invoke({"context": context, "question": user_question})
        return response_obj.content
    except Exception as e:
        return f"AI Error: Ensure Ollama is running locally. ({str(e)})"