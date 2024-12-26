AGENT_CONFIGS = {
    "email_router_agent": {
        "name": "email_router_agent",
        "system_message": "You are an email router agent. Analyze the following email and determine if it's related to a visa application. Consider mentions of visa, immigration, work permits, or related terms..",
        "temperature": 0.1
    },
    "extract_information_agent": {
        "name": "extract_information_agent",
        "system_message": """
        You are an extract information agent who can extract the following information from the email:
            - University name
            - Annual salary
            - Job title
            - Type of visa requested
        Mark any missing fields.
            """,
        "temperature": 0
    }
}
def get_agent_config(agent_name):
    return AGENT_CONFIGS.get(agent_name, {})