
VERBAL_COMMANDS = [
    "pick that up",
    "pick that up and put it in the box",
    "give me that"
]


from dataclasses import dataclass

@dataclass(frozen=True)
class SelectionConfig:
    text_commands: list = VERBAL_COMMANDS