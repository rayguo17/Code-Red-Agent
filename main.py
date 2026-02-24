import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from textual.app import App, ComposeResult
from textual.widgets import Static, Input, Button

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variable
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    raise ValueError("OPENROUTER_API_KEY environment variable is not set. Please check your .env file.")

model = init_chat_model(
    model="qwen/qwen3.5-plus-02-15",
    model_provider="openai",
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
    )

def get_weather(city: str) -> str:
    """Fetches the current weather for a given city."""
    # This is a placeholder implementation. In a real implementation, you would call a weather API.
    return f"The current weather in {city} is sunny with a temperature of 25°C."

agent = create_agent(model=model,
                     tools=[get_weather],
                     system_prompt="You are a helpful assistant that can answer questions and provide information."
                    )

res = agent.invoke({
    "messages":[{"role":"user","content":"What is the weather like in New York?"}]
})
print(res)

# handle message from user input in TUI

class AgentTUI(App):
    def compose(self) -> ComposeResult:
        yield Static("Ask the agent a question:")
        yield Input(placeholder="Type your question here...")
        yield Button("Submit", id="submit")
        
    def on_button_pressed(self, event):
        user_input = self.query_one(Input).value
        if user_input:
            response = agent.invoke({
                "messages":[{"role":"user","content":user_input}]
            })
            self.query_one(Static).update(f"Agent response: {response}")