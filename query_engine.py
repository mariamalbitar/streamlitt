import json
import os
import requests
import streamlit as st
from llama_index.llms.openrouter import OpenRouter
from llama_index.core import Settings, Document
from llama_index.core.query_engine import RouterQueryEngine
from llama_index.core.tools import QueryEngineTool
from llama_index.core.selectors import LLMSingleSelector
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.indices.struct_store import JSONQueryEngine
from llama_index.embeddings.huggingface import HuggingFaceEmbedding


API_URL = "http://127.0.0.1:8002"

def initialize_query_engine(companies_paths):
    """
    Initialize a RouterQueryEngine to handle financial queries for stock data, cleaned data, and financial phrasebank.
    Fetches data from FastAPI endpoints and falls back to local JSON files if API fails.
    Args:
        companies_paths (dict): Dictionary containing file paths for stock data, cleaned data, and financial phrasebank.
    Returns:
        RouterQueryEngine or None: Returns the initialized query engine or None if initialization fails.
    """
    try:
       
        os.environ["OPENROUTER_API_KEY"] = "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"
        llm = OpenRouter(
            api_key=os.environ["OPENROUTER_API_KEY"],
            model="mistralai/mixtral-8x7b-instruct",
            max_tokens=512,
            context_window=4096,
        )
        Settings.llm = llm
        Settings.chunk_size = 1024
        embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
        Settings.embed_model = embed_model

     
        try:
            response = requests.get(f"{API_URL}/data/financial_phrasebank", proxies={"http": None, "https": None})
            response.raise_for_status()
            phrase_data = response.json()
            phrase_docs = [Document(text=f"{item.split('@')[0]} (Sentiment: {item.split('@')[1]})") for item in phrase_data]
           

            phrase_index = VectorStoreIndex.from_documents(phrase_docs)
            phrase_engine = phrase_index.as_query_engine(similarity_top_k=3)
        except Exception as e:
            st.error(f"Error fetching financial_phrasebank data from API: {e}. Trying local file.")
            try:
                if not os.path.exists(companies_paths["financial_phrasebank"]):
                    st.error(f"Local file not found: {companies_paths['financial_phrasebank']}")
                    phrase_engine = None
                else:
                    with open(companies_paths["financial_phrasebank"], "r", encoding="utf-8") as f:
                        phrase_data = json.load(f)
                    phrase_docs = [Document(text=f"{item.split('@')[0]} (Sentiment: {item.split('@')[1]})") for item in phrase_data]
                   
                    phrase_index = VectorStoreIndex.from_documents(phrase_docs)
                    phrase_engine = phrase_index.as_query_engine(similarity_top_k=3)
            except Exception as e:
                st.error(f"Error loading local financial_phrasebank data: {e}")
                phrase_engine = None

        
        try:
            response = requests.get(f"{API_URL}/data/cleaned", proxies={"http": None, "https": None})
            response.raise_for_status()
            stage_data = response.json()

            stage_schema = {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "Index": {"type": "integer"},
                        "Credit Expiration": {"type": "integer"},
                        "DPD": {"type": "integer"},
                        "FS": {"type": "string"},
                        "CDR": {"type": "string"},
                        "SICR": {"type": "string"},
                        "Follow Up": {"type": "string"},
                        "Rescheduled": {"type": "string"},
                        "Restructuring": {"type": "string"},
                        "Covenant": {"type": "string"},
                        "Turnover": {"type": "string"},
                        "Group Reason": {"type": "string"},
                        "Current Stage": {"type": "integer"},
                        "Stage As last Month": {"type": "integer"}
                    },
                    "required": ["Credit Expiration", "Current Stage", "DPD"]
                }
            }
            stage_engine = JSONQueryEngine(json_value=stage_data, json_schema=stage_schema)
        except Exception as e:
            st.error(f"Error fetching cleaned data from API: {e}. Trying local file.")
            try:
                if not os.path.exists(companies_paths["cleaned"]):
                    st.error(f"Local file not found: {companies_paths['cleaned']}")
                    stage_engine = None
                else:
                    with open(companies_paths["cleaned"], "r", encoding="utf-8") as f:
                        stage_data = json.load(f)
                    stage_engine = JSONQueryEngine(json_value=stage_data, json_schema=stage_schema)
            except Exception as e:
                st.error(f"Error loading local cleaned data: {e}")
                stage_engine = None

      
        stock_schema = {
            "type": "object",
            "properties": {
                "Apple": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "Date": {"type": "string"},
                            "Close": {"type": "number"},
                            "Open": {"type": "number"},
                            "High": {"type": "number"},
                            "Low": {"type": "number"},
                            "Volume": {"type": "integer"}
                        },
                        "required": ["Date", "Close"]
                    }
                },
                "Meta": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "Date": {"type": "string"},
                            "Close": {"type": "number"},
                            "Open": {"type": "number"},
                            "High": {"type": "number"},
                            "Low": {"type": "number"},
                            "Volume": {"type": "integer"}
                        },
                        "required": ["Date", "Close"]
                    }
                },
                "Microsoft": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "Date": {"type": "string"},
                            "Close": {"type": "number"},
                            "Open": {"type": "number"},
                            "High": {"type": "number"},
                            "Low": {"type": "number"},
                            "Volume": {"type": "integer"}
                        },
                        "required": ["Date", "Close"]
                    }
                }
            }
        }

        # Load stock data from local files
        try:
            apple_data = json.load(open(companies_paths["Apple"], "r", encoding="utf-8"))
            meta_data = json.load(open(companies_paths["Meta"], "r", encoding="utf-8"))
            msft_data = json.load(open(companies_paths["Microsoft"], "r", encoding="utf-8"))
            apple_engine = JSONQueryEngine(json_value=apple_data, json_schema=stock_schema)
            meta_engine = JSONQueryEngine(json_value=meta_data, json_schema=stock_schema)
            msft_engine = JSONQueryEngine(json_value=msft_data, json_schema=stock_schema)
        except Exception as e:
            st.error(f"Error loading stock data: {e}")
            apple_engine, meta_engine, msft_engine = None, None, None

        # Initialize Llama-Index tools
        tools = [
            QueryEngineTool.from_defaults(
                query_engine=apple_engine,
                name="Apple_Financials",
                description="Use this for questions about Apple's financial data."
            ) if apple_engine else None,
            QueryEngineTool.from_defaults(
                query_engine=meta_engine,
                name="Meta_Financials",
                description="Use this for questions about Meta's financial data."
            ) if meta_engine else None,
            QueryEngineTool.from_defaults(
                query_engine=msft_engine,
                name="Microsoft_Financials",
                description="Use this for questions about Microsoft's financial data."
            ) if msft_engine else None,
            QueryEngineTool.from_defaults(
                query_engine=phrase_engine,
                name="Phrasebank_Tool",
                description="Use this to search phrases and sentiments in the financial phrasebank."
            ) if phrase_engine else None,
            QueryEngineTool.from_defaults(
                query_engine=stage_engine,
                name="Stage_Tool",
                description="Use this for questions about company credit and maturity stages."
            ) if stage_engine else None,
        ]
        tools = [tool for tool in tools if tool is not None]
        
        if not tools:
            st.error("No valid query engines available. Please check data sources.")
            return None

       
        try:
            selector = LLMSingleSelector.from_defaults(llm=llm)
            router_engine = RouterQueryEngine.from_defaults(
                selector=selector,
                query_engine_tools=tools,
                llm=llm
            )
            return router_engine
        except Exception as e:
            st.error(f"Error initializing RouterQueryEngine: {e}")
            return None
    except Exception as e:
        st.error(f"Error initializing query engine: {e}")
        return None

def run_query(query, router_engine):
    """
    Run a query using the provided RouterQueryEngine.
    Args:
        query (str): The query string (JSONPath or natural language).
        router_engine (RouterQueryEngine): The initialized query engine.
    Returns:
        str: The query result as a string.
    Raises:
        Exception: If the query engine is not initialized, the query is empty, or an error occurs during processing.
    """
    if not router_engine:
        raise Exception("Query engine is not initialized.")
    if not query:
        raise Exception("Query is empty.")
    try:
        response = router_engine.query(query)
        return str(response)
    except Exception as e:
        raise Exception(f"Error processing query: {e}")

