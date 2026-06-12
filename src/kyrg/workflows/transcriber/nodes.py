from kyrg.editor import MediaContext, CommandRunner
from kyrg.editor.audio import ExtractAudio, ConvertToWhisperFormat
from kyrg.transcribers.base import TranscriberAPIBase
from kyrg.workflows.transcriber.state import TranscriberState
from kyrg.workflows.transcriber.actions import ExtractDomainContext
from kyrg.workflows.base import AIActionExecutor
from kyrg.workflows.transcriber.prompts import TranscriptionPrompts
from kyrg.workflows.core import WorkflowRuntime


def primary_router(state: TranscriberState):
    source_type = state.get('source_type')
    
    if source_type == "audio":
        return "normalize_audio"
    
    else:
        return "extract_audio"
        
def prepare_audio(state: TranscriberState) -> dict:
    context = MediaContext(
        input_path=state["source_path"],
        output_path=state["audio_path"],
    )
    converter = ConvertToWhisperFormat(
        context=context,
        runner=CommandRunner(),
    )
    converter.execute()

    return {
        "audio_path": state["audio_path"]
    }
    
def extract_audio(state: TranscriberState)-> dict: 
    context = MediaContext(input_path=state["source_path"], output_path=state["audio_path"])
    extractor = ExtractAudio(context=context, runner=CommandRunner())
    extractor.execute()
    
    return {
        "audio_path": state["audio_path"]
    }
    

def audio_text_converter(state: TranscriberState, runtime: WorkflowRuntime) -> dict: 
    context = runtime.context
    
    if context is None:
        raise RuntimeError("Transcriber workflow context is required.")

    transcriptor = context.transcriptor_config.transcriptor
    temperature = context.transcriptor_config.transcriptor_temperature
    
    language=state.get("language") 

    if issubclass(transcriptor, TranscriberAPIBase):
        api_key=context.transcriptor_config.transcriptor_api_key
        
        if api_key is None:
            raise ValueError("api_key is required for remote transcriber")
        
        transcriber = transcriptor(
            audio_path=state["audio_path"],
            model_name=state["model_name"],
            language=language,
            temperature=temperature,
            api_key=api_key,
        )
        
    else:
        transcriber = transcriptor(
            audio_path=state["audio_path"],
            model_name=state["model_name"],
            language=language,
            temperature=temperature,
        )
    
    result = transcriber.transcribe()
    return {
        'result': result
    }
    
def extract_hybrid_context(state: TranscriberState, runtime: WorkflowRuntime) -> dict:
    context = runtime.context
    
    if context is None:
        raise RuntimeError("Transcriber workflow context is required.")
    
    result = state.get("result")
    
    if result is None:
        raise ValueError("result is required to extract domain context")
    
    action = ExtractDomainContext(
        llm=context.extract_context_llm,
        result=result,
    )
    
    domain_context = AIActionExecutor.run(action)
    
    token_usage = action.tokens_usage
    return {
        "domain_context": domain_context,
        "messages": [
            {
                "role": "user",
                "content": TranscriptionPrompts.QUALITY_AGENT_INPUT.format(
                    domain_context=domain_context.model_dump_json(indent=2),
                    result=result.model_dump_json(indent=2),
                ),
            }
        ],
        "input_tokens": token_usage["input_tokens"],
        "output_tokens": token_usage["output_tokens"],
        "total_tokens": token_usage["total_tokens"],
    }

def collect_agent_tokens(state: TranscriberState) -> dict:
    input_tokens = 0
    output_tokens = 0

    for message in state.get("messages", []):
        usage = getattr(message, "usage_metadata", None)

        if usage is None:
            continue

        input_tokens += usage.get("input_tokens", 0)
        output_tokens += usage.get("output_tokens", 0)

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }
