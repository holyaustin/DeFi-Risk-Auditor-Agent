import json
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator, HttpUrl
from a2a.server.tasks import TaskUpdater
from a2a.types import Message, TaskState, Part, TextPart, DataPart
from a2a.utils import get_message_text, new_agent_text_message

from src.messenger import Messenger
from src.contracts.simulator import HardhatSimulator
from src.contracts.evaluator import VulnerabilityEvaluator
from src.sponsor_integrations.lambda_compute import LambdaCompute
from src.sponsor_integrations.nebius_inference import NebiusInference
from src.utils.deterministic import DeterministicTester


class VulnerabilityFinding(BaseModel):
    contract: str = Field(..., description="Contract name")
    vulnerability_type: str = Field(..., description="reentrancy, flash_loan, oracle_manipulation")
    severity: float = Field(..., ge=0.0, le=1.0, description="Severity score 0-1")
    line_number: int = Field(..., description="Line number of vulnerability")
    description: str = Field(..., description="Detailed description")
    exploit_condition: Optional[str] = Field(None, description="Condition to trigger exploit")
    proof_of_concept: Optional[str] = Field(None, description="Proof of concept code")


class FixProposal(BaseModel):
    line_number: int = Field(..., description="Line to fix")
    original_code: str = Field(..., description="Original vulnerable code")
    fixed_code: str = Field(..., description="Fixed code")
    explanation: str = Field(..., description="Explanation of the fix")


class PurpleAgentSubmission(BaseModel):
    agent_id: str = Field(..., description="Purple agent ID")
    findings: List[VulnerabilityFinding] = Field(default_factory=list)
    fixes: List[FixProposal] = Field(default_factory=list)
    exploit_simulation: Optional[Dict[str, Any]] = Field(None, description="Exploit simulation results")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvalRequest(BaseModel):
    """Request format sent by the AgentBeats platform to green agents."""
    participants: Dict[str, HttpUrl] = Field(..., description="role -> agent URL")
    config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "contract_files": ["ReentrancyVault.sol", "FlashLoanPool.sol", "OracleManipulation.sol"],
            "max_execution_time": 300,
            "scoring_weights": {
                "detection": 0.4,
                "severity": 0.2,
                "fixes": 0.2,
                "reproducibility": 0.2
            }
        }
    )


