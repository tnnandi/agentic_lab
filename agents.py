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
        
        
        Provide a clear, actionable plan that all agents can follow. ABSOLUTELY DO NOT plan for tasks that haven't been asked for, if you do, it will destroy the pipeline.
        I REPEAT, DO NOT PLAN FOR TASKS THAT HAVEN'T BEEN ASKED FOR.
        """

        if changes:
            plan_prompt += f"""
        User requested the following changes to the plan:
        {changes}

        Reasoning about the changes and incorporating them into the new plan.
        """
        
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

                # Only execute code if mode is code_only or both
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
                
                # Only review document if mode is research_only or both
                if self.mode in ["research_only", "both"]:
                    critique_report = self.critic_agent.review_document(report, sources)
                else:
                    critique_report = ""
                
                # Handle feedback based on mode
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

                # if the code failed, improve it based on feedback
                # if self.mode in ["both", "code_only"] and "failed" in execution_result.lower():
                #     print("\nPI: Code execution failed. Improving code based on feedback.")
                #     code = self.code_writer_agent.improve_code(code, review_feedback)

                if self.mode in ["both", "code_only"] and ("failed" in execution_result.lower() or "User declined" in execution_result):
                    print("\nPI: Code execution failed or was declined. Improving code based on feedback.")
                    
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
                    report = self.research_agent.improve_document(report, critique_report)
                    
                    # print("\nPI: Pipeline execution complete. Finalizing.")
                    # return report, code, True

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
                        print(f"❌ Failed to access {link} - Status code: {response.status_code}")
                        content = f"URL: {link}\nFailed to access content"
                        
                link_contents.append(content)
                print(f"✅ Successfully processed {link}")
                    
            except Exception as e:
                print(f"❌ Error accessing {link}: {e}")
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
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.plan = None  # gets the plan from PI agent (self.code_writer_agent.plan = plan)
        
    def execute_code(self, code):
        if self.verbose:
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

        user_input = input("Do you want to execute this code? (y/n): ").strip().lower()

        # if user_input != "yes":
        #     print("User opted to rewrite the code.")
        #     return "User requested a code rewrite." # add abilities to request user input on why the code needs rewrite
        
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

                    # Ask user again before retrying execution
                    user_retry = input("\nPackages were installed or fixes were made. Do you want to retry executing the code? (y/n): ").strip().lower()
                    if user_retry != "y":
                        reason = input("You declined to retry running the improved code. Why? (optional feedback): ").strip()
                        feedback_msg = f"Execution skipped after fix: User declined to run improved code."
                        if reason:
                            feedback_msg += f" Feedback: {reason}"
                        print("User opted not to retry the code.")
                        return feedback_msg

                    # Proceed with re-execution
                    print("\nRetrying execution after fixes...\n")
                    result = subprocess.run(["python", temp_file], capture_output=True, text=True)

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
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.plan = None  # gets the plan from PI agent (self.code_writer_agent.plan = plan)
        
    def review_code(self, code, execution_result):
        if self.verbose:
            print("********** Code Reviewer Agent: reviewing code")
        
        # Choose the appropriate prompt based on whether execution succeeded or failed
        if "failed" in execution_result.lower() or "User declined" in execution_result:
            prompt = prompts.get_code_review_failed_prompt(code, execution_result)
        else:
            prompt = prompts.get_code_review_succeeded_prompt(code, execution_result)
            
        return query_llm(prompt, temperature=LLM_CONFIG["temperature"]["review"])


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

