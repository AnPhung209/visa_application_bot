from agentops import track_agent, record_action
from config.tasks import get_task_name

class BaseAgent:
    def __init__(self, openai_client, config):
        self.client = openai_client
        self.config = config

    def create_completion(self, messages, temperature=None):
        return self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=temperature or self.config.get('temperature', 0.5)
        )

@track_agent(name="email_router_agent")
class EmailRouterAgent(BaseAgent):
    @record_action(get_task_name("CUSTOMER_SERVICE", "handle_inquiry"))
    def completion(self, prompt: str):
        messages = [
            {
                "role": "system",
                "content": self.config['system_message']
            },
            {"role": "user", "content": prompt}
        ]
        res = self.create_completion(messages)
        return res.choices[0].message.content

@track_agent(name="technical_agent")
class TechnicalAgent(BaseAgent):
    @record_action(get_task_name("CUSTOMER_SERVICE", "technical_solution"))
    def completion(self, prompt: str):
        messages = [
            {
                "role": "system",
                "content": self.config['system_message']
            },
            {"role": "user", "content": prompt}
        ]
        res = self.create_completion(messages)
        return res.choices[0].message.content