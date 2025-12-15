
import pandas as pd
from dotenv import load_dotenv        
import os
import json

from langgraph.graph import StateGraph, END
from pydantic import BaseModel

from groq import Groq

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    raise ValueError("GROQ_API_KEY is missing. Set it as an environment variable")

# Configure Groq client
client = Groq(api_key=groq_api_key)

# Use Groq model (llama-3.3-70b-versatile for best results)
MODEL = "llama-3.3-70b-versatile"

# -------------------------------
# State Definition
# -------------------------------
class CleaningState(BaseModel):
    input_text: str 
    structured_response: str = ""

# -------------------------------
# AI Agent
# -------------------------------
class AIAgent:
    def __init__(self):
        self.graph = self.create_graph()

    def create_graph(self):
        graph = StateGraph(CleaningState)

        def agent_logic(state: CleaningState) -> CleaningState:
            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {"role": "user", "content": state.input_text}
                    ],
                    temperature=0.1,
                    max_tokens=4096
                )
                response_text = response.choices[0].message.content
                return CleaningState(
                    input_text=state.input_text,
                    structured_response=response_text
                )
            except Exception as e:
                return CleaningState(
                    input_text=state.input_text,
                    structured_response=f"ERROR: {str(e)}"
                )
        
        graph.add_node("cleaning_agent", agent_logic)
        graph.add_edge("cleaning_agent", END)
        graph.set_entry_point("cleaning_agent")
        return graph.compile()
    
    def process_data(self, df: pd.DataFrame, batch_size: int = 20):
        cleaned_response = []

        for i in range(0, len(df), batch_size):
            df_batch = df.iloc[i: i + batch_size]

            prompt = f"""You are an AI Data Cleaning Agent. Clean this dataset:

{df_batch.to_string()}

Tasks:
- Impute missing values (mean for numbers, mode for text)
- Remove duplicates
- Normalize numeric values
- Format text consistently

CRITICAL: Return ONLY a valid JSON array. No explanations, no markdown, no code blocks.
Output format: [{{"col1": "val1", "col2": 123}}, ...]"""

            state = CleaningState(input_text=prompt, structured_response="")
            response = self.graph.invoke(state)

            if isinstance(response, dict):
                response = CleaningState(**response)

            cleaned_response.append(response.structured_response)

        return "\n".join(cleaned_response)
