import argparse
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)

from src.executor import Executor


def main():
    parser = argparse.ArgumentParser(description="Run the DeFi Risk Auditor Agent.")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind the server")
    parser.add_argument("--port", type=int, default=9009, help="Port to bind the server")
    parser.add_argument("--card-url", type=str, help="URL to advertise in the agent card")
    args = parser.parse_args()

    # Define agent skills
    skills = [
        AgentSkill(
            id="smart-contract-auditing",
            name="Smart Contract Auditing",
            description="Evaluate smart contracts for security vulnerabilities",
            tags=["solidity", "security", "audit"],
            examples=["Detect reentrancy bugs", "Identify flash loan vulnerabilities"]
        ),
        AgentSkill(
            id="exploit-simulation",
            name="Exploit Simulation",
            description="Simulate attacks to verify vulnerabilities",
            tags=["exploit", "simulation", "hardhat"],
            examples=["Test reentrancy attacks", "Verify oracle manipulation"]
        ),
        AgentSkill(
            id="risk-scoring",
            name="Risk Scoring",
            description="Calculate risk scores based on vulnerability severity",
            tags=["scoring", "risk-assessment", "metrics"],
            examples=["Severity scoring", "Overall risk calculation"]
        )
    ]

    agent_card = AgentCard(
        name="DeFi Risk Arena",
        description="Green agent that evaluates DeFi security agents on detecting smart contract vulnerabilities including reentrancy, flash loan exploits, and oracle manipulation.",
        url=args.card_url or f"http://{args.host}:{args.port}/",
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=skills
    )

    request_handler = DefaultRequestHandler(
        agent_executor=Executor(),
        task_store=InMemoryTaskStore(),
    )
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )
    
    print(f"Starting DeFi Risk Auditor Agent on {args.host}:{args.port}")
    uvicorn.run(server.build(), host=args.host, port=args.port)


if __name__ == '__main__':
    main()