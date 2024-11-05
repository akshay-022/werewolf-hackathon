from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

class PlayerRole(Enum):
    UNKNOWN = "unknown"
    VILLAGER = "villager"
    WEREWOLF = "werewolf"
    SEER = "seer"
    DOCTOR = "doctor"

class PlayerStatus(Enum):
    ALIVE = "alive"
    DEAD = "dead"

@dataclass
class Claim:
    timestamp: datetime
    content: str
    channel: str

@dataclass
class PlayerState:
    name: str
    suspected_role: PlayerRole = PlayerRole.UNKNOWN
    status: PlayerStatus = PlayerStatus.ALIVE
    claims: List[Claim] = None
    voting_history: List[str] = None  # List of who they voted for
    times_voted_against: List[str] = None  # List of who voted against them
    suspicion_score: float = 0.0  # Higher means more suspicious
    protected_by_doctor: bool = False
    investigated_by_seer: bool = False
    
    def __post_init__(self):
        self.claims = self.claims or []
        self.voting_history = self.voting_history or []
        self.times_voted_against = self.times_voted_against or []

class MemoryStorer:
    def __init__(self, my_name: str):
        self.my_name = my_name
        self.players: Dict[str, PlayerState] = {}
        self.day_count: int = 0
        self.night_count: int = 0
        self.is_night: bool = False
        self.my_role: PlayerRole = PlayerRole.UNKNOWN
        
    def initialize_player(self, player_name: str) -> None:
        """Add a new player to track"""
        if player_name != self.my_name and player_name not in self.players:
            self.players[player_name] = PlayerState(name=player_name)
    
    def add_claim(self, player_name: str, content: str, channel: str) -> None:
        """Record a claim made by a player"""
        if player_name in self.players:
            claim = Claim(
                timestamp=datetime.now(),
                content=content,
                channel=channel
            )
            self.players[player_name].claims.append(claim)
    
    def record_vote(self, voter: str, target: str) -> None:
        """Record a vote made during the day phase"""
        if voter in self.players:
            self.players[voter].voting_history.append(target)
        if target in self.players:
            self.players[target].times_voted_against.append(voter)
    
    def mark_player_dead(self, player_name: str) -> None:
        """Mark a player as dead"""
        if player_name in self.players:
            self.players[player_name].status = PlayerStatus.DEAD
    
    def update_suspicion_score(self, player_name: str, delta: float) -> None:
        """Update the suspicion score for a player"""
        if player_name in self.players:
            self.players[player_name].suspicion_score += delta
    
    def set_suspected_role(self, player_name: str, role: PlayerRole) -> None:
        """Set the suspected role for a player"""
        if player_name in self.players:
            self.players[player_name].suspected_role = role
    
    def get_alive_players(self) -> List[str]:
        """Get a list of players who are still alive"""
        return [name for name, state in self.players.items() 
                if state.status == PlayerStatus.ALIVE]
    
    def get_most_suspicious_players(self, count: int = 3) -> List[str]:
        """Get the top N most suspicious players"""
        alive_players = [(name, state) for name, state in self.players.items() 
                        if state.status == PlayerStatus.ALIVE]
        sorted_players = sorted(alive_players, 
                              key=lambda x: x[1].suspicion_score, 
                              reverse=True)
        return [name for name, _ in sorted_players[:count]]
    
    def get_player_claims(self, player_name: str) -> List[Claim]:
        """Get all claims made by a specific player"""
        if player_name in self.players:
            return self.players[player_name].claims
        return []
