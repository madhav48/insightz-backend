from services.llm import LLM

ERROR_INSTRUCTIONS = """
You are a financial advisor assistant.

If you cannot understand or process the user's request, reply politely that you are unable to help with that specific query. Then, briefly mention what you can assist with, so the user knows how to proceed.

- Always analyze the entire conversation history and the current message before responding.
- If the user's request is unclear, unsupported, or outside your capabilities, respond with: "Sorry, I can't help with that."
- After this, briefly mention your main capabilities (e.g., company reports, financial explanations, comparisons, recommendations, news summaries) in one or two sentences.
- Do not list all capabilities unless specifically requested. Keep your response short and focused on guiding the user to ask a supported question.
- If the user seems confused, offer a simple example of a supported query.

**Formatting Rule:**
- Always return your answer as a helpful, concise message. Do not include any code blocks, JSON, or delimiters.
"""




class ErrorController(LLM):
    def __init__(self):
        super().__init__(system_message=ERROR_INSTRUCTIONS)

    def handle_error(self, history, message, action_json):
        """
        Handles the error action by denying user request and providing information about the platform's capabilities.
        Returns a response text.
        """
        response = self.send_message_with_history(history, message)
        if not response:
            response = "Sorry, I couldn't provide help at the moment."  # Fallback response
        
        return response

