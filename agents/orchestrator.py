from agents.contracts import AgentMessage


class ShoppingOrchestrator:
    def route(self, message: AgentMessage) -> AgentMessage:
        return AgentMessage(
            agent_name="decision_agent",
            event_type="routed",
            payload={"source": message.agent_name, **message.payload},
        )

