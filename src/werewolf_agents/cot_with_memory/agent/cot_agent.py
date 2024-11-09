from typing import Any, Dict, List
from autogen import ConversableAgent, Agent, runtime_logging

import os,json,re
import asyncio
import logging
from collections import defaultdict
import time
from datetime import datetime
from memory_storer import (
    MemoryStorer,
    PlayerRole,
    PlayerStatus,
    Claim,
    MyState
)
from sentient_campaign.agents.v1.api import IReactiveAgent, AgentBase, INotify, IRespond, ActivityMessage, ActivityResponse
from sentient_campaign.agents.v1.message import MessageChannelType
import requests

GAME_CHANNEL = "play-arena"
WOLFS_CHANNEL = "wolf's-den"
MODERATOR_NAME = "moderator"
MODEL_NAME = "Llama31-70B-Instruct"

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger = logging.getLogger("demo_agent")
level = logging.DEBUG
logger.setLevel(level)
logger.propagate = True
handler = logging.StreamHandler()
handler.setLevel(level)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class CoTAgent(IReactiveAgent):
    # input -> thoughts -> init action -> reflection -> final action

    WOLF_PROMPT = """You are a wolf in a game of Werewolf. Your goal is to eliminate villagers without being detected. Consider the following:
    1. Blend in with villagers during day discussions.
    2. Coordinate with other werewolves to choose a target.
    3. Pay attention to the seer and doctor's potential actions.
    4. Defend yourself if accused, but don't be too aggressive."""

    VILLAGER_PROMPT = """You are a villager in a game of Werewolf. Your goal is to identify and eliminate the werewolves. Consider the following:
    1. Observe player behavior and voting patterns.
    2. Share your suspicions and listen to others.
    3. Be cautious of false accusations.
    4. Try to identify the seer and doctor to protect them."""

    SEER_PROMPT = """You are the seer in a game of Werewolf. Your ability is to learn one player's true identity each night. Consider the following:
    1. Use your knowledge wisely without revealing your role.
    2. Keep track of the information you gather each night.
    3. Guide village discussions subtly.
    4. Be prepared to reveal your role if it can save the village."""

    DOCTOR_PROMPT = """You are the doctor in a game of Werewolf. Your ability is to protect one player from elimination each night. Consider the following:
    1. Decide whether to protect yourself or others.
    2. Try to identify key players to protect (like the seer).
    3. Vary your protection pattern to avoid being predictable.
    4. Participate in discussions without revealing your role."""

    def __init__(self):
        logger.debug("WerewolfAgent initialized.")
        

    def __initialize__(self, name: str, description: str, config: dict = None):
        super().__initialize__(name, description, config)
        self._name = name
        self._description = description
        self.MODERATOR_NAME = MODERATOR_NAME
        self.WOLFS_CHANNEL = WOLFS_CHANNEL
        self.GAME_CHANNEL = GAME_CHANNEL
        self.config = config
        self.have_thoughts = True
        self.have_reflection = True
        self.role = None
        self.direct_messages = defaultdict(list)
        self.group_channel_messages = defaultdict(list)
        self.seer_checks = {}  # To store the seer's checks and results
        self.game_history = []  # To store the interwoven game history
        self.memory = MemoryStorer(self._name)

        self.llm_config = {
                "api_key": os.getenv("OPENAI_API_KEY"),
                "llm_base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                "llm_model_name": os.getenv("OPENAI_MODEL_NAME", MODEL_NAME)
            }
        self.model = self.llm_config["llm_model_name"]
        logger.info(
            f"WerewolfAgent initialized with name: {name}, description: {description}, and config: {config}"
        )
        self.game_intro = None

    async def async_notify(self, message: ActivityMessage):
        """Process incoming messages and update memory"""
        logger.info(f"ASYNC NOTIFY called with message: {message}")
        
        # Store message and initialize new players
        self.memory.initialize_player(message.header.sender)
        self.memory.add_claim(
            message.header.sender,
            message.content.text,
            message.header.channel
        )

        # Process direct messages
        if message.header.channel_type == MessageChannelType.DIRECT:
            self.direct_messages[message.header.sender].append(message)
            user_messages = self.direct_messages[message.header.sender]
            
            # Handle role assignment from moderator
            if not len(user_messages) > 1 and message.header.sender == self.MODERATOR_NAME:
                self.role = self.find_my_role(message)
                self.memory.update_my_role(PlayerRole(self.role.lower()))
                self.memory.add_thought_process(f"Assigned role: {self.role}")
                logger.info(f"Role assigned to {self._name}: {self.role}")
                
        # Process group messages
        else:
            self.group_channel_messages[message.header.channel].append(message)
            self._analyze_message_for_behavior(message)
            
            if message.header.sender == self.MODERATOR_NAME:
                self._process_moderator_message(message)
            
            self.game_history.append(f"{message.header.sender}: {message.content.text}")

    def _analyze_message_for_behavior(self, message: ActivityMessage):
        """Analyze messages for patterns and suspicious behavior"""
        content = message.content.text.lower()
        sender = message.header.sender
        
        # Track voting patterns
        if "vote" in content:
            vote_match = re.search(r"vote (?:for )?(\w+)", content)
            if vote_match:
                target = vote_match.group(1)
                self.memory.record_vote(sender, target)
                self.memory.add_behavioral_note(
                    sender,
                    f"Voted for {target}"
                )

        # Track accusations
        if "suspicious" in content or "wolf" in content:
            for player in self.memory.get_alive_players():
                if player.lower() in content:
                    self.memory.update_suspicion_score(player, 0.2)
                    self.memory.add_behavioral_note(
                        sender,
                        f"Accused {player} of suspicious behavior"
                    )

        # Track defensive behavior
        if sender in content.lower() and ("not" in content or "innocent" in content):
            self.memory.add_behavioral_note(
                sender,
                "Defensive behavior in response to accusations"
            )
            self.memory.update_suspicion_score(sender, 0.1)

    def _process_moderator_message(self, message: ActivityMessage):
        """Process moderator announcements and update game state"""
        content = message.content.text.lower()
        
        # Track eliminations
        death_match = re.search(r"(\w+) has been eliminated", content)
        if death_match:
            dead_player = death_match.group(1)
            self.memory.mark_player_dead(dead_player)
            self.memory.record_key_event(
                "elimination",
                f"{dead_player} was eliminated",
                [dead_player]
            )

        # Track phase changes
        if "night phase" in content:
            self.memory.is_night = True
            self.memory.night_count += 1
            self.memory.record_key_event("phase_change", "Night phase began", [])
        elif "day phase" in content:
            self.memory.is_night = False
            self.memory.day_count += 1
            self.memory.record_key_event("phase_change", "Day phase began", [])

    def find_my_role(self, message):
        """Extract role from moderator message using Sentient API"""
        headers = {
            "Authorization": f"Bearer {self.llm_config['api_key']}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": f"The user is playing a game of werewolf as user {self._name}, help the user with question with less than a line answer"
                },
                {
                    "role": "user",
                    "content": f"You have got message from moderator here about my role in the werewolf game, here is the message -> '{message.content.text}', what is your role? possible roles are 'wolf','villager','doctor' and 'seer'. answer in a few words."
                }
            ]
        }

        try:
            response = requests.post(
                f"{self.llm_config['llm_base_url']}/chat/completions",
                headers=headers,
                json=payload
            )
            result = response.json()
            my_role_guess = result["choices"][0]["message"]["content"]
            
            logger.info(f"my_role_guess: {my_role_guess}")
            if "villager" in my_role_guess.lower():
                role = "villager"
            elif "seer" in my_role_guess.lower():
                role = "seer"
            elif "doctor" in my_role_guess.lower():
                role = "doctor"
            else:
                role = "wolf"
            
            return role
        except Exception as e:
            logger.error(f"Error determining role: {e}")
            return "villager"  # default role on error

    def get_interwoven_history(self, include_wolf_channel=False):
        return "\n".join([
            event for event in self.game_history
            if include_wolf_channel or not event.startswith(f"[{self.WOLFS_CHANNEL}]")
        ])

    async def async_respond(self, message: ActivityMessage):
        logger.info(f"ASYNC RESPOND called with message: {message}")

        if message.header.channel_type == MessageChannelType.DIRECT and message.header.sender == self.MODERATOR_NAME:
            self.direct_messages[message.header.sender].append(message.content.text)
            if self.role == "seer":
                response_message = self._get_response_for_seer_guess(message)
            elif self.role == "doctor":
                response_message = self._get_response_for_doctors_save(message)
            
            response = ActivityResponse(response=response_message)
            self.game_history.append(f"[From - {message.header.sender}| To - {self._name} (me)| Direct Message]: {message.content.text}")
            self.game_history.append(f"[From - {self._name} (me)| To - {message.header.sender}| Direct Message]: {response_message}")    
        elif message.header.channel_type == MessageChannelType.GROUP:
            self.group_channel_messages[message.header.channel].append(
                (message.header.sender, message.content.text)
            )
            if message.header.channel == self.GAME_CHANNEL:
                response_message = self._get_discussion_message_or_vote_response_for_common_room(message)
            elif message.header.channel == self.WOLFS_CHANNEL:
                response_message = self._get_response_for_wolf_channel_to_kill_villagers(message)
            self.game_history.append(f"[From - {message.header.sender}| To - {self._name} (me)| Group Message in {message.header.channel}]: {message.content.text}")
            self.game_history.append(f"[From - {self._name} (me)| To - {message.header.sender}| Group Message in {message.header.channel}]: {response_message}")
        
        return ActivityResponse(response=response_message)

    def _get_inner_monologue(self, role_prompt: str, game_situation: str, specific_prompt: str) -> str:
        """Generate inner thoughts using memory and game state"""
        memory_state = self.memory.get_my_state()
        
        enhanced_situation = f"""
{role_prompt}

Current Game State:
- Day: {self.memory.day_count}, Night: {self.memory.night_count}
- Alive Players: {', '.join(self.memory.get_alive_players())}
- Most Suspicious Players: {', '.join(self.memory.get_most_suspicious_players(3))}
- My Alliances: {', '.join([f'{p}(trust:{t:.1f})' for p,t in memory_state['alliances'].items()])}
- My Enemies: {', '.join([f'{p}({r})' for p,r in memory_state['enemies'].items()])}

Recent Events:
{self._format_key_events(memory_state['key_events'][-3:])}

Behavioral Observations:
{self._format_behavioral_notes(memory_state['behavioral_notes'])}

Game Situation:
{game_situation}

Consider carefully:
{specific_prompt}"""

        response = self._get_llm_response(enhanced_situation)
        self.memory.add_thought_process(response)
        return response

    def _get_response_for_seer_guess(self, message):
        """Generate seer investigation response"""
        # Compile seer investigation history
        seer_checks_info = "\n".join([f"Checked {player}: {result}" for player, result in self.seer_checks.items()])
        for player, result in self.seer_checks.items():
            self.memory.record_role_action(player, "investigate", result)
        
        game_situation = f"""
Previous Investigations:
{seer_checks_info}

Current Game State:
{self.get_interwoven_history()}"""
        
        specific_prompt = """Think through your investigation choice:
1. Who remains uninvestigated among suspicious players?
2. Which player's role would provide the most valuable information?
3. How can you use this information to guide the village?
4. Should you reveal your role based on what you discover?"""

        inner_monologue = self._get_inner_monologue(self.SEER_PROMPT, game_situation, specific_prompt)
        action = self._get_final_action(self.SEER_PROMPT, game_situation, inner_monologue, "investigation target")
        
        self.memory.record_role_action(action, "investigate")
        return action

    def _get_response_for_doctors_save(self, message):
        """Generate doctor protection response"""
        protected_players = self.memory.my_state.protected_players
        
        game_situation = f"""
Previous Protections:
{', '.join(protected_players) if protected_players else 'None'}

Current Game State:
{self.get_interwoven_history()}"""
        
        specific_prompt = """Consider your protection choice:
1. Who faces the highest risk tonight?
2. Have you protected yourself recently?
3. Which players seem most valuable to the village?
4. How can you avoid predictable protection patterns?"""

        inner_monologue = self._get_inner_monologue(self.DOCTOR_PROMPT, game_situation, specific_prompt)
        action = self._get_final_action(self.DOCTOR_PROMPT, game_situation, inner_monologue, "protection target")
        
        self.memory.record_role_action(action, "protect")
        return action

    def _get_response_for_wolf_channel_to_kill_villagers(self, message):
        """Generate werewolf kill response"""
        if self.role != "wolf":
            return "I am not a werewolf"
        
        pack_members = self.memory.my_state.pack_members
        game_situation = f"""
Pack Information:
Known werewolves: {', '.join(pack_members) if pack_members else 'None'}

Current Game State:
{self.get_interwoven_history(include_wolf_channel=True)}"""
        
        specific_prompt = """Plan your elimination target:
1. Who poses the biggest threat to the werewolves?
2. Which elimination would cause maximum confusion?
3. How can we coordinate with other wolves?
4. Which target would least expose our identities?"""

        inner_monologue = self._get_inner_monologue(self.WOLF_PROMPT, game_situation, specific_prompt)
        target = self._get_final_action(self.WOLF_PROMPT, game_situation, inner_monologue, "elimination target")
        
        self.memory.record_role_action(target, "target_for_elimination")
        return target

    def _get_discussion_message_or_vote_response_for_common_room(self, message):
        """Generate discussion or voting response"""
        role_prompt = getattr(self, f"{self.role.upper()}_PROMPT", self.VILLAGER_PROMPT)
        
        game_situation = f"""
Recent Game History:
{self.get_interwoven_history()}"""
        
        specific_prompt = """Consider for your response:
1. What patterns have emerged in recent discussions?
2. Which players' behaviors seem most suspicious?
3. How can you contribute valuable insights?
4. What evidence supports your suspicions?
5. How should you position yourself in the discussion?"""

        inner_monologue = self._get_inner_monologue(role_prompt, game_situation, specific_prompt)
        response = self._get_final_action(role_prompt, game_situation, inner_monologue, "discussion contribution or vote")
        
        if "vote" in message.content.text.lower():
            self.memory.record_vote_justification(response, inner_monologue)
            
        return response

    def _get_final_action(self, role_prompt: str, situation: str, inner_monologue: str, action_type: str) -> str:
        """Generate final action based on inner monologue"""
        action_prompt = f"""
Based on this analysis:
{inner_monologue}

And considering:
{situation}

Provide only your final {action_type} in a clear, concise format.
Do not include explanations or additional text."""

        response = self._get_llm_response(action_prompt)
        self.memory.add_thought_process(f"Final {action_type}: {response}")
        return response.strip()

    def _get_llm_response(self, prompt: str) -> str:
        """Get response from LLM using Sentient API"""
        headers = {
            "Authorization": f"Bearer {self.llm_config['api_key']}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.llm_config["llm_model_name"],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 500
        }

        try:
            response = requests.post(
                f"{self.llm_config['llm_base_url']}/chat/completions",
                headers=headers,
                json=payload
            )
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Error getting LLM response: {e}")
            return "I need more time to think about this."

    def _summarize_game_history(self):

        self.detailed_history = "\n".join(self.game_history)

        # send the llm the previous summary of each of the other players and suspiciona nd information, the detailed chats of this day or night
        # llm will summarize the game history and provide a summary of the game so far
        # summarized game history is used for current situation

        pass

    def _format_behavioral_notes(self, notes: Dict) -> str:
        """Format behavioral observations"""
        if not notes:
            return "No behavioral observations recorded"
            
        formatted = []
        for player, observations in notes.items():
            if not observations:
                continue
            formatted.append(f"{player}:")
            # Get last 3 observations for each player
            for obs in observations[-3:]:
                formatted.append(f"  - {obs['observation']}")
        return "\n".join(formatted)

    def _format_key_events(self, events: List[Dict]) -> str:
        """Format key game events"""
        if not events:
            return "No key events recorded"
            
        formatted = []
        for event in events:
            formatted.append(
                f"- {event['type'].title()}: {event['details']} "
                f"(Players: {', '.join(event['players'])})"
            )
        return "\n".join(formatted)
