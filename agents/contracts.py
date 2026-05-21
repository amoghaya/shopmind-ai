from dataclasses import dataclass, field


@dataclass
class AgentMessage:
    agent_name: str
    event_type: str
    payload: dict = field(default_factory=dict)

