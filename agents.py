from llm_utils import query_llm
import subprocess
import utils
from config import LLM_CONFIG
import re

# Principal Investigator agent
class PrincipalInvestigatorAgent:
    def __init__(
            self,
            browsing_agent,
            research_agent,
            code_writer_agent,
            code_executor_agent,
            code_reviewer_agent,
            critic_agent,
            max_rounds=3,
            # each subsequent round improves on the previous round's outputs using feedback from the critic
            verbose=True,
    ):
        self.browsing_agent = browsing_agent
        self.research_agent = research_agent
        self.code_writer_agent = code_writer_agent
        self.code_executor_agent = code_executor_agent
        self.code_reviewer_agent = code_reviewer_agent
        self.critic_agent = critic_agent
        self.iteration = 0
        self.max_rounds = max_rounds
        self.verbose = verbose

    def coordinate(self, topic):
        """
        Coordinate with other agents to complete the task
        """
        global total_tokens_used, output_log
        while self.iteration < self.max_rounds:
            print(
                f"################  PI: Starting round {self.iteration + 1} for topic '{topic}' ########################"
            )

            if self.iteration == 0:  # use the topic prompt for the first round of iteration
                sources = self.browsing_agent.browse(topic)
                if self.verbose:
                    print("PI: Browsing Agent provided the following sources:")
                    print(sources)
                report = self.research_agent.draft_document(sources, topic)
                if self.verbose:
                    print("\nPI: Research Agent drafted the following report:")
                    print(report)
                code = self.code_writer_agent.create_code(sources, topic)
                if self.verbose:
                    print("\nPI: Code Writer Agent created the following code:")
                    print(code)
            else:  # use the critic feedback for the subsequent rounds of iteration
                report = self.research_agent.improve_document(report, self.last_critique["document"])
                if self.verbose:
                    print("\nPI: Research Agent improved the draft of the report:")
                    print(report)
                code = self.code_writer_agent.improve_code(code, self.last_critique["code"])
                if self.verbose:
                    print("\nPI: Code Writer Agent improved the code:")
                    print(code)

            # Code Executor agent executes the code
            execution_result = self.code_executor_agent.execute_code(code)
            if self.verbose:
                print("\nPI: Code Executor Agent execution result:")
                print(execution_result)

            # Code Reviewer agent checks the output and suggests changes if needed
            review_feedback = self.code_reviewer_agent.review_code(
                code, execution_result
            )
            if self.verbose:
                print("\nPI: Code Reviewer Agent provided the following feedback:")
                print(review_feedback)

            # Critic agent reviews BOTH the document and the executed code
            critique_report = self.critic_agent.review_document(report, sources)
            critique_code = self.critic_agent.review_code_execution(code, execution_result)
            summary_feedback = self.critic_agent.communicate_with_pi(critique_report, critique_code)
            self.last_critique = {"document": critique_report, "code": critique_code}

            if self.verbose:
                print("\nPI: Critic Agent summarized the feedback:")
                print(summary_feedback)

            # save outputs after every round
            utils.save_output(report, code, execution_result, self.iteration)

            # if the code failed, improve it based on feedback
            if "failed" in execution_result.lower():
                print("\nPI: Code execution failed. Improving code based on feedback.")
                code = self.code_writer_agent.improve_code(
                    code, review_feedback
                )
            else:
                print("\nPI: Code executed successfully. Finalizing.")
                return report, code, True

            self.iteration += 1

        print(f"\nPI: Maximum rounds ({self.max_rounds}) reached. Stopping.")
        return report, code, False


# Browsing Agent
class BrowsingAgent:
    def browse(self, topic):
        print(f"********* Browsing Agent: Gathering sources for topic '{topic}'")
        prompt = (
            f"You are tasked with gathering reliable sources for the topic '{topic}'. Use resources like PubMed, arXiv, and other credible sources. "
            "Provide a summary of the gathered information."
        )
        return query_llm(prompt)


# Research Agent
class ResearchAgent:
    def draft_document(self, sources, topic):
        print(f"********* Research Agent: Drafting research report for topic '{topic}'")
        # prompt = (
        #     f"Based on the following sources:\n{sources}\n"
        #     f"Draft a comprehensive research report on {topic}.\n"
        #     f"Please do not include your chains of thought in the report.\n"
        #     f"Write the report in the format of a published scientific article."
        # )

