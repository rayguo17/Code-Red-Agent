import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain.messages import HumanMessage, AIMessage, SystemMessage
from textual import work
from textual.app import App, ComposeResult
from textual.widgets import Static, Input, Button, Footer
from textual.command import Provider, Hit
from typing import AsyncGenerator
import json

def pretty_json(obj) -> str:
    def default_encoder(o):
        if hasattr(o, "dict") and callable(o.dict):
            return o.dict()
        elif hasattr(o, "model_dump") and callable(o.model_dump):
            return o.model_dump()
        elif hasattr(o, "__dict__"):
            return o.__dict__
        return str(o)
    return json.dumps(obj, indent=2, ensure_ascii=False, default=default_encoder)

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

class StateCommandProvider(Provider):
    """A command provider to print the current message state."""
    
    async def search(self, query: str) -> AsyncGenerator[Hit, None]:
        """Search for commands."""
        matcher = self.matcher(query)
        
        # We only have one command, check if it matches the query
        command_name = "Print Message State"
        score = matcher.match(command_name)
        
        if score > 0:
            # Return a hit if the query matches
            yield Hit(
                score=score,
                match_display=matcher.highlight(command_name),
                command=self.app.action_print_state,
                help="Print the current agent message state to the terminal"
            )

class AgentTUI(App):
    COMMANDS = App.COMMANDS | {StateCommandProvider}

    def __init__(self):
        super().__init__()
        self.agent = agent
        self.message_state = {"messages": []}
    
    def compose(self) -> ComposeResult:
        yield Static("Ask the agent a question:", id="output")
        yield Input(placeholder="Type your question here...", id="user_input")
        yield Button("Submit", id="submit")
        yield Footer()
        
    def on_button_pressed(self, event: Button.Pressed):
        
        self.process_input()

    def on_input_submitted(self, event: Input.Submitted):
        self.process_input()

    def process_input(self):
        input_widget = self.query_one("#user_input", Input)
        user_input = input_widget.value
        if user_input:
            # Disable input and button while processing
            input_widget.disabled = True
            self.query_one("#submit", Button).disabled = True
            
            # Add user message to state
            self.message_state["messages"].append({"role": "user", "content": user_input})
            
            # Clear input
            input_widget.value = ""
            
            # Update UI to show processing
            self.query_one("#output", Static).update("Agent is thinking...")
            
            # Run agent in background thread
            self.run_agent()

    @work(thread=True)
    def run_agent(self):
        try:
            response = self.agent.invoke(self.message_state)
            # Update state with response
            self.message_state = response
            
            # Extract the last message content
            last_message = response["messages"][-1]
            content = last_message.content if hasattr(last_message, 'content') else last_message.get("content", str(last_message))
            
            # Update UI safely from thread
            self.call_from_thread(self.update_ui, f"Agent response: {content}")
        except Exception as e:
            self.call_from_thread(self.update_ui, f"Error: {str(e)}")

    def update_ui(self, text: str):
        self.query_one("#output", Static).update(text)
        input_widget = self.query_one("#user_input", Input)
        input_widget.disabled = False
        self.query_one("#submit", Button).disabled = False
        input_widget.focus()

    def action_print_state(self):
        with self.suspend():
            print("\n--- Current Message State ---")
            print(pretty_json(self.message_state))
            print("-----------------------------\n")
            input("Press Enter to return to the app...")
            
if __name__ == "__main__":
    app = AgentTUI()
    app.run()