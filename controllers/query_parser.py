import re
import json
from services.llm import LLM
from services.llm_system_messages import QUERY_PARSE_INSTRUCTIONS
from controllers.news_summariser import NewsSummary
from controllers.clarification import ClarificationHandler
from controllers.help import HelpController
from controllers.error import ErrorController  
from controllers.report_generator import ReportGenerator
from services.data_parser import parse_json

class QueryParser:
    def __init__(self):
        self.llm = LLM(system_message= QUERY_PARSE_INSTRUCTIONS)
        self.response = GenerateResponseController()

    def handle_query(self, chat_history, query_summary=None):
        """
        Parses the query by sending it to the LLM and extracting the JSON response.
        Returns a dict with the parsed parameters or None if parsing fails.
        """

        query = chat_history[-1]['parts'][0]['text'] if chat_history else ""
        history = chat_history[:-1]  # Exclude the last user message from history
        parsed_query = self.parse_query(history, query)

        return self.response.generate_response(history, query, parsed_query, query_summary)


    def get_llm_response(self, history, message):
        """
        Sends the conversation history and message to the LLM and returns the raw response.
        """
        return self.llm.send_message_with_history(history, message)


    def parse_query(self, history, message):
        """
        Parses the query by sending it to the LLM and extracting the JSON response.
        Returns a dict with the parsed parameters or None if parsing fails.
        """
        llm_response = self.get_llm_response(history, message)
        if not llm_response:
            return None
        # print("LLM 1 Response: ", llm_response)
        parsed_json = parse_json(llm_response)
        return parsed_json if parsed_json else None


class GenerateResponseController:

    def __init__(self):
        
        self.help_controller = HelpController()
        self.error_controller = ErrorController()
    
        self.news_summariser = NewsSummary()
        self.handle_internal_error = self.help_controller.handle_help

        self.clarification_handler = ClarificationHandler(verbose=True)
        self.report_generator = ReportGenerator(verbose=True)

    def generate_response(self, history, message, action_json, query_summary=None):
        """
        Generates a response from the LLM based on the conversation history and the new message.
        Returns the response text.
        """

        # Check for all the actions and generate response accordingly..
        if action_json is not None:
            action = action_json.get("action", "")
        else:
            action = None

        # print(action)
        if action == "report":
            # Handle report action
            return self.report_generator.handle_report(history, message, action_json, query_summary)
        elif action == "clarify_concept":
            # Handle clarify action
            return self.clarification_handler.handle_clarify_concept(history, message, action_json)
        elif action == "clarify_company":
            # Handle company clarify action
            return self.clarification_handler.handle_clarify_company(history, message, action_json)
        elif action == "clarify_comparison":
            # Handle clarify comparison action
            return self.clarification_handler.handle_clarify_comparison(history, message, action_json)
        elif action == "recommend":
            # Handle recommend action
            return self.handle_recommend(history, message, action_json)
        elif action == "news_summary":
            # Handle news summary action
            return self.news_summariser.handle_news_summary(history, message, action_json)
        elif action == "help":
            # Handle help action
            return self.help_controller.handle_help(history, message, action_json)
        elif action == "error":
            # Handle error action
            return self.error_controller.handle_error(history, message, action_json)
        else:
            # Default case for unknown actions
            return self.handle_internal_error(history, message, action_json)





if __name__ == "__main__":
    history = [
            {"role": "user", "parts": [{"text": "Hello"}]},
            {"role": "model", "parts": [{"text": "Hi! How can I help you?"}]}
        ]
    parser = QueryParser()
    while True:
        query = input("Enter your query: ")
        if query.lower() == "exit":
            break
        history.append({"role": "user", "parts": [{"text": query}]})
        resp = parser.handle_query(history)
        history.append({"role": "assistant", "parts": [{"text": resp}]})
        print(resp)