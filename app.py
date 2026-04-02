import sys
import asyncio
from typing import Union
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
import pathlib
PROJECT_PATH = pathlib.Path(__file__).absolute().parents[1].absolute()
sys.path.insert(0,str(PROJECT_PATH))
from fastapi import FastAPI,Response,status,Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_ollama.chat_models import ChatOllama
from agent import AssistantAgent
from mcp_client import get_client
import logging
logging.basicConfig(level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI(name="Agent Bot",debug=True)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"]
)
agent = None
@app.get("/health")
def get_health(response:Response):
    global agent
    print("health agent ",agent)
    if agent!=None:
        return {"message":"Model is Online!"}
    response.status_code = status.HTTP_409_CONFLICT
    return {"message":"Model is offline"}

@app.post("/")
async def chat_assistant(message:str=Form(...),user_id:Union[str,int]=Form(...)):
    global agent
    config = {"configurable": {"thread_id": user_id, "user_id": user_id}}
    if (agent==None):
        print("getting agent ")
        agent = await init_agent()
    async def event_generator():
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
            # print(token,end="",flush=True)
            if token:
                yield token
                await asyncio.sleep(0.01)
    return StreamingResponse(
        event_generator(),
        media_type="text/plain", )




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
    message = "explain about finance in erp make it very short"
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

# if __name__=="__main__":
#     asyncio.run(main())
if __name__=="__main__":    
    try:
       agent = asyncio.run(init_agent())
    except Exception as e:
        logging.error("Faild when initializing agent ",e)
    import uvicorn
    # important on windows asyncio:SelectorEventLoop
    uvicorn.run("app:app",loop="asyncio:SelectorEventLoop",host="127.0.0.1",port=4000,reload=False)
