def get_quick_search_summary_prompt(query, raw_text):
    return (
            f"You are a smart research assistant. Based on the following search results, provide a concise factual answer to the question:\n\n"
            f"Question: {query}\n\n"
            f"Search Results:\n{raw_text}\n\n"
            f"Answer:"
        )



def get_browsing_prompt(topic, formatted_sources):
    # return (
    #     f"You are tasked with gathering reliable sources for the topic '{topic}'. "
    #     "Use resources like PubMed, arXiv, TCGA, GTEx, GeneCard, and other credible databases. "
    #     "Provide a summary of the gathered information."
    # )

    return (
            f"The following are links and sources for the topic: '{topic}'.\n"
            f"Summarize the key ideas or themes based on the URLs:\n{formatted_sources}\n\n"
            f"Return a concise summary suitable for grounding a research report."
        )


def get_research_draft_prompt(sources, topic):
    return (
        f"Based on the following sources:\n{sources}\n\n"
        f"Write a comprehensive, formal research report on the topic: '{topic}'.\n"
        f"Structure the report like a peer-reviewed scientific article, including sections such as Abstract, Introduction, Methods, Results, Discussion, and Conclusion.\n"
        f"Do not include any internal thoughts, reasoning steps, or assistant commentary. Only output the final report.\n"
        f"Do not use markdown formatting. Use plain text with section headings clearly labeled.\n"
    )

def get_research_improve_prompt(draft, feedback):
    return (
        f"Here is a draft report:\n{draft}\n\n"
        f"And here is the feedback:\n{feedback}\n\n"
        "Please revise the draft to address the feedback and improve its quality."
    )

def get_code_prompt(sources, topic):
    return (
        f"Based on the following sources:\n{sources}\n"
        f"Create a Python code for {topic}. Include detailed comments explaining each step. "
        f"If data is not available, first try to download public datasets, and if not found, create synthetic data."
    )

def get_code_improve_prompt(code, feedback):
    return (
        f"Here is a code:\n{code}\n\n"
        f"And here is the feedback:\n{feedback}\n\n"
        "Please revise the code to address the feedback and improve its clarity and functionality."
    )

def get_code_review_failed_prompt(code, execution_result):
    return (
        f"The following code failed to execute:\n\n{code}\n\n"
        f"Here is the execution result:\n{execution_result}\n\n"
        "Please analyze the error and suggest specific changes to fix the code."
    )
def get_code_review_succeeded_prompt(code, execution_result):
    return (
        f"The following code executed successfully:\n\n{code}\n\n"
        f"Here is the execution result:\n{execution_result}\n\n"
        "Please review the output and suggest any improvements if necessary."
    )

def get_document_critique_prompt(document, sources):
    return (
        f"The following is a research report on '{sources}':\n\n"
        f"Report:\n{document}\n\n"
        "Please critique this draft. Identify any gaps in logic, missing details, or areas that need improvement. "
        "Provide actionable feedback to improve the quality of the research."
    )

def get_code_execution_review_prompt(code, execution_result):
    return (
        f"The following code was executed:\n\n{code}\n\n"
        f"Execution result:\n{execution_result}\n\n"
        "Please provide a detailed critique of the code. If it failed, analyze the reason and suggest improvements. "
        "If it succeeded, suggest ways to optimize the code for efficiency, readability, or best practices."
    )

def get_summary_feedback_prompt(report_feedback, code_feedback):
    return (
        f"The Principal Investigator requires a summary of the following feedback:\n\n"
        f"Report Feedback:\n{report_feedback}\n\n"
        f"Code Feedback:\n{code_feedback}\n\n"
        "Please combine these into a concise and actionable summary, including recommendations for the next steps."
    )
