import re
from dataclasses import dataclass
from typing import Callable


@dataclass
class Tool:
    """A small function the chat can run instead of asking the AI."""

    name: str
    description: str
    keywords: list[str]  # words or phrases in the user's message that pick this tool
    example: str  # something the user can type to try the tool
    run: Callable[[str], str | None]  # gets the user's message, returns Markdown (None = couldn't understand it)
    pattern: str | None = None  # optional regex that also picks this tool, e.g. "12 + 7" for the calculator


class ToolManager:
    """Keeps the list of tools and finds the one that matches what the user typed."""

    PATTERN_SCORE = 20

    def __init__(self, tools=None):
        self.tools = []
        for tool in tools or []:
            self.register(tool)

    def register(self, tool):
        self.tools.append(tool)

    def get(self, name):
        """The tool with this name, or None."""
        return next((tool for tool in self.tools if tool.name == name), None)

    def score(self, tool, text):
        """How well a message matches a tool. Longer keywords count more, so 'random number' beats 'number'."""
        score = 0
        for keyword in tool.keywords:
            # Letters can't touch the keyword, so "time" doesn't match "times" but "km" matches "10km"
            if re.search(rf"(?<![a-z]){re.escape(keyword)}(?![a-z])", text):
                score += len(keyword)
        if tool.pattern and re.search(tool.pattern, text):
            score += self.PATTERN_SCORE
        return score

    def find(self, text):
        """Return the best matching tool, or None if no tool matches."""
        text = text.lower()
        best_tool, best_score = None, 0
        for tool in self.tools:
            score = self.score(tool, text)
            if score > best_score:
                best_tool, best_score = tool, score
        return best_tool

    def run(self, text):
        """Run the matching tool. Returns (tool, answer), or None so the AI answers instead."""
        tool = self.find(text)
        if tool is None:
            return None
        try:
            answer = tool.run(text)
        except Exception as error:
            answer = f"Sorry, the {tool.name} tool failed: {error}"
        if answer is None:
            return None
        return tool, answer
