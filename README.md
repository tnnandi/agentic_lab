# Agentic Lab: AI Agent Driven Scientific Research Lab

Agentic Lab is a multi-agent system designed to automate scientific research where a **Principal Investigator Agent (PI Agent)** interacts with multiple specialized agents to conduct literature reviews, generate research reports, write and execute code, and iteratively refine outputs based on feedback from the user as well as a critic agent.

## **Features**
- **Automated Research**: Fetches relevant literature and drafts comprehensive reports.
- **Code Generation & Execution**: Generates Python code based on research findings, executes it, and refines it iteratively.
- **Multi-Agent Collaboration**: Includes browsing, research, coding, execution, reviewing, and critique agents.
- **Iterative Improvement**: Feedback-driven iterative refinement to enhance outputs.
- **Can use open source LLMs with zero API costs**: Uses free DeepSeek R1 model and other open-source alternatives to avoid API expenses.
- **Privacy-Preserving Computation**: Runs locally or on secure environments without sending data to third-party servers.
## Types of Agents

The system consists of multiple AI agents that collaborate to execute research tasks.

### **1. Principal Investigator Agent (PI Agent)**
- The **main orchestrator** that coordinates all the other agents.
- Ensures that research and code generation go through **multiple rounds of refinement**.
- Integrates feedback from **Critic Agents**.

### **2. Browsing Agent**
- Searches for **reliable sources** related to the research topic.
- Gathers information from **PubMed, arXiv, and other credible sources**.
- Summarizes the gathered information for **downstream agents**.

### **3. Research Agent**
- Drafts an **initial research document** based on gathered sources.
- Refines and improves the document using feedback from the **Critic Agent**.
- Ensures the research is **structured, comprehensive, and scientifically accurate**.

### **4. Code Writer Agent**
- Generates **Python code** based on the research findings.
- Ensures that code includes **detailed comments explaining each step**.
- Improves code iteratively based on feedback from **Code Reviewer Agent** and **Critic Agent**.

### **5. Code Executor Agent**
- Runs the **generated Python code** and captures execution results.
- Detects **missing dependencies** and installs required packages automatically.
- Handles **execution errors** and passes output to the **Critic Agent** for review.

### **6. Code Reviewer Agent**
- Evaluates the **generated code** and its execution results.
- Suggests **improvements for efficiency, readability, and correctness**.
- Provides **actionable feedback** for the **Code Writer Agent**.

### **7. Critic Agent**
- Reviews both the **research document** and the **generated code**.
- Identifies **gaps, errors, and areas for improvement**.
- Summarizes feedback for the **PI Agent** to guide iterative improvements.

Later we will add the capability for the agentic system to create custom agents on the fly instead of them being hard coded

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
