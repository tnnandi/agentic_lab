#!/usr/bin/env python3
"""
BioMCP Hypothesis Generator

This agent uses BioMCP CLI and LLM to generate biological hypotheses about user topics.
It combines scientific literature data with AI reasoning to propose testable hypotheses.
"""

import requests
import json
import subprocess
import time
import re
from typing import Dict, Any, Optional, List

class BioMCPHypothesisGenerator:
    def __init__(self, ollama_host="http://localhost:11434", model="llama3.1:8b"):
        self.ollama_host = ollama_host
        self.model = model
        
        # Test Ollama connection
        if self.test_ollama_connection():
            self.llm_enabled = True
            print(f"Connected to Ollama LLM: {model}")
        else:
            self.llm_enabled = False
            print("Warning: Could not connect to Ollama. LLM processing disabled.")

    def test_ollama_connection(self):
        """Test if Ollama is running and accessible"""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False

    def extract_scientific_terms(self, topic):
        """Extract scientific terms from the user topic using LLM"""
        if not self.llm_enabled:
            return {"genes": [], "diseases": [], "processes": [], "molecules": []}
            
        prompt = f"""
        Analyze this biological topic and extract scientific terms in these categories:
        Topic: "{topic}"
        
        Provide your response in this JSON format:
        {{
            "genes": ["gene1", "gene2"],
            "diseases": ["disease1", "disease2"],
            "processes": ["process1", "process2"],
            "molecules": ["molecule1", "molecule2"],
            "key_concepts": ["concept1", "concept2"]
        }}
        
        Focus on specific, testable biological entities. Be precise and specific to the topic and not on general terms and concepts. 

        JSON only:
        """
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "format": "json",
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            content = result.get("response", "{}")
            
            parsed = json.loads(content)
            return parsed
        except Exception as e:
            print(f"LLM term extraction failed: {e}")
            return {"genes": [], "diseases": [], "processes": [], "molecules": [], "key_concepts": []}

    def search_literature(self, topic, terms):
        """Search for relevant literature with gene and disease terms using BioMCP"""
        literature_data = []
        
        # Search for genes
        for gene in terms.get("genes", [])[:10]:  # Limit to 3 genes
            try:
                print(f"Searching literature for gene: {gene}")
                result = subprocess.run(
                    ["biomcp", "article", "search", "--gene", gene, "--page", "1"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    literature_data.append(f"Gene {gene} literature:\n{result.stdout[:500]}...")
            except Exception as e:
                print(f"Error searching for gene {gene}: {e}")
        
        # Search for diseases
        for disease in terms.get("diseases", [])[:10]:  # Limit to 3 diseases
            try:
                print(f"Searching literature for disease: {disease}")
                result = subprocess.run(
                    ["biomcp", "article", "search", "--disease", disease, "--page", "1"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    literature_data.append(f"Disease {disease} literature:\n{result.stdout[:1000]}...")
            except Exception as e:
                print(f"Error searching for disease {disease}: {e}")
        
        # Search for general topic
        try:
            print(f"Searching general literature for: {topic}")
            result = subprocess.run(
                ["biomcp", "article", "search", "--keyword", topic, "--page", "1"],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                literature_data.append(f"General literature:\n{result.stdout[:1000]}...")
        except Exception as e:
            print(f"Error searching general literature: {e}")
        
        return literature_data

    def search_variants(self, genes):
        """Search for genetic variants"""
        variant_data = []
        
        for gene in genes[:10]:  # Limit to 2 genes
            try:
                print(f"Searching variants for gene: {gene}")
                result = subprocess.run(
                    ["biomcp", "variant", "search", "--gene", gene],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    variant_data.append(f"Variants for {gene}:\n{result.stdout[:1000]}...")
            except Exception as e:
                print(f"Error searching variants for {gene}: {e}")
        
        return variant_data

    def search_trials(self, diseases):
        """Search for clinical trials"""
        trial_data = []
        
        for disease in diseases[:10]:  # Limit to 2 diseases
            try:
                print(f"Searching trials for disease: {disease}")
                result = subprocess.run(
                    ["biomcp", "trial", "search", "--condition", disease],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    trial_data.append(f"Trials for {disease}:\n{result.stdout[:1000]}...")
            except Exception as e:
                print(f"Error searching trials for {disease}: {e}")
        
        return trial_data

    def generate_hypotheses(self, topic, literature_data, variant_data, trial_data):
        """Generate biological hypotheses using LLM"""
        if not self.llm_enabled:
            return ["LLM not available for hypothesis generation"]
        
        # Combine all data
        combined_data = "\n\n".join([
            f"Topic: {topic}",
            "Literature Data:",
            "\n".join(literature_data),
            "Variant Data:",
            "\n".join(variant_data),
            "Clinical Trial Data:",
            "\n".join(trial_data)
        ])
        
        prompt = f"""
        Based on the following biological data, generate 5 testable scientific hypotheses.
        
        Data:
        {combined_data}
        
        Generate hypotheses that are:
        1. Specific and testable
        2. Based on the exact topicprovided data
        3. Mechanistic (explain how/why)
        4. Novel (not obvious)
        5. Feasible to test
        
        Format each hypothesis as:
        HYPOTHESIS X: [Clear statement of the hypothesis]
        RATIONALE: [Why this hypothesis makes sense based on the data]
        PREDICTION: [What you would expect to observe if this hypothesis is true]
        TEST: [How you could test this hypothesis experimentally]
        
        Provide 5 hypotheses in this format:
        """
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            
            result = response.json()
            content = result.get("response", "")
            
            # Split into individual hypotheses
            hypotheses = []
            current_hypothesis = ""
            
            for line in content.split('\n'):
                if line.strip().startswith('HYPOTHESIS'):
                    if current_hypothesis:
                        hypotheses.append(current_hypothesis.strip())
                    current_hypothesis = line
                else:
                    current_hypothesis += "\n" + line
            
            if current_hypothesis:
                hypotheses.append(current_hypothesis.strip())
            
            return hypotheses if hypotheses else [content]
            
        except Exception as e:
            print(f"Hypothesis generation failed: {e}")
            return ["Error generating hypotheses"]

    def analyze_hypothesis_strength(self, hypothesis, literature_data):
        """Analyze the strength of a hypothesis based on literature support"""
        if not self.llm_enabled:
            return "LLM not available for analysis"
        
        prompt = f"""
        Analyze the strength of this biological hypothesis based on the literature data.
        
        Hypothesis:
        {hypothesis}
        
        Literature Data:
        {literature_data}
        
        Rate the hypothesis on these criteria (1-10 scale):
        1. Novelty: How new/innovative is this hypothesis?
        2. Feasibility: How practical is it to test this hypothesis?
        3. Literature Support: How well does existing literature support this hypothesis?
        4. Mechanistic Clarity: How clear is the proposed mechanism?
        5. Clinical Relevance: How relevant is this to human health/disease?
        
        Provide your analysis in JSON format:
        {{
            "novelty": score,
            "feasibility": score,
            "literature_support": score,
            "mechanistic_clarity": score,
            "clinical_relevance": score,
            "overall_strength": average_score,
            "strengths": ["strength1", "strength2"],
            "weaknesses": ["weakness1", "weakness2"],
            "recommendations": ["recommendation1", "recommendation2"]
        }}
        """
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "format": "json",
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            content = result.get("response", "{}")
            
            return json.loads(content)
            
        except Exception as e:
            print(f"Hypothesis analysis failed: {e}")
            return {"error": "Analysis failed"}

    def generate_research_plan(self, hypothesis, analysis):
        """Generate a research plan to test the hypothesis"""
        if not self.llm_enabled:
            return "LLM not available for research planning"
        
        prompt = f"""
        Create a detailed research plan to test this biological hypothesis.
        
        Hypothesis:
        {hypothesis}
        
        Analysis:
        {json.dumps(analysis, indent=2)}
        
        Provide a research plan with:
        1. EXPERIMENTAL DESIGN: Detailed experimental approach
        2. METHODS: Specific techniques and protocols
        3. CONTROLS: What controls are needed
        4. TIMELINE: Estimated timeline for experiments
        5. RESOURCES: Required resources and equipment
        6. EXPECTED OUTCOMES: What results would support/refute the hypothesis
        7. ALTERNATIVE APPROACHES: Backup experimental strategies
        
        Format as a structured research plan:
        """
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "Error generating research plan")
            
        except Exception as e:
            print(f"Research plan generation failed: {e}")
            return "Error generating research plan"

    def process_topic(self, topic):
        """Main method to process a topic and generate hypotheses"""
        print(f" Processing topic: {topic}")
        print("=" * 60)
        
        # Step 1: Extract scientific terms
        print("Extracting scientific terms...")
        terms = self.extract_scientific_terms(topic)
        print(f"Found terms: {terms}")
        
        # Step 2: Search literature
        print("\n Searching literature...")
        literature_data = self.search_literature(topic, terms)
        
        # Step 3: Search variants
        print("\n Searching genetic variants...")
        variant_data = self.search_variants(terms.get("genes", []))
        
        # Step 4: Search clinical trials
        print("\n Searching clinical trials...")
        trial_data = self.search_trials(terms.get("diseases", []))
        
        # Step 5: Generate hypotheses
        print("\n Generating hypotheses...")
        hypotheses = self.generate_hypotheses(topic, literature_data, variant_data, trial_data)
        
        # Step 6: Analyze and rank hypotheses
        print("\n Analyzing hypothesis strength...")
        hypothesis_analyses = []
        for i, hypothesis in enumerate(hypotheses, 1):
            print(f"\nAnalyzing Hypothesis {i}...")
            analysis = self.analyze_hypothesis_strength(hypothesis, literature_data)
            hypothesis_analyses.append((hypothesis, analysis))
        
        # Step 7: Generate research plans for top hypotheses
        print("\n Generating research plans...")
        research_plans = []
        for i, (hypothesis, analysis) in enumerate(hypothesis_analyses[:2], 1):  # Top 2 hypotheses
            print(f"\nGenerating research plan for Hypothesis {i}...")
            research_plan = self.generate_research_plan(hypothesis, analysis)
            research_plans.append((hypothesis, analysis, research_plan))
        
        return {
            "topic": topic,
            "terms": terms,
            "literature_data": literature_data,
            "variant_data": variant_data,
            "trial_data": trial_data,
            "hypotheses": hypotheses,
            "hypothesis_analyses": hypothesis_analyses,
            "research_plans": research_plans
        }

def main():
    """Main function"""
    print("BioMCP Hypothesis Generator")
    print("=" * 60)
    print("Capabilities:")
    print("Extract scientific terms from topics")
    print("Search biomedical literature")
    print("Search genetic variants")
    print("Search clinical trials")
    print("Generate testable hypotheses")
    print("Analyze hypothesis strength")
    print("Generate research plans")
    print("=" * 60)
    
    # Initialize agent
    agent = BioMCPHypothesisGenerator(ollama_host="http://localhost:11434", model="llama3.1:8b")
    
    print("\n Ready to generate biological hypotheses!")
    print("Enter 'quit' to exit\n")
    
    try:
        while True:
            topic = input("Enter a biological topic: ").strip()
            
            if topic.lower() in ['quit', 'exit']:
                print("Goodbye!")
                break
                
            if not topic:
                continue
                
            print("\n" + "="*60)
            result = agent.process_topic(topic)
            
            # Display results
            print(f"\nRESULTS FOR: {result['topic']}")
            print("="*60)
            
            print(f"\n Extracted Terms:")
            for category, terms in result['terms'].items():
                if terms:
                    print(f"  {category.title()}: {', '.join(terms)}")
            
            print(f"\n Generated Hypotheses ({len(result['hypotheses'])}):")
            for i, hypothesis in enumerate(result['hypotheses'], 1):
                print(f"\n--- Hypothesis {i} ---")
                print(hypothesis)
            
            print(f"\n Hypothesis Analysis:")
            for i, (hypothesis, analysis) in enumerate(result['hypothesis_analyses'], 1):
                print(f"\n--- Analysis {i} ---")
                if isinstance(analysis, dict):
                    for key, value in analysis.items():
                        print(f"  {key}: {value}")
                else:
                    print(f"  {analysis}")
            
            print(f"\n Research Plans:")
            for i, (hypothesis, analysis, plan) in enumerate(result['research_plans'], 1):
                print(f"\n--- Research Plan {i} ---")
                print(plan)
            
            print("="*60 + "\n")
            
    except KeyboardInterrupt:
        print("\n Goodbye!")

if __name__ == "__main__":
    main() 