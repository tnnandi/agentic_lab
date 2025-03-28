from llm_utils import query_llm
import prompts
import os
import subprocess
import utils
from config import LLM_CONFIG
import re
import requests
from duckduckgo_search import DDGS
from llm_utils import query_llm  # Your LLM wrapper
import xml.etree.ElementTree as ET
from pdb import set_trace

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
            max_rounds=3, # each subsequent round improves on the previous round's outputs using feedback from the critic
            quick_search=False,
            mode="both",
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
        self.quick_search = quick_search
        self.mode = mode
        self.verbose = verbose
        

    def coordinate(self, topic):
        """
        Coordinate with other agents to complete the task
        """
        if self.quick_search:
            print("Shortcut mode activated: Directly searching for real-time results using DuckDuckGo.\n")
            results = utils.quick_duckduckgo_search(topic)
            print(results)
            return results, None, True

        else:
            global total_tokens_used, output_log
            print("self.mode: ", self.mode)
            while self.iteration < self.max_rounds:
                print(
                    f"################  PI: Starting round {self.iteration + 1} for topic '{topic}' ########################"
                )

                if self.iteration == 0:  # use the topic prompt for the first round of iteration
                    sources = self.browsing_agent.browse(topic)
                    if self.verbose:
                        print("PI: Browsing Agent provided the following sources:")
                        print(sources)
                        print("------------------------------------")
                    if self.mode in ["research_only", "both"]:
                        raw_report = self.research_agent.draft_document(sources, topic)
                        print("Cleaning up report to a professional format")
                        report = utils.clean_report(raw_report)
                    else:
                        report = None
                    if self.verbose:
                        print("\nPI: Research Agent drafted the following report:")
                        print(report)
                    
                    if self.mode in ["code_only", "both"]:
                        code = self.code_writer_agent.create_code(sources, topic)
                        if self.verbose:
                            print("\nPI: Code Writer Agent created the following code:")
                            print(" --------------------------- ")
                            print(code) 
                            # set_trace()
                    else:
                        code = None
                        
                else:  # use the critic feedback for the subsequent rounds of iteration
                    if self.mode in ["research_only", "both"]:
                        raw_report = self.research_agent.improve_document(report, self.last_critique["document"])
                        # create a clean report removing LLM's inner thoughts and non-standard separators
                        print("Cleaning up report to a professional format")
                        report = utils.clean_report(raw_report)

                        if self.verbose:
                            print("\nPI: Research Agent improved the draft of the report:")
                            print(report)

                    if self.mode in ["code_only", "both"]:
                        code = self.code_writer_agent.improve_code(code, self.last_critique["code"])
                        if self.verbose:
                            print("\nPI: Code Writer Agent improved the code:")
                            print(code)

                # Critic agent reviews BOTH the document and the executed code
                if self.mode in ["code_only", "both"]:
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
                    critique_code = self.critic_agent.review_code_execution(code, execution_result)
                else:
                    critique_code = ""
                    execution_result = ""
                
                if self.mode in ["research_only", "both"]:
                    critique_report = self.critic_agent.review_document(report, sources)
                else:
                    critique_report = ""
                
                if self.mode == "both":
                    summary_feedback = self.critic_agent.communicate_with_pi(critique_report, critique_code)
                    self.last_critique = {"document": critique_report, "code": critique_code}
                    if self.verbose:
                        print("\nPI: Critic Agent summarized the feedback:")
                        print(summary_feedback)

                # save outputs after every round
                utils.save_output(report, code, execution_result, self.iteration)

                # if the code failed, improve it based on feedback
                # if self.mode in ["both", "code_only"] and "failed" in execution_result.lower():
                #     print("\nPI: Code execution failed. Improving code based on feedback.")
                #     code = self.code_writer_agent.improve_code(code, review_feedback)

                if self.mode in ["both", "code_only"] and "failed" in execution_result.lower(): # ensure "failed" is present in responses from all failed instances
                    print("\nPI: Code execution failed. Improving code based on feedback.")

                    # extract user feedback from the execution result
                    user_feedback_match = re.search(r"Feedback: (.*)", execution_result)
                    user_feedback = user_feedback_match.group(1).strip() if user_feedback_match else ""

                    # combine review feedback and user feedback into one string
                    combined_feedback = review_feedback
                    if user_feedback:
                        combined_feedback += f"\n\nAdditional user feedback:\n{user_feedback}"

                    # improve the code based on both sources
                    code = self.code_writer_agent.improve_code(code, combined_feedback)


                else:
                    print("\nPI: Pipeline execution complete. Finalizing.")
                    return report, code, True

                self.iteration += 1

            print(f"\nPI: Maximum rounds ({self.max_rounds}) reached. Stopping.")
            return report, code, False


