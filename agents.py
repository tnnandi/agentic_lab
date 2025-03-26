from llm_utils import query_llm
from prompts import *
import os
import subprocess
import utils
from config import LLM_CONFIG
import re

# add capabilities for real time browsing, and browsing medical databases like TCGA, GTEx, GeneCard, 
# add persistent context memory

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
                raw_report = self.research_agent.draft_document(sources, topic)
                print("Cleaning up report to a professional format")
                report = utils.clean_report(raw_report)

                if self.verbose:
                    print("\nPI: Research Agent drafted the following report:")
                    print(report)
                code = self.code_writer_agent.create_code(sources, topic)
                if self.verbose:
                    print("\nPI: Code Writer Agent created the following code:")
                    print(code)
            else:  # use the critic feedback for the subsequent rounds of iteration
                raw_report = self.research_agent.improve_document(report, self.last_critique["document"])
                # create a clean report removing LLM's inner thoughts and non-standard separators
                print("Cleaning up report to a professional format")
                report = utils.clean_report(raw_report)

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
# currently does not fetch real time info (need to do it)
class BrowsingAgent:
    def browse(self, topic):
        print(f"********* Browsing Agent: Gathering sources for topic '{topic}'")
        prompt = get_browsing_prompt(topic)
        return query_llm(prompt)


# Research Agent
class ResearchAgent:
    def draft_document(self, sources, topic):
        print(f"********* Research Agent: Drafting research report for topic '{topic}'")
        prompt = get_research_draft_prompt(sources, topic)
        return query_llm(prompt)


    def improve_document(self, draft, feedback):
        print("********* Research Agent: Improving draft based on feedback")
        prompt = get_research_improve_prompt(draft, feedback)
        return query_llm(prompt)


# Code Writer Agent
class CodeWriterAgent:
    def create_code(self, sources, topic):
        print("********** Code Writer Agent: writing code")
        prompt = get_code_prompt(sources, topic)
        return query_llm(prompt, temperature=LLM_CONFIG["temperature"]["coding"])

    def improve_code(self, code, feedback):
        print("********** Code Writer Agent: improving code based on feedback")
        prompt = get_code_improve_prompt(code, feedback)
        return query_llm(prompt, temperature=LLM_CONFIG["temperature"]["coding"])


# Code Executor Agent
class CodeExecutorAgent:
    def execute_code(self, code):
        print("********** Code Executor Agent: executing code")

        # extract only the code section using regex
        # code not being extracted properly
        cleaned_code = self.extract_code(code)

        if not cleaned_code.strip():
            print("Execution aborted: No valid Python code detected.")
            return "Execution failed: No valid Python code detected."

        # print extracted code and ask for user confirmation
        print("\n========= Extracted code ========= \n")
        print(" *********** Code starts here (no non-code elements should be below this) ***********")
        print(cleaned_code)
        print("*********** Code ends here ***********\n")

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
            prompt = get_code_review_failed_prompt(code, execution_result)
        else:
            prompt = get_code_review_succeeded_prompt(code, execution_result)
        return query_llm(prompt, temperature=LLM_CONFIG["temperature"]["critique"])


# Critic agent
class CriticAgent:
    def review_document(self, document, sources):
        """Review the research document for clarity, completeness, and accuracy."""
        print("********** Critic Agent: Reviewing research document **********")
        prompt = get_document_critique_prompt(document, sources)
        return query_llm(prompt)

    def review_code_execution(self, code, execution_result):
        """Analyze the code and execution result, checking for correctness and potential improvements."""
        print("********** Critic Agent: Reviewing code execution **********")
        prompt = get_code_execution_review_prompt(code, execution_result)
        return query_llm(prompt)

    def communicate_with_pi(self, report_feedback, code_feedback):
        print("********** Critic Agent: Communicating with PI")
        prompt = get_summary_feedback_prompt(report_feedback, code_feedback)
        return query_llm(prompt)

