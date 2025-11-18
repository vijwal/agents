import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import List
import asyncio
import string

logger = logging.getLogger(__name__)


class InterruptDecision(Enum):
    IGNORE = "ignore"
    ALLOW = "allow"
    INTERRUPT = "interrupt"


@dataclass
class InterruptFilterConfig:
    ignored_words: List[str] = field(default_factory=list)
    interrupt_keywords: List[str] = field(default_factory=lambda: ["stop", "wait"])
    min_confidence: float = 0.5


class ConversationState:
    def __init__(self):
        self._speaking = False
        self._lock = asyncio.Lock()

    async def set_speaking(self, value: bool):
        async with self._lock:
            self._speaking = value

    def is_speaking(self) -> bool:
        return self._speaking


class InterruptFilter:
    def __init__(self, config: InterruptFilterConfig, state: ConversationState):
        self.config = config
        self.state = state

    def decide(self, text: str, confidence: float = 1.0) -> InterruptDecision:
        if not text:
            return InterruptDecision.IGNORE

        text_norm = text.lower().strip()
        tokens = [t.strip(string.punctuation) for t in text_norm.split()]

        if all(t in self.config.ignored_words for t in tokens):
            logger.info(f"Ignoring filler: {text}")
            return InterruptDecision.IGNORE

        if any(t in self.config.interrupt_keywords for t in tokens):
            logger.info(f"Detected interruption keyword: {text}")
            return InterruptDecision.INTERRUPT

        if not self.state.is_speaking():
            return InterruptDecision.ALLOW

        if confidence < self.config.min_confidence:
            logger.info(f"Ignoring low-confidence: '{text}'")
            return InterruptDecision.IGNORE

        return InterruptDecision.INTERRUPT

    def decide_sync(self, text, confidence):
        return asyncio.get_event_loop().run_until_complete(
            self.decide(text, confidence)
        )

    def add_ignored_word(self, word: str):
        w = word.strip().lower()
        if w not in self.config.ignored_words:
            self.config.ignored_words.append(w)

    def update_ignored_words(self, new_list: List[str]):
        self.config.ignored_words = [w.strip().lower() for w in new_list]