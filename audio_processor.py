# SPDX-FileCopyrightText: 2026 Siddhant Tiwari
# SPDX-License-Identifier: AGPL-3.0-only
# RIFT is distributed without warranty. See LICENSE and COPYRIGHT.md.


"""
Audio Processor Module for IoT Anonymous Feedback System
Upgraded to use Hugging Face Transformers for 24GB VRAM environments.
"""

import os
import tempfile
import logging
from typing import Optional, Tuple
from pathlib import Path
import torch
from transformers import pipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Upgraded for 24GB VRAM constraint
DEFAULT_MODEL_SIZE = os.environ.get("WHISPER_MODEL", "openai/whisper-large-v3")
DEFAULT_DEVICE = os.environ.get("WHISPER_DEVICE", "cuda")


class AudioProcessor:
    """
    Handles audio file processing and speech-to-text conversion.
    Uses Hugging Face Transformers optimized for high VRAM environments.
    """
    
    def __init__(
        self,
        model_size: str = DEFAULT_MODEL_SIZE,
        device: str = DEFAULT_DEVICE
    ):
        self.model_size = model_size
        self.device = device
        self.pipe = None
        self._initialize_model()
    
    def _initialize_model(self):
        """
        Initialize the Hugging Face Whisper pipeline.
        Handles device fallback if CUDA is unavailable.
        """
        logger.info(f"Loading Whisper model: {self.model_size}")
        
        # Check actual CUDA availability
        use_cuda = torch.cuda.is_available() and self.device == "cuda"
        device_id = "cuda:0" if use_cuda else "cpu"
        
        # Use float16 on GPU to maximize memory efficiency and speed
        torch_dtype = torch.float16 if use_cuda else torch.float32
        
        try:
            self.pipe = pipeline(
                "automatic-speech-recognition",
                model=self.model_size,
                dtype=torch_dtype,
                device=device_id,
                model_kwargs={"attn_implementation": "sdpa"} # Uses Flash Attention for speed
            )
            logger.info(f"Model loaded on {device_id} with {torch_dtype}")
                
        except Exception as e:
            logger.error(f"Pipeline initialization failed: {e}")
            raise
    
    def transcribe(
        self,
        audio_path: str,
        language: str = "english",
        vad_filter: bool = True,
        vad_parameters: Optional[dict] = None
    ) -> Tuple[str, list]:
        """
        Transcribe an audio file to text.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        logger.info(f"Starting transcription of: {audio_path}")
        
        try:
            # The pipeline automatically chunks long audio files
            result = self.pipe(
                audio_path,
                chunk_length_s=30,
                batch_size=4, 
                return_timestamps=True,
                generate_kwargs={"language": language}
            )
            
            transcript_text = result["text"].strip()
            
            # Map Hugging Face chunk format back to your expected segment format
            segments_list = []
            for chunk in result.get("chunks", []):
                segments_list.append({
                    'start': chunk['timestamp'][0],
                    'end': chunk['timestamp'][1],
                    'text': chunk['text'].strip(),
                    'confidence': 1.0 
                })
            
            logger.info(f"Transcription complete. Transcript length: {len(transcript_text)} characters")
            
            return transcript_text, segments_list
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise

    def transcribe_file_streaming(
        self,
        file_stream: bytes,
        file_extension: str = ".wav",
        language: str = "english",
        vad_filter: bool = True
    ) -> Tuple[str, list]:
        """
        Transcribe audio from a byte stream.
        Saves to temporary file first for processing.
        """
        with tempfile.NamedTemporaryFile(
            suffix=file_extension,
            delete=False
        ) as temp_file:
            temp_file.write(file_stream)
            temp_path = temp_file.name
        
        try:
            return self.transcribe(
                temp_path,
                language=language,
                vad_filter=vad_filter
            )
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def get_audio_info(self, audio_path: str) -> dict:
        """
        Get information about an audio file.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        file_size = os.path.getsize(audio_path)
        file_ext = Path(audio_path).suffix
        
        return {
            'file_path': audio_path,
            'file_size_mb': round(file_size / (1024 * 1024), 2),
            'file_extension': file_ext
        }


# ==================== Standalone Functions ====================

def process_uploaded_audio(
    audio_file_path: str,
    model_size: str = DEFAULT_MODEL_SIZE
) -> dict:
    processor = AudioProcessor(model_size=model_size)
    
    audio_info = processor.get_audio_info(audio_file_path)
    transcript_text, segments = processor.transcribe(audio_file_path)
    
    return {
        'transcript': transcript_text,
        'segments': segments,
        'audio_info': audio_info,
        'model_used': model_size
    }

def save_transcript(transcript_text: str, output_path: str) -> str:
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(transcript_text)
    
    logger.info(f"Transcript saved to: {output_path}")
    return output_path

def validate_audio_file(file_path: str) -> Tuple[bool, str]:
    supported_formats = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.webm'}
    
    if not os.path.exists(file_path):
        return False, "File does not exist"
    
    ext = Path(file_path).suffix.lower()
    if ext not in supported_formats:
        return False, f"Unsupported format: {ext}. Supported: {supported_formats}"
    
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > 500:
        logger.warning(f"Large file detected: {file_size_mb:.2f}MB. Processing may take longer.")
    
    return True, f"Valid audio file ({file_size_mb:.2f}MB)"

# Module-level processor instance for convenience
_processor_instance: Optional[AudioProcessor] = None

def get_processor(model_size: str = DEFAULT_MODEL_SIZE) -> AudioProcessor:
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = AudioProcessor(model_size=model_size)
    return _processor_instance

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python audio_processor.py <audio_file_path>")
        sys.exit(1)
    
    audio_path = sys.argv[1]
    is_valid, message = validate_audio_file(audio_path)
    
    if not is_valid:
        print(f"Invalid file: {message}")
        sys.exit(1)
    
    print(f"Processing: {audio_path}")
    print(f"Validation: {message}")
    
    result = process_uploaded_audio(audio_path)
    print(f"\nTranscript ({len(result['transcript'])} chars):")
    print(result['transcript'][:500] + "..." if len(result['transcript']) > 500 else result['transcript'])
