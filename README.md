<!--BEGIN_BANNER_IMAGE-->

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="/.github/banner_dark.png">
  <source media="(prefers-color-scheme: light)" srcset="/.github/banner_light.png">
  <img style="width:100%;" alt="The LiveKit icon, the name of the repository and some sample code in the background." src="https://raw.githubusercontent.com/livekit/agents/main/.github/banner_light.png">
</picture>

<!--END_BANNER_IMAGE-->

<br /><br />
Looking for the JS/TS library? Check out [AgentsJS](https://github.com/livekit/agents-js)

## ✨ 1.0 release ✨

This README reflects the 1.0 release. For documentation on the previous 0.x release, see the [0.x branch](https://github.com/livekit/agents/tree/0.x)

## What is Agents?

<!--BEGIN_DESCRIPTION-->

The **Agents framework** enables you to build voice AI agents that can see, hear, and speak in realtime. It provides a fully open-source platform for creating server-side agentic applications.

<!--END_DESCRIPTION-->

## Features

- **Flexible integrations**: A comprehensive ecosystem to mix and match the right STT, LLM, TTS, and Realtime API to suit your use case.
- **Integrated job scheduling**: Built-in task scheduling and distribution with [dispatch APIs](https://docs.livekit.io/agents/build/dispatch/) to connect end users to agents.
- **Extensive WebRTC clients**: Build client applications using LiveKit's open-source SDK ecosystem, supporting nearly all major platforms.
- **Telephony integration**: Works seamlessly with LiveKit's [telephony stack](https://docs.livekit.io/sip/), allowing your agent to make calls to or receive calls from phones.
- **Exchange data with clients**: Use [RPCs](https://docs.livekit.io/home/client/data/rpc/) and other [Data APIs](https://docs.livekit.io/home/client/data/) to seamlessly exchange data with clients.
- **Semantic turn detection**: Uses a transformer model to detect when a user is done with their turn, helps to reduce interruptions.
- **Open-source**: Fully open-source, allowing you to run the entire stack on your own servers, including [LiveKit server](https://github.com/livekit/livekit), one of the most widely used WebRTC media servers.

## Installation

To install the core Agents library, along with plugins for popular model providers:

```bash
pip install "livekit-agents[openai,silero,deepgram,cartesia,turn-detector]~=1.0"
```

## Docs and guides

Documentation on the framework and how to use it can be found [here](https://docs.livekit.io/agents/)

## Core concepts

- Agent: An LLM-based application with defined instructions.
- AgentSession: A container for agents that manages interactions with end users.
- entrypoint: The starting point for an interactive session, similar to a request handler in a web server.

## Usage

### Simple voice agent

---

```python
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import deepgram, openai, silero

@function_tool
async def lookup_weather(
    context: RunContext,
    location: str,
):
    """Used to look up weather information."""

    return {"weather": "sunny", "temperature": 70}


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    agent = Agent(
        instructions="You are a friendly voice assistant built by LiveKit.",
        tools=[lookup_weather],
    )
    session = AgentSession(
        vad=silero.VAD.load(),
        # any combination of STT, LLM, TTS, or realtime API can be used
        stt=deepgram.STT(model="nova-3"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=openai.TTS(voice="ash"),
    )

    await session.start(agent=agent, room=ctx.room)
    await session.generate_reply(instructions="greet the user and ask about their day")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
```

You'll need the following environment variables for this example:

- LIVEKIT_URL
- LIVEKIT_API_KEY
- LIVEKIT_API_SECRET
- DEEPGRAM_API_KEY
- OPENAI_API_KEY

### Multi-agent handoff

---

This code snippet is abbreviated. For the full example, see [multi_agent.py](examples/voice_agents/multi_agent.py)

```python
...
class IntroAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=f"You are a story teller. Your goal is to gather a few pieces of information from the user to make the story personalized and engaging."
            "Ask the user for their name and where they are from"
        )

    async def on_enter(self):
        self.session.generate_reply(instructions="greet the user and gather information")

    @function_tool
    async def information_gathered(
        self,
        context: RunContext,
        name: str,
        location: str,
    ):
        """Called when the user has provided the information needed to make the story personalized and engaging.

        Args:
            name: The name of the user
            location: The location of the user
        """

        context.userdata.name = name
        context.userdata.location = location

        story_agent = StoryAgent(name, location)
        return story_agent, "Let's start the story!"


class StoryAgent(Agent):
    def __init__(self, name: str, location: str) -> None:
        super().__init__(
            instructions=f"You are a storyteller. Use the user's information in order to make the story personalized."
            f"The user's name is {name}, from {location}"
            # override the default model, switching to Realtime API from standard LLMs
            llm=openai.realtime.RealtimeModel(voice="echo"),
            chat_ctx=chat_ctx,
        )

    async def on_enter(self):
        self.session.generate_reply()


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    userdata = StoryData()
    session = AgentSession[StoryData](
        vad=silero.VAD.load(),
        stt=deepgram.STT(model="nova-3"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=openai.TTS(voice="echo"),
        userdata=userdata,
    )

    await session.start(
        agent=IntroAgent(),
        room=ctx.room,
    )
...
```

## Examples

<table>
<tr>
<td width="50%">
<h3>🎙️ Starter Agent</h3>
<p>A starter agent optimized for voice conversations.</p>
<p>에이전트 기본 클래스, 세션 컨테이너, 컨텍스트 등 핵심 컴포넌트와 플러그인 사용법을 보여주는 기본 예제입니다.</p>
<p>
<a href="examples/voice_agents/basic_agent.py">Code</a>
</p>
</td>
<td width="50%">
<h3>🔄 Multi-user push to talk</h3>
<p>Responds to multiple users in the room via push-to-talk.</p>
<p>다중 참가자 환경에서 Push-to-Talk 방식으로 사용자의 발화를 수동 제어하는 예제입니다.</p>
<p>
<a href="examples/voice_agents/push_to_talk.py">Code</a>
</p>
</td>
</tr>

<tr>
<td width="50%">
<h3>🎵 Background audio</h3>
<p>Background ambient and thinking audio to improve realism.</p>
<p>세션 중 배경음악과 효과음을 재생하여 현실감을 높이는 방법을 보여줍니다.</p>
<p>
<a href="examples/voice_agents/background_audio.py">Code</a>
</p>
</td>
<td width="50%">
<h3>🛠️ Dynamic tool creation</h3>
<p>Creating function tools dynamically.</p>
<p>실행 시점에 에이전트 도구를 동적으로 생성하고 업데이트하는 방법을 보여줍니다.</p>
<p>
<a href="examples/voice_agents/dynamic_tool_creation.py">Code</a>
</p>
</td>
</tr>

<tr>
<td width="50%">
<h3>☎️ Phone Caller</h3>
<p>Agent that makes outbound phone calls</p>
<p>
<a href="https://github.com/livekit-examples/outbound-caller-python">Code</a>
</p>
</td>
<td width="50%">
<h3>📋 Structured output</h3>
<p>Using structured output from LLM to guide TTS tone.</p>
<p>LLM의 구조화된 출력을 파싱하여 TTS의 톤, 감정 등을 제어하는 방법을 보여줍니다.</p>
<p>
<a href="examples/voice_agents/structured_output.py">Code</a>
</p>
</td>
</tr>

<tr>
<td width="50%">
<h3>🍽️ Restaurant ordering and reservations</h3>
<p>Full example of an agent that handles calls for a restaurant.</p>
<p>음성 기반 레스토랑 예약 및 주문 에이전트의 전체 워크플로우를 보여주는 예제입니다.</p>
<p>
<a href="examples/full_examples/restaurant_agent/">Code</a>
</p>
</td>
<td width="50%">
<h3>👁️ Gemini Live vision</h3>
<p>Full example (including iOS app) of Gemini Live agent that can see.</p>
<p>
<a href="https://github.com/livekit-examples/vision-demo">Code</a>
</p>
</td>
</tr>

<tr>
<td width="50%">
<h3>🕸️ Web Search Agent</h3>
<p>Agent that performs web searches using DuckDuckGo.</p>
<p>DuckDuckGo 검색 툴을 function_tool로 등록하여 웹 검색을 수행하고 결과를 음성으로 전달하는 예제입니다.</p>
<p>
<a href="examples/voice_agents/web_search.py">Code</a>
</p>
</td>
<td width="50%">
<h3>🌦️ Weather Agent</h3>
<p>Agent that fetches weather information using Open-Meteo API.</p>
<p>음성 명령으로 위치를 받아 Open-Meteo API에서 날씨 정보를 가져와 응답하는 예제입니다.</p>
<p>
<a href="examples/voice_agents/weather_agent.py">Code</a>
</p>
</td>
</tr>

<tr>
<td width="50%">
<h3>↔️ Toggle I/O</h3>
<p>Agent demonstrating toggling audio/text input/output via RPC.</p>
<p>RPC를 사용하여 에이전트의 오디오/텍스트 입출력을 실시간으로 토글하는 방법을 보여줍니다.</p>
<p>
<a href="examples/voice_agents/toggle_io.py">Code</a>
</p>
</td>
<td width="50%">
<h3>⏩ Speed Up Output Audio</h3>
<p>Agent demonstrating post-processing audio stream to adjust playback speed.</p>
<p>출력 오디오 스트림을 후처리하여 재생 속도를 조절하는 방법을 보여줍니다.</p>
<p>
<a href="examples/voice_agents/speedup_output_audio.py">Code</a>
</p>
</td>
</tr>

<tr>
<td width="50%">
<h3>🤫 Silent Function Call</h3>
<p>Agent demonstrating function calls without voice response.</p>
<p>함수 호출 시 별도의 음성 응답 없이 함수 실행만 수행하도록 구성하는 방법을 보여줍니다.</p>
<p>
<a href="examples/voice_agents/silent_function_call.py">Code</a>
</p>
</td>
<td width="50%">
<h3>⏱️ Realtime Turn Detector</h3>
<p>Agent combining LiveKit's Turn Detection with a realtime LLM.</p>
<p>LiveKit의 Turn Detection 모델과 실시간 LLM을 결합하여 사용하는 방법을 보여줍니다.</p>
<p>
<a href="examples/voice_agents/realtime_turn_detector.py">Code</a>
</p>
</td>
</tr>

<tr>
<td width="50%">
<h3>📜 Load Chat History (Realtime)</h3>
<p>Agent loading existing chat history into OpenAI Realtime model.</p>
<p>기존 대화 내역을 OpenAI Realtime 모델에 로드하여 세션을 시작하는 방법을 보여줍니다.</p>
<p>
<a href="examples/voice_agents/realtime_load_chat_history.py">Code</a>
</p>
</td>
<td width="50%">
<h3>🎭 Multi-Agent Storyteller</h3>
<p>Example of a multi-agent workflow for storytelling.</p>
<p>여러 에이전트를 사용하여 스토리텔링 워크플로우를 구성하는 방법을 보여줍니다.</p>
<p>
<a href="examples/voice_agents/multi_agent.py">Code</a>
</p>
</td>
</tr>

<tr>
<td width="50%">
<h3>📞 Error Callback & SIP Transfer</h3>
<p>Agent demonstrating error/close callbacks and SIP participant transfer.</p>
<p>오류/종료 콜백을 사용하여 맞춤 오류 메시지 재생 및 SIP 참가자 전송을 처리하는 방법을 보여줍니다.</p>
<p>
<a href="examples/voice_agents/error_callback.py">Code</a>
</p>
</td>
<td width="50%">
<h3>✍️ Annotated Tool Arguments</h3>
<p>Agent demonstrating generating tool argument descriptions using type hints.</p>
<p>타입 힌트, Pydantic Field, docstring을 활용하여 LLM 함수 호출 시 인수 설명을 자동 생성하는 방법을 보여줍니다.</p>
<p>
<a href="examples/voice_agents/annotated_tool_args.py">Code</a>
</p>
</td>
</tr>

<tr>
<td width="50%">
<h3>📹 Gemini Vision Agent (Track Sub)</h3>
<p>Agent using Gemini Live API for voice and video analysis (track subscription).</p>
<p>Gemini Live API를 사용하여 음성 대화 및 참가자 비디오를 실시간 분석하는 예제 (트랙 구독 방식).</p>
<p>
<a href="examples/vision_agents/basic_agent_gemini.py">Code</a>
</p>
</td>
<td width="50%">
<h3>📹 Gemini Vision Agent (Video Input)</h3>
<p>Agent using Gemini Live API for voice and video analysis (session.video_input).</p>
<p>Gemini Live API를 사용하여 음성 대화 및 참가자 비디오를 실시간 분석하는 예제 (session.video_input 방식).</p>
<p>
<a href="examples/vision_agents/basic_agent_gemini_2.py">Code</a>
</p>
</td>
</tr>

<tr>
<td width="50%">
<h3>💬 Text-Only Agent</h3>
<p>Agent configured using only text streams.</p>
<p>텍스트 스트림만 사용하여 에이전트를 구성하는 방법을 보여줍니다.</p>
<p>
<a href="examples/other/text_only.py">Code</a>
</p>
</td>
<td width="50%">
<h3>🗣️ Kokoro TTS Agent</h3>
<p>Agent demonstrating usage of Kokoro-FastAPI TTS with LiveKit Agents.</p>
<p>Kokoro-FastAPI의 OpenAI 호환 TTS 모델을 사용하는 방법을 보여줍니다.</p>
<p>
<a href="examples/other/kokoro_tts.py">Code</a>
</p>
</td>
</tr>

<tr>
<td width="50%">
<h3>👂 Datastream Chat Listener</h3>
<p>Chat listener example using LiveKit TextStream.</p>
<p>LiveKit TextStream을 사용하여 채팅 및 전사 메시지를 수신하고 콘솔에 출력하는 리스너 예제입니다.</p>
<p>
<a href="examples/other/datastream-chat-listener.py">Code</a>
</p>
</td>
<td width="50%">
<h3>⚡ Fast Pre-response Agent</h3>
<p>Agent generating quick pre-responses (silence fillers).</p>
<p>사용자 입력에 대해 빠른 사전 응답(침묵 채우기)을 생성하는 예제입니다.</p>
<p>
<a href="examples/voice_agents/fast-preresponse.py">Code</a>
</p>
</td>
</tr>

<tr>
<td width="50%">
<h3>🔩 Raw Function Description Agent</h3>
<p>Agent demonstrating usage of raw function tools with OpenAI API.</p>
<p>Raw function tool을 사용하여 OpenAI API 함수 호출 기능을 활용하는 방법을 보여줍니다.</p>
<p>
<a href="examples/voice_agents/raw_function_description.py">Code</a>
</p>
</td>
<td width="50%">
<h3>🌐 Browser Track Publisher</h3>
<p>Publishing browser page rendering as a video track.</p>
<p>브라우저 플러그인을 사용하여 페이지 렌더링을 비디오 트랙으로 퍼블리시하는 예제입니다.</p>
<p>
<a href="examples/other/browser/browser_track.py">Code</a>
</p>
</td>
</tr>

<tr>
<td width="50%">
<h3>🗣️ Echo Agent</h3>
<p>Agent that echoes user's speech back to them using VAD.</p>
<p>VAD를 사용하여 사용자 발화를 감지하고 그대로 다시 재생하는 에코 에이전트 예제입니다.</p>
<p>
<a href="examples/other/echo-agent/echo-agent.py">Code</a>
</p>
</td>
<td width="50%">
<h3>🛡️ Hive Moderation Agent</h3>
<p>Agent performing visual content moderation using Hive API.</p>
<p>Hive API를 사용하여 시각적 콘텐츠를 검열하는 에이전트 예제입니다.</p>
<p>
<a href="examples/other/hive-moderation-agent/">Code</a>
</p>
</td>
</tr>

<tr>
<td width="50%">
<h3>👥 Participant Entrypoint</h3>
<p>Example demonstrating adding participant-specific entrypoints.</p>
<p>각 참가자에 대해 개별 작업을 실행하는 진입점을 추가하는 방법을 보여주는 예제입니다.</p>
<p>
<a href="examples/other/participant-entrypoint/">Code</a>
</p>
</td>
<td width="50%">
<h3>🎨 Simple Color Video Agent</h3>
<p>Agent publishing a video track filled with changing solid colors.</p>
<p>단색으로 채워지고 주기적으로 색상이 변경되는 비디오 트랙을 퍼블리시하는 에이전트 예제입니다.</p>
<p>
<a href="examples/other/simple-color/">Code</a>
</p>
</td>
</tr>

<tr>
<td width="50%">
<h3>🎤 Standalone STT Transcriber</h3>
<p>Standalone speech-to-text transcriber agent.</p>
<p>참가자의 오디오 트랙을 구독하여 실시간으로 전사하는 독립적인 STT 에이전트 예제입니다.</p>
<p>
<a href="examples/other/speech-to-text/">Code</a>
</p>
</td>
<td width="50%">
<h3>🔊 Text-to-Speech Examples</h3>
<p>Examples using various TTS plugins (OpenAI, Neuphonic, Cartesia, ElevenLabs).</p>
<p>다양한 TTS 플러그인(OpenAI, Neuphonic, Cartesia, ElevenLabs) 사용법 및 동기화된 전사 출력 예제입니다.</p>
<p>
<a href="examples/other/text-to-speech/">Code</a>
</p>
</td>
</tr>

<tr>
<td width="50%">
<h3>📻 Audio Datastream Examples</h3>
<p>Examples for sending and receiving audio via datastreams.</p>
<p>오디오 데이터를 데이터스트림으로 전송하고 수신하는 방법을 보여주는 예제입니다.</p>
<p>
<a href="examples/other/datastream-audio/">Code</a>
</p>
</td>
<td width="50%">
<h3>📚 LlamaIndex RAG Examples</h3>
<p>Examples integrating LlamaIndex for Retrieval-Augmented Generation.</p>
<p>LlamaIndex를 사용하여 RAG(검색 증강 생성)를 구현하는 방법을 보여주는 예제입니다.</p>
<p>
<a href="examples/voice_agents/llamaindex-rag/">Code</a>
</p>
</td>
</tr>

<tr>
<td width="50%">
<h3>🧑‍💻 Browser Standalone App</h3>
<p>Standalone application example using the browser plugin.</p>
<p>브라우저 플러그인을 사용하는 독립 실행형 애플리케이션 예제입니다.</p>
<p>
<a href="examples/other/browser/standalone_app.py">Code</a>
</p>
</td>
<td width="50%">
<h3>👤 Avatar Agents Examples</h3>
<p>Examples integrating various avatar technologies (Tavus, Bey, BitHuman, Audio Wave Viz).</p>
<p>다양한 아바타 기술(Tavus, Bey, BitHuman, 오디오 파형 시각화) 연동 예제입니다.</p>
<p>
<a href="examples/avatar_agents/">Code</a>
</p>
</td>
</tr>

</table>

## Running your agent

### Testing in terminal

```shell
python myagent.py console
```

Runs your agent in terminal mode, enabling local audio input and output for testing.
This mode doesn't require external servers or dependencies and is useful for quickly validating behavior.

### Developing with LiveKit clients

```shell
python myagent.py dev
```

Starts the agent server and enables hot reloading when files change. This mode allows each process to host multiple concurrent agents efficiently.

The agent connects to LiveKit Cloud or your self-hosted server. Set the following environment variables:
- LIVEKIT_URL
- LIVEKIT_API_KEY
- LIVEKIT_API_SECRET

You can connect using any LiveKit client SDK or telephony integration.
To get started quickly, try the [Agents Playground](https://agents-playground.livekit.io/).

### Running for production

```shell
python myagent.py start
```

Runs the agent with production-ready optimizations.

## Contributing

The Agents framework is under active development in a rapidly evolving field. We welcome and appreciate contributions of any kind, be it feedback, bugfixes, features, new plugins and tools, or better documentation. You can file issues under this repo, open a PR, or chat with us in LiveKit's [Slack community](https://livekit.io/join-slack).

<!--BEGIN_REPO_NAV-->

<br/><table>

<thead><tr><th colspan="2">LiveKit Ecosystem</th></tr></thead>
<tbody>
<tr><td>LiveKit SDKs</td><td><a href="https://github.com/livekit/client-sdk-js">Browser</a> · <a href="https://github.com/livekit/client-sdk-swift">iOS/macOS/visionOS</a> · <a href="https://github.com/livekit/client-sdk-android">Android</a> · <a href="https://github.com/livekit/client-sdk-flutter">Flutter</a> · <a href="https://github.com/livekit/client-sdk-react-native">React Native</a> · <a href="https://github.com/livekit/rust-sdks">Rust</a> · <a href="https://github.com/livekit/node-sdks">Node.js</a> · <a href="https://github.com/livekit/python-sdks">Python</a> · <a href="https://github.com/livekit/client-sdk-unity">Unity</a> · <a href="https://github.com/livekit/client-sdk-unity-web">Unity (WebGL)</a></td></tr><tr></tr>
<tr><td>Server APIs</td><td><a href="https://github.com/livekit/node-sdks">Node.js</a> · <a href="https://github.com/livekit/server-sdk-go">Golang</a> · <a href="https://github.com/livekit/server-sdk-ruby">Ruby</a> · <a href="https://github.com/livekit/server-sdk-kotlin">Java/Kotlin</a> · <a href="https://github.com/livekit/python-sdks">Python</a> · <a href="https://github.com/livekit/rust-sdks">Rust</a> · <a href="https://github.com/agence104/livekit-server-sdk-php">PHP (community)</a> · <a href="https://github.com/pabloFuente/livekit-server-sdk-dotnet">.NET (community)</a></td></tr><tr></tr>
<tr><td>UI Components</td><td><a href="https://github.com/livekit/components-js">React</a> · <a href="https://github.com/livekit/components-android">Android Compose</a> · <a href="https://github.com/livekit/components-swift">SwiftUI</a></td></tr><tr></tr>
<tr><td>Agents Frameworks</td><td><b>Python</b> · <a href="https://github.com/livekit/agents-js">Node.js</a> · <a href="https://github.com/livekit/agent-playground">Playground</a></td></tr><tr></tr>
<tr><td>Services</td><td><a href="https://github.com/livekit/livekit">LiveKit server</a> · <a href="https://github.com/livekit/egress">Egress</a> · <a href="https://github.com/livekit/ingress">Ingress</a> · <a href="https://github.com/livekit/sip">SIP</a></td></tr><tr></tr>
<tr><td>Resources</td><td><a href="https://docs.livekit.io">Docs</a> · <a href="https://github.com/livekit-examples">Example apps</a> · <a href="https://livekit.io/cloud">Cloud</a> · <a href="https://docs.livekit.io/home/self-hosting/deployment">Self-hosting</a> · <a href="https://github.com/livekit/livekit-cli">CLI</a></td></tr>
</tbody>
</table>
<!--END_REPO_NAV-->
