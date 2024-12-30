from typing import Dict, List
from pydantic import BaseModel
from langchain.agents import initialize_agent, Tool
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
import os
from fastapi import FastAPI, Request
import uvicorn
import requests
import json
import logging

app = FastAPI()

# Initialize OpenAI LLM
llm = ChatOpenAI(temperature=0)

# Email Analysis Agent
email_analysis_prompt = PromptTemplate(
    input_variables=["email_content"],
    template="""
    Analyze the following email and determine if it's related to a visa application:
    
    {email_content}
    
    Is this a visa application related email? Return JSON with format:
    {{"is_visa_related": boolean, "explanation": "string"}}
    """
)

email_analysis_chain = llm|email_analysis_prompt

# Information Extraction Agent
info_extraction_prompt = PromptTemplate(
    input_variables=["email_content"],
    template="""
    Extract the following information from the email:
    
    {email_content}
    
    Return JSON with format:
    {{
        "university": "string or null",
        "salary": "string or null",
        "job_title": "string or null",
        "visa_type": "string or null",
        "missing_fields": ["list of missing required fields"]
    }}
    """
)

info_extraction_chain = llm|info_extraction_prompt


# Email Response Generator
response_generator_prompt = PromptTemplate(
    input_variables=["is_visa_related", "missing_fields", "email_address"],
    template="""
    Generate an email response based on the following conditions:
    
    Is visa related: {is_visa_related}
    Missing fields: {missing_fields}
    Send to: {email_address}
    
    Generate a professional email response. If not visa related, direct to manager.
    If visa related but missing fields, list the missing information needed.
    If all information is present, confirm receipt.
    
    Return JSON with format:
    {{"subject": "string", "body": "string"}}
    """
)

response_generator_chain = llm|response_generator_prompt

def send_email_response(to_email: str, subject: str, body: str):
    try:
        webhook_url = os.getenv("ZAPIER_EMAIL_WEBHOOK_URL")
        if not webhook_url:
            raise EnvironmentError("ZAPIER_EMAIL_WEBHOOK_URL environment variable is not set")
        payload = {
            "to_email": to_email,
            "subject": subject,
            "body": body
        }
        
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status() 
        return response.status_code == 200
    except requests.RequestException as e:
        print(f"Error sending email response: {e}")
        return False

@app.post("/process-email")
async def process_email(request: Request):
    logging.info("Received email processing request")
    try:
        data = await request.json()
        email_content = data.get("email_content")
        from_email = data.get("from_email")
        
        # Step 1: Analyze if email is visa related
        analysis_result = email_analysis_chain.invoke(email_content)
        analysis_data = json.loads(analysis_result)
        
        if not analysis_data["is_visa_related"]:
            response = response_generator_chain.invoke({
                "is_visa_related": False,
                "missing_fields": [],
                "email_address": from_email
            })
            response_data = json.loads(response)
            send_email_response(from_email, response_data["subject"], response_data["body"])
            return {"status": "completed", "action": "non_visa_response_sent"}
        
        # Step 2: Extract information
        extraction_result = info_extraction_chain.invoke(email_content)
        extraction_data = json.loads(extraction_result)
        
        response = response_generator_chain.invoke({
            "is_visa_related": True,
            "missing_fields": extraction_data["missing_fields"],
            "email_address": from_email
        })
        response_data = json.loads(response)
        send_email_response(from_email, response_data["subject"], response_data["body"])

        return {
            "status": "completed",
            "action": "visa_response_sent",
            "extracted_data": extraction_data
        }
    except Exception as e:
        logging.error(f"Error processing email: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)