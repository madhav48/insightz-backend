import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain, SequentialChain
from dotenv import load_dotenv
from services.contextualize_user_query import format_history
from services.data_parser import parse_json, parse_list
from controllers.clarification import ClarificationHandler
from langchain_community.tools.tavily_search import TavilySearchResults
from services.download_content import load_documents


load_dotenv()

class ReportGenerator:
    def __init__(self, verbose=False):
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
        self.verbose = verbose
        self.clarfication_handler = ClarificationHandler(verbose=verbose)
        self.search_tool = TavilySearchResults(k=10)

        # Chain: Analyze intent and extract report factors
        self.intent_and_factors_chain = self.build_intent_and_factors_chain()


    def handle_report(self, history, user_query, action_json=None, query_summary=None):

        formatted_history = format_history(history)
        result = self.intent_and_factors_chain({
            "history": formatted_history,
            "user_query": user_query
        })

        parsed = parse_json(result.get("intent_and_factors", ""))
        summary = {}

        print(parsed)
        
        if parsed.get("intent") is True and parsed.get("factors", {}).get("company") and len(parsed.get("factors", {})) >= 1:
            rep = "Generating report for " + parsed["factors"]["company"] + "..."
        elif parsed.get("intent") is True:
            rep = parsed.get("question", "Please provide the company name to generate the report.")
        else:
            rep = self.clarfication_handler.handle_clarify_company(history, user_query, action_json)

        summary = parsed.get("factors", {})
        self.update_query_summary(query_summary, summary)
        return rep

    def update_query_summary(self, query_summary, summary):
        """
        Updates the query summary with the report details.
        """
        if not query_summary:
            query_summary = {}
        query_summary.update(summary)
        return query_summary

    
    def build_intent_and_factors_chain(self):

        return LLMChain(
            llm=self.llm,
            prompt=PromptTemplate(
                input_variables=["history", "user_query"],
                template=(
                    "You are a financial assistant. "
                    "To determine the user's intent, ONLY use the latest user message (user_query):\n"
                    "- If the user_query is explicitly asking to generate a report (using words like 'generate report', 'create report', 'download report', etc.), and provides any parameters (like company, timeframe, focus areas, etc.), set \"intent\": true.\n"
                    "- In all other cases, including if the user is just asking a question, clarification, or not insisting on report generation, set \"intent\": false (this is the default).\n"
                    "Do NOT use the conversation history to decide intent, only use it to extract parameters if intent is true.\n\n"
                    "Conversation History (for extracting parameters only):\n{history}\n\n"
                    "User Query (for intent):\n{user_query}\n\n"
                    "Extract all key factors mentioned (company, focusAreas, timeframe, analysisType, etc.) as a JSON object. "
                    "Do NOT guess or invent any values. Only include what is explicitly mentioned in the query or history.\n\n"
                    "If intent is true, add a 'question' field to the JSON, asking the user for the most relevant missing parameter to proceed with report generation.\n\n"
                    "Output format:\n"
                    "{{\n"
                    "  \"intent\": true/false,\n"
                    "  \"factors\": {{\n"
                    "    \"company\": ...,\n  // Captialized company name, e.g. 'Apple Inc.'\n" 
                    "    \"focusAreas\": [...],\n"
                    "    \"timeframe\": ...,\n"
                    "    \"analysisType\": ...\n"
                    "    // ...other extracted fields\n"
                    "  }},\n"
                    "  \"question\": \"...\"  // Only present if intent is true\n"
                    "}}\n"
                    "If a field is missing, omit it from the JSON."
                )
            ),
            output_key="intent_and_factors"
        )
    
    def build_user_preferences_chain(self):
        return LLMChain(
            llm=self.llm,
            prompt=PromptTemplate(
                input_variables=["query_summary"],
                template=(
                    "You are a financial advisor. Given the following user requirements and preferences as a JSON object:\n"
                    "{query_summary}\n\n"
                    "Summarize what the user wants in 3-4 concise lines. Focus on the user's input such as company, focus areas, timeframe, etc. whatever provided. "
                    "If any key information is missing, just omit that, don't make up or guess any values.\n\n"
                )
            ),
            output_key="user_preferences"
        )
    
    def build_search_query_generation_chain(self):
        """
        Returns an LLMChain that takes user preferences (as JSON) and generates a Python list of focused search queries.
        The queries should be tailored to the company, focus areas, timeframe, and analysis type provided in user preferences.
        """
        prompt = PromptTemplate(
            input_variables=["user_preferences"],
            template=(
                "You are a financial research analyst. The user's preferences for a financial report are as follows:\n"
                "{user_preferences}\n\n"
                "Break down the user's requirements and generate 7 to 10 highly focused web search queries. "
                "Each query should be specific to the company, focus areas, timeframe, analysis type, etc. mentioned. "
                "Cover:\n"
                "- Latest financial news and results for the company\n"
                "- Key financial metrics and performance\n"
                "- Business overview and segment/geography breakdown\n"
                "- Valuation, price targets, and analyst opinions\n"
                "- Major risk factors and board/governance info\n"
                "- Competitive landscape and main competitors\n"
                "- Strategic outlook, growth catalysts, and recommendations\n"
                "If any parameter is missing, skip that aspect in the queries. Do NOT make up or guess any values.\n\n"
                "Return ONLY a valid Python list of search queries, e.g.:\n"
                "['Apple Inc. latest financial news 2025', 'Apple Inc. revenue and profit breakdown', 'Apple Inc. valuation and analyst targets', ...]\n"
            )
        )

        return LLMChain(
            llm=self.llm,
            prompt=prompt,
            output_key="search_queries"
        )
    
    def search_queries(self, search_queries):

        results_url = []
        for query in search_queries:
            result = self.search_tool.run(query)
            for item in result:
                if isinstance(item, dict) and "url" in item:
                    results_url.append(item.get("url", ""))
            
        return results_url


    # def build_report_chain(self):
    #     """
    #     Builds a SequentialChain that generates each section of the report using LLMs and search agents.
    #     Each component is generated using the extracted parameters and search results.
    #     If information is missing, the LLM is instructed to use "N/A".
    #     """

    #     # 1. Prompt for each section of the report
    #     def section_prompt(section_name, section_desc, output_key):
    #         return LLMChain(
    #             llm=self.llm,
    #             prompt=PromptTemplate(
    #                 input_variables=["company", "focusAreas", "timeframe", "analysisType", "search_context"],
    #                 template=(
    #                     f"You are a financial analyst. Using ONLY the provided search context and parameters, generate the '{section_name}' section for a financial report.\n"
    #                     f"Section Description: {section_desc}\n"
    #                     "Parameters:\n"
    #                     "- Company: {company}\n"
    #                     "- Focus Areas: {focusAreas}\n"
    #                     "- Timeframe: {timeframe}\n"
    #                     "- Analysis Type: {analysisType}\n"
    #                     "Relevant Information:\n{search_context}\n\n"
    #                     "If you do not have enough information for this section, simply output 'N/A'.\n"
    #                     f"Return ONLY the content for the '{section_name}' section."
    #                 )
    #             ),
    #             output_key=output_key
    #         )

    #     # 2. Example: Use your search agent to get context for each section (pseudo-code, replace with your agent)
    #     def get_search_context(company, focusAreas, timeframe, analysisType, section):
    #         # You can use your search agent or multiple agents here
    #         query = f"{company} {section} {focusAreas} {timeframe} {analysisType}"
    #         return self.clarfication_handler.search_agent.run(query)

    #     # 3. Build the chains for each section
    #     summary_chain = section_prompt(
    #         "summary",
    #         "A concise summary of the company's current position and outlook.",
    #         "summary"
    #     )
    #     key_metrics_chain = section_prompt(
    #         "keyMetrics",
    #         "Key financial metrics such as market cap, P/E ratio, revenue, gross margin, etc.",
    #         "keyMetrics"
    #     )
    #     business_overview_chain = section_prompt(
    #         "businessOverview",
    #         "Overview of the company's business, segments, and geographic breakdown.",
    #         "businessOverview"
    #     )
    #     financial_performance_chain = section_prompt(
    #         "financialPerformance",
    #         "Recent financial performance, growth, margins, and cash flow.",
    #         "financialPerformance"
    #     )
    #     valuation_chain = section_prompt(
    #         "valuation",
    #         "Current valuation, price targets, and valuation summary.",
    #         "valuation"
    #     )
    #     risk_factors_chain = section_prompt(
    #         "riskFactors",
    #         "Major risk factors affecting the company.",
    #         "riskFactors"
    #     )
    #     board_info_chain = section_prompt(
    #         "boardInfo",
    #         "Board composition and governance highlights.",
    #         "boardInfo"
    #     )
    #     competitive_landscape_chain = section_prompt(
    #         "competitiveLandscape",
    #         "Key competitors, advantages, and competitive summary.",
    #         "competitiveLandscape"
    #     )
    #     strategic_outlook_chain = section_prompt(
    #         "strategicOutlook",
    #         "Growth catalysts, recommendation, and strategic summary.",
    #         "strategicOutlook"
    #     )

    #     # 4. SequentialChain to run all sections in order
    #     return SequentialChain(
    #         chains=[
    #             summary_chain,
    #             key_metrics_chain,
    #             business_overview_chain,
    #             financial_performance_chain,
    #             valuation_chain,
    #             risk_factors_chain,
    #             board_info_chain,
    #             competitive_landscape_chain,
    #             strategic_outlook_chain
    #         ],
    #         input_variables=["company", "focusAreas", "timeframe", "analysisType", "search_context"],
    #         output_variables=[
    #             "summary", "keyMetrics", "businessOverview", "financialPerformance",
    #             "valuation", "riskFactors", "boardInfo", "competitiveLandscape", "strategicOutlook"
    #         ],
    #         verbose=self.verbose
    #     )

    def generate_report(self, query_summary):
        """
        Generates the full report JSON using the report chain.
        """


        # Extract parameters

        user_preferences = self.build_user_preferences_chain().run({
            "query_summary": query_summary
        })

        print("User Preferences: ", user_preferences)

        queries = parse_list(self.build_search_query_generation_chain().run({
            "user_preferences": user_preferences
        }))
        print("Generated Search Queries: ", queries)

        # Search for relevant information using the generated queries
        urls = self.search_queries(queries)
        docs = load_documents(urls)

        print("Loaded Documents: ", len(docs)) 

        
           


        
        # # Optionally, aggregate search context for all sections (or do per-section in build_report_chain)
        # search_context = self.clarfication_handler.search_agent.run(
        #     f"{company} {focusAreas} {timeframe} {analysisType} financial report"
        # )

        # # Run the report chain
        # report_chain = self.build_report_chain()
        # sections = report_chain({
        #     "company": company,
        #     "focusAreas": focusAreas,
        #     "timeframe": timeframe,
        #     "analysisType": analysisType,
        #     "search_context": search_context
        # })

        # # Compose the final report JSON
        # from datetime import date
        # report = {
        #     "company": company,
        #     "generatedAt": str(date.today()),
        #     "summary": sections.get("summary", "N/A"),
        #     "keyMetrics": sections.get("keyMetrics", "N/A"),
        #     "businessOverview": sections.get("businessOverview", "N/A"),
        #     "financialPerformance": sections.get("financialPerformance", "N/A"),
        #     "valuation": sections.get("valuation", "N/A"),
        #     "riskFactors": sections.get("riskFactors", "N/A"),
        #     "boardInfo": sections.get("boardInfo", "N/A"),
        #     "competitiveLandscape": sections.get("competitiveLandscape", "N/A"),
        #     "strategicOutlook": sections.get("strategicOutlook", "N/A"),
        # }
        # return report
