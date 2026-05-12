from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class NormalizedEntry(BaseModel):
    source_type: str  # 'text', 'voice', 'image', 'url'
    original_text: Optional[str] = None
    transcription: Optional[str] = None
    extracted_text: Optional[str] = None
    image_description: Optional[str] = None
    url: Optional[str] = None
    timestamp: datetime
    
    @property
    def core_content(self) -> str:
        return self.extracted_text or self.transcription or self.image_description or self.original_text or ""