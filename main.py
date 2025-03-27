# on laptop: conda activate /mnt/c/Users/tnandi/Downloads/ai_codes/ai_py3p12_env OR conda activate llm_env
# on Polaris: module load conda;conda activate /lus/grand/projects/GeomicVar/tarak/ai_codes/ai_py3p12_env

# Now using deepseek reasoning models hosted on Sophia/Polaris using Ollama. Will move to the ALCF inference endpoints when they make deepseek-r1 available
# the 70b model workd fine, but the 671b model throws error related to the number of experts being used is more than that allowed by the ollama llama.cpp installation

# To do:
# try out the code written out manually to check its veracity; temporarily allow human in the loop to run the code and check for errors before proceeding
# split the file into multiple files (one related to prompts, another to the definition of the agent classes etc)
# create a list of predefined agent specific prompts
# make the communication between different agents two-way (in the form of meetings)
# make the prompts to the agents accessible easily as templates
# have multiple rounds of code corrections
# write out in a file all the outputs for every communication in every round
# start from the topic prompt in round 0, but use the critic's feedback from the 2nd round onwards
# add more capabilities to the agent class (check autogen, magentic-one, smolagents, amd langchain/langgraph agent types and classes and the communication patterns)
# using an orchestrator-worker pattern, allow the orchestrator to create agents it can delegate jobs to instead of having these agents predetermined

# to check if the ollama server is active try
# curl --noproxy localhost http://localhost:11434/api/generate -d '{"model": "deepseek-r1:70b", "prompt": "Explain polygenic risk scores.", "temperature": 0.3}'


# add options for research, code, or both
# add validation metrics using standard datasets 

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

# Aagument parser for topic input
parser = argparse.ArgumentParser(description="Run Agentic Lab with a specified research topic.")
parser.add_argument("--topic", type=str, required=True, help="Specify the research topic.")
parser.add_argument("--quick_search", action="store_true", help="Carry out quick search without extensive research.")
parser.add_argument("--mode", choices=["research_only", "code_only", "both"], default="both", help="Choose task mode: only generate research report, only code, or both (default)")
args = parser.parse_args()

# initialize agents
browsing_agent = BrowsingAgent()
research_agent = ResearchAgent()
code_writer_agent = CodeWriterAgent()
code_executor_agent = CodeExecutorAgent()
code_reviewer_agent = CodeReviewerAgent()
critic_agent = CriticAgent()

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
    verbose=True,
)

# topic = "Polygenic risk score calculation using publicly available GWAS and genotype data"
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

