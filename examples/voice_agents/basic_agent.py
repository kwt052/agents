import logging
import os

from dotenv import load_dotenv

from livekit.agents import (
    Agent,            # 에이전트 기반 클래스: 시스템 프롬프트와 챗 컨텍스트를 관리하며 대화 흐름 제어
    AgentSession,     # 에이전트 세션 컨테이너: STT, TTS, LLM, VAD 연결 및 LiveKit 룸 입출력 통합 관리
    JobContext,       # 작업 컨텍스트: 방 정보, 유저 데이터, shutdown callback 등록 등 세션 실행 환경 제공
    JobProcess,       # 프로세스 초기화 컨텍스트: prewarm 시 모델 로딩 결과(proc.userdata) 공유에 사용
    RoomInputOptions, # 룸 입장 시 입력 스트림 옵션 설정(마이크, 카메라 트랙, 노이즈 캔슬 등)
    RoomOutputOptions,# 룸 입장 시 출력 옵션 설정(자막 활성화, 오디오/비디오 트랙 옵션)
    RunContext,       # function_tool 호출 시 전달되는 컨텍스트: 로그, userdata 접근, 업데이트 지원
    WorkerOptions,    # 워커 실행 옵션: entrypoint, prewarm 함수, LiveKit URL/API 키/시크릿 설정
    cli,              # CLI 실행기: python 스크립트를 명령행 도구로 동작시키기 위한 래퍼
    metrics,          # 메트릭 유틸리티: 모델 사용량, 토큰 수집과 로깅 기능 제공
)
from livekit.agents.llm import function_tool  # LLM 함수 호출 기능을 데코레이터로 등록
from livekit.agents.voice import MetricsCollectedEvent  # 음성 대화 중 수집된 메트릭 이벤트 타입
from livekit.plugins import deepgram, openai, silero  # STT(Deepgram), LLM/TTS(OpenAI), VAD(Silero) 플러그인
from livekit.plugins.turn_detector.multilingual import MultilingualModel  # 다국어 턴 감지 모델(semantic VAD)
from livekit.agents.voice.events import UserInputTranscribedEvent, ConversationItemAddedEvent

# 배경 음성/노이즈 캔슬링 활성화를 위해서는 주석을 해제 하십시오.
# 현재는 Linux와 MacOS에서만 지원됩니다.
# from livekit.plugins import noise_cancellation

logger = logging.getLogger("basic-agent")

# --- 대화 로그 파일 설정 ---
# 로그 저장 디렉터리를 미리 생성합니다. 이미 존재할 경우 에러 없이 넘어갑니다.
os.makedirs("basic_agent_log", exist_ok=True)
# 파일 로거(dialogue_logger) 객체 생성 및 로그 레벨 설정
# INFO 레벨 이상의 메시지를 기록합니다.
file_logger = logging.getLogger("dialogue_logger")
file_logger.setLevel(logging.INFO)
# 파일 핸들러 추가: 로그를 basic_agent_log/dialogue.log 에 UTF-8 인코딩으로 기록
fh = logging.FileHandler("basic_agent_log/dialogue.log", encoding="utf-8")
# 로그 메시지 포맷 설정: 타임스탬프와 메시지 내용만 남깁니다.
fh.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
file_logger.addHandler(fh)
file_logger.propagate = False

load_dotenv()


class MyAgent(Agent):
    """
    실제 사용자의 의도에 따라 동작할 에이전트 정의 클래스.
    Agent 생성자에 전달한 instructions가 '시스템 메시지'로 LLM에게 주입됩니다.
    """
    def __init__(self) -> None:
        # “시스템 메시지”로 LLM 컨텍스트에 한 번만 주입됩니다.
        # 에이전트 전체 대화의 행위 양식(톤·스타일·언어 등)을 정의하는 전역 가이드라인 역할
        super().__init__(
            instructions=(
                "모든 대화는 한글로 진행됩니다."
                "당신의 이름은 태식이 입니다.당신은 사용자와 음성 대화를 합니다."
                "대화를 할 때는 친구처럼 친근하게 대화를 진행합니다."
            ),
        )

    async def on_enter(self):
        """
        세션이 시작되어 에이전트가 룸에 들어온 직후 호출됩니다.
        초기 인사 및 질문을 자동으로 생성하도록 지시합니다.
        """
        self.session.generate_reply(
            instructions="당신은 먼저 반갑게 인사하며 자신의 이름을 밝힌 후, 상대방의 이름을 물어보며 대화를 시작합니다."
        )

    @function_tool
    async def lookup_weather(
        self,
        context: RunContext,
        location: str,
        latitude: str,
        longitude: str,
    ):
        """
        @function_tool 데코레이터를 통해 LLM이 호출할 수 있는 툴로 등록됩니다.
        사용자가 날씨를 물어보면 이 함수가 호출되어 실제 정보를 반환하는 역할을 합니다.

        Args:
            location: 사용자가 요청한 지역
            latitude: 위도 (LLM이 추정해서 전달 가능)
            longitude: 경도 (LLM이 추정해서 전달 가능)
        """
        logger.info(f"Looking up weather for {location}")
        # 실제 외부 API 호출 대신 예시 데이터 반환
        return {
            "weather": "sunny",
            "temperature": 70,
            "location": location,
        }


