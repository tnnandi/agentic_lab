# on laptop: conda activate /mnt/c/Users/tnandi/Downloads/ai_codes/ai_py3p12_env OR conda activate llm_env
# on Polaris: module load conda;conda activate /lus/grand/projects/GeomicVar/tarak/ai_codes/ai_py3p12_env

# Now using deepseek and qwen reasoning models hosted on Sophia/Polaris using Ollama. Will move to the ALCF inference endpoints when they make these models available
# the deepseek 70b and qwen 32B models work fine, but the 671b model throws error related to the number of experts being used is more than that allowed by the ollama llama.cpp installation

# to check if the ollama server is active try: curl --noproxy localhost http://localhost:11434/api/generate -d '{"model": "deepseek-r1:70b", "prompt": "Explain polygenic risk scores.", "temperature": 0.3}'
# OR for the qwen model: curl --noproxy localhost http://localhost:11434/api/generate -d '{"model": "qwq:latest", "prompt": "Explain polygenic risk scores.", "temperature": 0.3}'

# curl --noproxy localhost http://localhost:11434/api/generate -d '{"model": "codellama:latest", "prompt": "Write optimized matrix vector multiplication CUDA code without using cuBLAS", "temperature": 0.3}' -o output.jsonl

# to list all models available (but may not be currently active): curl http://localhost:11434/api/tags | jq '.models[] | {name, parameter_size: .details.parameter_size, quant: .details.quantization_level}'
# 


# To do:
# save all communications to a word doc
# write out codes, outputs, reports from every round
# ask for user inputs after each round to guide the workflow in the intended direction
# ensure the research reports are professional with all relevant sections and references
# allow downloading of datasets like TCGA, PDB, GTEx 

# add validation metrics using standard datasets 
# ​Make sure the code execution agent only execute the code and nothing else
# Try some coding benchmark problem execution 
# Add multimodal capabilities 


# try out the code written out manually to check its veracity; temporarily allow human in the loop to run the code and check for errors before proceeding
# make the communication between different agents two-way (in the form of meetings)
# make the prompts to the agents accessible easily as templates
# write out in a file all the outputs for every communication in every round
# add more capabilities to the agent class (check autogen, magentic-one, smolagents, amd langchain/langgraph agent types and classes and the communication patterns)
# using an orchestrator-worker pattern, allow the orchestrator to create agents it can delegate jobs to instead of having these agents predetermined
# add options for research, code, or both


from agents import (
    PrincipalInvestigatorAgent,
    BrowsingAgent,
    ResearchAgent,
    CodeWriterAgent,
    CodeExecutorAgent,
    CodeReviewerAgent,
    CriticAgent,
)
import config
import utils
import argparse
import os
from pdb import set_trace

# Argument parser for topic input
parser = argparse.ArgumentParser(description="Run Agentic Lab with a specified research topic.")
parser.add_argument("--topic", type=str, required=True, help="Specify the research topic.")
parser.add_argument("--pdfs", nargs="+", help="Specify one or more PDF files to include in the research.")
parser.add_argument("--links", nargs="+", help="Specify one or more URLs to include in the research.")
parser.add_argument("--files_dir", type=str, help="Path to directory containing files to analyze.")
parser.add_argument("--quick_search", action="store_true", help="Carry out quick search without extensive research.")
parser.add_argument("--mode", choices=["research_only", "code_only", "both"], default="both", help="Choose task mode: only generate research report, only code, or both (default)")
parser.add_argument("--conda_env", type=str, default="/Users/tnandi/Downloads/agents/agentic_lab/agentic_lab_env", help="Path to conda environment for code execution (e.g., /path/to/env)")

def main():
    args = parser.parse_args()
    
    # Process PDFs if provided
    pdf_content = ""
    if args.pdfs:
        pdf_content = utils.process_pdfs(args.pdfs)
        if pdf_content:
            print(f"Successfully processed {len(args.pdfs)} PDF file(s)")
        else:
            print("Warning: No PDF content could be extracted")
    
    # Process links if provided
    link_content = ""
    if args.links:
        print(f"Processing {len(args.links)} link(s)...")
        # The browsing agent will handle link processing
    
    # Process files directory if provided
    files_dir_content = ""
    if args.files_dir:
        print(f"Exploring files directory: {args.files_dir}")
        files_dir_content = utils.explore_files_directory(args.files_dir)
        if files_dir_content:
            print(f"Successfully explored files directory")
        else:
            print("Warning: Could not explore files directory")
    
    # Initialize agents
    browsing_agent = BrowsingAgent(verbose=True)
    research_agent = ResearchAgent(mode=args.mode, verbose=True)
    code_writer_agent = CodeWriterAgent(verbose=True)
    code_executor_agent = CodeExecutorAgent(verbose=True, conda_env_path=args.conda_env)
    code_reviewer_agent = CodeReviewerAgent(verbose=True)
    critic_agent = CriticAgent(verbose=True)
    
    # Pass links to browsing agent
    if args.links:
        browsing_agent.links = args.links
    
    pi_agent = PrincipalInvestigatorAgent(
        browsing_agent=browsing_agent,
        research_agent=research_agent,
        code_writer_agent=code_writer_agent,
        code_executor_agent=code_executor_agent,
        code_reviewer_agent=code_reviewer_agent,
        critic_agent=critic_agent,
        verbose=True,
        pdf_content=pdf_content,
        link_content=link_content, # PDFs and links are passed to the browsing agent
        files_dir_content=files_dir_content,
        mode=args.mode,
        quick_search=args.quick_search,
    )
    print(f"args: {args}")
    # # Run the research
    # if args.quick_search:
    #     pi_agent.quick_search(args.topic) #, pdf_content)
    # else:
    pi_agent.coordinate(args.topic)  # Remove the pdf_content argument

if __name__ == "__main__":
    main()

