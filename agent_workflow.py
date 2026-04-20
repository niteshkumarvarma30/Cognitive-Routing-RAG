import json
import os
from typing import TypedDict
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
#everthing is mentioned according to the workflow needed 
# I have imported the Bot_Router from database_engine.py so that it can get which Bot is ranked above in term of similarity score
try:
    from database_engine import Bot_Router
except ImportError:
    print("[Error] database_engine.py not found. Ensure Phase 1 is in the same directory.")

#Defination of States used in Langraph Agentic workflow. this states that these are features of States 
class AgentState(TypedDict):
    bot_id: str
    persona: str
    topic: str
    search_query: str
    context: str
    final_output: dict

# this tool is used for websearch in python framework when the query is made by LLM after reviewing query 
@tool
def mock_searxng_search(query: str):
    """
    Hardcoded search utility that shows a web-search result.
    This fulfills the requirement of the bot in 'real-world' facts.
    """
    term = query.lower()
    
    # Logic is mainly based on specific assignment keywords
    if any(k in term for k in ["ai", "openai", "model"]):
        return "OpenAI has unveiled a reasoning model that boosts developer productivity by 40%."
    elif "crypto" in term:
        return "Bitcoin hits new all-time high amid regulatory ETF approvals."
    elif "market" in term or "finance" in term:
        return "Tech stocks surge as interest rate cooling signals higher ROI for investors."
    
    return "Global tech trends show an increasing shift toward decentralized AI systems."
# this is the workflow given here and ollama is used locally in my pc with specifying the model version and format
class ContentEngine:
    def __init__(self, model_id="llama3"):
        # Initializing the Local Brain with JSON mode enabled
        self.llm = ChatOllama(model=model_id, temperature=0.7, format="json")
        self.workflow = self._initialize_graph()

    def _initialize_graph(self):
        """Constructs the LangGraph state machine."""
        builder = StateGraph(AgentState)

        # Mapping nodes to internal methods
        builder.add_node("decide_search", self._node_decide_search)
        builder.add_node("web_search", self._node_web_search)
        builder.add_node("draft_post", self._node_draft_post)

        # Defining the execution flow . This is the workflow needed for the complete execution 
        builder.set_entry_point("decide_search")
        builder.add_edge("decide_search", "web_search")
        builder.add_edge("web_search", "draft_post")
        builder.add_edge("draft_post", END)

        return builder.compile()

    def _node_decide_search(self, state: AgentState): #here the persona of selected bot is conserved along with LLM deciding context while query
        """Node 1: LLM decides what information it needs based on the persona."""
        prompt = (
            f"Role: {state['persona']}\n"
            f"Topic: {state['topic']}\n"
            "Task: Create a single search query to find supporting facts for this topic."
        )
        response = self.llm.invoke(prompt)
        # Using a simple string to capture for the query
        return {"search_query": response.content.strip()}

    def _node_web_search(self, state: AgentState): #websearching for the exact matching of the keyword and so that again given to LLM ollama for posting 
        """Node 2: Executes the mock tool using the generated query."""
        search_result = mock_searxng_search.invoke(state['search_query'])
        return {"context": str(search_result)}

    def _node_draft_post(self, state: AgentState): #drafting the final json results and task is mentioned by the question itself and that one is stated here 
        """Node 3: Final content generation with strict JSON formatting."""
        prompt = f"""
        Identity: {state['bot_id']}
        Persona: {state['persona']}
        Retrieved Context: {state['context']}
        Target Topic: {state['topic']}

        Task: Draft a highly opinionated social media post (max 280 chars). 
        Format: Return ONLY a valid JSON object.
        Template: 
        {{
            "bot_id": "{state['bot_id']}",
            "topic": "{state['topic']}",
            "post_content": "Your content here"
        }}
        """
        response = self.llm.invoke(prompt) #calling with the prompt + web search result 
        
        try:
            data = json.loads(response.content)
            return {"final_output": data}
        except json.JSONDecodeError:
            # Fallback logic for production resistant 
            return {"final_output": {"bot_id": state['bot_id'], "error": "JSON parse error"}}

    def execute(self, bot_id, bio, topic):
        """Entry point for the engine."""
        print(f" [Phase 2] Orchestrating workflow for {bot_id}...")
        inputs = {"bot_id": bot_id, "persona": bio, "topic": topic}
        return self.workflow.invoke(inputs)

#  Execution Process
if __name__ == "__main__":
    #API key is used here 
    JINA_KEY = "jina_b6f6796f142b47ef914af24c527e370bnAPyDLnsGTKawhk8xDwpDacJEV6f" 
    
    #using Bot_Router to get the exact bot details 
    router = Bot_Router(api_key=JINA_KEY) #
    
    raw_topic = "OpenAI just released a new model that might replace junior developers."
    matches = router.find_best_match(raw_topic)

    if matches:
        primary_bot = matches[0]
        
        # 2. Running  the LangGraph Engine with states 
        engine = ContentEngine()
        result = engine.execute(
            bot_id=primary_bot['id'],
            bio=primary_bot['context']['persona'],
            topic=raw_topic
        )

        print("\n[PHASE 2 OUTPUT]")
        print(json.dumps(result["final_output"], indent=4))