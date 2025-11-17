import asyncio
from livekit.agents import Agent, AgentSession
from livekit.agents.stt import SpeechEvent, SpeechEventType, SpeechData
from interrupt_filter import InterruptFilter, InterruptFilterConfig, ConversationState, InterruptDecision


class InterruptAwareAgent(Agent):
    def __init__(self):
        super().__init__(instructions="Test interruption logic integration.")
        self.state = ConversationState()
        self.filter = InterruptFilter(
            InterruptFilterConfig(
                ignored_words=["uh", "uhh","umm", "um", "hmm", "haan", "huh", "hmmmmm", "hmmm", "ah", "oh", "hmmhmm", "mmm", "mm", "eh", "arey", "accha", "acha", "haanji"],
                interrupt_keywords=["stop", "wait", "hold on", "hold", "pause", "one sec", "one second", "no", "not that", "listen"],
                min_confidence=0.5,
            ),
            self.state,
        )

    async def on_tts_started(self):
        await self.state.set_speaking(True)
        print("tts started")

    async def on_tts_finished(self):
        await self.state.set_speaking(False)
        print("tts finished")

    async def on_transcription(self, text, is_final, confidence):
        print(f"stt: {text} (conf={confidence:.2f}, final={is_final})")
        decision = self.filter.decide(text, confidence)

        if decision == InterruptDecision.IGNORE:
            print("decision: ignore")
            return None

        if decision == InterruptDecision.INTERRUPT:
            print("decision: interrupt (would stop tts)")
            return text

        print("decision: allow")
        return text


async def simulate_transcription(agent: InterruptAwareAgent):
    while True:
        txt = input("\nYou (type STT text): ").strip()
        if txt == "exit":
            break
        event = SpeechEvent(type=SpeechEventType.FINAL_SPEECH, speech=SpeechData(text=txt, confidence=1.0))
        await agent.on_transcription(text=event.speech.text, is_final=True, confidence=event.speech.confidence)


async def main():
    agent = InterruptAwareAgent()
    session = AgentSession(stt=None, llm=None, tts=None, vad=None)
    session._agent = agent
    session._interrupt_filter = agent.filter
    session._interrupt_state = agent.state

    print("commands: 'agent on', 'agent off', any text for stt, 'exit'")

    while True:
        command = input("\n> ").strip()
        if command == "exit":
            break
        if command == "agent on":
            await agent.on_tts_started()
            continue
        if command == "agent off":
            await agent.on_tts_finished()
            continue
        await session._agent.on_transcription(command, True, 1.0)


if __name__ == "__main__":
    asyncio.run(main())