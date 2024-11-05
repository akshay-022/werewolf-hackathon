import json
import os
from typing import List, Dict
from dataclasses import dataclass
from pathlib import Path
from sentient_campaign.activity_runner.runner import WerewolfCampaignActivityRunner, PlayerAgentConfig

@dataclass
class GameMetrics:
    total_games: int
    wins: int
    losses: int
    response_failures: int
    survival_rate: float
    win_rate: float
    failure_rate: float

class WerewolfMetricsCollector:
    def __init__(self, base_port: int = 14000):
        self.runner = WerewolfCampaignActivityRunner()
        self.base_port = base_port
        
    def run_games(
        self,
        agent_config: PlayerAgentConfig,
        num_games: int,
        api_keys: List[str],
        results_dir: str = "game_results",
        transcripts_dir: str = "transcripts"
    ) -> GameMetrics:
        """Run multiple games and collect metrics"""
        
        # Create directories if they don't exist
        Path(results_dir).mkdir(exist_ok=True)
        Path(transcripts_dir).mkdir(exist_ok=True)
        
        game_results = []
        for game_num in range(num_games):
            # Run game with incremented port to allow parallel runs
            port = self.base_port + game_num
            activity_id = self.runner.run_locally(
                agent_config=agent_config,
                players_sentient_llm_api_keys=api_keys,
                path_to_final_transcript_dump=transcripts_dir,
                force_rebuild_agent_image=False,
                port=port
            )
            
            # Load and parse results
            result_file = os.path.join(results_dir, f"{activity_id}.json")
            if os.path.exists(result_file):
                with open(result_file) as f:
                    game_results.append(json.load(f))
                    
        return self._calculate_metrics(game_results, agent_config.player_name)
    
    def get_metrics_from_previous_games(
        self,
        results_dir: str,
        player_name: str
    ) -> GameMetrics:
        """Calculate metrics from existing game result files without running new games"""
        game_results = []
        
        # Load all JSON files from results directory
        for result_file in Path(results_dir).glob("*.json"):
            try:
                with open(result_file) as f:
                    game_results.append(json.load(f))
            except json.JSONDecodeError:
                print(f"Warning: Could not parse {result_file}")
                continue
                    
        return self._calculate_metrics(game_results, player_name)
    
    def _calculate_metrics(self, game_results: List[Dict], player_name: str) -> GameMetrics:
        """Calculate metrics from game results"""
        total_games = len(game_results)
        wins = 0
        survivals = 0
        failures = 0
        
        for result in game_results:
            player_result = result.get("player_results", {}).get(player_name, {})
            
            # Count wins
            if player_result.get("won", False):
                wins += 1
                
            # Count survivals    
            if player_result.get("survived", False):
                survivals += 1
                
            # Count response failures
            failures += player_result.get("response_failures", 0)
        
        return GameMetrics(
            total_games=total_games,
            wins=wins,
            losses=total_games - wins,
            response_failures=failures,
            survival_rate=survivals / total_games if total_games > 0 else 0,
            win_rate=wins / total_games if total_games > 0 else 0,
            failure_rate=failures / total_games if total_games > 0 else 0
        )

# Example usage:
if __name__ == "__main__":
    # Configure your agent
    agent_config = PlayerAgentConfig(
        player_name="TestAgent",
        agent_wheel_path="/path/to/agent.whl",
        module_path="agent.module",
        agent_class_name="AgentClass",
        agent_config_file_path="/path/to/config.yaml"
    )
    
    # Run metrics collection
    collector = WerewolfMetricsCollector()
    metrics = collector.run_games(
        agent_config=agent_config,
        num_games=5,
        api_keys=["your-api-key"]
    )
    
    print(f"""
    Results over {metrics.total_games} games:
    Win Rate: {metrics.win_rate:.2%}
    Survival Rate: {metrics.survival_rate:.2%}
    Response Failure Rate: {metrics.failure_rate:.2%}
    Total Wins: {metrics.wins}
    Total Losses: {metrics.losses}
    Total Response Failures: {metrics.response_failures}
    """)
