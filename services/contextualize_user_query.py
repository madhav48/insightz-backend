from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate


def build_query_refiner_chain(llm):
    """
    Returns a chain that takes conversation history and user query,
    and outputs a refined, context-aware query for downstream use.
    """
    prompt = PromptTemplate(
        input_variables=["history", "user_query"],
        template=(
            "You are a financial assistant. Given the conversation history and the latest user message, "
            "analyze the user's intent and generate a clear, concise query for a financial search.\n\n"
            "Conversation History:\n{history}\n\n"
            "User Query:\n{user_query}\n\n"
            "Output ONLY the best possible search query, no explanations or extra text. Keep the response short and concise.\n\n"
        )
    )
    return LLMChain(llm=llm, prompt=prompt, output_key="refined_query")




def format_history(history):
        if len(history) > 10:
            history = history[-10:]
        mapped = []
        for msg in history:
            role = msg.get("role", "user").capitalize()
            parts = msg.get("parts", [])
            content = " ".join([p.get("text", "") for p in parts])
            mapped.append(f"{role}: {content}")
        return "\n".join(mapped)


def contextualize_user_query(llm, history, user_query):
    """
    Formats history, runs the query refiner chain, and returns the refined query.
    """

    formatted_history = format_history(history)
    query_refiner_chain = build_query_refiner_chain(llm)
    result = query_refiner_chain.run({"history": formatted_history, "user_query": user_query})
    return result
