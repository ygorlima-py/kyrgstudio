from kyrg.editor import MediaContext, CommandRunner
from kyrg.editor.audio import ExtractAudio, ConvertToWhisperFormat
from kyrg.transcribers.base import TranscriberAPIBase
from kyrg.workflows.transcriber.state import TranscriberState
from kyrg.workflows.transcriber.actions import ExtractDomainContext
from kyrg.workflows.base import AIActionExecutor
from kyrg.workflows.transcriber.prompts import TranscriptionPrompts

from langgraph.runtime import Runtime

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
    

def audio_text_converter(state: TranscriberState) -> dict: 
    transcriber_class = state["transcriber"]
    
    language=state.get("language")
    temperature=state.get("temperature", 0.0)
    
    if issubclass(transcriber_class, TranscriberAPIBase):
        api_key=state.get("api_key")
        
        if api_key is None:
            raise ValueError("api_key is required for remote transcriber")
        
        transcriber = transcriber_class(
            audio_path=state["audio_path"],
            model_name=state["model_name"],
            language=language,
            temperature=temperature,
            api_key=api_key,
        )
        
    else:
        transcriber = transcriber_class(
            audio_path=state["audio_path"],
            model_name=state["model_name"],
            language=language,
            temperature=temperature,
        )
    
    result = transcriber.transcribe()
    return {
        'result': result
    }
    
def extract_hybrid_context(state: TranscriberState, runtime: Runtime) -> dict:
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
        ]
    }



