from openai import OpenAI
from dotenv import load_dotenv
import os

from tool_manager import ToolManager
from tools import TOOLS

load_dotenv()

client = OpenAI(
    base_url=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY")
)

MODEL = os.getenv("MODEL")

# Keyword matcher, used when the model's reply isn't a tool name
tool_manager = ToolManager(TOOLS)

# "- Time: Current time, or the time in a city (e.g. What time is it in Tokyo?)" - one line per tool
TOOL_LIST = "\n".join(f"- {tool.name}: {tool.description} (e.g. {tool.example})" for tool in TOOLS)


def choose_tool(user_input):
    """Ask the model which tool fits the input. Returns a Tool from tools.py, or None."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a tool router. Do NOT answer the user's message. "
                    "Only pick the tool that should answer it.\n"
                    f"Tools:\n{TOOL_LIST}\n"
                    "Reply with only the tool name exactly as written before the colon "
                    "(for example: Time), or none if no tool fits."
                )
            },
            {
                "role": "user",
                "content": user_input
            }
        ],
        # "none" turns off thinking in Ollama
        reasoning_effort="none",
        max_tokens=20
    )

    answer = (response.choices[0].message.content or "").strip(" .\"'\n").lower()

    if answer == "none":
        return None

    # Only trust names we actually have: the exact name first, then a name inside the reply ("Today's date" -> Date)
    exact = next((tool for tool in TOOLS if tool.name.lower() == answer), None)
    if exact:
        return exact
    mentioned = [tool for tool in TOOLS if tool.name.lower() in answer]
    if mentioned:
        return max(mentioned, key=lambda tool: len(tool.name))

    # Small models sometimes answer the question instead of naming a tool, so fall back to keywords
    return tool_manager.find(user_input)
