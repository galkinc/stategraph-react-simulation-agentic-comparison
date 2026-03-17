import logging
import json
from dataclasses import dataclass

from config import settings
from src.aws_client import bedrock_manager, BedrockClientManager
from src.profile.schemas import PatientProfile
from src.simulator.retriever import SimpleRetriever
from src.simulator.prompt import PATIENT_SIMULATOR_SYSTEM, PATIENT_SIMULATOR_USER

logger = logging.getLogger(__name__)


class PatientSimulator:
    """
    Simulates patient responses using Bedrock LLM.
    Grounded in PatientProfile data and dialogue context.
    """
    
    def __init__(
        self, 
        client: BedrockClientManager | None = None,
        model_id: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 50,  # Enough for 8-12 words
        retriever: SimpleRetriever | None= None
    ):
        self.client = client or bedrock_manager
        self.model_id = model_id or settings.model.model_id
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.retriever = retriever or SimpleRetriever()
    
    async def generate_response(
        self, 
        profile: PatientProfile, 
        agent_question: str
    ) -> str:
        """
        Generate patient response to agent's question.
        
        Args:
            profile: PatientProfile with dialogue + entities
            agent_question: Question from ReAct agent
            
        Returns:
            Patient response string (8-12 words)
        """
        # 1. Retrieve relevant context
        context = self.retriever.retrieve_context(profile, agent_question)
        
        # 2. Format prompt
        system_prompt = PATIENT_SIMULATOR_SYSTEM.format(
            min_words = settings.min_words or 5,
            max_words = settings.max_words or 12,
            allowed_topics=", ".join(profile.allowed_topics[:10]) if profile.allowed_topics else "any medical topic",
            forbidden_facts=", ".join(profile.forbidden_facts) if profile.forbidden_facts else "none",
            age=profile.age or "unknown",
            gender=profile.gender or "unknown"
        )
        
        user_prompt = PATIENT_SIMULATOR_USER.format(
            retrieved_context=context,
            agent_question=agent_question,
            min_words = settings.min_words or 5,
            max_words = settings.max_words or 12
        )
        
        # 3. Call Bedrock
        async with self.client.get_client() as bedrock_client:
            try:
                response = await bedrock_client.converse(
                    modelId=self.model_id,
                    messages=[
                        {"role": "user", "content": [{"text": user_prompt}]}
                    ],
                    system=[{"text": system_prompt}],
                    inferenceConfig={
                        "temperature": self.temperature,
                        "maxTokens": self.max_tokens,
                    }
                )
                
                # Extract response text
                content = response.get("output", {}).get("message", {}).get("content", [])
                if content and content[0].get("text"):
                    answer = content[0]["text"].strip()
                    # Post-process: ensure non-empty and 8-12 words (soft enforcement)
                    if not answer or len(answer) == 0:
                        logger.warning("Bedrock returned empty text, using fallback")
                        return "I'm not sure about that."
                    
                    words = answer.split()
                    if len(words) > 12:
                        answer = " ".join(words[:12])
                    elif len(words) < 8:
                        # Pad with ellipsis if too short (edge case)
                        answer = answer.rstrip(".,!?") + "..."
                    return answer
                else:
                    logger.warning("Empty response from Bedrock")
                    return "I'm not sure about that."
                    
            except Exception as e:
                logger.error(f"Bedrock error in PatientSimulator: {e}")
                return "I don't recall that."
    
    async def generate_with_profile_id(
        self, 
        dialogue_id: str, 
        agent_question: str,
        profiles_path: str = "data/processed/patient_profiles.jsonl"
    ) -> tuple[str, PatientProfile | None]:
        """
        Convenience method: load profile by ID and generate response.
        
        Returns:
            (response_text, profile_or_None)
        """
        # Load profile from JSONL
        profile = None
        with open(profiles_path, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                if data.get('dialogue_id') == dialogue_id:
                    profile = PatientProfile(**data)
                    break
        
        if not profile:
            logger.error(f"Profile not found for dialogue_id: {dialogue_id}")
            return "I don't have information about that.", None
        
        response = await self.generate_response(profile, agent_question)
        return response, profile