from flask import Flask, request, render_template
from src.providers.llm_provider import get_provider
from src.chatbot.chatbot import TravelChatbot
from src.agent.agent import TravelReActAgent
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app)

@app.route('/', methods=['GET', 'POST'])
def index():
    chatbot_response = None
    agent_response = None
    agent_steps = None

    if request.method == 'POST':
        query = request.form['query']
        provider = get_provider()

        # Chatbot response
        chatbot = TravelChatbot(provider, session_id="web_chatbot")
        chatbot_response = chatbot.chat(query)

        # Agent response
        agent = TravelReActAgent(provider, session_id="web_agent")
        agent_result = agent.run(query)
        agent_response = agent_result['answer']
        agent_steps = agent_result['steps']

    return render_template('index.html', chatbot_response=chatbot_response, agent_response=agent_response, agent_steps=agent_steps)

@socketio.on('start_agent')
def handle_agent(data):
    query = data['query']
    provider = get_provider()
    agent = TravelReActAgent(provider, session_id="web_agent")

    for step in agent.run_stream(query):  # Assuming run_stream yields steps
        emit('agent_step', step)

@socketio.on('start_chatbot')
def handle_chatbot(data):
    query = data['query']
    provider = get_provider()
    chatbot = TravelChatbot(provider, session_id="web_chatbot")

    response = chatbot.chat(query)
    emit('chatbot_response', {'response': response})

if __name__ == '__main__':
    socketio.run(app, debug=True)