def prewarm(proc: JobProcess):
    """
    워커 프로세스 초기화(prewarm) 단계에 단 한번만 호출됩니다.
    세션마다 반복되지 않아도 되는 모든 무거운 초기화 작업을 proc.userdata에 저장합니다.
    예를 들어,silero.VAD 모델을 미리 로드하여 이후 STT 스트림 처리 시 로딩 비용을 절감합니다.
    """
    pass
    # realtime 모델 사용 시 VAD 모델을 별도로 사용 안함.
    # proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    """
    각 참가자(세션)에 대해 실행되는 진입점 함수입니다.
    LiveKit 서버로부터 “실제 참가자(사용자)가 방(room)에 들어왔다”는 할당(job)을 받을 때마다, 참가자 1명당 한 번씩 실행됩니다.
    - LiveKit 서버 접속
    - AgentSession 생성
    - 메트릭 수집 설정
    - 참가자 조인 대기 → 세션 시작
    """
    # 로그에 room, user_id를 자동 포함하도록 설정. 여기서 user_id는 agent를 호출한 사용자의 고유 ID입니다.
    # 로깅 포맷터(Formatter)에서 %(room)s 또는 %(user_id)s를 지정해 두면, 이 필드들이 자동으로 출력됩니다.
    # 정리하자면, ctx.log_context_fields에 원하는 키·값을 할당하면 그 이후 생성되는 모든 로그 레코드에 해당 키·값이 주입(injection)되어, 
    # 로그 메시지나 JSON 출력을 할 때 손쉽게 메타데이터(룸 이름, 사용자 ID, 워커 ID 등)를 포함시킬 수 있습니다.
    ctx.log_context_fields = {
        "room": ctx.room.name,
        "user_id": ctx.job.participant.identity
    }
    # Agent가 LiveKit 서버에 연결
    # e2ee 종단간 암호화, 룸 내 원격 트랙(오디오/비디오)을 자동으로 구독(subscribe)설정 가능. 기본값은 암호화 비활성화, 오디오·비디오 모두 구독
    # (예시) await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    # 이때, auto_subscribe 옵션은 LiveKit SFU 수준에서 “원격 참가자가 퍼블리시하는 오디오/비디오 트랙을 자동으로 구독(subscribe)할 것인가”를 결정
    # 이는 아래 코드에서 나오는 RoomInputOptions(audio_enabled=False) 옵션과는 다른 개념
    # RoomInputOptions은 Agent 세션 수준에서 구독된 미디어 데이터를 실제로 llm 파이프 라인에 넘길지, 텍스트 스트림을 활성화할지 결정
    await ctx.connect()

    # AgentSession 생성: STT, LLM, TTS, 턴 감지 구성
    session = AgentSession(
        # ① VAD 컴포넌트: prewarm()에서 로드한 silero.VAD
        # vad=ctx.proc.userdata["vad"],

        # ② Realtime API 한 줄로 STT/TTS/VAD/턴 감지 통합
        llm=openai.realtime.RealtimeModel(),

        # 개별 세팅을 원한다면 아래 주석 해제
        # stt=deepgram.STT(model="nova-3", language="multi"),
        # tts=openai.TTS(voice="ash"),
        # turn_detection=MultilingualModel(),
    )

    # --- 사용자 STT 자막 로깅 이벤트 ---

    # 여기서 "user_input_transcribed"과 같은 것은 미리 정의된 이벤트 이름입니다.
    # 다음과 같은 종류가 있습니다.
    # user_input_transcribed: 사용자의 STT 자막이 도착했을 때(UserInputTranscribedEvent)
    # conversation_item_added: 챗 컨텍스트에 메시지(유저/에이전트)가 추가될 때(ConversationItemAddedEvent)
    # function_tools_executed: 함수 호출(function tool) 처리 완료 후 발생(FunctionToolsExecutedEvent)
    # metrics_collected: STT, LLM, TTS, VAD 등 각종 메트릭 수집 시(MetricsCollectedEvent)
    # speech_created: 에이전트의 발화(SpeechHandle) 생성 직후 발생(SpeechCreatedEvent)
    # agent_state_changed: 에이전트 내부 상태 변경 시(Initializing→Listening→Thinking→Speaking)(AgentStateChangedEvent)
    # user_state_changed: VAD 기준으로 사용자의 음성 상태 변경 시(UserStateChangedEvent)
    # close: 세션이 종료되었을 때(CloseEvent)
    # 추가로, 오류 발생 시 error 이벤트(ErrorEvent)를 통해 recoverable 여부 등을 구독할 수 있습니다

    # 서버측 STT가 변환한 자막 중 최종 결과(ev.is_final=True)만 파일에 기록합니다.
    @session.on("user_input_transcribed")
    def _log_user(ev: UserInputTranscribedEvent):
        if ev.is_final:
            file_logger.info(f"USER: {ev.transcript}")

    # --- 에이전트 챗 메시지 로깅 이벤트 ---
    # AI 에이전트의 assistant 역할 메시지를 text_content로 추출해 기록합니다.
    @session.on("conversation_item_added")
    def _log_agent(ev: ConversationItemAddedEvent):
        """Assistant 역할의 챗 메시지를 파일에 기록합니다."""
        msg = ev.item
        # role은 Literal['developer','system','user','assistant']
        if msg.role == "assistant":
            # text_content는 content 내 문자열을 줄바꿈으로 반환
            text = msg.text_content or ""
            file_logger.info(f"AGENT: {text}")

    # 메트릭 수집기 생성
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        """
        세션 중 발생하는 메트릭 이벤트마다 호출됩니다.
        - metrics.log_metrics: 실시간 로깅
        - usage_collector.collect: 최종 요약 수집
        """
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        """세션 종료 시 최종 사용량 요약을 로그로 출력합니다."""
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    # 세션 종료(shutdown) 시 log_usage 호출 등록
    ctx.add_shutdown_callback(log_usage)

    # 사용자가 방에 들어올 때까지 대기
    await ctx.wait_for_participant()

    # 세션 시작
    await session.start(
        agent=MyAgent(),           # MyAgent 인스턴스
        room=ctx.room,             # LiveKit 룸 객체
        room_input_options=RoomInputOptions(

            # RoomInputOptions 은 AgentSession.start() 호출 시 전달되어, 
            # 룸으로부터 구독된 미디어를 에이전트 내부로 어떻게 흘려보낼지 제어합니다.
            # 기본값은 아래와 같습니다.

            # text_enabled: bool = True          # 텍스트(채팅) 입력 수신 여부
            # audio_enabled: bool = True         # 오디오 입력 수신 여부
            # video_enabled: bool = False        # 비디오 입력 수신 여부
            # audio_sample_rate: int = 24000     # 오디오 샘플링 레이트(Hz)
            # audio_num_channels: int = 1        # 오디오 채널 수
            # noise_cancellation: rtc.NoiseCancellationOptions | None = None  
                                        # 필요시 노이즈 캔슬링 옵션 (없으면 None), 현재는 linux, macos에서만 지원
            # text_input_cb: TextInputCallback = _default_text_input_cb  
                                        # 텍스트 입력 이벤트 발생 시 호출할 콜백
            # sync_transcription: NotGivenOr[bool] = NOT_GIVEN  
                                        # True일 때 오디오 출력과 자막(전사) 동기화
        ),
        room_output_options=RoomOutputOptions(

            # RoomOutputOptions 은 룸에 다시 내보낼 오디오/자막 출력을 어떤 형태로 발행할지 제어합니다.
            
            # transcription_enabled: bool = True  # 전사(자막) 출력 여부
            # audio_enabled: bool = True          # 오디오 출력 여부
            # audio_sample_rate: int = 24000      # 오디오 샘플링 레이트(Hz)
            # audio_num_channels: int = 1         # 오디오 채널 수
            # audio_publish_options: rtc.TrackPublishOptions = field(
            #     default_factory=lambda: rtc.TrackPublishOptions(
            #         source=rtc.TrackSource.SOURCE_MICROPHONE
            #     )
            # )                                   # 발행할 오디오 트랙 옵션

            transcription_enabled=True  # 실시간 자막(transcription) 활성화
        ),
    )


if __name__ == "__main__":
    # 워커 실행 옵션 설정에서 LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET 을 지정하지 않을 경우, 환경변수에서 찾습니다.
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        )
    )
