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
    
    if changes:
        plan_prompt = f"""
        As a Principal Investigator, analyze the following sources and create a detailed plan for the topic: '{topic}'
        
        Sources:
        {sources}
        
        Mode: {mode}
        
        IMPORTANT: The user has requested specific changes to the previous plan. You MUST incorporate these changes:
        
        USER REQUESTED CHANGES: {changes}
        
        Your task is to create a NEW plan that specifically addresses these user-requested changes while maintaining the overall objective.
        
        Create a detailed plan by THINKING STEP BY STEP that includes:
        1. Key insights from the sources
        2. Analysis of any files found in the directory (if applicable)
        3. Specific tasks for each agent that incorporate the user's requested changes:
           - Research Agent: What aspects to focus on (modified based on user feedback)
           - Code Writer Agent: What code to implement, what packages to import (modified based on user feedback)
           - Code Executor Agent: How to execute the code, what packages to install (modified based on user feedback)
           - Code Reviewer Agent: What to review in the code and the execution result or error messages (modified based on user feedback)
           - Critic Agent: What to evaluate in the report and the code (modified based on user feedback)
        
        CRITICAL REQUIREMENTS:
        - You MUST modify the plan to specifically address: {changes}
        - Focus ONLY on the tasks requested by the user
        - Do NOT include tasks that weren't requested
        - Ensure the plan is actionable and specific to the user's feedback
        
        Provide a clear, actionable plan that all agents can follow, specifically incorporating the user's requested changes.
        """
    else:
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
        f"CRITICAL FILE PATH REQUIREMENTS - READ CAREFULLY:\n"
        f"1. EXTRACT ACTUAL FILE PATHS FROM SOURCES:\n"
        f"   - CAREFULLY analyze the sources to find the EXACT file paths mentioned\n"
        f"   - Look for file paths in the sources, user commands, or directory listings\n"
        f"   - Use ONLY the actual file paths that exist and are mentioned in the sources\n"
        f"   - If no specific paths are mentioned, use reasonable defaults based on the context\n\n"
        f"2. NEVER USE PLACEHOLDER PATHS:\n"
        f"   - '/path/to/files', '/path/to/actual/files', '/data/files'\n"
        f"   - 'input_dir', 'output_dir', 'data_dir'\n"
        f"   - Any generic placeholder paths\n\n"
        f"3. NEVER USE COMMAND LINE ARGUMENTS:\n"
        f"   - sys.argv, sys.argv[1], argparse, ArgumentParser()\n"
        f"   - --input_dir, --output_dir, or any command line flags\n"
        f"   - parser.add_argument(), parser.parse_args()\n\n"
        f"4. ALWAYS USE DIRECT FILE PATHS:\n"
        f"   - Use the actual file paths directly in the code\n"
        f"   - Include proper validation and error handling\n"
        f"   - Check if files/directories exist before using them\n\n"
        f"OTHER REQUIREMENTS:\n"
        f"- ONLY output valid Python code.\n"
        f"- DO NOT include any thoughts, explanations, or markdown outside the code.\n"
        f"- WRAP the code in triple backticks as follows:\n"
        f"```python\n<your code here>\n```\n"
        f"- INCLUDE inline comments to explain the logic clearly.\n"
        f"- Include proper error handling for file operations.\n"
    )



def get_code_improve_prompt(code, feedback):
    return (
        f"You are a professional Python developer. Improve the following code based on the user's feedback:\n\n"
        f"User Feedback:\n"
        f"\"{feedback}\"\n\n"
        f"Current Code:\n"
        f"{code}\n\n"
        f"CRITICAL FILE PATH REQUIREMENTS - READ CAREFULLY:\n"
        f"1. EXTRACT ACTUAL FILE PATHS FROM SOURCES:\n"
        f"   - CAREFULLY analyze the sources to find the EXACT file paths mentioned\n"
        f"   - Look for file paths in the sources, user commands, or directory listings\n"
        f"   - Use ONLY the actual file paths that exist and are mentioned in the sources\n"
        f"   - If no specific paths are mentioned, use reasonable defaults based on the context\n\n"
        f"2. NEVER USE PLACEHOLDER PATHS:\n"
        f"   - '/path/to/files', '/path/to/actual/files', '/data/files'\n"
        f"   - 'input_dir', 'output_dir', 'data_dir'\n"
        f"   - Any generic placeholder paths\n\n"
        f"3. NEVER USE COMMAND LINE ARGUMENTS:\n"
        f"   - sys.argv, sys.argv[1], argparse, ArgumentParser()\n"
        f"   - --input_dir, --output_dir, or any command line flags\n"
        f"   - parser.add_argument(), parser.parse_args()\n\n"
        f"4. ALWAYS USE DIRECT FILE PATHS:\n"
        f"   - Use the actual file paths directly in the code\n"
        f"   - Include proper validation and error handling\n"
        f"   - Check if files/directories exist before using them\n\n"
        f"OTHER REQUIREMENTS:\n"
        f"- Fix any file path issues mentioned in the feedback\n"
        f"- Include proper error handling for file operations\n"
        f"- ONLY output valid Python code wrapped in ```python``` blocks.\n"
        f"- Include inline comments to explain the logic.\n"
        f"- Make the code more robust and user-friendly.\n"
    )




