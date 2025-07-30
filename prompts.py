import os
import re
from datetime import datetime
from docx import Document
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import requests
from llm_utils import query_llm
import prompts
import io


def get_quick_search_summary_prompt(query, raw_text):
    return (
        f"You are a smart research assistant. Based on the search results below, provide a factual and concise answer to the question.\n\n"
        f"Question: {query}\n\n"
        f"Search Results:\n{raw_text}\n\n"
        f"Answer:\n"
        f"Do not include your internal reasoning. Only provide the final answer clearly.\n"
    )

def get_pi_plan_prompt(sources, topic, mode, changes=None):
    """Create a comprehensive plan prompt for the Principal Investigator"""
    plan_prompt = f"""
    As a Principal Investigator, analyze the following sources and create a detailed plan for the topic: '{topic}'
    
    Sources:
    {sources}
    
    Mode: {mode}
    
    Create a detailed plan by THINKING STEP BY STEP that includes:
    1. Key insights from the sources
    2. Analysis of any files found in the directory (if applicable)
    3. Specific tasks for each agent:
       - Research Agent: What aspects to focus on
       - Code Writer Agent: What code to implement, what packages to import
       - Code Executor Agent: How to execute the code, what packages to install
       - Code Reviewer Agent: What to review in the code and the execution result or error messages
       - Critic Agent: What to evaluate in the report and the code
    
    
    Provide a clear, actionable plan that all agents can follow. You do not need to provide time estimates for tasks. 
    ABSOLUTELY DO NOT plan for tasks that haven't been asked for, if you do, it will destroy the pipeline.
    I REPEAT, DO NOT PLAN FOR TASKS THAT HAVEN'T BEEN ASKED FOR.
    """

    if changes:
        plan_prompt += f"""
    User requested the following changes to the plan:
    {changes}

    Reasoning about the changes and incorporating them into the new plan.
    """
    
    return plan_prompt

def get_browsing_prompt(topic, formatted_sources):
    return (
        f"You are a research assistant summarizing information from multiple sources.\n\n"
        f"Topic: {topic}\n\n"
        f"Sources:\n{formatted_sources}\n\n"
        f"Write a concise summary of the main findings and ideas from the above links. Do not include reasoning steps or commentary."
    )


def get_only_research_draft_prompt(sources, topic, plan_section=""):
    return (
        f"Write a professional research report on the topic: '{topic}', using the following sources:\n\n"
        f"{sources}\n\n"
        f"{plan_section}\n\n"
        f"Structure it like a scientific paper with these sections: Abstract, Introduction, Methods, Results, Discussion, and Conclusion.\n"
        f"Only include the final report in plain text. No markdown formatting or internal reasoning."
    )

# def get_research_draft_prompt(sources, topic, pdf_content="", link_content=""):
#     pdf_section = f"\n\nPDF Documents:\n{pdf_content}\n" if pdf_content else ""
#     link_section = f"\n\nLink Content:\n{link_content}\n" if link_content else ""
#     return (
#         f"Write a professional research report on the topic: '{topic}', using the following sources:\n\n"
#         f"{sources}{pdf_section}{link_section}\n\n"
#         f"Structure it like a scientific paper with these sections: Abstract, Introduction, Methods, Results, Discussion, and Conclusion.\n"
#         f"Only include the final report in plain text. No markdown formatting or internal reasoning."
#     )

def get_research_improve_prompt(draft, feedback):
    return (
        f"Improve the following research report using the provided feedback.\n\n"
        f"Original Draft:\n{draft}\n\n"
        f"Feedback:\n{feedback}\n\n"
        f"Return the revised version in a professional format with no commentary or thought process."
    )