class DeFiRiskAuditorAgent:
    required_roles: List[str] = ["auditor"]
    required_config_keys: List[str] = ["contract_files"]
    
    def __init__(self):
        self.messenger = Messenger()
        self.simulator = HardhatSimulator()
        self.evaluator = VulnerabilityEvaluator()
        self.deterministic_tester = DeterministicTester()
        self.lambda_compute = LambdaCompute()
        self.nebius_inference = NebiusInference()
        
        # Expected vulnerabilities for scoring
        self.expected_vulnerabilities = {
            "ReentrancyVault": {
                "type": "reentrancy",
                "severity": 0.9,
                "line": 15,  # withdraw function
                "description": "Reentrancy vulnerability allows recursive calls to drain contract"
            },
            "FlashLoanPool": {
                "type": "flash_loan",
                "severity": 0.8,
                "line": 20,  # updatePrice function
                "description": "Price can be manipulated during flash loan execution"
            },
            "OracleManipulation": {
                "type": "oracle_manipulation",
                "severity": 0.7,
                "line": 18,  # updatePrice function
                "description": "Single source oracle controlled by owner"
            }
        }
    
    def validate_request(self, request: EvalRequest) -> tuple[bool, str]:
        missing_roles = set(self.required_roles) - set(request.participants.keys())
        if missing_roles:
            return False, f"Missing roles: {missing_roles}"
        
        missing_config_keys = set(self.required_config_keys) - set(request.config.keys())
        if missing_config_keys:
            return False, f"Missing config keys: {missing_config_keys}"
        
        return True, "ok"
    
    async def run(self, message: Message, updater: TaskUpdater) -> None:
        """Main agent execution logic."""
        try:
            input_text = get_message_text(message)
            request: EvalRequest = EvalRequest.model_validate_json(input_text)
            
            # Validate request
            ok, msg = self.validate_request(request)
            if not ok:
                await updater.reject(new_agent_text_message(msg))
                return
            
            await updater.update_status(
                TaskState.working,
                new_agent_text_message("Starting DeFi risk audit evaluation...")
            )
            
            # Get purple agent URL
            purple_agent_url = request.participants.get("auditor")
            if not purple_agent_url:
                await updater.reject(new_agent_text_message("No auditor agent URL provided"))
                return
            
            # Step 1: Request audit from purple agent
            await updater.update_status(
                TaskState.working,
                new_agent_text_message("Requesting audit from purple agent...")
            )
            
            audit_request = {
                "task": "audit_smart_contracts",
                "contracts": request.config.get("contract_files", []),
                "config": request.config
            }
            
            purple_response = await self.messenger.talk_to_agent(
                message=json.dumps(audit_request),
                url=str(purple_agent_url),
                new_conversation=True
            )
            
            # Step 2: Parse purple agent submission
            try:
                submission_data = json.loads(purple_response)
                submission = PurpleAgentSubmission(**submission_data)
            except Exception as e:
                await updater.reject(new_agent_text_message(f"Invalid submission format: {str(e)}"))
                return
            
            # Step 3: Evaluate submission with sponsor integrations
            await updater.update_status(
                TaskState.working,
                new_agent_text_message("Evaluating submission with sponsor technologies...")
            )
            
            # Use Nebius for LLM analysis of findings
            if submission.findings:
                analysis_result = await self.nebius_inference.analyze_findings(submission.findings)
            
            # Use Lambda for heavy exploit simulation
            exploit_results = None
            if submission.exploit_simulation:
                with self.deterministic_tester.deterministic_context():
                    exploit_results = await self.lambda_compute.simulate_exploit(
                        submission.exploit_simulation
                    )
            
            # Step 4: Calculate scores
            scores = await self.evaluate_submission(submission, exploit_results)
            
            # Step 5: Store results in Snowflake (if configured)
            if hasattr(self, 'snowflake_db'):
                await self.snowflake_db.store_results(
                    agent_id=submission.agent_id,
                    scores=scores,
                    findings_count=len(submission.findings)
                )
            
            # Step 6: Return evaluation results
            await self.return_evaluation_results(updater, scores, submission)
            
        except Exception as e:
            await updater.failed(new_agent_text_message(f"Evaluation failed: {str(e)}"))
    
    async def evaluate_submission(self, submission: PurpleAgentSubmission, exploit_results: Optional[Dict]) -> Dict[str, float]:
        """Calculate evaluation scores."""
        scores = {}
        
        # 1. Vulnerability detection score
        detection_score = self.calculate_detection_score(submission.findings)
        
        # 2. Severity accuracy score
        severity_score = self.calculate_severity_score(submission.findings)
        
        # 3. Fix quality score
        fix_score = self.evaluate_fixes(submission.fixes)
        
        # 4. Reproducibility score
        reproducibility_score = self.calculate_reproducibility_score(exploit_results)
        
        # 5. Overall score (weighted)
        weights = {"detection": 0.4, "severity": 0.2, "fixes": 0.2, "reproducibility": 0.2}
        overall_score = (
            detection_score * weights["detection"] +
            severity_score * weights["severity"] +
            fix_score * weights["fixes"] +
            reproducibility_score * weights["reproducibility"]
        )
        
        return {
            "overall": overall_score,
            "detection": detection_score,
            "severity_accuracy": severity_score,
            "fix_quality": fix_score,
            "reproducibility": reproducibility_score,
            "findings_count": len(submission.findings),
            "false_positives": self.count_false_positives(submission.findings)
        }
    
    def calculate_detection_score(self, findings: List[VulnerabilityFinding]) -> float:
        """Calculate percentage of expected vulnerabilities detected."""
        detected = set()
        for finding in findings:
            key = f"{finding.contract}:{finding.vulnerability_type}"
            detected.add(key)
        
        expected = set(self.expected_vulnerabilities.keys())
        if not expected:
            return 0.0
        
        return len(detected.intersection(expected)) / len(expected)
    
    def calculate_reproducibility_score(self, exploit_results: Optional[Dict]) -> float:
        """Score based on exploit reproducibility."""
        if not exploit_results:
            return 0.0
        
        if exploit_results.get("success") and exploit_results.get("steps"):
            return 0.8 + (0.2 if exploit_results.get("verified") else 0.0)
        
        return 0.0
    
    async def return_evaluation_results(self, updater: TaskUpdater, scores: Dict, submission: PurpleAgentSubmission) -> None:
        """Format and return evaluation results."""
        results_data = {
            "scores": scores,
            "metadata": {
                "agent_id": submission.agent_id,
                "timestamp": asyncio.get_event_loop().time(),
                "version": "1.0.0"
            },
            "detailed_feedback": {
                "strengths": self.identify_strengths(submission),
                "weaknesses": self.identify_weaknesses(submission),
                "recommendations": self.generate_recommendations(submission)
            }
        }
        
        await updater.add_artifact(
            parts=[
                Part(root=TextPart(text="DeFi Risk Audit Evaluation Complete")),
                Part(root=DataPart(data=results_data))
            ],
            name="Evaluation Results",
        )
        
        await updater.complete()