#         prompt = (
#             f"Based on the following sources:\n{sources}\n\n"
#             f"Draft a comprehensive and professional scientific research report on the topic: '{topic}'.\n"
#             f"Do NOT include any reasoning steps, internal thought processes, or self-reflection.\n"
#             f"Write the report in the formal tone and structure of a published scientific article, including sections such as Abstract, Introduction, Methods, Results, Discussion, and Conclusion, as appropriate.\n"
#             f"Focus entirely on the topic, using the sources provided. Do not include any assistant or AI commentary.\n"
# )
        prompt = (
            f"Based on the following sources:\n{sources}\n\n"
            f"Write a comprehensive, formal research report on the topic: '{topic}'.\n"
            f"Structure the report like a peer-reviewed scientific article, including sections such as Abstract, Introduction, Methods, Results, Discussion, and Conclusion.\n"
            f"Do not include any internal thoughts, reasoning steps, or assistant commentary. Only output the final report.\n"
            f"Do not use markdown formatting. Use plain text with section headings clearly labeled.\n"
)

        return query_llm(prompt)

    def improve_document(self, draft, feedback):
        print("********* Research Agent: Improving draft based on feedback")

        prompt = (
            f"Here is a draft report:\n{draft}\n\n"
            f"And here is the feedback:\n{feedback}\n\n"
            "Please revise the draft to address the feedback and improve its quality."
        )

        return query_llm(prompt)


# Code Writer Agent
class CodeWriterAgent:
    def create_code(self, sources, topic):
        print("********** Code Writer Agent: writing code")
        prompt = (
            f"Based on the following sources:\n{sources}\n"
            f"Create a Python code for {topic}. Include detailed comments explaining each step. If data is not available, create synthetic data."
        )

        return query_llm(prompt, temperature=LLM_CONFIG["temperature"]["coding"])

    def improve_code(self, code, feedback):
        print("********** Code Writer Agent: improving code based on feedback")
        prompt = (
            f"Here is a code:\n{code}\n\n"
            f"And here is the feedback:\n{feedback}\n\n"
            "Please revise the code to address the feedback and improve its clarity and functionality."
        )

        return query_llm(prompt, temperature=LLM_CONFIG["temperature"]["coding"])


