
from agent import AssistantAgent
from mcp_client import get_client
import asyncio

async def init_agent():
    client = await get_client()
    tools = await client.get_tools()
    agent = await AssistantAgent( 
                        tools=tools,
                        sync=False
                        ).get_graph()
    return agent

async def main():
    agent = await init_agent()
    user_id = 1
    config = {"configurable": {"thread_id": user_id, "user_id": user_id}}
    message = "explain about finance in erp"
    async for message_chunk,meta_data in agent.astream(
            {"messages": message},
            config=config,
            version="v1",
            stream_mode="messages"
        ):
            is_tool = getattr(message_chunk, "type", "")  # if your chunk has this attribute
            # Or use meta_data flag if available
            if meta_data.get("langgraph_node","")=="tools" or is_tool=="tool_call" or meta_data.get("langgraph_node","")=="security_check":
                # skip streaming tool outputs
                continue
            token = message_chunk.content
            
            if isinstance(token, list):
            # join list items into a single string
                token = " ".join(str(c) for c in token)
            print(token,end="",flush=True)
            # if token:
            #     yield token
            #     await asyncio.sleep(0.01)

if __name__=="__main__":
    asyncio.run(main())
