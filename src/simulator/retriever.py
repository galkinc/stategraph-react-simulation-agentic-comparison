# src/simulator/retriever.py
import re
import logging

from src.profile.schemas import PatientProfile

logger = logging.getLogger(__name__)


class SimpleRetriever:
    """
    Keyword-based retriever: finds relevant patient utterances 
    using profile entities as search terms.
    No embeddings required.
    """
    
    def __init__(self, min_keyword_matches: int = 1, context_radius: int = 1):
        self.min_keyword_matches = min_keyword_matches
        self.context_radius = context_radius  # utterances before/after
    
    def _extract_keywords(self, profile: PatientProfile, query: str) -> set[str]:
        """Extract search keywords from profile entities + query"""
        keywords = set()
        
        # Add profile entities (lowercase for case-insensitive match)
        for entity_list in [
            profile.conditions, 
            profile.anatomy, 
            profile.medications,
            profile.treatments
        ]:
            for entity in entity_list:
                if entity and len(entity) > 2:  # Skip short words
                    keywords.add(entity.lower())
        
        # Add query words (simple tokenization)
        query_words = re.findall(r'\b[a-z]{3,}\b', query.lower())
        keywords.update(query_words)
        
        return keywords
    
    def _score_utterance(self, utterance: str, keywords: set[str]) -> int:
        """Count keyword matches in utterance"""
        utterance_lower = utterance.lower()
        return sum(1 for kw in keywords if kw in utterance_lower)
    
    def retrieve_context(self, profile: PatientProfile, query: str, top_k: int = 3) -> str:
        """
        Find most relevant patient utterances for the given query.
        
        Returns:
            Concatenated context string for LLM prompt
        """
        if not profile.patient_utterances:
            return profile.raw_dialogue[:500]  # Fallback to raw text
        
        keywords = self._extract_keywords(profile, query)
        if not keywords:
            # Fallback: return last 2 patient utterances
            return " | ".join(profile.patient_utterances[-2:])
        
        # Score each utterance
        scored = []
        for idx, utterance in enumerate(profile.patient_utterances):
            score = self._score_utterance(utterance, keywords)
            if score >= self.min_keyword_matches:
                # Add context: include neighboring utterances
                start = max(0, idx - self.context_radius)
                end = min(len(profile.patient_utterances), idx + self.context_radius + 1)
                context = " | ".join(profile.patient_utterances[start:end])
                scored.append((score, context))
        
        if not scored:
            # Fallback: return last utterances
            return " | ".join(profile.patient_utterances[-2:])
        
        # Return top-k unique contexts
        seen = set()
        results = []
        for score, context in sorted(scored, key=lambda x: x[0], reverse=True):
            if context not in seen and len(results) < top_k:
                seen.add(context)
                results.append(context)
        
        return " ; ".join(results)