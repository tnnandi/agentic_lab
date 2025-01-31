# Agentic Lab: AI Agent Driven Research and Code Generation

Agentic Lab is a multi-agent system designed to automate scientific research and code generation. It orchestrates a **Principal Investigator Agent (PI Agent)** that interacts with multiple specialized agents to conduct literature reviews, generate research reports, write and execute code, and iteratively refine outputs based on feedback from the user as well as a critic agent.

## **Features**
- **Automated Research**: Fetches relevant literature and drafts comprehensive reports.
- **Code Generation & Execution**: Generates Python code based on research findings, executes it, and refines it iteratively.
- **Multi-Agent Collaboration**: Includes browsing, research, coding, execution, reviewing, and critique agents.
- **Iterative Improvement**: Feedback-driven iterative refinement to enhance outputs.

---

## **Installation and Setup**
### **Prerequisites**
Ensure you have the following installed:
- Python 3.12+
- [Ollama](https://ollama.com/) for hosting large language models
- Conda (recommended for environment management)

### **Project Structure**
```plaintext
agentic_lab/
│── agents.py         # Defines the Principal Investigator (PI) agent and sub-agents
│── config.py         # Model configurations 
│── llm_utils.py      # Handles interactions with the LLM (for now, DeepSeek R1 70B)
│── main.py           # Main entry point 
│── utils.py          # Helper functions for saving output and logging
│── output_agent/     # Directory where generated reports, code, and logs are saved
```
### **Clone the Repository**
```bash
git clone https://github.com/tnnandi/agentic_lab.git
cd agentic_lab
```

### **Run the code**
```bash
python main.py --topic=<topic> 

Example: python main.py --topic="Polygenic risk score calculation using publicly available GWAS and genotype data"
```



#### Note: 
Now using deepseek reasoning models hosted on Sophia/Polaris using Ollama. Will move to the ALCF inference endpoints when they make deepseek-r1 available.
The 70b model works fine, but the 671b model throws error related to the number of experts being used is more than that allowed by the ollama llama.cpp installation
