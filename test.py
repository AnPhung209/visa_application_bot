# main.py

import agentops
from agentops import track_agent, record_action
from openai import OpenAI
import os
from dotenv import load_dotenv
import logging
from IPython.display import display, Markdown

from config.agents import get_agent_config
from config.tasks import get_task_name
from models.agent_models import SupportAgent, TechnicalAgent

#! INITIALIZE PHASE ---------------------------------------------------------------------------------------------
# Setup logging and API keys
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 
AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY") 
logging.basicConfig(level=logging.DEBUG)

# Initialize clients
agentops.init(AGENTOPS_API_KEY, default_tags=["customer-service-notebook"])
openai_client = OpenAI(api_key=OPENAI_API_KEY)


# Initialize agents with their configurations
support = SupportAgent(openai_client, get_agent_config("support_agent"))
technical = TechnicalAgent(openai_client, get_agent_config("technical_agent"))
#! INITIALIZE PHASE -------------------------------------------------------------------------------------------------

@record_action(get_task_name("CUSTOMER_SERVICE", "process_request"))
def handle_customer_case(inquiry):
    # Get initial response from support agent
    initial_response = support.completion(inquiry)
    display(Markdown("Support Agent Response:\n" + initial_response))

    technical_response = technical.completion(
        f"Customer issue: {inquiry}\nProvide technical troubleshooting steps."
    )
    display(Markdown("Technical Agent Response:\n" + technical_response))
    
    return "Responses generated successfully"

def main():
    try:
        customer_inquiry = "I'm having trouble logging into my account."
        result = handle_customer_case(customer_inquiry)

        general_response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a general assistant"},
                {"role": "user", "content": "Summarize the interaction"},
            ],
        )
        print(general_response.choices[0].message.content)

        agentops.end_session("Success")

    except Exception as e:
        agentops.end_session(f"Error: {str(e)}")

if __name__ == "__main__":
    main()