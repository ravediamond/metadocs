import logging
from datetime import datetime
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from .tools import create_data_loading_tools
from .models import State

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class GraphAssistant:
    def __init__(self, llm_client, db):
        # Bind tools to LLM
        self.llm = llm_client.bind_tools(create_data_loading_tools(db))
        self.db = db
        self.graph = self._create_graph()

    def _create_graph(self):
        builder = StateGraph(State)

        def chatbot(state: State):
            print(f"\n=== Chatbot Node ===")
            print(f"Input state: {state}")
            response = self.llm.invoke(state["messages"])
            print(f"LLM response: {response}")
            return {"messages": [response]}

        builder.add_node("chatbot", chatbot)

        tool_node = ToolNode(tools=create_data_loading_tools(self.db))
        builder.add_node("tools", tool_node)

        def route_tools(state: State):
            print(f"\n=== Router ===")
            print(f"Current state: {state}")
            if messages := state.get("messages", []):
                last_msg = messages[-1]
                if hasattr(last_msg, "tool_calls") and len(last_msg.tool_calls) > 0:
                    print("Routing to: tools")
                    return "tools"
            print("Routing to: end")
            return "__end__"

        builder.add_conditional_edges(
            "chatbot", route_tools, {"tools": "tools", "__end__": "__end__"}
        )
        builder.add_edge("tools", "chatbot")
        builder.set_entry_point("chatbot")

        return builder.compile()

    async def process_message(self, state_dict):
        try:
            print("\n=== New Message Processing ===")
            print(f"Initial state: {state_dict}")

            state = {
                "messages": state_dict["messages"],
                "tenant_id": state_dict["tenant_id"],
                "domain_id": state_dict["domain_id"],
                "versions": state_dict["versions"],
                "domain_info": {},
                "file_info": {},
                "db": self.db,
            }

            result = await self.graph.ainvoke(state)
            print(f"\n=== Final Result ===")
            print(f"Result: {result}")

            return {
                "message_type": "TEXT",
                "intent": "ANALYZE_RESULTS",
                "response": result["messages"][-1].content,
                "suggestions": [],
                "warnings": [],
            }

        except Exception as e:
            print(f"\n=== Error ===")
            print(f"Error processing message: {str(e)}")
            return {
                "message_type": "ERROR",
                "intent": "ERROR",
                "response": f"Error processing message: {str(e)}",
                "warnings": [str(e)],
            }
