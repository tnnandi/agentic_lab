def get_quick_search_summary_prompt(query, raw_text):
    return (
        f"You are a smart research assistant. Based on the search results below, provide a factual and concise answer to the question.\n\n"
        f"Question: {query}\n\n"
        f"Search Results:\n{raw_text}\n\n"
        f"Answer:\n"
        f"Do not include your internal reasoning. Only provide the final answer clearly.\n"
    )


def get_browsing_prompt(topic, formatted_sources):
    return (
        f"You are a research assistant summarizing information from multiple sources.\n\n"
        f"Topic: {topic}\n\n"
        f"Sources:\n{formatted_sources}\n\n"
        f"Write a concise summary of the main findings and ideas from the above links. Do not include reasoning steps or commentary."
    )


def get_research_draft_prompt(sources, topic):
    return (
        f"Write a professional research report on the topic: '{topic}', using the following sources:\n\n"
        f"{sources}\n\n"
        f"Structure it like a scientific paper with these sections: Abstract, Introduction, Methods, Results, Discussion, and Conclusion.\n"
        f"Only include the final report in plain text. No markdown formatting or internal reasoning."
    )


def get_research_improve_prompt(draft, feedback):
    return (
        f"Improve the following research report using the provided feedback.\n\n"
        f"Original Draft:\n{draft}\n\n"
        f"Feedback:\n{feedback}\n\n"
        f"Return the revised version in a professional format with no commentary or thought process."
    )


def get_code_prompt(sources, topic):
    return (
        f"You are a professional Python developer. Based on the following sources:\n\n"
        f"{sources}\n\n"
        f"Your task is to write Python code to accomplish this objective:\n"
        f"\"{topic}\"\n\n"
        f"Requirements:\n"
        f"- ONLY output valid Python code.\n"
        f"- DO NOT include any thoughts, explanations, or markdown outside the code.\n"
        f"- WRAP the code in triple backticks as follows:\n"
        f"```python\n<your code here>\n```\n"
        f"- INCLUDE inline comments to explain the logic clearly.\n"
        f"- If data is missing, first search for public datasets, and if not found, generate synthetic data as needed.\n"
    )



def get_code_improve_prompt(code, feedback):
    return (
        f"You are a Python developer. Improve the following code based on the feedback below.\n\n"
        f"--- Original Code ---\n{code}\n\n"
        f"--- Feedback ---\n{feedback}\n\n"
        f"Rules:\n"
        f"- Return ONLY the final, corrected Python code.\n"
        f"- Do NOT include any commentary, explanations, or thoughts.\n"
        f"- WRAP the code in:\n```python\n<your code>\n```\n"
        f"- Include comments in the code to explain steps.\n"
    )



def get_code_review_failed_prompt(code, execution_result):
    return (
        f"The following code failed to execute:\n\n{code}\n\n"
        f"Execution Result:\n{execution_result}\n\n"
        f"Identify the cause of failure and suggest a corrected version of the code. Return only the improved code inside a ```python block``` with inline comments."
    )


def get_code_review_succeeded_prompt(code, execution_result):
    return (
        f"The following code executed successfully:\n\n{code}\n\n"
        f"Execution Result:\n{execution_result}\n\n"
        f"Suggest improvements for clarity, performance, or best practices. Return only the improved code in a ```python block```."
    )


def get_document_critique_prompt(document, sources):
    return (
        f"Review the following research document and critique it for clarity, completeness, and relevance.\n\n"
        f"Document:\n{document}\n\n"
        f"Sources:\n{sources}\n\n"
        f"Identify any logical gaps, inconsistencies, or missing information. Provide specific suggestions for improvement."
    )


def get_code_execution_review_prompt(code, execution_result):
    return (
        f"Review this executed code and its result.\n\n"
        f"Code:\n{code}\n\n"
        f"Execution Output:\n{execution_result}\n\n"
        f"Provide a detailed analysis. If it failed, suggest corrections. If it worked, suggest optimizations or refactoring. Return suggested code in a ```python block``` if applicable."
    )


def get_summary_feedback_prompt(report_feedback, code_feedback):
    return (
        f"Summarize the feedback below into a single, actionable message for the PI.\n\n"
        f"Research Report Feedback:\n{report_feedback}\n\n"
        f"Code Feedback:\n{code_feedback}\n\n"
        f"Clearly highlight what should be improved in the next iteration."
    )
