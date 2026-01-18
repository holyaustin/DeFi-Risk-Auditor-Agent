import os
import openai
from typing import List, Dict, Any
from src.agent import VulnerabilityFinding, FixProposal


class NebiusInference:
    def __init__(self):
        # Nebius provides $50 inference credits
        self.api_key = os.getenv("NEBIUS_API_KEY")
        self.base_url = os.getenv("NEBIUS_BASE_URL", "https://api.nebius.ai/v1")
        
        if self.api_key:
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        else:
            self.client = None
    
    async def analyze_findings(self, findings: List[VulnerabilityFinding]) -> Dict[str, Any]:
        """Use Nebius LLM for advanced analysis of vulnerability findings."""
        if not self.client:
            return {"analysis": "Nebius not configured", "using_fallback": True}
        
        try:
            findings_text = "\n".join([
                f"- {f.contract}: {f.vulnerability_type} (Severity: {f.severity})"
                for f in findings
            ])
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a smart contract security expert specializing in DeFi vulnerabilities."
                    },
                    {
                        "role": "user",
                        "content": f"""Analyze these DeFi vulnerability findings for correctness and completeness:
                        
                        Findings:
                        {findings_text}
                        
                        Please provide:
                        1. Overall assessment of findings quality
                        2. Potential false positives
                        3. Missing vulnerabilities to check
                        4. Severity scoring accuracy
                        5. Recommendations for improvement
                        """
                    }
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            return {
                "analysis": response.choices[0].message.content,
                "model": "gpt-4",
                "provider": "Nebius"
            }
            
        except Exception as e:
            return {"error": str(e), "using_fallback": True}
    
    async def validate_fix_proposals(self, fixes: List[FixProposal]) -> Dict[str, Any]:
        """Validate fix proposals using LLM analysis."""
        if not self.client:
            return {"validation": "Nebius not configured"}
        
        fixes_text = "\n".join([
            f"Line {f.line_number}:\nOriginal: {f.original_code}\nFixed: {f.fixed_code}\nExplanation: {f.explanation}"
            for f in fixes
        ])
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a Solidity security auditor validating fix proposals."
                },
                {
                    "role": "user",
                    "content": f"""Validate these Solidity fix proposals:
                    
                    {fixes_text}
                    
                    For each fix, assess:
                    1. Correctness of the fix
                    2. Potential side effects
                    3. Whether it fully addresses the vulnerability
                    4. Alternative approaches
                    5. Security implications
                    """
                }
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        return {
            "validation": response.choices[0].message.content,
            "fixes_count": len(fixes)
        }