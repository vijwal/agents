import logging
import asyncio
from dotenv import load_dotenv
import string

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RunContext,
    cli,
    metrics,
    room_io,
    llm,
    AgentStateChangedEvent,
    UserInputTranscribedEvent,
)
import os
from livekit.agents.llm import function_tool, StopResponse
from livekit.plugins import silero, groq, cartesia

logger = logging.getLogger("basic-agent")
logger.setLevel(logging.INFO)
load_dotenv()

from interrupt_filter import InterruptFilter, InterruptFilterConfig, ConversationState, InterruptDecision

def load_list(name: str):
    raw = os.getenv(name, "")
    return [w.strip().lower() for w in raw.split(",") if w.strip()]


IGNORED_WORDS = load_list("IGNORED_WORDS")
INTERRUPT_WORDS = load_list("INTERRUPT_WORDS")
class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="Your name is Kelly. You would interact with users via voice. "
                         "Keep your responses concise. "
                         "You are curious and friendly, and have a sense of humor.",
        )
        self.state = ConversationState()
        self.filter = InterruptFilter(
            InterruptFilterConfig(
                ignored_words=IGNORED_WORDS,
                interrupt_keywords=INTERRUPT_WORDS,
                min_confidence=0.5,
            ),
            self.state,
        )

    async def on_enter(self):
        logger.info("Agent session initialized")
        self.session.generate_reply()

    async def on_user_turn_completed(self, turn_ctx: llm.ChatContext, new_message: llm.ChatMessage):
        text = new_message.text_content or ""
        confidence = getattr(new_message, "transcript_confidence", 1.0)

        logger.info(f"[INTERCEPT] User final transcript: '{text}'")

        decision = self.filter.decide(text, confidence)

        if decision == InterruptDecision.IGNORE:
            logger.info("[INTERCEPT] Decision: IGNORE ")
            return None

        if decision == InterruptDecision.INTERRUPT:
            logger.info("[INTERCEPT] Decision: INTERRUPT")

            clean_text = text.strip(string.punctuation).lower()

            if any(cmd in clean_text for cmd in self.filter.config.interrupt_keywords):
                logger.info("[INTERCEPT] User explicitly requested silence")
                self.session.interrupt()
                logger.info("[INTERCEPT] Interrupt applied successfully")
                raise StopResponse()

        logger.info("[INTERCEPT] Decision: ALLOW (processing user turn)")
        await super().on_user_turn_completed(turn_ctx, new_message)

    @function_tool
    async def lookup_weather(
        self,
        context: RunContext,
        location: str,
        latitude: str | None = None,
        longitude: str | None = None
    ):
        return f"It is sunny in {location} with a temperature of 70 degrees."


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}
    logger.info(f"Connected to room: {ctx.room.name}")

    session = AgentSession(
        stt="deepgram/nova-3",
        llm=groq.LLM(model="llama-3.1-8b-instant"),
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        vad=ctx.proc.userdata["vad"],
        min_interruption_words=1,
        preemptive_generation=False,
    )

    agent = MyAgent()

    @session.on("agent_state_changed")
    def on_agent_state(ev: AgentStateChangedEvent):
        if ev.new_state == "speaking":
            asyncio.create_task(agent.state.set_speaking(True))
            logger.info("[TTS] Agent started speaking")
        elif ev.new_state in ("listening", "thinking") and ev.old_state == "speaking":
            asyncio.create_task(agent.state.set_speaking(False))
            logger.info("[TTS] Agent stopped speaking")

    @session.on("user_input_transcribed")
    def on_user_transcript(ev: UserInputTranscribedEvent):
        if not ev.is_final:
            text = ev.transcript.lower()
            if any(cmd in text for cmd in INTERRUPT_WORDS):
                if agent.state.is_speaking():
                    logger.info(f"[PARTIAL] Hard interrupt requested based on partial transcript: '{text}'")
                    session.interrupt()

    await session.start(agent=agent, room=ctx.room)


if __name__ == "__main__":
    cli.run_app(server)