def get_execution_failure_reasoning_prompt(code, stdout, stderr):
    return (
        "You are an expert Python debugging assistant with knowledge of bioinformatics pipelines. Analyze the failed execution below, identify the most likely root causes, "
        "and propose concrete fixes that can be attempted next.\n\n"
        "--- Code ---\n"
        f"{code}\n\n"
        "--- Standard Output ---\n"
        f"{stdout if stdout else 'N/A'}\n\n"
        "--- Standard Error ---\n"
        f"{stderr if stderr else 'N/A'}\n\n"
        "Provide your response with the following structure:\n"
        "1. Root Cause Analysis: <succinct explanation>\n"
        "2. Recommended Fixes: <numbered list of actionable steps>\n"
        "3. Verification: <how to confirm the issue is resolved>\n"
        "Return only the above, without any internal reasoning or markdown fences."
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
        f"Error handling strategy\n"
        f"How you will handle file paths\n\n"
        f"CRITICAL FILE PATH REQUIREMENTS - READ CAREFULLY:\n"
        f"1. ANALYZE CURRENT DIRECTORY STRUCTURE:\n"
        f"   - The code will run in the current working directory\n"
        f"   - You MUST use ONLY files that actually exist in the current directory\n"
        f"   - Look for actual file listings in the sources (e.g., directory contents, file listings)\n"
        f"   - If the sources mention specific files, use those exact filenames\n"
        f"   - If no specific files are mentioned, use common filenames that would likely exist\n\n"
        f"2. EXTRACT ACTUAL FILE PATHS FROM SOURCES:\n"
        f"   - CAREFULLY analyze the sources to find the EXACT file paths mentioned\n"
        f"   - Look for file paths in the sources, user commands, or directory listings\n"
        f"   - Use ONLY the actual file paths that exist and are mentioned in the sources\n"
        f"   - If no specific paths are mentioned, use reasonable defaults based on the context\n\n"
        f"3. NEVER USE PLACEHOLDER PATHS:\n"
        f"   - '/path/to/files', '/path/to/actual/files', '/data/files'\n"
        f"   - 'input_dir', 'output_dir', 'data_dir'\n"
        f"   - Any generic placeholder paths\n"
        f"   - Hardcoded paths that don't exist (like GSM8080315_sample1_R0_matrix.mtx)\n\n"
        f"4. NEVER USE COMMAND LINE ARGUMENTS:\n"
        f"   - sys.argv, sys.argv[1], argparse, ArgumentParser()\n"
        f"   - --input_dir, --output_dir, or any command line flags\n"
        f"   - parser.add_argument(), parser.parse_args()\n\n"
        f"5. ALWAYS USE DIRECT FILE PATHS:\n"
        f"   - Use the actual file paths directly in the code\n"
        f"   - Include proper validation and error handling\n"
        f"   - Check if files/directories exist before using them\n"
        f"   - Use simple filenames like 'R0_matrix.mtx' instead of complex paths\n\n"
        f"6. FILE PATH PLANNING:\n"
        f"   - Plan to extract actual file paths from the sources\n"
        f"   - Plan to include file existence validation\n"
        f"   - Plan to handle missing files gracefully\n"
        f"   - Plan to use reasonable defaults if no specific paths are mentioned\n"
        f"   - Plan to use simple, common filenames (e.g., 'R0_matrix.mtx')\n"
        f"   - Plan to include clear error messages when files are missing\n\n"
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
        f"You are a professional Python developer with a strong understanding of the Python programming language and its libraries. "
        f"You are also an expert on Bioinformatics and Genomics.\n\n"
        f"Based on the following sources:\n"
        f"{sources}\n\n"
        f"{plan_section}\n\n"
        f"Approved coding plan:\n"
        f"{coding_plan}\n\n"
        f"Your task is to write Python code to accomplish this objective:\n"
        f"\"{topic}\"\n\n"
        f"CRITICAL FILE PATH REQUIREMENTS - READ CAREFULLY:\n"
        f"1. ANALYZE CURRENT DIRECTORY STRUCTURE:\n"
        f"   - The code will run in the current working directory\n"
        f"   - You MUST use ONLY files that actually exist in the current directory\n"
        f"   - Look for actual file listings in the sources (e.g., directory contents, file listings)\n"
        f"   - If the sources mention specific files, use those exact filenames\n"
        f"   - If no specific files are mentioned, use common filenames that would likely exist\n\n"
        f"IMPORTANT: The sources above contain file listings. Use ONLY files that are actually listed there.\n\n"
        f"2. EXTRACT ACTUAL FILE PATHS FROM SOURCES:\n"
        f"   - CAREFULLY analyze the sources to find the EXACT file paths mentioned\n"
        f"   - Look for file paths in the sources, user commands, or directory listings\n"
        f"   - Use ONLY the actual file paths that exist and are mentioned in the sources\n"
        f"   - If no specific paths are mentioned, use reasonable defaults based on the context\n\n"
        f"3. NEVER USE PLACEHOLDER PATHS:\n"
        f"   - '/path/to/files', '/path/to/actual/files', '/data/files'\n"
        f"   - 'input_dir', 'output_dir', 'data_dir'\n"
        f"   - Any generic placeholder paths\n"
        f"   - Hardcoded paths that don't exist (like GSM8080315_sample1_R0_matrix.mtx)\n\n"
        f"4. NEVER USE COMMAND LINE ARGUMENTS:\n"
        f"   - sys.argv, sys.argv[1], argparse, ArgumentParser()\n"
        f"   - --input_dir, --output_dir, or any command line flags\n"
        f"   - parser.add_argument(), parser.parse_args()\n\n"
        f"5. ALWAYS USE DIRECT FILE PATHS:\n"
        f"   - Use the actual file paths directly in the code\n"
        f"   - Include proper validation and error handling\n"
        f"   - Check if files/directories exist before using them\n\n"
        f"OTHER REQUIREMENTS:\n"
        f"- ONLY output valid Python code.\n"
        f"- Go through the sources to understand the dependencies and the code.\n"
        f"- Only import packages that exist in the sources.\n"
        f"- Include proper error handling for file operations.\n"
        f"- DO NOT include any thoughts, explanations, or markdown outside the code.\n"
        f"- WRAP the code in triple backticks as follows:\n"
        f"```python\n"
        f"<your code here>\n"
        f"```\n"
        f"- INCLUDE inline comments to explain the logic clearly.\n"
        f"- Follow the approved plan exactly.\n"
        f"- Use appropriate libraries based on the task and file types mentioned.\n"
        f"- Include comments in the code to explain steps.\n"
        f"- Add file path validation and error handling.\n"
        f"6. EXAMPLE OF USING FULL FILE PATHS FROM SOURCES:\n"
        f"```python\n"
        f"import os\n\n"
        f"# If sources show files in '/path/to/data/directory/', use the FULL path:\n"
        f"matrix_file = '/path/to/data/directory/data_matrix.mtx'\n"
        f"features_file = '/path/to/data/directory/data_features.tsv'\n"
        f"barcodes_file = '/path/to/data/directory/data_barcodes.tsv'\n\n"
        f"# Validate file existence\n"
        f"for file_path in [matrix_file, features_file, barcodes_file]:\n"
        f"    if not os.path.exists(file_path):\n"
        f"        raise FileNotFoundError(f'Missing file: {{file_path}}')\n"
        f"```\n\n"
        f"CRITICAL: NO PLACEHOLDERS OR FAKE IMPORTS:\n"
        f"- NEVER use placeholder imports. ALWAYS use actual imports from the sources.\n"
        f"- NEVER use fake function names or modules\n"
        f"- ONLY use real, working Python code that can be run directly\n"
        f"- ONLY import packages that actually exist\n"
        f"- If you don't know the exact import, use standard libraries or skip that part\n\n"
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


def get_package_issue_feedback_prompt(error_message, failed_packages):
    """Create a prompt to ask user for feedback about package installation issues"""
    return f"""
    A package installation failed with the following error:
    
    Error: {error_message}
    Failed packages: {failed_packages}
    
    Please provide feedback about this issue. Consider:
    - What might be causing this installation failure?
    - Do you know the correct package name or installation method?
    - Are there alternative packages or installation sources?
    - Are there environment-specific issues (conda vs pip, version conflicts, etc.)?
    - Do you have experience with this specific package or similar issues?
    
    Your feedback will help determine the best approach to resolve this issue.
    """


def get_package_feedback_processing_prompt(user_feedback, error_message, failed_packages):
    """Create a prompt to process user feedback about package installation issues"""
    return f"""
    You are a Python package installation expert. A package installation failed with this error:
    
    Error: {error_message}
    Failed packages: {failed_packages}
    
    The user provided this feedback about the issue:
    {user_feedback}
    
    Based on the error and user feedback, determine the best approach to resolve this issue.
    
    Your task is to:
    1. Analyze the error message and user feedback
    2. Identify the root cause of the installation failure
    3. Determine the most appropriate solution
    4. Provide specific installation commands or alternative approaches
    
    Consider these possibilities:
    - Package name variations 
    - Alternative installation sources (PyPI, conda, GitHub, etc.)
    - Installation method changes (pip vs conda, --user flag, etc.)
    - Environment issues (Python version, dependencies, etc.)
    - Alternative packages that provide similar functionality
    
    Respond with a JSON object in this exact format:
    {{
        "analysis": "Brief analysis of the issue and user feedback",
        "root_cause": "What's causing the installation failure",
        "solution_type": "package_name|installation_method|alternative_package|environment_fix",
        "action": "Specific command or action to take",
        "explanation": "Why this solution should work"
    }}
    """


def get_package_reasoning_prompt(error_message, failed_packages):
    """Create a prompt for the LLM to reason about package installation issues"""
    return f"""
    You are a Python package installation expert. A package installation failed with this error:
    
    Error: {error_message}
    Failed packages: {failed_packages}
    
    Your task is to analyze this error and reason about the best solution. Think step by step:
    
    1. **Analyze the error message**: What specific error is occurring?
    2. **Identify the root cause**: Why is this installation failing?
    3. **Consider possible solutions**: What are the different ways to fix this?
    4. **Determine the best approach**: What is the most appropriate solution?
    
    Consider these possibilities:
    - Package name variations 
    - Alternative installation sources (PyPI, conda, GitHub, etc.)
    - Installation method changes (pip vs conda, --user flag, etc.)
    - Environment issues (Python version, dependencies, etc.)
    - Alternative packages that provide similar functionality
    
    Provide your reasoning and proposed solution in this format:
    
    **ANALYSIS:**
    [Your analysis of the error and root cause]
    
    **POSSIBLE SOLUTIONS:**
    [List 2-3 possible approaches to fix this]
    
    **RECOMMENDED SOLUTION:**
    [Your recommended approach with specific command]
    
    **REASONING:**
    [Why this solution should work]
    
    **USER FEEDBACK REQUEST:**
    [What specific feedback you need from the user to proceed]
    """


def get_plan_changes_reasoning_prompt(changes, topic, mode):
    """Create a prompt to explain reasoning behind incorporating user-requested changes"""
    return f"""
    Explain the reasoning behind incorporating the following user-requested changes into the plan:
    
    User Requested Changes: {changes}
    
    Original Topic: {topic}
    Mode: {mode}
    
    Please explain:
    1. What specific modifications were made to address the user's request
    2. Why these changes are necessary and appropriate
    3. How the new plan differs from the original plan
    4. What aspects of the user's feedback were incorporated
    
    Provide a clear, detailed explanation of the reasoning process.
    """


def get_file_path_validation_prompt():
    return (
        f"CRITICAL FILE PATH VALIDATION REQUIREMENTS:\n\n"
        f"1. NEVER use hardcoded placeholder paths:\n"
        f"   - '/path/to/files'\n"
        f"   - '/path/to/actual/files'\n"
        f"   - '/data/files'\n"
        f"   - Any other placeholder paths\n\n"
        f"2. NEVER use command line arguments:\n"
        f"   - sys.argv for command line arguments\n"
        f"   - argparse for argument parsing\n"
        f"   - ArgumentParser() or parser.add_argument()\n"
        f"   - --input_dir, --output_dir, or any command line flags\n"
        f"   - len(sys.argv) or sys.argv[1]\n\n"
        f"3. ALWAYS use direct file paths in code:\n"
        f"   - Use actual file paths directly in the code\n"
        f"   - Use the file paths provided in the original command\n"
        f"   - Include proper validation and error handling\n\n"
        f"4. Include proper validation:\n"
        f"   - Check if files/directories exist before using them\n"
        f"   - Provide clear error messages if paths are invalid\n"
        f"   - Handle both absolute and relative paths\n"
        f"   - Support multiple file formats and extensions\n\n"
    )



