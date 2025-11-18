
## Real-Time Interruptible Voice Agent 

For this task I have made a coppy of basic_agent.py and worked on it.
No modifications were made to the underlying LiveKit SDK. All logic is contained within the updated example files.

---
## What Changed

### New modules and logic

The following changes were added inside `examples/voiceagent/`:

* `interrupt_filter.py`
    See [interrupt_filter.py](examples/voice_agents/interrupt_filter.py)

  * Filters ASR transcripts in real time.
  * Distinguishes between filler-only segments and meaningful interruptions.
  * Exposes two environment-driven lists: `IGNORED_WORDS` and `INTERRUPT_WORDS`.
  * Logs ignored fillers vs. accepted interruptions separately.

* `real_interrupt_agent.py`
    See [real_interrupt_agent.py](examples/voice_agents/real_interrupt_agent.py)

  * Integrates the filter into the LiveKit event loop.
  * Over writes on_user_turn_completed() fn to make this happen.
  * Ensures filler words do not pause TTS when the agent is speaking.
  * Ensures legitimate commands (example: "stop", "wait", "hold on") interrupt immediately.
  * Adds state management for agent-speaking vs user-speaking conditions.

No LiveKit SDK files were modified.
Only example files under `examples/voiceagent/` were changed.

---

## Required Environment Variables

To run the agent, set the following variables:
```
LIVEKIT_URL=wss://<your-url>
LIVEKIT_API_KEY=<your-key>
LIVEKIT_API_SECRET=<your-secret>

DEEPGRAM_API_KEY=<asr-key>
GROQ_API_KEY=<groq-key>

IGNORED_WORDS=uh,umm,hmm,haan,yeah
INTERRUPT_WORDS=stop,wait,hold on
```

All values must be present in the environment before starting the agent.

---

## What Works

The following behavior has been tested and verified:

* The agent pauses for half a second(cannot be fixed without altering vad) and then continues speaking when encountering filler-only segments (e.g., "uh", "umm", "hmm", "haan").
* The same fillers are still registered as speech when the agent is silent.
* Legitimate user interruptions immediately stop TTS.
* Mixed segments containing both filler and real command (e.g. "uh okay stop") correctly trigger interruption.
* Logging clearly distinguishes ignored fillers, accepted interruptions, and normal speech.
* No detectable latency added to LiveKit's speech event loop for interrupt and about 0.5 sec for ignore.

---

## Known Issues

* There is visible latency when ignoring a keyword.
* The system depends on the accuracy and timeliness of the transcription provider.
* Dynamic updates to the ignored-word list are present but not fully integrated in this branch.

---

