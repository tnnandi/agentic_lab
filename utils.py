import os
import re
from datetime import datetime
from docx import Document

def save_output(report, code, execution_result, iteration):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"./output_agent/output_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)

    # save report
    doc = Document()
    doc.add_heading(f"Research Report - Iteration {iteration + 1}", level=1)
    doc.add_paragraph(report)
    report_file = os.path.join(output_dir, f"research_report_iteration_{iteration + 1}.docx")
    doc.save(report_file)

    # save code
    code_file = os.path.join(output_dir, f"code_iteration_{iteration + 1}.py")
    with open(code_file, "w") as f:
        f.write(code)

    # save execution results
    result_file = os.path.join(output_dir, f"execution_result_{iteration + 1}.txt")
    with open(result_file, "w") as f:
        f.write(execution_result)

    print(f"\nOutputs saved for iteration {iteration + 1} in {output_dir}")

# function to clean up the report to conform to professional standards
def clean_report(text):
    """
    Removes LLM reasoning, markdown, and formatting artifacts from report output.
    """
    # Remove <think>...</think> blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

    # Remove markdown-style headers and separators
    text = re.sub(r"^\s*#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*-{3,}\s*$", "", text, flags=re.MULTILINE)

    # Remove extra leading/trailing whitespace
    return text.strip()