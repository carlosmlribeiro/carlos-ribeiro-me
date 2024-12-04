import pytest
from unittest.mock import patch, MagicMock
from app.app import chatbot, stream_graph_updates, State

# Mock Streamlit components
@pytest.fixture
def mock_streamlit():
    with patch('app.app.st.chat_message') as mock_chat_message, \
         patch('app.app.st.session_state', {'messages': []}) as mock_session_state:
        yield mock_chat_message, mock_session_state

def test_chatbot(mock_streamlit):
    mock_chat_message, mock_session_state = mock_streamlit
    state = State(messages=[{"role": "user", "content": "Hello"}])
    
    with patch('app.app.using_prompt_template'), \
         patch('app.app.llm_with_tools.invoke', return_value={"role": "ai", "content": "Hi there!"}):
        response = chatbot(state)
    
    assert response["messages"][0]["role"] == "ai"
    assert response["messages"][0]["content"] == "Hi there!"

def test_stream_graph_updates(mock_streamlit):
    mock_chat_message, mock_session_state = mock_streamlit
    user_input = "Tell me about Carlos"
    
    with patch('app.app.graph.stream', return_value=[{"values": [("ai", MagicMock(content="Carlos is an AI leader"))]}]):
        stream_graph_updates(user_input)
    
    assert mock_chat_message.call_count == 2  # One for human, one for ai
    mock_chat_message.assert_any_call("human")
    mock_chat_message.assert_any_call("ai")