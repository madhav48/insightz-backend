from typing import List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_community.document_loaders import WebBaseLoader
from langchain.chains.summarize import load_summarize_chain
from langchain_community.tools.tavily_search import TavilySearchResults
from services.contextualize_user_query import format_history
from dotenv import load_dotenv

load_dotenv()


class NewsSummary:
    
    """
    1. Generate/refine query
    2. Use search tool to search results
    3. Load document content
    4. Summarize
    """

    def __init__(self, model_name="gemini-2.0-flash", verbose=False):
        self.verbose = verbose
        self.llm = ChatGoogleGenerativeAI(model=model_name, temperature=0)
        self.summarizer = load_summarize_chain(self.llm, chain_type="map_reduce")
        self.search_tool = TavilySearchResults(k=10)

        # Query-refinement chain
        self.query_chain = LLMChain(
            llm=self.llm,
            prompt=PromptTemplate(
                input_variables=["history", "latest_message"],
                template=(
                    "You are a financial news assistant. Refine this user query into a high-precision web search query:\n\n"
                    "History:\n{history}\nLatest message:\n{latest_message}\n\n"
                    "Output ONLY a single and best concise web search query. Just the query, no explanations or extra text.\n\n "
                )
            ),
            output_key="search_query"
        )


        # Summarization...
        map_prompt = PromptTemplate(
            input_variables=["text", "query"],
            template="""
                You are a financial news assistant.
                Here is a chunk of a news article:
                ---------------------
                {text}
                ---------------------

                Given the user query:
                "{query}"

                Write a short, relevant summary of this chunk that answers the query.
                Ignore irrelevant details.
                """
            )

        reduce_prompt = PromptTemplate(
            input_variables=["text", "query"],
            template="""
                You are a financial news assistant.
                Below are summaries of news article chunks, written based on the query:
                "{query}"

                ---------------------
                {text}
                ---------------------

                Write a final concise summary that answers the user query as clearly and completely as possible.
                Only include insights that are relevant to the query. Keep the answer focused, short and concise.
                Do not include any irrelevant details or generic statements.
                """
            )

        # Build the summarizer chain
        self.summarizer = load_summarize_chain(
            llm=self.llm,
            chain_type="map_reduce",
            map_prompt=map_prompt,
            combine_prompt=reduce_prompt,
        )


    def generate_query(self, history: List[str], latest_message: str) -> str:

        history = format_history(history)

        q = self.query_chain.invoke({
            "history": "\n".join(history),
            "latest_message": latest_message
        })["search_query"].strip()
        print(q)
        if self.verbose:
            print("[NEWS] Refined search query:", q)
        return q

    def search_with_agent(self, query: str) -> List[str]:
        result = self.search_tool.run(query)
        if self.verbose:
            print("[NEWS] Search result:", result)

        results_url = []
        for item in result:
            results_url.append(item.get("url", ""))
            
        return results_url


    def load_documents(self, urls: List[str]) -> List[Any]:
        if not urls:
            return []
        docs = WebBaseLoader(urls).load()
        if self.verbose:
            print(f"[NEWS] Loaded {len(docs)} documents")

        return docs

    def handle_news_summary(self, history: List[str], latest_message: str, verbose=None, *args) -> Dict[str, Any]:
        if verbose is not None:
            self.verbose = verbose

        query = self.generate_query(history, latest_message)
        urls = self.search_with_agent(query)
        docs = self.load_documents(urls)
        if docs:
            summary = self.summarizer.run({"input_documents": docs, "query": latest_message}) 
        else:
            summary = "No relevant news articles found."
        
        if self.verbose:
            print("[NEWS] Summary:", summary)

        return summary


if __name__ == "__main__":
    summariser = NewsSummary(verbose=True)
    history = ["Model: Hello!"]
    while True:
        u = input("You: ")
        if u.lower() in ("exit", "quit"):
            break
        history.append(f"User: {u}")
        resp = summariser.handle_news(history, u)
        print("Model:", resp)
