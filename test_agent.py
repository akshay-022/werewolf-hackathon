import asyncio
import logging
from src.werewolf_agents.cot_with_memory.agent.cot_agent import CoTAgent
from sentient_campaign.agents.v1.message import (
    ActivityMessage,
    TextContent,
    ActivityMessageHeader,
    MessageChannelType,
)

import uuid
# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class GameSimulator:
    def __init__(self, agent_name="test_player", api_key="your-api-key"):
        sentient_config = {
            "api_key": api_key,
            "llm_base_url": "https://api.sentient.ai/v1",
            "llm_model_name": "gpt-4",
            "sentient_llm_config": {
                "api_key": api_key,
                "llm_base_url": "https://api.sentient.ai/v1",
                "llm_model_name": "gpt-4"
            }
        }
        
        self.agent = CoTAgent()
        self.agent.__initialize__(
            agent_name, 
            "Test Player Description", 
            sentient_config
        )
        self.players = ["player1", "player2", "player3", "player4", "player5"]

    def create_message(self, sender: str, content: str, channel: str, channel_type: MessageChannelType) -> ActivityMessage:
        return ActivityMessage(
            header=ActivityMessageHeader(
                sender=sender,
                channel=channel,
                channel_type=channel_type,
                message_id=str(uuid.uuid4())
            ),
            content=TextContent(text=content),
            content_type='text/plain'
        )

    async def simulate_role_assignment(self, role: str):
        """Simulate the moderator assigning a role"""
        logger.info(f"Simulating role assignment: {role}")
        msg = self.create_message(
            sender="moderator",
            content=f"You are a {role} in this game.",
            channel="direct",
            channel_type=MessageChannelType.DIRECT
        )
        await self.agent.async_notify(msg)

    async def simulate_day_phase(self, day_number: int):
        """Simulate a day phase with discussions and voting"""
        logger.info(f"Simulating day {day_number}")
        
        # Announce day phase
        day_start = self.create_message(
            sender="moderator",
            content=f"Day {day_number} has begun. Please discuss and vote.",
            channel="play-arena",
            channel_type=MessageChannelType.GROUP
        )
        await self.agent.async_notify(day_start)

        # Simulate some discussion
        discussions = [
            ("player1", "I think player3 is acting suspicious"),
            ("player3", "No, I'm innocent! player2 is the one acting weird"),
            ("player2", "I'm just trying to help the village"),
        ]

        for speaker, text in discussions:
            msg = self.create_message(
                sender=speaker,
                content=text,
                channel="play-arena",
                channel_type=MessageChannelType.GROUP
            )
            await self.agent.async_notify(msg)
            response = await self.agent.async_respond(msg)
            logger.info(f"Agent response to discussion: {response.response}")

        # Simulate voting phase
        vote_msg = self.create_message(
            sender="moderator",
            content="Please cast your votes now using 'vote [player_name]'",
            channel="play-arena",
            channel_type=MessageChannelType.GROUP
        )
        await self.agent.async_notify(vote_msg)
        response = await self.agent.async_respond(vote_msg)
        logger.info(f"Agent vote: {response.response}")

    async def simulate_night_phase(self, night_number: int):
        """Simulate night phase actions"""
        logger.info(f"Simulating night {night_number}")
        
        # Announce night phase
        night_start = self.create_message(
            sender="moderator",
            content=f"Night {night_number} has fallen. Special roles perform your actions.",
            channel="play-arena",
            channel_type=MessageChannelType.GROUP
        )
        await self.agent.async_notify(night_start)

        # If agent is wolf, simulate wolf chat
        if self.agent.role == "wolf":
            wolf_msg = self.create_message(
                sender="other_wolf",
                content="Who should we target tonight?",
                channel="wolf's-den",
                channel_type=MessageChannelType.GROUP
            )
            await self.agent.async_notify(wolf_msg)
            response = await self.agent.async_respond(wolf_msg)
            logger.info(f"Agent wolf chat response: {response.response}")

        # If agent is seer, simulate investigation
        elif self.agent.role == "seer":
            seer_msg = self.create_message(
                sender="moderator",
                content="Choose a player to investigate",
                channel="direct",
                channel_type=MessageChannelType.DIRECT
            )
            await self.agent.async_notify(seer_msg)
            response = await self.agent.async_respond(seer_msg)
            logger.info(f"Agent seer investigation: {response.response}")

        # If agent is doctor, simulate protection
        elif self.agent.role == "doctor":
            doctor_msg = self.create_message(
                sender="moderator",
                content="Choose a player to protect",
                channel="direct",
                channel_type=MessageChannelType.DIRECT
            )
            await self.agent.async_notify(doctor_msg)
            response = await self.agent.async_respond(doctor_msg)
            logger.info(f"Agent doctor protection: {response.response}")

async def run_test_game():
    """Run a simulated game"""
    simulator = GameSimulator(api_key="your-actual-sentient-api-key-here")  # Make sure to use Sentient API key
    
    # Test each role
    roles = ["villager", "wolf", "seer", "doctor"]
    for role in roles:
        logger.info(f"\n=== Testing {role.upper()} role ===")
        
        # Reset agent for new role
        simulator = GameSimulator(agent_name=f"test_{role}")
        await simulator.simulate_role_assignment(role)
        
        # Simulate 2 day/night cycles
        for i in range(1, 3):
            await simulator.simulate_day_phase(i)
            await simulator.simulate_night_phase(i)
            
        logger.info(f"=== Completed {role.upper()} test ===\n")

async def run_specific_scenario():
    """Run a specific test scenario"""
    simulator = GameSimulator(api_key="your-api-key-here")
    
    # Test specific role (e.g., wolf)
    await simulator.simulate_role_assignment("wolf")
    
    # Simulate specific game events
    elimination_msg = simulator.create_message(
        sender="moderator",
        content="player2 has been eliminated. They were a villager.",
        channel="play-arena",
        channel_type=MessageChannelType.GROUP
    )
    await simulator.agent.async_notify(elimination_msg)
    
    # Test agent's response to suspicious behavior
    suspicious_msg = simulator.create_message(
        sender="player3",
        content="I saw player4 acting very suspicious last night!",
        channel="play-arena",
        channel_type=MessageChannelType.GROUP
    )
    await simulator.agent.async_notify(suspicious_msg)
    response = await simulator.agent.async_respond(suspicious_msg)
    logger.info(f"Agent response to suspicious behavior: {response.response}")

if __name__ == "__main__":
    # Run full test game
    asyncio.run(run_test_game())
    
    # Or run specific scenario
    # asyncio.run(run_specific_scenario()) 