"""
Supply Chain Crisis Sentinel — entry point.

Usage:
    python main.py          # run the full crisis-detection pipeline
    python main.py train 3  # train for 3 iterations
"""

import sys
import warnings
from datetime import datetime

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


def run() -> None:
    from src.crew import SupplyChainCrew

    inputs = {"current_year": str(datetime.now().year)}

    result = SupplyChainCrew().crew().kickoff(inputs=inputs)

    print("\n" + "=" * 60)
    print("  SUPPLY CHAIN CRISIS SENTINEL — RUN COMPLETE")
    print("=" * 60)
    print(result)


def train() -> None:
    from src.crew import SupplyChainCrew

    inputs = {"current_year": str(datetime.now().year)}
    SupplyChainCrew().crew().train(
        n_iterations=int(sys.argv[2]),
        filename=sys.argv[3] if len(sys.argv) > 3 else "trained_crew.pkl",
        inputs=inputs,
    )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "train":
        train()
    else:
        run()
