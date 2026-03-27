
VERBAL_COMMANDS = [
    "pick that up",
    "pick that up and put it in the box",
    "give me that"
]


from dataclasses import dataclass, field

@dataclass(frozen=True)
class SelectionConfig:
    text_commands: list[str] = field(default_factory=lambda: VERBAL_COMMANDS)