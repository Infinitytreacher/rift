# SPDX-FileCopyrightText: 2026 Siddhant Tiwari
# SPDX-License-Identifier: AGPL-3.0-only
# RIFT is distributed without warranty. See LICENSE and COPYRIGHT.md.


"""
NLP Engine Module for IoT Anonymous Feedback System
Handles topic extraction from transcripts using Ollama LLM.
Upgraded for 24GB VRAM and large-context processing.
"""

import json
import os
import re
import logging
import requests
from typing import List, Optional, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ollama API configuration
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_GENERATE_ENDPOINT = f"{OLLAMA_BASE_URL}/api/generate"

# Preserve the original model selection. Review its provenance and terms before use.
DEFAULT_MODEL = os.environ.get(
    "OLLAMA_MODEL", "juilpark/gemma-4-26B-A4B-it-heretic:q4_k_m"
)

# System prompt updated for 5-10 topics constraint and standard JSON Object formatting
SYSTEM_PROMPT = """You are an expert academic data extraction system. Your sole function is to read unformatted lecture transcripts and extract the core technical topics discussed.

Constraints:
1. You must extract exactly 5 to 10 primary topics.
2. Each topic must be a concise string (maximum 5 words).
3. You must output ONLY a valid JSON object with a single key "topics" containing an array of strings.
4. DO NOT include any conversational filler, preambles, or markdown formatting (do not use ```json).
5. If the transcript is empty or unintelligible, output {"topics": []}

Example Input:
"Alright class, today we are going to dive into the transport layer. We'll start by looking at how TCP handles three-way handshakes to establish a connection. Then, I want to spend a good chunk of time comparing that to UDP and why you'd use it for real-time video streaming despite packet loss."

Example Output:
{
  "topics": [
    "Transport Layer",
    "TCP Three-way Handshake",
    "UDP vs TCP",
    "Real-time Video Streaming"
  ]
}"""


