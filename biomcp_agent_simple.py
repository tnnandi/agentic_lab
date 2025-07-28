#!/usr/bin/env python3
"""
Simple BioMCP Agent

This agent uses BioMCP CLI directly for biomedical research without running a server.
"""

import requests
import json
import subprocess
import time
from typing import Dict, Any, Optional

class SimpleBioMCPAgent:
    def __init__(self, ollama_host="http://localhost:11434", model="llama3.1:8b"):
        self.ollama_host = ollama_host
        self.model = model
        
        # Test Ollama connection
        if self.test_ollama_connection():
            self.llm_enabled = True
            print(f"✅ Connected to Ollama LLM: {model}")
        else:
            self.llm_enabled = False
            print("⚠️  Warning: Could not connect to Ollama. LLM processing disabled.")

    def test_ollama_connection(self):
        """Test if Ollama is running and accessible"""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False

    def process_with_llm(self, question):
        """Use local Ollama LLM to analyze and refine the question"""
        if not self.llm_enabled:
            return question, {"key_terms": [], "question_type": "other"}
            
        prompt = f"""
        Analyze this biology question and extract the key scientific concepts.
        Question: "{question}"
        
        Provide your response in this JSON format:
        {{
            "refined_question": "clearly rephrased question focusing on core biology concepts",
            "key_terms": ["term1", "term2", "term3"],
            "question_type": "definition|process|comparison|function|other"
        }}
        
        JSON Response only, no additional text:
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
            
            # Parse the JSON response
            parsed = json.loads(content)
            return parsed.get("refined_question", question), parsed
        except Exception as e:
            print(f"LLM processing failed: {e}")
            return question, {"key_terms": [], "question_type": "other"}

    def search_articles(self, query):
        """Search for biomedical articles using BioMCP"""
        try:
            print(f"🔍 Searching articles for: {query}")
            
            # Parse the query to extract different types of search terms
            query_lower = query.lower()
            
            # Check for gene names (uppercase patterns like TP53, BRAF, etc.)
            import re
            gene_matches = re.findall(r'\b[A-Z]{2,}\d*\b', query)
            
            # Check for disease terms
            disease_terms = ["cancer", "melanoma", "lung", "breast", "leukemia", "lymphoma", "tumor", "diabetes", "alzheimer"]
            found_diseases = [disease for disease in disease_terms if disease in query_lower]
            
            # Build the command based on what we find
            cmd = ["biomcp", "article", "search"]
            
            if gene_matches:
                # Search by gene
                for gene in gene_matches[:2]:  # Limit to 2 genes
                    cmd.extend(["--gene", gene])
                    print(f"🧬 Adding gene search: {gene}")
            
            if found_diseases:
                # Search by disease
                for disease in found_diseases[:2]:  # Limit to 2 diseases
                    cmd.extend(["--disease", disease])
                    print(f"🏥 Adding disease search: {disease}")
            
            # If no specific terms found, use keyword search
            if not gene_matches and not found_diseases:
                # Extract key terms for keyword search
                key_terms = query.split()[:3]  # Use first 3 words
                for term in key_terms:
                    cmd.extend(["--keyword", term])
                    print(f"🔍 Adding keyword search: {term}")
            
            # Add limit and JSON format
            cmd.extend(["--page", "1"])
            
            print(f"🚀 Running command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return {"success": True, "data": result.stdout}
            else:
                return {"success": False, "error": result.stderr}
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Search timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_variants(self, gene):
        """Search for genetic variants using BioMCP"""
        try:
            print(f"🧬 Searching variants for gene: {gene}")
            result = subprocess.run(
                ["biomcp", "variant", "search", "--gene", gene],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return {"success": True, "data": result.stdout}
            else:
                return {"success": False, "error": result.stderr}
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Search timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_trials(self, condition):
        """Search for clinical trials using BioMCP"""
        try:
            print(f"🏥 Searching trials for condition: {condition}")
            result = subprocess.run(
                ["biomcp", "trial", "search", "--condition", condition],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return {"success": True, "data": result.stdout}
            else:
                return {"success": False, "error": result.stderr}
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Search timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_article_details(self, pmid):
        """Get detailed information about a specific article"""
        try:
            print(f"📄 Getting details for article: {pmid}")
            result = subprocess.run(
                ["biomcp", "article", "get", str(pmid)],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return {"success": True, "data": result.stdout}
            else:
                return {"success": False, "error": result.stderr}
                
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Request timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def process_question(self, question):
        """Process user question through LLM and BioMCP"""
        print(f"🔍 Original question: {question}")
        
        # Step 1: Process with LLM to refine question
        refined_question, analysis = self.process_with_llm(question)
        print(f"🎯 Refined question: {refined_question}")
        
        if analysis.get("key_terms"):
            print(f"🔑 Key terms: {', '.join(analysis['key_terms'])}")
        
        # Step 2: Determine what type of search to perform
        question_lower = refined_question.lower()
        
        # Check for gene/variant related terms
        gene_terms = ["gene", "variant", "mutation", "genetic", "dna", "rna", "protein"]
        if any(term in question_lower for term in gene_terms):
            # Extract potential gene names
            import re
            gene_matches = re.findall(r'\b[A-Z]{2,}\d*\b', refined_question)
            if gene_matches:
                gene = gene_matches[0]  # Use the first gene found
                print(f"🧬 Detected gene search: {gene}")
                result = self.search_variants(gene)
                if result["success"]:
                    return f"📊 Variant Search Results for {gene}:\n{result['data']}"
                else:
                    print(f"❌ Variant search failed: {result['error']}")
        
        # Check for clinical trial related terms
        trial_terms = ["trial", "clinical", "treatment", "therapy", "drug", "medication", "phase"]
        if any(term in question_lower for term in trial_terms):
            # Extract potential condition/disease
            disease_terms = ["cancer", "melanoma", "lung", "breast", "leukemia", "lymphoma", "tumor"]
            for disease in disease_terms:
                if disease in question_lower:
                    print(f"🏥 Detected clinical trial search: {disease}")
                    result = self.search_trials(disease)
                    if result["success"]:
                        return f"📊 Clinical Trial Results for {disease}:\n{result['data']}"
                    else:
                        print(f"❌ Trial search failed: {result['error']}")
                    break
        
        # Default to article search
        print("📚 Performing article search...")
        result = self.search_articles(refined_question)
        
        if result["success"]:
            return f"📊 Article Search Results:\n{result['data']}"
        else:
            return f"Error: {result['error']}"

def main():
    """Main function"""
    print("🧬 Simple BioMCP Agent")
    print("=" * 50)
    print("Capabilities:")
    print("✅ Article search (PubMed, bioRxiv, medRxiv)")
    print("✅ Variant search (genetic mutations)")
    print("✅ Clinical trial search")
    print("✅ LLM question refinement")
    print("=" * 50)
    
    # Initialize agent
    agent = SimpleBioMCPAgent(ollama_host="http://localhost:11434", model="llama3.1:8b")
    
    print("\n🎯 Ready to answer biology questions!")
    print("Enter 'quit' to exit\n")
    
    try:
        while True:
            question = input("🔬 Ask a biology question: ").strip()
            
            if question.lower() in ['quit', 'exit']:
                print("👋 Goodbye!")
                break
                
            if not question:
                continue
                
            print("\n" + "="*50)
            response = agent.process_question(question)
            print(f"\n📝 Response:\n{response}")
            print("="*50 + "\n")
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    main() 