def get_code_prompt(sources, topic, plan_section=""):
    return (
        f"You are a professional Python developer. Based on the following sources:\n\n"
        f"{sources}\n\n"
        f"{plan_section}\n\n"
        f"Your task is to write Python code to accomplish this objective:\n"
        f"\"{topic}\"\n\n"
        f"Requirements:\n"
        f"- ONLY output valid Python code.\n"
        f"- DO NOT include any thoughts, explanations, or markdown outside the code.\n"
        f"- WRAP the code in triple backticks as follows:\n"
        f"```python\n<your code here>\n```\n"
        f"- INCLUDE inline comments to explain the logic clearly.\n"
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


def get_coding_plan_prompt(sources, topic, plan_section=""):
    return (
        f"You are a professional Python developer with a strong understanding of the Python programming language and its libraries. "
        f"You are also an expert on Bioinformatics and Genomics.\n\n"
        f"Based on the following sources:\n"
        f"{sources}\n\n"
        f"{plan_section}\n\n"
        f"Your task is to write Python code to accomplish this objective:\n"
        f"\"{topic}\"\n\n"
        f"BEFORE writing the actual code, create a detailed plan explaining:\n"
        f"What libraries/packages you will use and why\n"
        f"What files you will use and why\n"
        f"The overall structure and approach you will take\n"
        f"Key functions/classes you will create\n"
        f"How you will handle data \n"
        f"Error handling strategy\n\n"
        f"Provide a clear, step-by-step plan that a user can review and approve before you write the actual code."
        f"DO NOT include anything that hasn't been asked for even though it might be in the sources."
    )


def get_improved_coding_plan_prompt(feedback, coding_plan):
    return (
        f"The user provided the following feedback on the coding plan:\n"
        f"\"{feedback}\"\n\n"
        f"Original plan:\n"
        f"{coding_plan}\n\n"
        f"Please revise the plan based on the user's feedback. Address their concerns and incorporate their suggestions."
    )


def get_code_writing_prompt(sources, topic, plan_section, coding_plan):
    return (
        f"You are a professional Python developerwith a strong understanding of the Python programming language and its libraries. "
        f"You are also an expert on Bioinformatics and Genomics.\n\n"
        f"Based on the following sources:\n"
        f"{sources}\n\n"
        f"{plan_section}\n\n"
        f"Approved coding plan:\n"
        f"{coding_plan}\n\n"
        f"Your task is to write Python code to accomplish this objective:\n"
        f"\"{topic}\"\n\n"
        f"Requirements:\n"
        f"- ONLY output valid Python code.\n"
        f"- ONLY use correct file paths and file names and not placeholder names.\n"
        f"- DO NOT include any thoughts, explanations, or markdown outside the code.\n"
        f"- WRAP the code in triple backticks as follows:\n"
        f"```python\n"
        f"<your code here>\n"
        f"```\n"
        f"- INCLUDE inline comments to explain the logic clearly.\n"
        f"- Follow the approved plan exactly.\n"
        f"- Use appropriate libraries based on the task and file types mentioned.\n"
        f"- Include comments in the code to explain steps.\n"
    )


def get_code_reviewer_analysis_prompt(code, execution_result):
    """Create a prompt to analyze the execution result and determine what needs to be fixed"""
    
    # Check if user provided a suggestion
    user_suggestion = ""
    if "User suggestion:" in execution_result:
        suggestion_start = execution_result.find("User suggestion:") + len("User suggestion:")
        suggestion_end = execution_result.find("\n", suggestion_start)
        if suggestion_end == -1:
            suggestion_end = len(execution_result)
        user_suggestion = execution_result[suggestion_start:suggestion_end].strip()
    
    return f"""Analyze this code execution result and identify what needs to be fixed:

Code:
{code}

Execution Result:
{execution_result}

{f"USER SUGGESTION: {user_suggestion}" if user_suggestion else ""}

Based on the execution result, identify:
1. What type of issue occurred (user feedback, execution error, output error, etc.)
2. What specific problems need to be addressed
3. What the root cause is
4. What approach should be taken to fix it

{f"IMPORTANT: The user provided a specific suggestion: '{user_suggestion}'. Prioritize this suggestion in your analysis and use it as the primary approach to fix the issue." if user_suggestion else ""}

Provide a concise analysis in this format:
ISSUE_TYPE: [user_feedback/execution_error/output_error/success]
ROOT_CAUSE: [brief description of the main problem]
SPECIFIC_PROBLEMS: [list of specific issues to fix]
APPROACH: [how to fix the issues - prioritize user suggestion if provided]

Focus on understanding the user's intent and the actual problems, not just surface-level issues."""


def get_code_reviewer_fix_prompt(code, execution_result, analysis):
    """Create a prompt to fix the code based on the intelligent analysis"""
    
    # Check if user provided a suggestion
    user_suggestion = ""
    if "User suggestion:" in execution_result:
        suggestion_start = execution_result.find("User suggestion:") + len("User suggestion:")
        suggestion_end = execution_result.find("\n", suggestion_start)
        if suggestion_end == -1:
            suggestion_end = len(execution_result)
        user_suggestion = execution_result[suggestion_start:suggestion_end].strip()
    
    return f"""Based on this analysis of the code execution:

ANALYSIS:
{analysis}

Code:
{code}

Execution Result:
{execution_result}

{f"USER SUGGESTION: {user_suggestion}" if user_suggestion else ""}

Provide a corrected version of the code that addresses the identified issues. 

{f"CRITICAL: The user provided a specific suggestion: '{user_suggestion}'. Implement this suggestion as the primary solution to fix the issue." if user_suggestion else ""}

Requirements:
1. Fix the specific problems identified in the analysis
2. Address the root cause, not just symptoms
3. Make the code more robust and user-friendly
4. Add proper error handling and validation
5. Include inline comments explaining the changes
{f"6. IMPLEMENT THE USER'S SUGGESTION: {user_suggestion}" if user_suggestion else ""}

Return only the improved code in a ```python block```."""



def get_package_resolution_prompt(mod):
    """Create a prompt for resolving package names with LLM"""
    return (
        f"You are a Python environment assistant.\n"
        f"The module '{mod}' was imported in the code, "
        f"but it raised 'No module named {mod}'.\n"
        f"What is the correct PyPI package name to install via pip for this module?\n"
        f"Respond with only the pip package name, no explanations."
    )



