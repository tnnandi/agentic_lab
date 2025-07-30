from llm_utils import query_llm
import prompts
import os
import subprocess
import utils
from config import LLM_CONFIG
import re
import requests
from duckduckgo_search import DDGS
import xml.etree.ElementTree as ET
from pdb import set_trace
import argparse
import json
from bs4 import BeautifulSoup

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
            pdf_content="",  # Add PDF content parameter
            link_content="",  # Add link content parameter
            files_dir_content="", # Add files directory content parameter
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
        self.pdf_content = pdf_content  # Store PDF content
        self.link_content = link_content  # Store link content
        self.files_dir_content = files_dir_content # Store files directory content

    def create_plan(self, sources, topic, mode, changes=None):
        """
        Create a detailed plan based on the sources and topic.
        This plan will guide all other agents in their tasks.
        """
        if self.verbose:
            print("PI: Creating detailed plan based on sources and topic...")
        
        # Create a comprehensive plan prompt
        plan_prompt = prompts.get_pi_plan_prompt(sources, topic, mode, changes)
        
        plan = query_llm(plan_prompt, temperature=LLM_CONFIG["temperature"]["research"])

        if changes:
            reasoning = f"""
            Reasoning for the new plan:
            - User requested changes: {changes}
            - Adjustments made to the plan based on user feedback.
            """
            print("PI: Reasoning about the changes and creating a new plan...")
            print(reasoning)

        return plan
        

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

                if self.iteration == 0:  # use the topic prompt for the first round of iteration; for subsequent rounds, use the topic as well as feedback from critic agent from the previous round/s
                    sources = self.browsing_agent.browse(topic, self.pdf_content, self.link_content, self.files_dir_content)
                    if self.verbose:
                        print("PI: Browsing Agent provided the following sources:")
                        print(sources[:1000])
                        print("------------------------------------")

                    # The PI agent will now plan the next steps and print the plan to screen
                    plan = self.create_plan(sources, topic, self.mode)
                    print("PI: Created the following plan:")
                    print(plan)
                    print("------------------------------------")
                    

                    # # Ask the user if they want to proceed with the plan, and recommned changes if needed
                    # user_input = input("PI: Do you want to proceed with the plan? (y/n): ")
                    # if user_input == "n":
                    #     print("PI: User requested changes to the plan.")
                    #     changes = input("PI: Please input the suggestedchanges: ")
                    #     # The PI should reason about the changes and create a new plan
                    #     # print the reasoining used to create the new plan
                    #     print("PI: Reasoning about the changes and creating a new plan...")
                        
                    #     plan = self.create_plan(sources, topic, self.mode, changes)
                    #     print("PI: Created the following plan:")
                    #     print(plan)
                    #     print("------------------------------------")

                    while True:
                        user_input = input("PI: Do you want to proceed with the plan? (y/n): ").lower().strip()
                        if user_input == "y":
                            print("PI: User agreed to the plan.")
                            break
                        elif user_input == "n":
                            print("PI: User requested changes to the plan.")
                            changes = input("PI: Please input the suggested changes: ")
                            # The PI should reason about the changes and create a new plan
                            print("PI: Reasoning about the changes and creating a new plan...")
                            
                            plan = self.create_plan(sources, topic, self.mode, changes)
                            print("PI: Created the following imrpoved plan:")
                            print(plan)
                            print("------------------------------------")
                        else:
                            print("PI: Invalid input. Please enter 'y' or 'n'.")

                    # The above plan should also be communicated to the other agents
                    self.research_agent.plan = plan
                    self.code_writer_agent.plan = plan
                    self.code_executor_agent.plan = plan
                    self.code_reviewer_agent.plan = plan
                    self.critic_agent.plan = plan
                
                    # Only create report if mode is research_only or both
                    if self.mode in ["research_only", "both"]:
                        raw_report = self.research_agent.draft_document(sources, topic)
                        print("Cleaning up report to a professional format")
                        report = utils.clean_report(raw_report)
                        if self.verbose:
                            print("\nPI: Research Agent drafted the following report:")
                            print(report)
                    else:
                        report = None
                    # set_trace()
                    # Only create code if mode is code_only or both
                    if self.mode in ["code_only", "both"]:
                        code = self.code_writer_agent.create_code(sources, topic)
                        if self.verbose:
                            print("\nPI: Code Writer Agent created the following code:")
                            print(" --------------------------- ")
                            print(code) 
                    else:
                        code = None
                        
                else:  # use the critic feedback for the subsequent rounds of iteration
                    # Only improve report if mode is research_only or both
                    if self.mode in ["research_only", "both"]:
                        raw_report = self.research_agent.improve_document(report, self.last_critique["document"])
                        print("Cleaning up report to a professional format")
                        report = utils.clean_report(raw_report)
                        if self.verbose:
                            print("\nPI: Research Agent improved the draft of the report:")
                            print(report)

                    # Only improve code if mode is code_only or both
                    if self.mode in ["code_only", "both"]:
                        code = self.code_writer_agent.improve_code(code, self.last_critique["code"])
                        if self.verbose:
                            print("\nPI: Code Writer Agent improved the code:")
                            print(code)

                # Handle code iteration and research improvement based on mode
                if self.mode in ["code_only", "both"]:
                    # Iterate between code agents until success
                    code, code_success = self._iterate_code_until_success(code, sources, topic)
                    if code_success:
                        print(" **** Code iteration completed successfully! ****")
                    else:
                        print("\n !!!! Code iteration completed but user may not be fully satisfied.")
                    
                    # Get final execution result for critic review
                    execution_result = self.code_executor_agent.execute_code(code)
                    if self.verbose:
                        print("\nPI: Final Code Executor Agent execution result:")
                        print(execution_result)
                else:
                    # Research-only mode: improve document
                    report = self.research_agent.improve_document(report, critique_report)
                    execution_result = ""

                # Only review document if mode is research_only or both
                if self.mode in ["research_only", "both"]:
                    critique_report = self.critic_agent.review_document(report, sources)
                else:
                    critique_report = ""
                
                # Only review code execution if mode is code_only or both
                if self.mode in ["code_only", "both"]:
                    critique_code = self.critic_agent.review_code_execution(code, execution_result)
                else:
                    critique_code = ""
                
                # Handle feedback based on mode - CRITIC AGENT CALLED AT END OF ROUND
                if self.mode == "both":
                    summary_feedback = self.critic_agent.communicate_with_pi(critique_report, critique_code)
                    self.last_critique = {"document": critique_report, "code": critique_code}
                    if self.verbose:
                        print("\nPI: Critic Agent summarized the feedback:")
                        print(summary_feedback)
                
                elif self.mode == "research_only":
                    summary_feedback = self.critic_agent.communicate_with_pi(critique_report, "")
                    self.last_critique = {"document": critique_report, "code": ""}
                    if self.verbose:
                        print("\nPI: Critic Agent summarized the research-only feedback:")
                        print(summary_feedback)

                elif self.mode == "code_only":
                    summary_feedback = self.critic_agent.communicate_with_pi("", critique_code)
                    self.last_critique = {"document": "", "code": critique_code}
                    if self.verbose:
                        print("\nPI: Critic Agent summarized the code-only feedback:")
                        print(summary_feedback)

                # save outputs after every round
                utils.save_output(report, code, execution_result, self.iteration)

                self.iteration += 1

            print(f"\nPI: Maximum rounds ({self.max_rounds}) reached. Stopping.")
            return report, code, False

    def _iterate_code_until_success(self, initial_code, sources, topic, max_code_iterations=10):
        """
        Iterate between CodeWriterAgent, CodeExecutorAgent, and CodeReviewerAgent 
        until the code runs successfully and the user is satisfied.
        
        Args:
            initial_code: The initial code to start with
            sources: The sources for context
            topic: The topic being worked on
            max_code_iterations: Maximum number of code improvement iterations
            
        Returns:
            tuple: (final_code, success_flag)
        """
        code = initial_code
        iteration = 0
        user_satisfied = False
        
        print(f"\n Starting code iteration loop (max {max_code_iterations} iterations) ...")
        
        while iteration < max_code_iterations and not user_satisfied:
            iteration += 1
            print(f"\n Code Iteration {iteration}/{max_code_iterations}")
            print("=" * 50)
            
            # Step 1: Execute the code
            print("\n CodeExecutorAgent: Executing code...")
            execution_result = self.code_executor_agent.execute_code(code)
            
            # Check if execution was successful
            if "failed" not in execution_result.lower() and "User declined" not in execution_result:
                print("Code executed successfully!")
                
                # Step 2: Review the successful execution
                print("\n CodeReviewerAgent: Reviewing successful execution...")
                review_feedback = self.code_reviewer_agent.review_code(code, execution_result)
                
                # Ask user if they're satisfied
                print(f"\n Code Review Feedback:")
                print(review_feedback[:500] + "..." if len(review_feedback) > 500 else review_feedback)
                
                user_input = input("\n Are you satisfied with the code execution? (y/n): ").strip().lower()
                
                if user_input == "y":
                    user_satisfied = True
                    print(" **** User satisfied! Code iteration complete. ****")
                    break
                else:
                    # User wants improvements
                    improvement_request = input(" What specific improvements would you like? ")
                    print("\n CodeWriterAgent: Improving code based on user feedback...")
                    code = self.code_writer_agent.improve_code(code, improvement_request)
                    
            else:
                # Code execution failed
                print("!!!! Code execution failed or was declined. !!!!")
                print(f"Error: {execution_result[:200]}...")
                
                # Step 3: Review the failed execution
                print("\n CodeReviewerAgent: Reviewing failed execution...")
                review_feedback = self.code_reviewer_agent.review_code(code, execution_result)
                
                # Extract user feedback if available
                user_feedback_match = re.search(r"Feedback: (.*)", execution_result)
                user_feedback = user_feedback_match.group(1).strip() if user_feedback_match else ""
                
                # Combine feedback
                combined_feedback = review_feedback
                if user_feedback:
                    combined_feedback += f"\n\nAdditional user feedback:\n{user_feedback}"
                
                print(f"\n Combined Feedback:")
                print(combined_feedback[:500] + "..." if len(combined_feedback) > 500 else combined_feedback)
                
                # Step 4: Improve the code
                print("\n CodeWriterAgent: Improving code based on feedback...")
                code = self.code_writer_agent.improve_code(code, combined_feedback)
        
        if iteration >= max_code_iterations:
            print(f"\n Maximum code iterations ({max_code_iterations}) reached.")
            print("Consider reviewing the code manually or adjusting the requirements.")
        
        return code, user_satisfied


