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

# Argument parser for topic input
parser = argparse.ArgumentParser(description="Run Agentic Lab with a specified research topic.")
parser.add_argument("--topic", type=str, required=True, help="Specify the research topic.")
parser.add_argument("--pdfs", nargs="+", help="Specify one or more PDF files to include in the research.")
parser.add_argument("--links", nargs="+", help="Specify one or more URLs to include in the research.")
parser.add_argument("--quick_search", action="store_true", help="Carry out quick search without extensive research.")
parser.add_argument("--mode", choices=["research_only", "code_only", "both"], default="both", help="Choose task mode: only generate research report, only code, or both (default)")
args = parser.parse_args()

# Process PDF files if provided
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
    link_content = utils.process_links(args.links)
    if link_content:
        print(f"Successfully processed {len(args.links)} link(s)")
    else:
        print("Warning: No link content could be extracted")

# initialize agents
browsing_agent = BrowsingAgent()
research_agent = ResearchAgent(mode=args.mode) 
code_writer_agent = CodeWriterAgent()
code_executor_agent = CodeExecutorAgent()
code_reviewer_agent = CodeReviewerAgent()
critic_agent = CriticAgent()

# Pass PDF content to the PI agent
pi_agent = PrincipalInvestigatorAgent(
    browsing_agent,
    research_agent,
    code_writer_agent,
    code_executor_agent,
    code_reviewer_agent,
    critic_agent,
    max_rounds=config.MAX_ROUNDS,
    quick_search=args.quick_search,
    mode=args.mode,
    verbose=True, # set to False to suppress verbose output
    pdf_content=pdf_content,  # Add PDF content
    link_content=link_content,  # Add link content
)

topic = args.topic
finalized = False

while not finalized:
    report, code, finalized = pi_agent.coordinate(topic)
    if args.quick_search:
        print("\n Quick search complete. Exiting.\n")
        exit(0)

    # ensure execution_result is passed correctly to be consistent with the other calls
    execution_result = "Success" if finalized else "Failed"

    utils.save_output(report, code, execution_result, pi_agent.iteration) # save conversations and outputs for each round of iteration