class NLPEngine:
    """
    Handles natural language processing tasks using Ollama LLM.
    Specializes in topic extraction from lecture transcripts.
    """
    
    def __init__(self, model: str = DEFAULT_MODEL, base_url: str = OLLAMA_BASE_URL):
        self.model = model
        self.base_url = base_url
        self.generate_endpoint = f"{base_url}/api/generate"
        self._verify_connection()
    
    def _verify_connection(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                logger.info(f"Connected to Ollama at {self.base_url}")
                return True
        except requests.exceptions.ConnectionError:
            logger.error(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Ensure Ollama is running: 'ollama serve'"
            )
            raise ConnectionError(
                f"Ollama server not reachable at {self.base_url}. "
                "Start Ollama with: ollama serve"
            )
        return False
    
    def _clean_json_response(self, response_text: str) -> str:
        cleaned = response_text.strip()
        cleaned = re.sub(r'^```json\s*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^```\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)
        
        # Look for the bounds of either a JSON object { or array [
        start_idx_obj = cleaned.find('{')
        start_idx_arr = cleaned.find('[')
        
        start_idx = -1
        if start_idx_obj != -1 and start_idx_arr != -1:
            start_idx = min(start_idx_obj, start_idx_arr)
        else:
            start_idx = max(start_idx_obj, start_idx_arr)
            
        end_idx_obj = cleaned.rfind('}')
        end_idx_arr = cleaned.rfind(']')
        end_idx = max(end_idx_obj, end_idx_arr)
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            cleaned = cleaned[start_idx:end_idx + 1]
        
        return cleaned.strip()
    
    def _parse_topics_json(self, response_text: str) -> List[str]:
        cleaned = self._clean_json_response(response_text)
        
        try:
            parsed_json = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            logger.error("Model response omitted from logs to protect lecture content")
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")
        
        # Extract the list from the dictionary
        topics = []
        if isinstance(parsed_json, dict):
            # Look for 'topics' key, or fallback to the first list found
            if "topics" in parsed_json and isinstance(parsed_json["topics"], list):
                topics = parsed_json["topics"]
            else:
                for val in parsed_json.values():
                    if isinstance(val, list):
                        topics = val
                        break
                if not topics:
                    raise ValueError("JSON dictionary did not contain a list of topics")
        elif isinstance(parsed_json, list):
            # Fallback just in case the LLM still returns a raw list
            topics = parsed_json
        else:
            raise ValueError(f"Expected dict or list, got {type(parsed_json).__name__}")
        
        validated_topics = []
        for topic in topics:
            if isinstance(topic, str):
                words = topic.split()
                if len(words) > 5:
                    topic = ' '.join(words[:5])
                validated_topics.append(topic)
            else:
                logger.warning("Skipping non-string topic")
        
        # Enforce 5-10 topics constraint
        if len(validated_topics) < 5:
            logger.warning(f"Only {len(validated_topics)} topics found, minimum is 5")
        elif len(validated_topics) > 10:
            validated_topics = validated_topics[:10]
            logger.info("Truncated to 10 topics")
        
        return validated_topics
    
    def extract_topics(
        self,
        transcript: str,
        course_name: Optional[str] = None,
        temperature: float = 0.0,
        max_retries: int = 3
    ) -> List[str]:
        if not transcript or not transcript.strip():
            logger.warning("Empty transcript provided")
            return []
        
        # Expanded limit for 24GB VRAM and large context window models
        max_chars = 300000 
        if len(transcript) > max_chars:
            logger.info(f"Truncating transcript from {len(transcript)} to {max_chars} chars")
            transcript = transcript[:max_chars]
        
        # Inject the course name into the prompt context if provided
        context_prefix = f"Context: This is a lecture transcript for the course '{course_name}'.\n\n" if course_name else ""
        user_prompt = f"{context_prefix}Transcript:\n{transcript}"
        
        payload = {
            "model": self.model,
            "system": SYSTEM_PROMPT,
            "prompt": user_prompt,
            "temperature": temperature,
            "stream": False,
            "format": "json"
        }
        
        last_error = None
        for attempt in range(max_retries):
            try:
                logger.info(f"Calling Ollama (attempt {attempt + 1}/{max_retries})")
                
                response = requests.post(
                    self.generate_endpoint,
                    json=payload,
                    timeout=120
                )
                response.raise_for_status()
                
                result = response.json()
                response_text = result.get("response", "")
                
                if not response_text:
                    raise ValueError("Empty response from LLM")
                
                topics = self._parse_topics_json(response_text)
                logger.info(f"Extracted {len(topics)} topics")
                return topics
                
            except json.JSONDecodeError as e:
                last_error = e
                logger.warning(f"JSON decode error on attempt {attempt + 1}: {e}")
            except requests.exceptions.RequestException as e:
                last_error = e
                logger.error(f"Request error on attempt {attempt + 1}: {e}")
            except ValueError as e:
                last_error = e
                logger.warning(f"Validation error on attempt {attempt + 1}: {e}")
        
        raise RuntimeError(
            f"Failed to extract topics after {max_retries} attempts. "
            f"Last error: {last_error}"
        )
    
    def extract_topics_with_metadata(
        self,
        transcript: str,
        course_name: Optional[str] = None
    ) -> Dict[str, Any]:
        import time
        start_time = time.time()
        
        try:
            topics = self.extract_topics(transcript, course_name=course_name)
            success = True
            error = None
        except Exception as e:
            topics = []
            success = False
            error = str(e)
        
        elapsed_time = time.time() - start_time
        
        return {
            'topics': topics,
            'topic_count': len(topics),
            'model_used': self.model,
            'transcript_length': len(transcript),
            'processing_time_seconds': round(elapsed_time, 2),
            'success': success,
            'error': error
        }
    
    def health_check(self) -> Dict[str, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]
                
                return {
                    'status': 'healthy',
                    'ollama_url': self.base_url,
                    'configured_model': self.model,
                    'model_available': any(self.model in name for name in model_names),
                    'available_models': model_names
                }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'ollama_url': self.base_url
            }
    
    def list_available_models(self) -> List[str]:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [m.get('name', '') for m in models]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
        return []

# ==================== Standalone Functions ====================

def extract_topics_from_transcript(
    transcript: str,
    course_name: Optional[str] = None,
    model: str = DEFAULT_MODEL
) -> List[str]:
    engine = NLPEngine(model=model)
    return engine.extract_topics(transcript, course_name=course_name)

def check_ollama_status() -> Dict[str, Any]:
    try:
        engine = NLPEngine()
        return engine.health_check()
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }

_engine_instance: Optional[NLPEngine] = None

def get_engine(model: str = DEFAULT_MODEL) -> NLPEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = NLPEngine(model=model)
    return _engine_instance
