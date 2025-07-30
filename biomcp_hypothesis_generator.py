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
from pdb import set_trace

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
        Extract and categorize scientific terms from: "{topic}"
        
        Categorize carefully with these specific guidelines:
        
        GENES: Specific gene names, symbols, or identifiers
        - Include: Gene symbols, full gene names, oncogenes, tumor suppressors
        - Exclude: General terms like "gene expression" or "genetic"
        
        DISEASES: Specific disease names, conditions, or disorders
        - Include: Cancer types, genetic disorders, chronic diseases
        - Exclude: General terms like "disease" or "illness"
        
        PROCESSES: Biological processes, pathways, or mechanisms
        - Include: Cellular processes, signaling pathways, metabolic processes
        - Exclude: General terms like "process" or "mechanism"
        
        MOLECULES: Specific chemical compounds, proteins, or biomolecules
        - Include: Only Proteins, small molecules, drugs, signaling molecules etc
        - Exclude: General terms like "molecule" or "compound". DO NOT include processes, pathways, or anything that is not a molecule.
        
        KEY_CONCEPTS: Important biological concepts or phenomena
        - Include: Research areas, therapeutic approaches, biological phenomena
        - Exclude: Very general terms
        
        Provide your response in this JSON format:
        {{
            "genes": ["specific_gene1", "specific_gene2"],
            "diseases": ["specific_disease1", "specific_disease2"],
            "processes": ["specific_process1", "specific_process2"],
            "molecules": ["specific_molecule1", "specific_molecule2"],
            "key_concepts": ["specific_concept1", "specific_concept2"]
        }}
        
        Be specific and precise. Only include terms that are clearly relevant to the topic.
        If a category has no relevant terms, use an empty array.
        
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
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            content = result.get("response", "{}")
            
            parsed = json.loads(content)
            
            # Validate and clean the parsed terms
            cleaned_terms = {}
            for category in ["genes", "diseases", "processes", "molecules", "key_concepts"]:
                if category in parsed and isinstance(parsed[category], list):
                    # Remove empty strings and duplicates
                    cleaned_terms[category] = list(set([
                        term.strip() for term in parsed[category] 
                        if term.strip() and len(term.strip()) > 1
                    ]))
                else:
                    cleaned_terms[category] = []
            
            return cleaned_terms
            
        except Exception as e:
            print(f"LLM term extraction failed: {e}")
            return {"genes": [], "diseases": [], "processes": [], "molecules": [], "key_concepts": []}

    def get_user_feedback_on_terms(self, extracted_terms):
        """Get user feedback on extracted scientific terms and update them"""
        print(f"\n{'='*60}")
        print("EXTRACTED SCIENTIFIC TERMS")
        print(f"{'='*60}")
        
        for category, terms in extracted_terms.items():
            if terms:
                print(f"\n{category.upper()}:")
                for i, term in enumerate(terms, 1):
                    print(f"  {i}. {term}")
            else:
                print(f"\n{category.upper()}: None found")
        
        print(f"\n{'='*60}")
        print("TERM FEEDBACK OPTIONS")
        print(f"{'='*60}")
        print("1. Accept all terms as-is")
        print("2. Add new terms")
        print("3. Remove specific terms")
        print("4. Replace specific terms")
        print("5. Manually edit all terms")
        
        while True:
            try:
                choice = input("\nEnter your choice (1-5): ").strip()
                
                if choice == "1":
                    print("Accepting all terms as-is...")
                    return extracted_terms
                
                elif choice == "2":
                    return self.add_new_terms(extracted_terms)
                
                elif choice == "3":
                    return self.remove_specific_terms(extracted_terms)
                
                elif choice == "4":
                    return self.replace_specific_terms(extracted_terms)
                
                elif choice == "5":
                    return self.manually_edit_all_terms(extracted_terms)
                
                else:
                    print("Invalid choice. Please enter 1-5.")
                    
            except KeyboardInterrupt:
                print("\n\nExiting...")
                return extracted_terms
            except Exception as e:
                print(f"Error: {e}")
                return extracted_terms

    def add_new_terms(self, current_terms):
        """Add new terms to the extracted terms"""
        print(f"\n{'='*40}")
        print("ADD NEW TERMS")
        print(f"{'='*40}")
        
        updated_terms = current_terms.copy()
        
        for category in current_terms.keys():
            print(f"\nAdd new {category} (comma-separated, or press Enter to skip):")
            new_terms_input = input(f"New {category}: ").strip()
            
            if new_terms_input:
                new_terms = [term.strip() for term in new_terms_input.split(',') if term.strip()]
                updated_terms[category].extend(new_terms)
                print(f"Added {len(new_terms)} new {category}")
        
        return updated_terms

    def remove_specific_terms(self, current_terms):
        """Remove specific terms from the extracted terms"""
        print(f"\n{'='*40}")
        print("REMOVE SPECIFIC TERMS")
        print(f"{'='*40}")
        
        updated_terms = current_terms.copy()
        
        for category, terms in current_terms.items():
            if terms:
                print(f"\n{category.upper()}:")
                for i, term in enumerate(terms, 1):
                    print(f"  {i}. {term}")
                
                remove_input = input(f"\nEnter numbers to remove (comma-separated, or press Enter to skip): ").strip()
                
                if remove_input:
                    try:
                        indices_to_remove = [int(x.strip()) - 1 for x in remove_input.split(',')]
                        # Remove terms in reverse order to avoid index issues
                        for index in sorted(indices_to_remove, reverse=True):
                            if 0 <= index < len(updated_terms[category]):
                                removed_term = updated_terms[category].pop(index)
                                print(f"Removed: {removed_term}")
                    except ValueError:
                        print("Invalid input. Skipping removal.")
        
        return updated_terms

    def replace_specific_terms(self, current_terms):
        """Replace specific terms in the extracted terms"""
        print(f"\n{'='*40}")
        print("REPLACE SPECIFIC TERMS")
        print(f"{'='*40}")
        
        updated_terms = current_terms.copy()
        
        for category, terms in current_terms.items():
            if terms:
                print(f"\n{category.upper()}:")
                for i, term in enumerate(terms, 1):
                    print(f"  {i}. {term}")
                
                replace_input = input(f"\nEnter 'number:new_term' to replace (e.g., '1:new_gene', or press Enter to skip): ").strip()
                
                if replace_input:
                    try:
                        parts = replace_input.split(':')
                        if len(parts) == 2:
                            index = int(parts[0].strip()) - 1
                            new_term = parts[1].strip()
                            
                            if 0 <= index < len(updated_terms[category]):
                                old_term = updated_terms[category][index]
                                updated_terms[category][index] = new_term
                                print(f"Replaced '{old_term}' with '{new_term}'")
                            else:
                                print("Invalid index.")
                    except ValueError:
                        print("Invalid input format. Use 'number:new_term'")
        
        return updated_terms

    def manually_edit_all_terms(self, current_terms):
        """Manually edit all terms"""
        print(f"\n{'='*40}")
        print("MANUALLY EDIT ALL TERMS")
        print(f"{'='*40}")
        
        updated_terms = {}
        
        for category, terms in current_terms.items():
            print(f"\nCurrent {category}: {', '.join(terms) if terms else 'None'}")
            new_terms_input = input(f"Enter new {category} (comma-separated): ").strip()
            
            if new_terms_input:
                updated_terms[category] = [term.strip() for term in new_terms_input.split(',') if term.strip()]
            else:
                updated_terms[category] = []
        
        return updated_terms

    def extract_references_from_biomcp_output(self, biomcp_output):
        """Extract actual references from BioMCP output"""
        references = []
        
        # BioMCP typically outputs structured data with titles, authors, DOIs, etc.
        lines = biomcp_output.split('\n')
        
        # Look for structured reference blocks
        current_reference = []
        in_reference_block = False
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Look for DOI patterns (these are usually complete references)
            if 'doi:' in line.lower() or 'doi.org' in line.lower():
                # Extract the full line as it likely contains the complete reference
                references.append(line)
                continue
            
            # Look for PubMed IDs (these are usually complete references)
            if 'pmid:' in line.lower() or 'pubmed:' in line.lower():
                references.append(line)
                continue
            
            # Look for structured reference patterns
            # BioMCP often outputs references in a structured format
            if any(pattern in line.lower() for pattern in [
                'title:', 'authors:', 'journal:', 'year:', 'volume:', 'pages:'
            ]):
                if not in_reference_block:
                    in_reference_block = True
                    current_reference = []
                current_reference.append(line)
            elif in_reference_block:
                # If we're in a reference block and hit a non-reference line
                if current_reference:
                    references.append('\n'.join(current_reference))
                    current_reference = []
                    in_reference_block = False
        
        # Add any remaining reference block
        if current_reference:
            references.append('\n'.join(current_reference))
        
        # If we didn't find structured references, look for citation patterns
        if not references:
            for line in lines:
                line = line.strip()
                
                # Look for author patterns (Last, First format)
                if re.match(r'^[A-Z][a-z]+, [A-Z]\.', line):
                    references.append(line)
                
                # Look for year patterns in parentheses
                elif re.search(r'\(\d{4}\)', line):
                    references.append(line)
                
                # Look for journal names (common pattern)
                elif any(journal in line.lower() for journal in [
                    'nature', 'science', 'cell', 'journal', 'proc', 'plos', 
                    'cancer res', 'mol cell', 'genes dev', 'embo j'
                ]):
                    references.append(line)
                
                # Look for complete citation patterns
                elif re.search(r'[A-Z][a-z]+ et al\.', line):
                    references.append(line)
                
                # Look for lines with both author and year
                elif re.search(r'[A-Z][a-z]+.*\(\d{4}\)', line):
                    references.append(line)
        
        # Clean up references - remove very short fragments
        cleaned_references = []
        for ref in references:
            ref = ref.strip()
            # Only keep references that are reasonably complete
            if len(ref) > 20 and not ref.startswith('Error') and not ref.startswith('No results'):
                cleaned_references.append(ref)
        
        return cleaned_references

    def search_literature(self, topic, terms):
        """Search for relevant literature with gene and disease terms using BioMCP"""
        literature_data = []
        all_references = []
        
        # Search for genes
        for gene in terms.get("genes", [])[:5]:  # Limit to 3 genes
            try:
                print(f"Searching literature for gene: {gene}")
                result = subprocess.run(
                    ["biomcp", "article", "search", "--gene", gene, "--page", "1"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    # Extract references from this search
                    gene_references = self.extract_references_from_biomcp_output(result.stdout)
                    all_references.extend(gene_references)
                    literature_data.append(f"Gene {gene} literature:\n{result.stdout[:500]}...")
                    print(f"  Found {len(gene_references)} references for {gene}")
            except Exception as e:
                print(f"Error searching for gene {gene}: {e}")
        
        # Search for diseases
        for disease in terms.get("diseases", [])[:5]:  # Limit to 3 diseases
            try:
                print(f"Searching literature for disease: {disease}")
                result = subprocess.run(
                    ["biomcp", "article", "search", "--disease", disease, "--page", "1"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    # Extract references from this search
                    disease_references = self.extract_references_from_biomcp_output(result.stdout)
                    all_references.extend(disease_references)
                    literature_data.append(f"Disease {disease} literature:\n{result.stdout[:500]}...")
                    print(f"  Found {len(disease_references)} references for {disease}")
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
                # Extract references from this search
                topic_references = self.extract_references_from_biomcp_output(result.stdout)
                all_references.extend(topic_references)
                literature_data.append(f"General literature:\n{result.stdout[:500]}...")
                print(f"  Found {len(topic_references)} references for general topic")
        except Exception as e:
            print(f"Error searching general literature: {e}")
        
        # Remove duplicates and format references
        unique_references = list(set(all_references))
        
        # Sort references by length (longer ones are usually more complete)
        unique_references.sort(key=len, reverse=True)
        
        print(f"Total unique references found: {len(unique_references)}")
        
        return literature_data, unique_references

    def search_variants(self, genes):
        """Search for genetic variants"""
        variant_data = []
        
        for gene in genes[:5]:  # Limit to 3 genes
            try:
                print(f"Searching variants for gene: {gene}")
                result = subprocess.run(
                    ["biomcp", "variant", "search", "--gene", gene],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    variant_data.append(f"Variants for {gene}:\n{result.stdout[:500]}...")
            except Exception as e:
                print(f"Error searching variants for {gene}: {e}")
        
        return variant_data

    def search_trials(self, diseases):
        """Search for clinical trials"""
        trial_data = []
        
        for disease in diseases[:5]:  # Limit to 3 diseases
            try:
                print(f"Searching trials for disease: {disease}")
                result = subprocess.run(
                    ["biomcp", "trial", "search", "--condition", disease],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    trial_data.append(f"Trials for {disease}:\n{result.stdout[:500]}...")
            except Exception as e:
                print(f"Error searching trials for {disease}: {e}")
        
        return trial_data

    def classify_hypothesis_novelty(self, hypothesis, literature_data):
        """Classify whether a hypothesis is known (supported by literature) or unknown (novel)"""
        if not self.llm_enabled:
            return "unknown"  # Default to unknown if LLM not available
        
        prompt = f"""
        Classify this hypothesis as "known" or "unknown":
        
        Hypothesis: {hypothesis[:200]}...
        Literature: {literature_data[:200]}...
        
        Response (known/unknown only):
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
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            content = result.get("response", "").strip().lower()
            
            return "known" if "known" in content else "unknown"
            
        except Exception as e:
            print(f"Hypothesis classification failed: {e}")
            return "unknown"

    def generate_known_hypotheses(self, topic, literature_data, variant_data, trial_data, references):
        """Generate hypotheses based on known/established mechanisms using real references"""
        if not self.llm_enabled:
            return ["LLM not available for hypothesis generation"]
        
        # Format references for the prompt (limit to avoid timeout)
        if references:
            references_text = "\n".join([f"[{i+1}] {ref}" for i, ref in enumerate(references[:10])])
        else:
            references_text = "No specific references found"
        
        # Truncate data to prevent timeout
        literature_summary = "\n".join([data[:200] for data in literature_data[:3]])
        variant_summary = "\n".join([data[:200] for data in variant_data[:2]])
        trial_summary = "\n".join([data[:200] for data in trial_data[:2]])
        
        prompt = f"""
        Generate 2 KNOWN hypotheses for: {topic}
        
        REAL REFERENCES FROM BIOMCP (USE ONLY THESE):
        {references_text}
        
        Literature: {literature_summary}
        Variants: {variant_summary}
        Trials: {trial_summary}
        
        CRITICAL: Only use references from the list above. Do NOT create fake citations.
        If no references are provided, say "No specific references available."
        
        Format each as:
        KNOWN HYPOTHESIS X: [Statement]
        LITERATURE SUPPORT: [Use ONLY references from the list above or say "No specific references available"]
        MECHANISM: [Established mechanism]
        CLINICAL RELEVANCE: [Clinical importance]
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
                timeout=120  # Increased timeout
            )
            response.raise_for_status()
            
            result = response.json()
            content = result.get("response", "")
            
            # Improved parsing - look for complete hypothesis blocks
            hypotheses = []
            lines = content.split('\n')
            current_hypothesis = ""
            in_hypothesis = False
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('KNOWN HYPOTHESIS'):
                    if current_hypothesis and in_hypothesis:
                        hypotheses.append(current_hypothesis.strip())
                    current_hypothesis = line
                    in_hypothesis = True
                elif in_hypothesis and line.startswith(('LITERATURE SUPPORT:', 'MECHANISM:', 'CLINICAL RELEVANCE:')):
                    current_hypothesis += "\n" + line
                elif in_hypothesis and not line.startswith('KNOWN HYPOTHESIS'):
                    # Continue adding to current hypothesis if it looks like part of it
                    if any(keyword in line.lower() for keyword in ['mechanism', 'clinical', 'literature', 'support', 'relevance']):
                        current_hypothesis += "\n" + line
                    else:
                        # Might be start of next hypothesis or unrelated text
                        if len(current_hypothesis) > 50:  # Only add if substantial
                            hypotheses.append(current_hypothesis.strip())
                        current_hypothesis = ""
                        in_hypothesis = False
            
            # Add the last hypothesis if it exists
            if current_hypothesis and in_hypothesis:
                hypotheses.append(current_hypothesis.strip())
            
            # If parsing failed, return the raw content
            if not hypotheses:
                # Try to split by "KNOWN HYPOTHESIS" markers
                parts = content.split('KNOWN HYPOTHESIS')
                if len(parts) > 1:
                    for i, part in enumerate(parts[1:], 1):  # Skip first empty part
                        if part.strip():
                            hypotheses.append(f"KNOWN HYPOTHESIS {i}:{part.strip()}")
                else:
                    hypotheses = [content]
            
            return hypotheses if hypotheses else [content]
            
        except Exception as e:
            print(f"Known hypothesis generation failed: {e}")
            return ["Error generating known hypotheses"]

    def generate_unknown_hypotheses(self, topic, literature_data, variant_data, trial_data, references):
        """Generate novel/unknown hypotheses using real references as context"""
        if not self.llm_enabled:
            return ["LLM not available for hypothesis generation"]
        
        # Format references for the prompt (limit to avoid timeout)
        if references:
            references_text = "\n".join([f"[{i+1}] {ref}" for i, ref in enumerate(references[:10])])
        else:
            references_text = "No specific references found"
        
        # Truncate data to prevent timeout
        literature_summary = "\n".join([data[:200] for data in literature_data[:3]])
        variant_summary = "\n".join([data[:200] for data in variant_data[:2]])
        trial_summary = "\n".join([data[:200] for data in trial_data[:2]])
        
        prompt = f"""
        Generate 2 NOVEL hypotheses for: {topic}
        
        REAL REFERENCES FROM BIOMCP (USE ONLY THESE):
        {references_text}
        
        Literature: {literature_summary}
        Variants: {variant_summary}
        Trials: {trial_summary}
        
        CRITICAL: Only use references from the list above. Do NOT create fake citations.
        If no references are provided, say "No specific references available."
        
        Format each as:
        UNKNOWN HYPOTHESIS X: [Novel statement]
        GAP IN KNOWLEDGE: [What is unknown]
        RATIONALE: [Why plausible based on available data]
        TESTING APPROACH: [How to test]
        LITERATURE CONTEXT: [Use ONLY references from the list above or say "No specific references available"]
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
                timeout=120  # Increased timeout
            )
            response.raise_for_status()
            
            result = response.json()
            content = result.get("response", "")
            
            # Improved parsing - look for complete hypothesis blocks
            hypotheses = []
            lines = content.split('\n')
            current_hypothesis = ""
            in_hypothesis = False
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('UNKNOWN HYPOTHESIS'):
                    if current_hypothesis and in_hypothesis:
                        hypotheses.append(current_hypothesis.strip())
                    current_hypothesis = line
                    in_hypothesis = True
                elif in_hypothesis and line.startswith(('GAP IN KNOWLEDGE:', 'RATIONALE:', 'TESTING APPROACH:', 'LITERATURE CONTEXT:')):
                    current_hypothesis += "\n" + line
                elif in_hypothesis and not line.startswith('UNKNOWN HYPOTHESIS'):
                    # Continue adding to current hypothesis if it looks like part of it
                    if any(keyword in line.lower() for keyword in ['gap', 'knowledge', 'rationale', 'testing', 'approach', 'literature', 'context']):
                        current_hypothesis += "\n" + line
                    else:
                        # Might be start of next hypothesis or unrelated text
                        if len(current_hypothesis) > 50:  # Only add if substantial
                            hypotheses.append(current_hypothesis.strip())
                        current_hypothesis = ""
                        in_hypothesis = False
            
            # Add the last hypothesis if it exists
            if current_hypothesis and in_hypothesis:
                hypotheses.append(current_hypothesis.strip())
            
            # If parsing failed, return the raw content
            if not hypotheses:
                # Try to split by "UNKNOWN HYPOTHESIS" markers
                parts = content.split('UNKNOWN HYPOTHESIS')
                if len(parts) > 1:
                    for i, part in enumerate(parts[1:], 1):  # Skip first empty part
                        if part.strip():
                            hypotheses.append(f"UNKNOWN HYPOTHESIS {i}:{part.strip()}")
                else:
                    hypotheses = [content]
            
            return hypotheses if hypotheses else [content]
            
        except Exception as e:
            print(f"Unknown hypothesis generation failed: {e}")
            return ["Error generating unknown hypotheses"]

    def analyze_hypothesis_strength(self, hypothesis, literature_data, hypothesis_type):
        """Analyze the strength and feasibility of a hypothesis"""
        if not self.llm_enabled:
            return "LLM not available for analysis"
        
        # Truncate hypothesis and literature to prevent timeout
        hypothesis_short = hypothesis[:300] if len(hypothesis) > 300 else hypothesis
        literature_short = literature_data[:300] if len(literature_data) > 300 else literature_data
        
        prompt = f"""
        Quick analysis of {hypothesis_type} hypothesis:
        
        Hypothesis: {hypothesis_short}
        Literature: {literature_short}
        
        Provide:
        STRENGTH: [1-10 with brief explanation]
        FEASIBILITY: [1-10 with brief explanation]
        EXPERIMENTAL APPROACH: [Brief testing method]
        TIMELINE: [Estimated time]
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
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "Analysis failed")
            
        except Exception as e:
            print(f"Hypothesis analysis failed: {e}")
            return "Analysis failed"

    def generate_research_plan(self, hypothesis, analysis, hypothesis_type):
        """Generate a detailed research plan for testing a hypothesis"""
        if not self.llm_enabled:
            return "LLM not available for research plan generation"
        
        # Truncate inputs to prevent timeout
        hypothesis_short = hypothesis[:200] if len(hypothesis) > 200 else hypothesis
        analysis_short = analysis[:200] if len(analysis) > 200 else analysis
        
        prompt = f"""
        Brief research plan for {hypothesis_type} hypothesis:
        
        Hypothesis: {hypothesis_short}
        Analysis: {analysis_short}
        
        Provide:
        OBJECTIVE: [Clear objective]
        SPECIFIC AIMS: [2-3 specific aims]
        METHODS: [Brief experimental methods]
        TIMELINE: [Estimated timeline]
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
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "Research plan generation failed")
            
        except Exception as e:
            print(f"Research plan generation failed: {e}")
            return "Research plan generation failed"

    def process_topic(self, topic):
        """Main method to process a topic and generate hypotheses"""
        print(f"\n{'='*60}")
        print(f"PROCESSING TOPIC: {topic}")
        print(f"{'='*60}")
        
        # Step 1: Extract scientific terms
        print("\n1. Extracting scientific terms...")
        extracted_terms = self.extract_scientific_terms(topic)
        print(f"Initial extracted terms: {extracted_terms}")
        
        # Step 2: Get user feedback on terms
        print("\n2. Getting user feedback on extracted terms...")
        final_terms = self.get_user_feedback_on_terms(extracted_terms)
        print(f"Final terms after user feedback: {final_terms}")
        
        # Step 3: Search literature with BioMCP
        print("\n3. Searching literature with BioMCP...")
        literature_data, references = self.search_literature(topic, final_terms)
        print(f"Found {len(references)} references from BioMCP")
        
        # Step 4: Search variants
        print("\n4. Searching genetic variants...")
        variant_data = self.search_variants(final_terms.get("genes", []))
        
        # Step 5: Search clinical trials
        print("\n5. Searching clinical trials...")
        trial_data = self.search_trials(final_terms.get("diseases", []))
        
        # Step 6: Generate known hypotheses
        print("\n6. Generating known hypotheses...")
        known_hypotheses = self.generate_known_hypotheses(topic, literature_data, variant_data, trial_data, references)
        
        # Step 7: Generate unknown hypotheses
        print("\n7. Generating unknown hypotheses...")
        unknown_hypotheses = self.generate_unknown_hypotheses(topic, literature_data, variant_data, trial_data, references)
        
        # Step 8: Analyze and create research plans (with timeout handling)
        print("\n8. Analyzing hypotheses and creating research plans...")
        
        results = {
            "topic": topic,
            "extracted_terms": final_terms,
            "biomcp_references": references,
            "known_hypotheses": [],
            "unknown_hypotheses": [],
            "research_plans": []
        }
        
        # Process known hypotheses with timeout handling
        for i, hypothesis in enumerate(known_hypotheses):
            try:
                print(f"  Analyzing known hypothesis {i+1}...")
                analysis = self.analyze_hypothesis_strength(hypothesis, literature_data, "known")
                research_plan = self.generate_research_plan(hypothesis, analysis, "known")
                
                results["known_hypotheses"].append({
                    "hypothesis": hypothesis,
                    "analysis": analysis,
                    "research_plan": research_plan
                })
            except Exception as e:
                print(f"  Error processing known hypothesis {i+1}: {e}")
                results["known_hypotheses"].append({
                    "hypothesis": hypothesis,
                    "analysis": "Analysis failed due to timeout",
                    "research_plan": "Research plan generation failed due to timeout"
                })
        
        # Process unknown hypotheses with timeout handling
        for i, hypothesis in enumerate(unknown_hypotheses):
            try:
                print(f"  Analyzing unknown hypothesis {i+1}...")
                analysis = self.analyze_hypothesis_strength(hypothesis, literature_data, "unknown")
                research_plan = self.generate_research_plan(hypothesis, analysis, "unknown")
                
                results["unknown_hypotheses"].append({
                    "hypothesis": hypothesis,
                    "analysis": analysis,
                    "research_plan": research_plan
                })
            except Exception as e:
                print(f"  Error processing unknown hypothesis {i+1}: {e}")
                results["unknown_hypotheses"].append({
                    "hypothesis": hypothesis,
                    "analysis": "Analysis failed due to timeout",
                    "research_plan": "Research plan generation failed due to timeout"
                })
        
        return results

def main():
    """Main function to run the hypothesis generator"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate biological hypotheses using BioMCP and LLM")
    parser.add_argument("--topic", type=str, required=True, help="Biological topic to analyze")
    parser.add_argument("--ollama-host", type=str, default="http://localhost:11434", help="Ollama host URL")
    parser.add_argument("--model", type=str, default="llama3.1:8b", help="Ollama model to use")
    
    args = parser.parse_args()
    
    # Initialize the hypothesis generator
    generator = BioMCPHypothesisGenerator(
        ollama_host=args.ollama_host,
        model=args.model
    )
    
    # Process the topic
    results = generator.process_topic(args.topic)
    
    # Print results with improved formatting
    print(f"\n{'='*80}")
    print("FINAL RESULTS SUMMARY")
    print(f"{'='*80}")
    
    print(f"\n TOPIC: {results['topic']}")
    print(f" FINAL TERMS: {results['extracted_terms']}")
    print(f" BIOMCP REFERENCES FOUND: {len(results['biomcp_references'])}")
    print(f" KNOWN HYPOTHESES GENERATED: {len(results['known_hypotheses'])}")
    print(f" UNKNOWN HYPOTHESES GENERATED: {len(results['unknown_hypotheses'])}")
    
    print(f"\n{'='*60}")
    print("KNOWN HYPOTHESES (ESTABLISHED MECHANISMS)")
    print(f"{'='*60}")
    
    for i, result in enumerate(results['known_hypotheses'], 1):
        print(f"\n KNOWN HYPOTHESIS {i}")
        print(f"{'─'*50}")
        
        # Display full hypothesis without truncation
        hypothesis = result['hypothesis']
        print(f"Hypothesis: {hypothesis}")
        
        # Only truncate analysis and research plan for readability
        analysis = result['analysis']
        if len(analysis) > 300:
            print(f"\n Analysis: {analysis[:300]}...")
            print(f"[TRUNCATED - Full analysis available in results]")
        else:
            print(f"\n Analysis: {analysis}")
        
        research_plan = result['research_plan']
        if len(research_plan) > 300:
            print(f"\n Research Plan: {research_plan[:300]}...")
            print(f"[TRUNCATED - Full research plan available in results]")
        else:
            print(f"\n Research Plan: {research_plan}")
    
    print(f"\n{'='*60}")
    print("UNKNOWN HYPOTHESES (NOVEL MECHANISMS)")
    print(f"{'='*60}")
    
    for i, result in enumerate(results['unknown_hypotheses'], 1):
        print(f"\n UNKNOWN HYPOTHESIS {i}")
        print(f"{'─'*50}")
        
        # Display full hypothesis without truncation
        hypothesis = result['hypothesis']
        print(f"Hypothesis: {hypothesis}")
        
        # Only truncate analysis and research plan for readability
        analysis = result['analysis']
        if len(analysis) > 300:
            print(f"\ Analysis: {analysis[:300]}...")
            print(f"[TRUNCATED - Full analysis available in results]")
        else:
            print(f"\n Analysis: {analysis}")
        
        research_plan = result['research_plan']
        if len(research_plan) > 300:
            print(f"\n Research Plan: {research_plan[:300]}...")
            print(f"[TRUNCATED - Full research plan available in results]")
        else:
            print(f"\n Research Plan: {research_plan}")
    
    print(f"\n{'='*60}")
    print(" BIOMCP REFERENCES")
    print(f"{'='*60}")
    
    if results['biomcp_references']:
        for i, ref in enumerate(results['biomcp_references'][:15], 1):  # Show first 15 references
            if len(ref) > 100:
                print(f"{i:2d}. {ref[:100]}...")
            else:
                print(f"{i:2d}. {ref}")
        
        if len(results['biomcp_references']) > 15:
            print(f"\n... and {len(results['biomcp_references']) - 15} more references")
    else:
        print("No references found from BioMCP searches")
    
    print(f"\n{'='*80}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*80}")
    
    # Summary statistics
    total_hypotheses = len(results['known_hypotheses']) + len(results['unknown_hypotheses'])
    successful_analyses = sum(1 for r in results['known_hypotheses'] + results['unknown_hypotheses'] 
                            if 'failed' not in r['analysis'].lower())
    
    print(f"\n SUMMARY STATISTICS:")
    print(f"    Total hypotheses generated: {total_hypotheses}")
    print(f"    Successful analyses: {successful_analyses}")
    print(f"    References found: {len(results['biomcp_references'])}")
    print(f"    Scientific terms extracted: {sum(len(terms) for terms in results['extracted_terms'].values())}")
    
    if total_hypotheses > 0:
        success_rate = (successful_analyses / total_hypotheses) * 100
        print(f"   Analysis success rate: {success_rate:.1f}%")
    
    print(f"\n TIP: If responses seem incomplete, try:")
    print(f"    Using a larger model ")
    print(f"    Increasing timeout values in the code")
    print(f"    Reducing the amount of data passed to the LLM")

if __name__ == "__main__":
    main() 
    set_trace()