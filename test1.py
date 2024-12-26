from langchain.agents import AgentExecutor, Tool
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List
import agentops
from zapier_integration import ZapierEmailTrigger, ZapierEmailSender

# Define output schemas
class EmailAnalysis(BaseModel):
    is_visa_related: bool = Field(description="Whether the email is related to visa application")
    confidence_score: float = Field(description="Confidence score of the classification")

class ApplicationInfo(BaseModel):
    university: str = Field(description="University name")
    salary: float = Field(description="Annual salary")
    job_title: str = Field(description="Job title")
    visa_type: str = Field(description="Type of visa")
    missing_fields: List[str] = Field(description="List of missing required fields")

# Email Analysis Agent
class AnalyzeEmailAgent:
    def __init__(self):
        self.llm = ChatOpenAI(temperature=0)
        self.parser = PydanticOutputParser(pydantic_object=EmailAnalysis)
        
        self.prompt = ChatPromptTemplate.from_template("""
            Analyze the following email and determine if it's related to a visa application.
            Consider mentions of visa, immigration, work permits, or related terms.
            
            Email content: {email_content}
            
            {format_instructions}
        """)

    @agentops.track
    async def analyze(self, email_content: str) -> EmailAnalysis:
        messages = self.prompt.format_messages(
            email_content=email_content,
            format_instructions=self.parser.get_format_instructions()
        )
        response = await self.llm.apredict_messages(messages)
        return self.parser.parse(response.content)

    async def send_redirect_email(self, to_email: str):
        email_content = """
        Dear Sir/Madam,
        
        Thank you for your email. This appears to not be related to visa application.
        I'll direct you to our manager who will assist you further.
        
        Best regards,
        Visa Application Team
        """
        await ZapierEmailSender.send_email(to_email, "Re: Your Inquiry", email_content)

# Information Extraction Agent
class ExtractInformationAgent:
    def __init__(self):
        self.llm = ChatOpenAI(temperature=0)
        self.parser = PydanticOutputParser(pydantic_object=ApplicationInfo)
        
        self.prompt = ChatPromptTemplate.from_template("""
            Extract the following information from the email:
            - University name
            - Annual salary
            - Job title
            - Type of visa requested
            
            Mark any missing fields.
            
            Email content: {email_content}
            
            {format_instructions}
        """)

    @agentops.track
    async def extract(self, email_content: str) -> ApplicationInfo:
        messages = self.prompt.format_messages(
            email_content=email_content,
            format_instructions=self.parser.get_format_instructions()
        )
        response = await self.llm.apredict_messages(messages)
        return self.parser.parse(response.content)

    async def send_status_email(self, to_email: str, info: ApplicationInfo):
        if not info.missing_fields:
            email_content = """
            Dear Sir/Madam,
            
            Thank you for providing your information. We have received all required details
            for your visa application.
            
            Best regards,
            Visa Application Team
            """
        else:
            missing_fields_str = "\n".join([f"- {field}" for field in info.missing_fields])
            email_content = f"""
            Dear Sir/Madam,
            
            Thank you for your visa application. However, we notice some required information
            is missing. Please provide the following details:
            
            {missing_fields_str}
            
            Best regards,
            Visa Application Team
            """
        
        await ZapierEmailSender.send_email(to_email, "Re: Visa Application Status", email_content)

# Main Orchestrator
class VisaApplicationOrchestrator:
    def __init__(self):
        self.analyze_agent = AnalyzeEmailAgent()
        self.extract_agent = ExtractInformationAgent()
        
    async def process_email(self, email_data: dict):
        email_content = email_data['body']
        sender_email = email_data['from']
        
        # Track the process with AgentOps
        with agentops.context({"email_id": email_data['id']}):
            # Analyze email
            analysis = await self.analyze_agent.analyze(email_content)
            
            if not analysis.is_visa_related:
                await self.analyze_agent.send_redirect_email(sender_email)
                return
            
            # Extract information
            info = await self.extract_agent.extract(email_content)
            await self.extract_agent.send_status_email(sender_email, info)

# Zapier Integration
def setup_zapier_trigger():
    """Set up Zapier trigger for new emails"""
    trigger = ZapierEmailTrigger(
        on_new_email=lambda email_data: asyncio.run(
            VisaApplicationOrchestrator().process_email(email_data)
        )
    )
    return trigger

# Usage
if __name__ == "__main__":
    # Set up the Zapier trigger
    email_trigger = setup_zapier_trigger()
    
    # Start monitoring for emails
    email_trigger.start()