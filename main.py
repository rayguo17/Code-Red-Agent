import os
import json
from typing import AsyncGenerator

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain.messages import HumanMessage, AIMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from textual import work
from textual.app import App, ComposeResult
from textual.widgets import Static, Input, Button, Footer, RichLog
from textual.command import Provider, Hit
from textual.containers import Horizontal


def pretty_json(obj) -> str:
    def default_encoder(o):
        if hasattr(o, "dict") and callable(o.dict):
            return o.dict()
        if hasattr(o, "model_dump") and callable(o.model_dump):
            return o.model_dump()
        if hasattr(o, "__dict__"):
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
    return f"The current weather in {city} is sunny with a temperature of 25C."


mcp_client = MultiServerMCPClient(
    {
        "local": {
            "transport": "stdio",
            "command": "python",
            "args": ["tools/local.py"],
        }
    }
)


class StateCommandProvider(Provider):
    """A command provider to print the current message state."""

    async def search(self, query: str) -> AsyncGenerator[Hit, None]:
        """Search for commands."""
        matcher = self.matcher(query)
        commands = [
            (
                "Print Message State",
                self.app.action_print_state,
                "Print the current agent message state to the terminal",
            ),
            (
                "List Agent Tools",
                self.app.action_list_tools,
                "List tools available to the agent",
            ),
        ]

        for command_name, command, help_text in commands:
            score = matcher.match(command_name)
            if score > 0:
                yield Hit(
                    score=score,
                    match_display=matcher.highlight(command_name),
                    command=command,
                    help=help_text,
                )


class AgentTUI(App):
    COMMANDS = App.COMMANDS | {StateCommandProvider}
    CSS = """
    #chat_log {
        height: 1fr;
        border: round $secondary;
        padding: 1;
    }
    #input_row {
        height: auto;
    }
    #status {
        height: auto;
    }
    #prompt_label {
        width: 8;
    }
    """

    def __init__(self):
        super().__init__()
        self.agent = None
        self.tools = []
        self.message_state = {"messages": []}
        self._agent_initialized = False

    async def on_compose(self) -> None:
        await self._initialize_agent()

    async def on_mount(self) -> None:
        await self._initialize_agent()

    async def _initialize_agent(self) -> None:
        if self._agent_initialized:
            return
        self._agent_initialized = True
        self.tools = await mcp_client.get_tools()
        self.agent = create_agent(
            model=model,
            tools=self.tools,
            system_prompt="You are a helpful assistant that can answer questions and provide information.",
        )

    def compose(self) -> ComposeResult:
        yield RichLog(id="chat_log", wrap=True, highlight=False)
        yield Static("Ready.", id="status")
        with Horizontal(id="input_row"):
            yield Static("Prompt:", id="prompt_label")
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
        if not self.agent:
            self.query_one("#status", Static).update("Agent is still initializing...")
            return
        if user_input:
            # Disable input and button while processing
            input_widget.disabled = True
            self.query_one("#submit", Button).disabled = True

            # Add user message to state
            self.message_state["messages"].append({"role": "user", "content": user_input})
            self.append_message("You", user_input)

            # Clear input
            input_widget.value = ""

            # Update UI to show processing
            self.query_one("#status", Static).update("Agent is thinking...")

            # Run agent in background thread
            self.run_agent()

    @work(thread=True)
    async def run_agent(self):
        try:
            response = await self.agent.ainvoke(self.message_state)
            # Update state with response
            self.message_state = response

            # Extract the last message content
            last_message = response["messages"][-1]
            content = (
                last_message.content
                if hasattr(last_message, "content")
                else last_message.get("content", str(last_message))
            )

            # Update UI safely from worker
            self.call_from_thread(self.update_ui, content)
        except Exception as e:
            self.call_from_thread(self.update_ui, f"Error: {str(e)}")

    def update_ui(self, text: str):
        if text.startswith("Error:"):
            self.append_message("Error", text)
        else:
            self.append_message("Assistant", text)
        self.query_one("#status", Static).update("Ready.")
        input_widget = self.query_one("#user_input", Input)
        input_widget.disabled = False
        self.query_one("#submit", Button).disabled = False
        input_widget.focus()

    def append_message(self, role: str, content: str) -> None:
        chat_log = self.query_one("#chat_log", RichLog)
        chat_log.write(f"{role}: {content}")

    def action_print_state(self):
        with self.suspend():
            print("\n--- Current Message State ---")
            print(pretty_json(self.message_state))
            print("-----------------------------\n")
            input("Press Enter to return to the app...")

    def action_list_tools(self):
        with self.suspend():
            print("\n--- Agent Tools ---")
            if not self.tools:
                print("(no tools registered)")
            else:
                for tool in self.tools:
                    name = getattr(tool, "name", None)
                    if not name and isinstance(tool, dict):
                        name = tool.get("name")
                    description = getattr(tool, "description", None)
                    if not description and isinstance(tool, dict):
                        description = tool.get("description")
                    if description:
                        print(f"- {name}: {description}")
                    else:
                        print(f"- {name}")
            print("-------------------\n")
            input("Press Enter to return to the app...")


if __name__ == "__main__":
    app = AgentTUI()
    app.run()
