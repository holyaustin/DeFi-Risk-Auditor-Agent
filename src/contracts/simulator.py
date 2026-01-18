import subprocess
import json
import tempfile
import os
import asyncio
from typing import Dict, Any, List
from web3 import Web3


class HardhatSimulator:
    def __init__(self, hardhat_dir: str = None):
        self.hardhat_dir = hardhat_dir or os.path.join(
            os.path.dirname(__file__), "../../hardhat"
        )
        self.web3 = None
        self.contract_addresses = {}
    
    async def initialize(self):
        """Initialize Hardhat environment."""
        # Start Hardhat node in background
        self.process = await asyncio.create_subprocess_exec(
            'npx', 'hardhat', 'node',
            cwd=self.hardhat_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for node to start
        await asyncio.sleep(3)
        
        # Connect Web3
        self.web3 = Web3(Web3.HTTPProvider('http://localhost:8545'))
        
        # Deploy test contracts
        await self.deploy_contracts()
    
    async def deploy_contracts(self) -> Dict[str, str]:
        """Deploy vulnerable contracts to local Hardhat network."""
        deploy_script = """
        const hre = require("hardhat");
        
        async function main() {
            const ReentrancyVault = await hre.ethers.getContractFactory("ReentrancyVault");
            const FlashLoanPool = await hre.ethers.getContractFactory("FlashLoanPool");
            const OracleManipulation = await hre.ethers.getContractFactory("OracleManipulation");
            
            const vault = await ReentrancyVault.deploy();
            await vault.waitForDeployment();
            
            const pool = await FlashLoanPool.deploy();
            await pool.waitForDeployment();
            
            const oracle = await OracleManipulation.deploy();
            await oracle.waitForDeployment();
            
            console.log(JSON.stringify({
                reentrancyVault: await vault.getAddress(),
                flashLoanPool: await pool.getAddress(),
                oracleManipulation: await oracle.getAddress()
            }));
        }
        
        main().catch((error) => {
            console.error(error);
            process.exitCode = 1;
        });
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(deploy_script)
            script_path = f.name
        
        try:
            result = subprocess.run(
                ['npx', 'hardhat', 'run', script_path, '--network', 'localhost'],
                cwd=self.hardhat_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                output_lines = result.stdout.strip().split('\n')
                contract_data = json.loads(output_lines[-1])
                self.contract_addresses = contract_data
                return contract_data
            else:
                raise Exception(f"Hardhat deployment failed: {result.stderr}")
        finally:
            os.unlink(script_path)
    
    async def simulate_exploit(self, exploit_code: str, contract_address: str) -> Dict[str, Any]:
        """Simulate an exploit attempt in isolated environment."""
        # Create temporary Hardhat test file
        test_content = f"""
        const hre = require("hardhat");
        
        describe("Exploit Simulation", function() {{
            it("Should execute exploit", async function() {{
                const Exploit = await hre.ethers.getContractFactory("ExploitContract");
                const exploit = await Exploit.deploy("{contract_address}");
                await exploit.waitForDeployment();
                
                // Execute exploit
                const result = await exploit.executeExploit();
                console.log(JSON.stringify({{
                    success: true,
                    profit: result.toString(),
                    steps: ["deployed", "executed"]
                }}));
            }});
        }});
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(test_content)
            test_file = f.name
        
        try:
            result = subprocess.run(
                ['npx', 'hardhat', 'test', test_file, '--network', 'localhost'],
                cwd=self.hardhat_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        finally:
            os.unlink(test_file)
    
    async def cleanup(self):
        """Clean up Hardhat processes."""
        if hasattr(self, 'process') and self.process:
            self.process.terminate()
            await self.process.wait()