# Code Executor Agent
class CodeExecutorAgent:
    def execute_code(self, code):
        print("********** Code Executor Agent: executing code")

        # extract only the code section using regex
        cleaned_code = self.extract_code(code)

        if not cleaned_code.strip():
            print("Execution aborted: No valid Python code detected.")
            return "Execution failed: No valid Python code detected."

        # print extracted code and ask for user confirmation
        print("\n========= Extracted Code =========")
        print(cleaned_code)
        print("==================================\n")

        user_input = input("Do you want to execute this code? (Yes/No): ").strip().lower()

        if user_input != "yes":
            print("User opted to rewrite the code.")
            return "User requested a code rewrite." # add abilities to request user input on why the code needs rewrite

        try:
            # save the cleaned code to a temporary file
            temp_file = "temp_code.py"
            with open(temp_file, "w") as f:
                f.write(cleaned_code)

            # execute the code using subprocess
            print("\nExecuting the code...\n")
            result = subprocess.run(
                ["python", temp_file], capture_output=True, text=True
            )

            # print standard output
            print("\n=== Execution Output ===")
            print(result.stdout)

            # print standard error if any
            if result.stderr:
                print("\n=== Execution Errors ===")
                print(result.stderr)

            # check if the execution failed due to missing packages
            if result.returncode != 0:
                missing_packages = self._detect_missing_packages(result.stderr)
                if missing_packages:
                    print(f"Missing packages detected: {missing_packages}")
                    self._install_packages(missing_packages)

                    # Retry executing the code after installing the packages
                    print("\nRetrying execution after installing missing packages...\n")
                    result = subprocess.run(
                        ["python", temp_file], capture_output=True, text=True
                    )

            if result.returncode == 0:
                print("Execution succeeded:")
                print(result.stdout)
                return result.stdout
            else:
                print("Execution failed:")
                print(result.stderr)
                return f"Execution failed:\n{result.stderr}"
        except Exception as e:
            print("Execution failed with exception:")
            print(str(e))
            return f"Execution failed with exception:\n{str(e)}"

    # def extract_code(self, text):
    #     """
    #     Extracts Python code from a response, removing non-code explanations.
    #     Prioritizes code within triple backticks (```) but defaults to full text if not found.
    #     """
    #     code_blocks = re.findall(r"```python\n(.*?)\n```", text, re.DOTALL) # often this only extracts a small subpart of the code due to stray backticks

    #     if code_blocks:
    #         return "\n".join(code_blocks)
    #     else:
    #         print("Warning: No explicit code block detected, using raw output.")
    #         return text  # Assume the entire response is Python code if no markers exist

    def extract_code(self, text):
        """
        Extracts Python code from the response while:
        - removing unnecessary backticks
        - ensuring full script extraction without truncation
        - removing non-code explanations before and after the script
        """

        # locate first and last occurrence of python code block
        start_idx = text.find("```python")
        end_idx = text.rfind("```")

        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            # extract only the text inside the first and last python block
            extracted_code = text[start_idx + len("```python"):end_idx].strip()
        else:
            # if no explicit code blocks exist, assume the full response is code
            extracted_code = text.strip()

        # remove any stray backticks or markdown headers inside the extracted code
        extracted_code = extracted_code.replace("```python", "").replace("```", "").strip()

        return extracted_code

    def _detect_missing_packages(self, error_message):
        """
        Detect missing packages from the error message.
        """
        missing_packages = set()
        # look for patterns like "No module named 'numpy'"
        matches = re.findall(r"No module named '([\w\.-]+)'", error_message)
        if matches:
            missing_packages.update(matches)
        return list(missing_packages)

    def _install_packages(self, packages):
        """
        Install the required packages using pip.
        """
        if not packages:
            return
        print(f"Installing missing packages: {packages}")
        try:
            subprocess.run(
                ["pip", "install"] + packages, check=True, capture_output=True, text=True
            )
            print("Packages installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install packages: {e.stderr}")
            raise


# Code Reviewer agent
class CodeReviewerAgent:
    def review_code(self, code, execution_result):
        print("********** Code Reviewer Agent: Reviewing code and execution result")
        if "failed" in execution_result.lower():
            prompt = (
                f"The following code failed to execute:\n\n{code}\n\n"
                f"Here is the execution result:\n{execution_result}\n\n"
                "Please analyze the error and suggest specific changes to fix the code."
            )
        else:
            prompt = (
                f"The following code executed successfully:\n\n{code}\n\n"
                f"Here is the execution result:\n{execution_result}\n\n"
                "Please review the output and suggest any improvements if necessary."
            )
        return query_llm(prompt, temperature=LLM_CONFIG["temperature"]["critique"])


# Critic agent
class CriticAgent:
    def review_document(self, document, sources):
        """Review the research document for clarity, completeness, and accuracy."""
        print("********** Critic Agent: Reviewing research document **********")
        prompt = (
            f"The following is a research report on '{sources}':\n\n"
            f"Report:\n{document}\n\n"
            "Please critique this draft. Identify any gaps in logic, missing details, or areas that need improvement. "
            "Provide actionable feedback to improve the quality of the research."
        )
        return query_llm(prompt)

    def review_code_execution(self, code, execution_result):
        """Analyze the code and execution result, checking for correctness and potential improvements."""
        print("********** Critic Agent: Reviewing code execution **********")
        prompt = (
            f"The following code was executed:\n\n{code}\n\n"
            f"Execution result:\n{execution_result}\n\n"
            "Please provide a detailed critique of the code. If it failed, analyze the reason and suggest improvements. "
            "If it succeeded, suggest ways to optimize the code for efficiency, readability, or best practices."
        )
        return query_llm(prompt)

    def communicate_with_pi(self, report_feedback, code_feedback):
        print("********** Critic Agent: Communicating with PI")
        prompt = (
            f"The Principal Investigator requires a summary of the following feedback:\n\n"
            f"Report Feedback:\n{report_feedback}\n\n"
            f"Code Feedback:\n{code_feedback}\n\n"
            "Please combine these into a concise and actionable summary, including recommendations for the next steps."
        )
        return query_llm(prompt)