# Browsing Agent
# currently does not fetch real time info (need to do it)
class BrowsingAgent_Old:
    def browse(self, topic):
        print(f"********* Browsing Agent: Gathering sources for topic '{topic}'")
        prompt = prompts.get_browsing_prompt(topic)
        return query_llm(prompt)

class BrowsingAgent:
    def browse(self, topic):
        print(f"********* Browsing Agent: Gathering sources for topic '{topic}'")

        results = {
            "PubMed": self.search_pubmed(topic),
            "DuckDuckGo": self.search_duckduckgo(topic),
            "arXiv": self.search_arxiv(topic),
            # "GTEx": [f"https://gtexportal.org/home/search/{topic}"],
            # "GeneCards": [f"https://www.genecards.org/Search/Keyword?queryString={topic}"],
            "Semantic Scholar": self.search_semantic_scholar(topic)
        }

        formatted_sources = "\n".join(
            f"\n[{source}]\n" + "\n".join(links)
            for source, links in results.items() if links
        )

        prompt = prompts.get_browsing_prompt(topic, formatted_sources)
        summary = query_llm(prompt)

        return summary + "\n\nSources:\n" + formatted_sources

    def search_duckduckgo(self, query, max_results=5):
        try:
            with DDGS() as ddgs:
                results = ddgs.text(query)
                return [res["href"] for res in list(results)[:max_results]]
        except Exception as e:
            print(f"DuckDuckGo search error: {e}")
            return []

    def search_pubmed(self, query, max_results=5):
        try:
            url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            params = {
                "db": "pubmed",
                "term": query,
                "retmode": "json",
                "retmax": max_results
            }
            res = requests.get(url, params=params)
            ids = res.json()["esearchresult"]["idlist"]
            return [f"https://pubmed.ncbi.nlm.nih.gov/{pid}/" for pid in ids]
        except Exception as e:
            print(f"PubMed search error: {e}")
            return []

    def search_arxiv(self, query, max_results=5):
        try:
            base_url = "http://export.arxiv.org/api/query"
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": max_results
            }
            response = requests.get(base_url, params=params)
            root = ET.fromstring(response.content)
            return [entry.find("{http://www.w3.org/2005/Atom}id").text for entry in root.findall("{http://www.w3.org/2005/Atom}entry")]
        except Exception as e:
            print(f"arXiv search error: {e}")
            return []

    def search_semantic_scholar(self, query, max_results=5):
        try:
            url = f"https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                "query": query,
                "limit": max_results,
                "fields": "title,url"
            }
            res = requests.get(url, params=params)
            data = res.json()
            return [paper["url"] for paper in data.get("data", [])]
        except Exception as e:
            print(f"Semantic Scholar search error: {e}")
            return []

# Research Agent
class ResearchAgent:
    def draft_document(self, sources, topic):
        print(f"********* Research Agent: Drafting research report for topic '{topic}'")
        prompt = prompts.get_research_draft_prompt(sources, topic)
        return query_llm(prompt, temperature=LLM_CONFIG["temperature"]["research"])


    def improve_document(self, draft, feedback):
        print("********* Research Agent: Improving draft based on feedback")
        prompt = prompts.get_research_improve_prompt(draft, feedback)
        return query_llm(prompt, temperature=LLM_CONFIG["temperature"]["research"])