# Browsing Agent
# currently does not fetch real time info (need to do it)
class BrowsingAgent_Old:
    def browse(self, topic):
        print(f"********* Browsing Agent: Gathering sources for topic '{topic}'")
        prompt = prompts.get_browsing_prompt(topic)
        return query_llm(prompt)

# Connect the browsing agent to the BioMCP server
class BrowsingAgent:
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.links = [] # Initialize links attribute

    def browse(self, topic, pdf_content="", link_content="", files_dir_content=""):
        print(f"********* Browsing Agent: Gathering sources for topic '{topic}'")

        results = {
            # "PubMed": self.search_pubmed(topic),
            # "DuckDuckGo": self.search_duckduckgo(topic),
            # "DuckDuckGo": self.search_duckduckgo(topic),
        }

        # Process any provided links
        if hasattr(self, 'links') and self.links:
            link_content = self.process_links(self.links)

        # Combine all sources (pubmed, duckduckgo, etc., and not PDFs or links)
        sources = []
        for source_name, source_results in results.items():
            if source_results:
                sources.append(f"{source_name}:\n{source_results}")
       
        # Add PDF content if available
        if pdf_content:
            sources.append(f"PDF Content:\n{pdf_content}")
    
        # Add link content if available
        if link_content:
            sources.append(f"Link Content:\n{link_content}")
    
        # Add files directory content if available
        if files_dir_content:
            sources.append(f"Files Directory Content:\n{files_dir_content}")

        formatted_sources = "\n\n".join(sources)
        # set_trace()

        if self.verbose:# print full content of each source
            for source in sources:
                print(f"Full content of {source[:100]}...")
                print(source[100:])
                print("--------------------------------")
        
        if self.verbose:
            print("Browsing Agent: Sources gathered:")
            print(formatted_sources[:1000])
        
        return formatted_sources

    def process_links(self, links):
        """Process multiple URLs and extract their content"""
        if not links:
            return ""
        
        link_contents = []
        for link in links:
            try:
                print(f"Browsing Agent: Accessing link: {link}")
                
                # Special handling for HuggingFace notebook URLs
                if "huggingface.co" in link and ".ipynb" in link:
                    content = self.extract_huggingface_notebook(link)
                else:
                    # Regular web scraping
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                    response = requests.get(link, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Remove script and style elements
                        for script in soup(["script", "style"]):
                            script.decompose()
                        
                        # Extract text content
                        text_content = soup.get_text()
                        # Clean up whitespace
                        lines = (line.strip() for line in text_content.splitlines())
                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                        text_content = ' '.join(chunk for chunk in chunks if chunk)
                        
                        # Extract code blocks separately
                        code_blocks = []
                        for code in soup.find_all(['code', 'pre']):
                            code_blocks.append(code.get_text().strip())
                        
                        content = f"URL: {link}\n"
                        content += f"Text Content: {text_content}\n"
                        if code_blocks:
                            content += f"Code Blocks ({len(code_blocks)} found):\n"
                            for i, code in enumerate(code_blocks, 1):
                                content += f"--- Code Block {i} ---\n{code}\n"
                    else:
                        print(f"Failed to access {link} - Status code: {response.status_code}")
                        content = f"URL: {link}\nFailed to access content"
                        
                link_contents.append(content)
                print(f"Successfully processed {link}")
                    
            except Exception as e:
                print(f"Error accessing {link}: {e}")
                link_contents.append(f"URL: {link}\nError: {str(e)}")
        
        return "\n\n".join(link_contents)

    def extract_huggingface_notebook(self, url):
        """Extract content from HuggingFace notebook URLs"""
        try:
            # Convert blob URL to raw URL
            raw_url = url.replace("/blob/", "/resolve/")
            
            print(f"Extracting HuggingFace notebook from: {raw_url}")
            response = requests.get(raw_url, timeout=10)
            
            if response.status_code == 200:
                # Parse the notebook JSON
                notebook = json.loads(response.text)
                
                content = f"URL: {url}\n"
                content += "HuggingFace Jupyter Notebook Content:\n"
                content += "=" * 50 + "\n"
                
                # Extract text and code from notebook cells
                for i, cell in enumerate(notebook.get('cells', []), 1):
                    cell_type = cell.get('cell_type', 'unknown')
                    
                    if cell_type == 'markdown':
                        # Extract markdown text
                        source = ''.join(cell.get('source', []))
                        content += f"\n--- Markdown Cell {i} ---\n{source}\n"
                        
                    elif cell_type == 'code':
                        # Extract code
                        source = ''.join(cell.get('source', []))
                        content += f"\n--- Code Cell {i} ---\n{source}\n"
                        
                        # Extract output if available
                        outputs = cell.get('outputs', [])
                        if outputs:
                            content += f"\n--- Output {i} ---\n"
                            for output in outputs:
                                if output.get('output_type') == 'stream':
                                    content += ''.join(output.get('text', []))
                                elif output.get('output_type') == 'execute_result':
                                    content += ''.join(output.get('data', {}).get('text/plain', []))
                
                return content
            else:
                return f"URL: {url}\nFailed to access HuggingFace notebook - Status code: {response.status_code}"
                
        except Exception as e:
            return f"URL: {url}\nError extracting HuggingFace notebook: {str(e)}"

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

    def fetch_special_url_content(self, sources):
        """
        Attempts to fetch content from URLs that might require special handling
        (e.g., HuggingFace, GitHub, raw GitHub, etc.) and append it to the sources.
        """
        enhanced_sources = sources
        # Look for URLs that might be HuggingFace or GitHub
        url_patterns = [
            r"huggingface\.co/models/[^/]+/blob/[^/]+",
            r"github\.com/[^/]+/blob/[^/]+",
            r"raw\.githubusercontent\.com/[^/]+/[^/]+",
            r"arxiv\.org/abs/[^/]+",
            r"pubmed\.ncbi\.nlm\.nih\.gov/[^/]+",
            r"duckduckgo\.com/[^/]+",
            r"eutils\.ncbi\.nlm\.nih\.gov/entrez/eutils/esearch\.fcgi"
        ]

        for pattern in url_patterns:
            matches = re.findall(pattern, enhanced_sources)
            for match in matches:
                if "huggingface.co" in match:
                    enhanced_sources += self.extract_huggingface_content(match)
                elif "github.com" in match:
                    enhanced_sources += self.extract_github_content(match)
                elif "raw.githubusercontent.com" in match:
                    enhanced_sources += self.extract_github_content(match)
                elif "arxiv.org" in match:
                    enhanced_sources += self.extract_arxiv_content(match)
                elif "pubmed.ncbi.nlm.nih.gov" in match:
                    enhanced_sources += self.extract_pubmed_content(match)
                elif "duckduckgo.com" in match:
                    enhanced_sources += self.extract_duckduckgo_content(match)
                elif "eutils.ncbi.nlm.nih.gov" in match:
                    enhanced_sources += self.extract_pubmed_content(match)

        return enhanced_sources

    def extract_huggingface_content(self, url):
        """Extract content from HuggingFace URLs"""
        try:
            # Convert blob URL to resolve URL
            resolve_url = url.replace('/blob/', '/resolve/')
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(resolve_url, headers=headers, timeout=10)
            if response.status_code == 200:
                content = response.text
                
                # Try to parse as Jupyter notebook
                if url.endswith('.ipynb'):
                    return self.parse_jupyter_notebook(content)
                else:
                    return content[:2000] + "..." if len(content) > 2000 else content
            else:
                print(f"Failed to fetch HuggingFace content: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error fetching HuggingFace content: {e}")
            return None


    def extract_github_content(self, url):
        """Extract content from GitHub URLs"""
        try:
            # Convert blob URL to raw URL
            raw_url = url.replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(raw_url, headers=headers, timeout=10)
            if response.status_code == 200:
                content = response.text
                return content[:2000] + "..." if len(content) > 2000 else content
            else:
                print(f"Failed to fetch GitHub content: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error fetching GitHub content: {e}")
            return None


    def extract_basic_content(self, url):
        """Extract basic web content"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                text_content = soup.get_text()
                return text_content[:2000] + "..." if len(text_content) > 2000 else text_content
            else:
                print(f"Failed to fetch basic content: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error fetching basic content: {e}")
            return None


    def parse_jupyter_notebook(self, content):
        """Parse Jupyter notebook content"""
        try:
            notebook = json.loads(content)
            cells = notebook.get('cells', [])
            
            extracted_text = []
            for i, cell in enumerate(cells):
                cell_type = cell.get('cell_type', '')
                source = cell.get('source', [])
                
                if isinstance(source, list):
                    text = ''.join(source)
                else:
                    text = str(source)
                
                if cell_type == 'markdown':
                    extracted_text.append(f"## Cell {i+1} (Markdown)\n{text}\n")
                elif cell_type == 'code':
                    extracted_text.append(f"## Cell {i+1} (Code)\n```python\n{text}\n```\n")
            
            return '\n'.join(extracted_text)
        except Exception as e:
            print(f"Error parsing notebook: {e}")
            return content

    def extract_arxiv_content(self, url):
        try:
            base_url = "http://export.arxiv.org/api/query"
            params = {
                "search_query": f"all:{url.split('/')[-1]}", # Assuming the last part of the URL is the ID
                "start": 0,
                "max_results": 1 # Fetch only one result
            }
            response = requests.get(base_url, params=params)
            root = ET.fromstring(response.content)
            entry = root.find("{http://www.w3.org/2005/Atom}entry")
            if entry:
                title = entry.find("{http://www.w3.org/2005/Atom}title").text
                summary = entry.find("{http://www.w3.org/2005/Atom}summary").text
                return f"\n[ArXiv Paper]\n{url}\n{title}\n{summary}\n"
            else:
                return f"\n[ArXiv Paper]\n{url}\nCould not find paper summary.\n"
        except Exception as e:
            print(f"Error fetching ArXiv content: {e}")
            return f"\n[ArXiv Paper]\n{url}\nCould not fetch ArXiv content.\n"

    def extract_pubmed_content(self, url):
        try:
            url = url.replace("pubmed.ncbi.nlm.nih.gov", "eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi")
            params = {
                "db": "pubmed",
                "term": url.split("/")[-1], # Assuming the last part of the URL is the ID
                "retmode": "json",
                "retmax": 1
            }
            res = requests.get(url, params=params)
            data = res.json()
            if data.get("esearchresult", {}).get("idlist"):
                pid = data["esearchresult"]["idlist"][0]
                return f"\n[PubMed Article]\n{url}\nCould not find article summary.\n"
            else:
                return f"\n[PubMed Article]\n{url}\nCould not find article summary.\n"
        except Exception as e:
            print(f"Error fetching PubMed content: {e}")
            return f"\n[PubMed Article]\n{url}\nCould not fetch PubMed content.\n"

    def extract_duckduckgo_content(self, url):
        try:
            with DDGS() as ddgs:
                results = ddgs.text(url)
                if results:
                    return f"\n[DuckDuckGo Search]\n{url}\n{results[0]['body']}\n"
                else:
                    return f"\n[DuckDuckGo Search]\n{url}\nCould not find search results.\n"
        except Exception as e:
            print(f"Error fetching DuckDuckGo content: {e}")
            return f"\n[DuckDuckGo Search]\n{url}\nCould not fetch DuckDuckGo content.\n"


# Research Agent
class ResearchAgent:
    def __init__(self, mode, verbose=True):
        self.mode = mode
        self.verbose = verbose
        self.plan = None  # Will store the plan from PI agent (self.code_writer_agent.plan = plan)
        
    def draft_document(self, sources, topic):
        if self.verbose:
            print(f"********* Research Agent: Drafting research report for topic '{topic}'")
            if self.plan:
                print(f"Research Agent: Following plan: {self.plan[:200]}...")
        
        # Include plan in the prompt if available
        plan_section = f"\n\nPI Agent's Plan:\n{self.plan}\n" if self.plan else ""
        prompt = prompts.get_only_research_draft_prompt(sources, topic, plan_section)
        return query_llm(prompt, temperature=LLM_CONFIG["temperature"]["research"])


    def improve_document(self, draft, feedback):
        if self.verbose:
            print("********* Research Agent: Improving draft based on feedback")
        prompt = prompts.get_research_improve_prompt(draft, feedback)
        return query_llm(prompt, temperature=LLM_CONFIG["temperature"]["research"])


# Code Writer Agent
class CodeWriterAgent:
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.plan = None  # gets the plan from PI agent (self.code_writer_agent.plan = plan)
        
    def create_code(self, sources, topic):
        if self.verbose:
            print("********** Code Writer Agent: writing code")
            if self.plan:
                print(f"Code Writer Agent: Following plan: {self.plan[:200]}...")
        
        # Include plan in the prompt if available
        plan_section = f"\n\nPI Agent's Plan:\n{self.plan}\n" if self.plan else ""
        
        # First, create a coding plan
        plan_prompt = prompts.get_coding_plan_prompt(sources, topic, plan_section)
        coding_plan = query_llm(plan_prompt, temperature=LLM_CONFIG["temperature"]["coding"])
        
        # Show the plan to user and get approval
        print("\n========= Code Writing Plan =========\n")
        print(coding_plan)
        print("\n========= End of Plan =========\n")
        
        user_input = input("Do you approve this coding plan? (y/n): ").strip().lower()
        
        while user_input != "y":
            if user_input == "n":
                feedback = input("What improvements or changes would you like to see in the plan? ")
                
                # Improve the plan based on user feedback
                improved_plan_prompt = prompts.get_improved_coding_plan_prompt(feedback, coding_plan)
                coding_plan = query_llm(improved_plan_prompt, temperature=LLM_CONFIG["temperature"]["coding"])
                
                print("\n========= Revised Code Writing Plan =========\n")
                print(coding_plan)
                print("\n========= End of Revised Plan =========\n")
                
                user_input = input("Do you approve this revised coding plan? (y/n): ").strip().lower()
            else:
                print("Please enter 'y' for yes or 'n' for no.")
                user_input = input("Do you approve this coding plan? (y/n): ").strip().lower()
        
        # Now write the actual code based on the approved plan
        code_prompt = prompts.get_code_writing_prompt(sources, topic, plan_section, coding_plan)
        response = query_llm(code_prompt, temperature=LLM_CONFIG["temperature"]["coding"])
        return utils.extract_code_only(response)
        

    def improve_code(self, code, feedback):
        if self.verbose:
            print("********** Code Writer Agent: improving code based on feedback")
        prompt = prompts.get_code_improve_prompt(code, feedback)
        response = query_llm(prompt, temperature=LLM_CONFIG["temperature"]["coding"])
        return utils.extract_code_only(response)



# Code Executor Agent
class CodeExecutorAgent:
    def __init__(self, verbose=True, conda_env_path=None):
        self.verbose = verbose
        self.plan = None  # gets the plan from PI agent (self.code_writer_agent.plan = plan)
        self.conda_env_path = conda_env_path
        
    def _verify_conda_environment(self):
        """Verify that the conda environment exists and is accessible"""
        if not self.conda_env_path:
            print("No conda environment path specified. Using system Python.")
            return False
            
        # Check if the conda environment directory exists
        if not os.path.exists(self.conda_env_path):
            print(f"ERROR: Conda environment path does not exist: {self.conda_env_path}")
            return False
            
        # Check if Python executable exists in the environment
        python_executable = self._get_python_executable()
        if not os.path.exists(python_executable):
            print(f"ERROR: Python executable not found in conda environment: {python_executable}")
            return False
            
        # Check if pip executable exists in the environment
        pip_executable = self._get_pip_executable()
        if not os.path.exists(pip_executable):
            print(f"ERROR: pip executable not found in conda environment: {pip_executable}")
            return False
            
        print(f"Conda environment verified: {self.conda_env_path}")
        return True
    
    def _get_python_version(self):
        """Get the Python version from the conda environment"""
        try:
            python_executable = self._get_python_executable()
            result = subprocess.run(
                [python_executable, "--version"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return "Unknown"
                
        except Exception as e:
            print(f"Error getting Python version: {e}")
            return "Unknown"
    
    def _get_conda_env_info(self):
        """Get information about the conda environment"""
        try:
            # Get the conda environment's site-packages directory
            python_executable = self._get_python_executable()
            result = subprocess.run(
                [python_executable, "-c", "import site; print(site.getsitepackages()[0])"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                site_packages = result.stdout.strip()
                return {
                    'python_version': self._get_python_version(),
                    'site_packages': site_packages,
                    'python_executable': python_executable
                }
            else:
                return None
                
        except Exception as e:
            print(f"Error getting conda environment info: {e}")
            return None
    
    def _get_python_executable(self):
        """Get the Python executable path for the conda environment"""
        if self.conda_env_path:
            # Use the conda environment's Python
            python_path = os.path.join(self.conda_env_path, "bin", "python")
            if os.path.exists(python_path):
                return python_path
            else:
                # Try Windows-style path
                python_path = os.path.join(self.conda_env_path, "Scripts", "python.exe")
                if os.path.exists(python_path):
                    return python_path
                else:
                    print(f"Warning: Python executable not found in {self.conda_env_path}")
                    return "python"  # Fallback to system Python
        else:
            return "python"  # Use system Python if no conda env specified
    
    def _get_pip_executable(self):
        """Get the pip executable path for the conda environment"""
        if self.conda_env_path:
            # Use the conda environment's pip
            pip_path = os.path.join(self.conda_env_path, "bin", "pip")
            if os.path.exists(pip_path):
                return pip_path
            else:
                # Try Windows-style path
                pip_path = os.path.join(self.conda_env_path, "Scripts", "pip.exe")
                if os.path.exists(pip_path):
                    return pip_path
                else:
                    print(f"Warning: pip executable not found in {self.conda_env_path}")
                    return "pip"  # Fallback to system pip
        else:
            return "pip"  # Use system pip if no conda env specified
    
    def _list_installed_packages(self):
        """List all installed packages in the conda environment"""
        try:
            pip_executable = self._get_pip_executable()
            result = subprocess.run(
                [pip_executable, "list"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                print(f"Failed to list packages: {result.stderr}")
                return ""
                
        except Exception as e:
            print(f"Error listing packages: {e}")
            return ""
    
    def _check_package_installed(self, package_name):
        """Check if a specific package is installed"""
        installed_packages = self._list_installed_packages()
        return package_name.lower() in installed_packages.lower()
    
    def _install_packages_in_conda(self, packages):
        """Install packages in the conda environment"""
        if not packages or not self.conda_env_path:
            return True
            
        try:
            print(f"Installing packages in conda environment: {packages}")
            
            # Get the pip executable
            pip_executable = self._get_pip_executable()
            
            # Clean up package names (remove any LLM thinking artifacts)
            clean_packages = []
            for package in packages:
                # Extract just the package name, removing any thinking artifacts
                clean_name = package.strip()
                # Remove any thinking artifacts like "<think>...</think>"
                if "<think>" in clean_name:
                    # Extract the last word after the thinking block
                    parts = clean_name.split("</think>")
                    if len(parts) > 1:
                        clean_name = parts[-1].strip()
                # Remove any newlines or extra whitespace
                clean_name = clean_name.replace("\n", "").strip()
                if clean_name and not clean_name.startswith("<"):
                    clean_packages.append(clean_name)
            
            if not clean_packages:
                print("No valid package names found after cleaning")
                print("\n" + "="*60)
                print("❓ PACKAGE INSTALLATION FAILED - USER FEEDBACK REQUESTED")
                print("="*60)
                user_suggestion = input("The system couldn't find valid package names. Do you have suggestions for the correct package names or installation method? (optional): ").strip()
                if user_suggestion:
                    print(f"User suggestion for package installation: {user_suggestion}")
                return False
            
            print(f"Cleaned package names: {clean_packages}")
            
            install_cmd = [pip_executable, "install"] + clean_packages
            
            result = subprocess.run(
                install_cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"Successfully installed packages: {clean_packages}")
                return True
            else:
                print(f"Failed to install packages: {result.stderr}")
                
                # Ask for user suggestions when package installation fails
                print("\n" + "="*60)
                print("❓ PACKAGE INSTALLATION FAILED - USER FEEDBACK REQUESTED")
                print("="*60)
                print(f"Failed to install: {clean_packages}")
                print(f"Error: {result.stderr}")
                user_suggestion = input("Do you have suggestions for fixing the package installation? (e.g., different package names, alternative installation methods, conda vs pip): ").strip()
                
                if user_suggestion:
                    print(f"User suggestion for package installation: {user_suggestion}")
                    # Could potentially retry with user suggestions here
                
                return False
                
        except Exception as e:
            print(f"Error installing packages: {e}")
            
            # Ask for user suggestions when package installation throws an exception
            print("\n" + "="*60)
            print("❓ PACKAGE INSTALLATION EXCEPTION - USER FEEDBACK REQUESTED")
            print("="*60)
            user_suggestion = input("An exception occurred during package installation. Do you have suggestions for fixing this? (e.g., environment issues, network problems, alternative packages): ").strip()
            
            if user_suggestion:
                print(f"User suggestion for package installation exception: {user_suggestion}")
            
            return False
        
    def execute_code(self, code):
        if self.verbose:
            print("********** Code Executor Agent: executing code")
            
            # Verify conda environment
            if self.conda_env_path:
                print(f"Specified conda environment: {self.conda_env_path}")
                
                # Verify the environment exists and is accessible
                if self._verify_conda_environment():
                    # Get environment information
                    env_info = self._get_conda_env_info()
                    if env_info:
                        print(f"Python version: {env_info['python_version']}")
                        print(f"Python executable: {env_info['python_executable']}")
                        print(f"Site-packages: {env_info['site_packages']}")
                    
                    # List installed packages
                    print("\n=== Currently Installed Packages ===")
                    installed_packages = self._list_installed_packages()
                    print(installed_packages)  # Show full output
                    print("=" * 50)
                else:
                    print("Conda environment verification failed. Using system Python.")
            else:
                print("No conda environment specified. Using system Python.")

        # extract only the code section using regex
        cleaned_code = self.extract_code(code)

        if not cleaned_code.strip():
            print("Execution aborted: No valid Python code detected.")
            user_suggestion = input("\n❓ Do you have any suggestions for what might be wrong with the code? (optional): ").strip()
            if user_suggestion:
                return f"Execution failed: No valid Python code detected. User suggestion: {user_suggestion}"
            return "Execution failed: No valid Python code detected."

        # print extracted code and ask for user confirmation
        print("\n========= Extracted code ========= \n")
        print(" *********** Code starts here (no non-code elements should be below this) ***********")
        print(cleaned_code)
        print("*********** Code ends here ***********\n")

        user_input = input("Do you want to execute this code? (y/n): ").strip().lower()

        if user_input != "y":
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

            # Get the appropriate Python executable
            python_executable = self._get_python_executable()
            
            # execute the code using the conda environment's Python
            print(f"\nExecuting the code using: {python_executable}\n")
            result = subprocess.run(
                [python_executable, temp_file], capture_output=True, text=True
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
                    
                    # Check which packages are actually missing
                    actually_missing = []
                    for package in missing_packages:
                        if not self._check_package_installed(package):
                            actually_missing.append(package)
                        else:
                            print(f"Package '{package}' is already installed")
                    
                    if actually_missing:
                        print(f"Packages that need installation: {actually_missing}")
                        packages_to_install = self._resolve_package_names_with_llm(actually_missing)
                        
                        # Install packages in conda environment
                        if self._install_packages_in_conda(packages_to_install):
                            # Ask user again before retrying execution
                            user_retry = input("\nPackages were installed in conda environment. Do you want to retry executing the code? (y/n): ").strip().lower()
                            if user_retry != "y":
                                reason = input("You declined to retry running the improved code. Why? (optional feedback): ").strip()
                                feedback_msg = f"Execution skipped after fix: User declined to run improved code."
                                if reason:
                                    feedback_msg += f" Feedback: {reason}"
                                print("User opted not to retry the code.")
                                return feedback_msg

                            # Proceed with re-execution
                            print("\nRetrying execution after package installation...\n")
                            result = subprocess.run([python_executable, temp_file], capture_output=True, text=True)
                    else:
                        print("All detected packages are already installed. The error might be due to import issues.")

            if result.returncode == 0:
                # Check if the output contains error messages even though return code is 0
                output_text = result.stdout.lower()
                error_indicators = [
                    'error', 'failed', 'exception', 'traceback', 'module not found',
                    'no module named', 'import error', 'syntax error', 'typeerror',
                    'valueerror', 'attributeerror', 'keyerror', 'indexerror',
                    'file not found', 'permission denied', 'timeout', 'connection error'
                ]
                
                has_error = any(indicator in output_text for indicator in error_indicators)
                
                if has_error:
                    print("Execution failed (detected error in output):")
                    print(result.stdout)
                    if result.stderr:
                        print("\n=== Execution Errors ===")
                        print(result.stderr)
                    
                    # Ask for user suggestions after detecting error in output
                    print("\n" + "="*60)
                    print("❓ EXECUTION FAILED (ERROR IN OUTPUT) - USER FEEDBACK REQUESTED")
                    print("="*60)
                    user_suggestion = input("The code ran but produced errors. Do you have suggestions for fixing these errors? (e.g., correct function parameters, data format, missing dependencies): ").strip()
                    
                    if user_suggestion:
                        return f"Execution failed (error in output):\n{result.stdout}\n\nUser suggestion: {user_suggestion}"
                    else:
                        return f"Execution failed (error in output):\n{result.stdout}"
                else:
                    print("Execution succeeded:")
                    print(result.stdout)
                    return result.stdout
            else:
                print("Execution failed:")
                print(result.stderr)
                
                # Ask for user suggestions after any failure
                print("\n" + "="*60)
                print("❓ EXECUTION FAILED - USER FEEDBACK REQUESTED")
                print("="*60)
                user_suggestion = input("Do you have any suggestions for fixing this error? (e.g., specific packages, code changes, environment issues): ").strip()
                
                if user_suggestion:
                    return f"Execution failed:\n{result.stderr}\n\nUser suggestion: {user_suggestion}"
                else:
                    return f"Execution failed:\n{result.stderr}"
                    
        except Exception as e:
            print("Execution failed with exception:")
            print(str(e))
            
            # Ask for user suggestions after any exception
            print("\n" + "="*60)
            print("EXECUTION FAILED WITH EXCEPTION - USER FEEDBACK REQUESTED")
            print("="*60)
            user_suggestion = input("Do you have any suggestions for fixing this exception? (e.g., code issues, environment problems, missing dependencies): ").strip()
            
            if user_suggestion:
                return f"Execution failed with exception:\n{str(e)}\n\nUser suggestion: {user_suggestion}"
            else:
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
            prompt = prompts.get_package_resolution_prompt(mod)

            print(f"Asking LLM: What to install for missing module '{mod}'...")
            try:
                response = query_llm(prompt).strip()
                resolved_packages.append(response)
            except Exception as e:
                print(f"LLM failed to resolve package for '{mod}': {e}")
                
                # Ask for user suggestions when LLM fails to resolve package names
                print("\n" + "="*60)
                print("❓ LLM PACKAGE RESOLUTION FAILED - USER FEEDBACK REQUESTED")
                print("="*60)
                user_suggestion = input(f"The LLM couldn't resolve the package name for '{mod}'. Do you know the correct package name or installation method? (optional): ").strip()
                
                if user_suggestion:
                    print(f"User suggestion for package '{mod}': {user_suggestion}")
                    resolved_packages.append(user_suggestion)
                else:
                    # Use the original module name as fallback
                    resolved_packages.append(mod)
        
        return resolved_packages


# Code Reviewer agent
class CodeReviewerAgent:
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.plan = None  # gets the plan from PI agent (self.code_writer_agent.plan = plan)
        
    def review_code(self, code, execution_result):
        if self.verbose:
            print(f"********** Code Reviewer Agent: reviewing code based on {execution_result[:100]}...")
        
        # Use LLM to analyze the execution result and determine the appropriate fix
        analysis_prompt = prompts.get_code_reviewer_analysis_prompt(code, execution_result)
        analysis = query_llm(analysis_prompt, temperature=LLM_CONFIG["temperature"]["review"])
        
        # Use the analysis to create a targeted fix prompt
        fix_prompt = prompts.get_code_reviewer_fix_prompt(code, execution_result, analysis)
        
        return query_llm(fix_prompt, temperature=LLM_CONFIG["temperature"]["review"])


# Critic agent
class CriticAgent:
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.plan = None  # gets the plan from PI agent (self.code_writer_agent.plan = plan)
        
    def review_document(self, document, sources):
        if self.verbose:
            print("********** Critic Agent: reviewing document")
        prompt = prompts.get_document_critique_prompt(document, sources)
        return query_llm(prompt, temperature=LLM_CONFIG["temperature"]["critic"])

    def review_code_execution(self, code, execution_result):
        if self.verbose:
            print("********** Critic Agent: reviewing code execution")
        prompt = prompts.get_code_execution_review_prompt(code, execution_result)
        return query_llm(prompt, temperature=LLM_CONFIG["temperature"]["critic"])

    def communicate_with_pi(self, report_feedback, code_feedback):
        if self.verbose:
            print("********** Critic Agent: communicating with PI")
        prompt = prompts.get_summary_feedback_prompt(report_feedback, code_feedback)
        return query_llm(prompt, temperature=LLM_CONFIG["temperature"]["critic"])

