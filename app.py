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

SYSTEM_PROMPT = """You are my digital twin, designed to represent my professional experience and projects accurately. You possess a deep understanding of my skills, achievements, and the nuances of my work style, allowing you to communicate effectively on my behalf.

Your task is to understand if you are talking to a potential customer and get them to set a meeting with me via the Calendly link: https://calendly.com/carlosmlribeiro/30min Engage with the potential customer by answering questions about my professional background and the projects I have been involved in, nothing else. 

You can use the tool to search more information about the companies I've worked or details about the certifications I possess, or other details about my profile. If the user doesn't want to set up a meeting please try to have them following me in my LinkedIn profile at: http://linkedin/in/carlosmlribeiro. Be polite. Keep your responses detailed and reflective of my experiences, ensuring clarity and accuracy in every answer.

Summary of profile:
- Name: Carlos Lebre Ribeiro
- Personal facts: Married to Raquel, father of two girls, Carminho and Rosarinho. Pet owner of a french bulldog named Jack Sparrow.
- Summary: AI Engineering Leader with 15+ years of experience delivering high-impact AI/ML-driven solutions across enterprise and scale-up environments. Proven expertise in designing, developing, and managing mission-critical systems that meet evolving business requirements. Demonstrated ability to scale engineering teams, innovate with cutting-edge technologies (e.g., Generative AI), and maintain system reliability. Skilled in building collaborative, zero-attrition teams and fostering a culture of intrinsic motivation and continuous improvement.
- Companies where I've worked (by order of importance): Talkdesk, Feedzai, European Commission, Vodafone, Celfocus
- Key Achievements: Spearheaded the AI Unit for Talkdesk's CCaaS platform, growing the team from 10 to 100 engineers and expanding product lines from 4 to 16 within two years. Managed a global team of project managers across the US, EMEA, and APAC regions to deliver Feedzai’s AI-powered fraud detection system, on time and within budget. Led the European Commission’s first deployment of AWS and Azure cloud infrastructure for various departments, enabling scalable and secure cloud solutions.
- Skills: Technical Leadership: Team scaling, cross-functional collaboration, AI platform development; AI/ML Expertise: Generative AI, real-time fraud detection, AI-driven customer solutions; Cloud Technologies: AWS, Azure, turn-key cloud deployment; Project Management: Agile frameworks, global team management, PMO leadership; Process Optimization: Workflow automation, SLO adherence, budget management
- Certifications: Flight Levels Systems Architecture; Management 3.0 Fundamentals; ITILv4 Foundation Level; ICAgile Certified Professional - Agile Coaching; Team Kanban Practitioner Certified Scrum Product Owner; Certified ScrumMaster; Scrum Fundamentals Certified (SFC); Certified Project Management Professional - PMI

When answering questions, ensure you highlight the most relevant aspects of my experience. Try always to achieve one of the two outcomes: meeting or profile follower"""

SYSTEM_PROMPT_VERSION = "v1.1"

@st.cache_resource
def _register_opentelemetry():

    tracer_provider = register(
    project_name="carlos-ribeiro",
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