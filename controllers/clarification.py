import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA, LLMChain
from langchain_community.tools import DuckDuckGoSearchResults
from langchain.agents import Tool, initialize_agent, AgentType
from dotenv import load_dotenv
from services.contextualize_user_query import contextualize_user_query
from services.agents import build_search_agent

load_dotenv()


# Load glossary vector DB with Google embeddings
def load_vector_db():
    return FAISS.load_local("./assets/glossary_index", GoogleGenerativeAIEmbeddings(model="models/embedding-001"), allow_dangerous_deserialization=True)


def define_user_query(query):
    return f"""

        You are a financial expert. Use the glossary context to answer the user's query clearly and factually. \n\n

        -----------------------
        Query: {query}\n\n
        -----------------------
        If the answer is not in the glossary context, respond only with 'No', nothing else. Do not make up answers or guess. Keep your response concise and to the point. \n\n
        """

# Concept Clarification RAG chain 
def build_concept_clarifier(llm, vector_db):
    retriever = vector_db.as_retriever()
    return RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type="stuff",
    )



# Main handler
class ClarificationHandler:
    def __init__(self, verbose = False):
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
        self.vector_db = load_vector_db()
        self.concept_chain = build_concept_clarifier(self.llm, self.vector_db)
        self.search_agent = build_search_agent(self.llm, verbose=verbose)

    def handle_clarify_concept(self, history: list, user_query: str, action_json: dict = None):

        user_query = contextualize_user_query(self.llm, history, user_query)
        
        if action_json and "parameters" in action_json and "concept" in action_json["parameters"]:
            response = self.concept_chain.run(define_user_query(user_query))
        else:
            response = self.concept_chain.run(define_user_query(user_query))

        if not response or response.lower() == "no":
            return self.search_agent.run(f"Explain the financial concept: {user_query}")
        return response

    def handle_clarify_company(self, history: list, user_query: str, action_json: dict = None):

        user_query = contextualize_user_query(self.llm, history, user_query)

        companies = self.get_company_from_json(action_json)
        if companies:
            return self.search_agent.run(f"Clarify about the {companies}: {user_query}")
        
        # If no specific company is provided, use the last message to infer the company
        return self.search_agent.run(f"Clarify : {user_query}")

    def handle_clarify_comparison(self, history: list, user_query: str, action_json: dict = None):

        user_query = contextualize_user_query(self.llm, history, user_query)

        companies = self.get_company_from_json(action_json)
        if companies: 
            return self.search_agent.run(f"Compare the {companies} on the basis of: {user_query}")
                
        # If no specific company is provided, use the last message to infer the company
        return self.search_agent.run(f"Compare companies: {user_query}")


    def get_company_from_json(self, action_json: dict) -> str:

        """
        Extracts the company name from the action JSON if available.
        """

        if action_json and "parameters" in action_json:

            if ("company" in action_json["parameters"]):
                # If company is directly specified
                return action_json["parameters"]["company"]
            elif ("companies" in action_json["parameters"]):
                return ", ".join(action_json["parameters"]["companies"])
        return ""


# Example usage
if __name__ == "__main__":
    handler = ClarificationHandler(verbose=True)
    history = [
        {"role": "user", "parts": [{"text": "Can you explain EBITDA margin?"}]},
        {"role": "model", "parts": [{"text": "EBITDA margin is..."}]},
        {"role": "user", "parts": [{"text": "And what about net profit margin?"}]}
    ]
    print("→ Concept Clarification:\n", handler.handle_clarify_concept(history, "racing game"))
    print("\n→ Company Clarification:\n", handler.handle_clarify_company(history, "What is the market cap of Apple?"))
    print("\n→ Comparison Clarification:\n", handler.handle_clarify_comparison(history, "Compare ROE of Infosys and TCS"))
