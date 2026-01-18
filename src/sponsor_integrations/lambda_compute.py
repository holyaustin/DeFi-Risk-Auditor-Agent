import os
import boto3
import asyncio
from typing import Dict, Any
import json


class LambdaCompute:
    def __init__(self):
        # Lambda provides $400 credits - configure via environment
        self.access_key = os.getenv("LAMBDA_ACCESS_KEY")
        self.secret_key = os.getenv("LAMBDA_SECRET_KEY")
        self.region = os.getenv("LAMBDA_REGION", "us-west-2")
        
        if self.access_key and self.secret_key:
            self.lambda_client = boto3.client(
                'lambda',
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region
            )
        else:
            self.lambda_client = None
    
    async def simulate_exploit(self, exploit_data: Dict[str, Any]) -> Dict[str, Any]:
        """Offload compute-heavy exploit simulations to Lambda."""
        if not self.lambda_client:
            # Fallback to local simulation if Lambda not configured
            return {"success": False, "error": "Lambda not configured", "local_fallback": True}
        
        try:
            # Prepare payload for Lambda function
            payload = {
                "exploit_code": exploit_data.get("code", ""),
                "contract_address": exploit_data.get("contract_address", ""),
                "network": "hardhat",
                "action": "simulate_exploit"
            }
            
            # Invoke Lambda function
            response = self.lambda_client.invoke(
                FunctionName='defi-exploit-simulator',
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "local_fallback": True
            }
    
    async def run_complex_analysis(self, contract_code: str) -> Dict[str, Any]:
        """Run complex symbolic execution or fuzzing on Lambda GPU instances."""
        if not self.lambda_client:
            return {"analysis": "Local analysis only"}
        
        payload = {
            "contract_code": contract_code,
            "analysis_type": "symbolic_execution",
            "tools": ["Mythril", "Slither"]
        }
        
        try:
            response = self.lambda_client.invoke(
                FunctionName='defi-contract-analyzer',
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            return json.loads(response['Payload'].read())
        except Exception as e:
            return {"error": str(e), "local_fallback": True}