# Code Writer Agent
class CodeWriterAgent:
    def create_code(self, sources, topic):
        print("********** Code Writer Agent: writing code")
        prompt = prompts.get_code_prompt(sources, topic)
        response = query_llm(prompt, temperature=LLM_CONFIG["temperature"]["coding"])
        return utils.extract_code_only(response)
        

    def improve_code(self, code, feedback):
        print("********** Code Writer Agent: improving code based on feedback")
        prompt = prompts.get_code_improve_prompt(code, feedback)
        response = query_llm(prompt, temperature=LLM_CONFIG["temperature"]["coding"])
        return utils.extract_code_only(response)



# Code Executor Agent
class CodeExecutorAgent:
    def execute_code(self, code):
        print("********** Code Executor Agent: executing code")

        # extract only the code section using regex
        # code not being extracted properly
        cleaned_code = self.extract_code(code) # can remove this now as the code is cleaned within by the code writer agent itself

        if not cleaned_code.strip():
            print("Execution aborted: No valid Python code detected.")
            return "Execution failed: No valid Python code detected."

        # print extracted code and ask for user confirmation
        print("\n========= Extracted code ========= \n")
        print(" *********** Code starts here (no non-code elements should be below this) ***********")
        print(cleaned_code)
        print("*********** Code ends here ***********\n")

        user_input = input("Do you want to execute this code? (Yes/No): ").strip().lower()

        # if user_input != "yes":
        #     print("User opted to rewrite the code.")
        #     return "User requested a code rewrite." # add abilities to request user input on why the code needs rewrite
        
        if user_input != "yes":
            reason = input("You declined to run the code. Why? (optional feedback): ").strip()
            feedback_msg = f"Execution failed: User declined to run the code."
            if reason:
                feedback_msg += f" Feedback: {reason}"
            print("User opted not to execute the code.")
            return feedback_msg

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
                    packages_to_install = self._resolve_package_names_with_llm(missing_packages)
                    self._install_packages(packages_to_install)

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

    def _detect_missing_packages(self, error_message): # doesn't use LLMs to find missing packages
        """
        Detect missing packages from the error message.
        """
        missing_packages = set()
        # look for patterns like "No module named 'numpy'"
        matches = re.findall(r"No module named '([\w\.-]+)'", error_message)
        if matches:
            missing_packages.update(matches)
        return list(missing_packages)
    
    def _resolve_package_names_with_llm(self, missing_modules):
        """
        Detect missing packages from the error message.
        """
        resolved_packages = []

        for mod in missing_modules:
            prompt = (
                f"You are a Python environment assistant.\n"
                f"The module '{mod}' was imported in the code, "
                f"but it raised 'No module named {mod}'.\n"
                f"What is the correct PyPI package name to install via pip for this module?\n"
                f"Respond with only the pip package name, no explanations."
            )

            print(f"Asking LLM: What to install for missing module '{mod}'...")
            try:
                response = query_llm(prompt).strip()
                resolved_packages.append(response)
            except Exception as e:
                print(f"LLM failed to resolve package for '{mod}': {e}")
        
        return resolved_packages


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
            prompt = prompts.get_code_review_failed_prompt(code, execution_result)
        else:
            prompt = prompts.get_code_review_succeeded_prompt(code, execution_result)
        return query_llm(prompt, temperature=LLM_CONFIG["temperature"]["critique"])


# Critic agent
class CriticAgent:
    def review_document(self, document, sources):
        """Review the research document for clarity, completeness, and accuracy."""
        print("********** Critic Agent: Reviewing research document **********")
        prompt = prompts.get_document_critique_prompt(document, sources)
        return query_llm(prompt, temperature=LLM_CONFIG["temperature"]["critique"])

    def review_code_execution(self, code, execution_result):
        """Analyze the code and execution result, checking for correctness and potential improvements."""
        print("********** Critic Agent: Reviewing code execution **********")
        prompt = prompts.get_code_execution_review_prompt(code, execution_result)
        return query_llm(prompt, temperature=LLM_CONFIG["temperature"]["critique"])

    def communicate_with_pi(self, report_feedback, code_feedback):
        print("********** Critic Agent: Communicating with PI")
        prompt = prompts.get_summary_feedback_prompt(report_feedback, code_feedback)
        return query_llm(prompt, temperature=LLM_CONFIG["temperature"]["critique"])

