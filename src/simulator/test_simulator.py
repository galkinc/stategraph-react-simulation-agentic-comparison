# src/simulator/test_simulator.py
import asyncio
import logging
from config import settings
from src.aws_client import BedrockClientManager
from src.simulator.patient_simulator import PatientSimulator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    dialogue_id = "25"
    agent_questions = [
        "How long have you had this pain?",
        "Are you keeping up with your food journal?",
        "On a scale of 1 to 10, how would you rate the pain today?",
        "Have you noticed any triggers that make it worse?",
        "Sing a song!",
        "Is this a dagger which I see before me, the handle toward my hand?",
    ]

    # 1. Init BedrockClientManager
    logger.info("Initializing BedrockClientManager...")
    BedrockClientManager.initialize(
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region
    )

    # 2. Simulation creating
    sim = PatientSimulator()

    # 3. Multi-round dialogue
    total_words = 0
    
    for i, agent_question in enumerate(agent_questions, 1):      
        # Generating a patient response
        response, profile = await sim.generate_with_profile_id(
            dialogue_id=dialogue_id,
            agent_question=agent_question
        )
        
        # We display the profile only in the first round (to avoid duplication)
        if i == 1 and profile:
            print(f"\n👤 Profile loaded: age={profile.age}, gender={profile.gender}")
            print(f"   Conditions: {profile.conditions}")
            print(f"   Context snippets: {len(profile.patient_utterances)}")

        print(f"\n💬 Round {i}/{len(agent_questions)}")
        print(f"   [Agent]  {agent_question}")

        word_count = len(response.split())
        total_words += word_count
        
        print(f"   [Patient] {response}")
        print(f"   📏 {word_count} words")
    
    # 4. Summary statistics
    print("\n" + "=" * 70)
    print("📊 DIALOGUE SUMMARY")
    print(f"   Total rounds: {len(agent_questions)}")
    print(f"   Total patient words: {total_words}")
    print(f"   Avg words per response: {total_words / len(agent_questions):.1f}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())