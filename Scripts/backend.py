import sys
import os
import pandas as pd
import io
import re
import aiohttp
from fastapi import FastAPI, UploadFile, File, HTTPException
from sqlalchemy import create_engine
from pydantic import BaseModel
import json

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from ai_agent import AIAgent
from data_cleaning import DataCleaning
from data_ingestion import DataIngestion


def parse_ai_response(response_text: str) -> pd.DataFrame:
    """Parse AI response, handling markdown code blocks and JSON extraction."""
    if isinstance(response_text, pd.DataFrame):
        return response_text
    
    text = response_text.strip()
    
    # Remove markdown code blocks if present
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if json_match:
        text = json_match.group(1).strip()
    
    # Try to find JSON array in the text
    array_match = re.search(r'\[[\s\S]*\]', text)
    if array_match:
        text = array_match.group(0)
    
    try:
        data = json.loads(text)
        return pd.DataFrame(data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Could not parse AI response as JSON: {e}")



app = FastAPI()

ai_agent = AIAgent()
cleaner = DataCleaning()

# -------------------------------
# CSV/EXCEL CLEANING MACHINE ENDPOINT
# -------------------------------
@app.post("/cleandata/")
async def clean_data(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        file_extension = file.filename.split(".")[-1].lower()

        if file_extension == "csv":
            df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
        elif file_extension in ["xls", "xlsx"]:
            df = pd.read_excel(io.BytesIO(contents))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Please upload a CSV or Excel file.")
        
        # Step 1: Apply traditional DataCleaning (this always works)
        df_cleaned = cleaner.clean_data(df)
        
        # Step 2: Try AI enhancement (optional - graceful fallback if it fails)
        ai_enhanced = False
        ai_error_message = None
        
        try:
            df_ai_cleaned = ai_agent.process_data(df_cleaned)
            print("\n--- AI Agent Raw Output ---\n", df_ai_cleaned, "\n-------------------------\n")
            
            if isinstance(df_ai_cleaned, str):
                # Check for AI errors in the response
                if df_ai_cleaned.startswith("ERROR:"):
                    ai_error_message = df_ai_cleaned
                    print(f"AI Agent returned error, using traditional cleaning: {ai_error_message}")
                else:
                    df_ai_cleaned = parse_ai_response(df_ai_cleaned)
                    df_cleaned = df_ai_cleaned
                    ai_enhanced = True
            else:
                df_cleaned = df_ai_cleaned
                ai_enhanced = True
                
        except Exception as ai_error:
            ai_error_message = str(ai_error)
            print(f"AI Agent failed, falling back to traditional cleaning: {ai_error_message}")
        
        # Return the best available result
        return {
            "cleaned_data": df_cleaned.to_dict(orient="records"),
            "ai_enhanced": ai_enhanced,
            "message": "Data cleaned successfully" + (" with AI enhancement" if ai_enhanced else " (AI unavailable, used traditional methods)")
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------
# DATABASE CLEANING MACHINE ENDPOINT
# -------------------------------
class DBQuery(BaseModel):
    db_url: str
    query: str

@app.post("/clean-db/")
async def clean_db(query: DBQuery):
    """Fetch data from DB, clean it using AI, and return JSON"""
    try:
        engine = create_engine(query.db_url)
        df = pd.read_sql(query.query, engine)

        df_cleaned = cleaner.clean_data(df)
        df_ai_cleaned = ai_agent.process_data(df_cleaned)

        print("\n--- AI Agent Raw Output (DB) ---\n", df_ai_cleaned, "\n-------------------------\n")

        if isinstance(df_ai_cleaned, str):
            try:
                df_ai_cleaned = parse_ai_response(df_ai_cleaned)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Invalid AI response format: {str(e)}")

        return {"cleaned_data": df_ai_cleaned.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------
# API CLEANING MACHINE ENDPOINT
# -------------------------------
class APIRequest(BaseModel):
    api_url: str

@app.post("/clean-api/")
async def clean_api(request: APIRequest):
    """Fetch API data, clean it using AI, and return JSON"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(request.api_url) as response:
                if response.status != 200:
                    raise HTTPException(status_code=400, detail=f"Failed to fetch data from API. Status code: {response.status}")
                
                data = await response.json()
                df = pd.DataFrame(data)

                df_cleaned = cleaner.clean_data(df)
                df_ai_cleaned = ai_agent.process_data(df_cleaned)

                try:
                    df_ai_cleaned = pd.DataFrame(json.loads(df_ai_cleaned))
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Invalid AI response format: {str(e)}")

                return {"cleaned_data": df_ai_cleaned.to_dict(orient="records")}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------
# RUN SERVER
# -------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
