import streamlit as st

import os
import uuid

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import AIMessage, SystemMessage

from typing import Annotated
from typing_extensions import TypedDict

from openinference.instrumentation.openai import OpenAIInstrumentor
from openinference.instrumentation import using_prompt_template
from phoenix.otel import register

try:
    SYSTEM_PROMPT = st.secrets["SYSTEM_PROMPT"]
    SYSTEM_PROMPT_VERSION = st.secrets["SYSTEM_PROMPT_VERSION"]
    INDEX_NAME = st.secrets["INDEX_NAME"]
except KeyError as e:
    st.error(f"Missing required secret: {e}. Please configure all required secrets in your .streamlit/secrets.toml file.")
    raise

@st.cache_resource
def _register_opentelemetry():

    tracer_provider = register(
    project_name=INDEX_NAME,
    endpoint="https://app.phoenix.arize.com/v1/traces",
    )
    OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)

@st.cache_resource
def setup_memory():
    return MemorySaver()

class State(TypedDict):
    messages: Annotated[list, add_messages]

def chatbot(state: State):
    with using_prompt_template(
        version=SYSTEM_PROMPT_VERSION,
    ):
        if(len(state["messages"])) == 1:
            state["messages"].insert(0,SystemMessage(content=SYSTEM_PROMPT)) 
        return {"messages": [llm_with_tools.invoke(state["messages"])]}

def stream_graph_updates(user_input: str):
    events = graph.stream({"messages": [("human", user_input)]}, config, stream_mode="values")
    for event in events:
        for value in event.values():
            if isinstance(value[-1], AIMessage):
                if value[-1].content:
                    st.chat_message("ai").write(value[-1].content)
                    st.session_state.messages.append([user_input, value[-1].content])

st.set_page_config(page_title="Carlos Lebre Ribeiro")
st.title("Carlos Lebre Ribeiro")
st.write("My digital twin is here to answer questions about my professional experience. Let him know if you liked it, I'll ask him later!")

openai_api_key = st.secrets["OPENAI_API_KEY"]
phoenix_api_key = st.secrets["PHOENIX_API_KEY"]
tavily_api_key = st.secrets["TAVILY_API_KEY"]

os.environ["PHOENIX_CLIENT_HEADERS"] = "api_key=" + phoenix_api_key
os.environ["TAVILY_API_KEY"] = tavily_api_key

graph_builder = StateGraph(State)

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    api_key=openai_api_key,
)

#register telemetry with Phoenix Arize
_register_opentelemetry()

tool = TavilySearchResults(max_results=2)
tools = [tool]

llm_with_tools = llm.bind_tools(tools)

# The first argument is the unique node name
# The second argument is the function or object that will be called whenever
# the node is used.
graph_builder.add_node("chatbot", chatbot)
tool_node = ToolNode(tools=[tool])
graph_builder.add_node("tools", tool_node)

graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)
# Any time a tool is called, we return to the chatbot to decide the next step
graph_builder.add_edge("tools", "chatbot")
graph_builder.set_entry_point("chatbot")

memory = setup_memory()

graph = graph_builder.compile(checkpointer=memory)

if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = uuid.uuid4()

config = {"configurable": {"thread_id": st.session_state.thread_id}}
    
for message in st.session_state.messages:
    st.chat_message('human').write(message[0])
    st.chat_message('ai').write(message[1])
#
if query := st.chat_input():
    st.chat_message("human").write(query)
    response = stream_graph_updates(query)