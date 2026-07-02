from kyrg.editor import MediaContext, CommandRunner
from kyrg.editor.audio import ExtractAudio, ConvertToWhisperFormat, AudioSize
from kyrg.transcribers.base import TranscriberAPIBase, TranscriberBase
from kyrg.workflows.transcriber.state import TranscriberState
from kyrg.workflows.transcriber.actions import ExtractDomainContext, CorrectTranscription
from kyrg.workflows.base import AIActionExecutor
from kyrg.workflows.transcriber.prompts import TranscriptionPrompts
from kyrg.workflows.workflow_types import WorkflowRuntime
from kyrg.workflows.transcriber.schemas import TranscriberWorkflowContext
from kyrg.workflows import guards


# ----- Nodes Sync --------------------

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
    

def audio_text_converter(
    state: TranscriberState,
    runtime: WorkflowRuntime[TranscriberWorkflowContext],
) -> dict: 
    context = guards.require_context(
        runtime.context,
        "Transcriber",
    )

    transcriptor = context.transcriptor_config.transcriptor
    temperature = (
        context.transcriptor_config.transcriptor_temperature
        if context.transcriptor_config.transcriptor_temperature is not None
        else 0.0
    )
    language=state.get("language") 

    if issubclass(transcriptor, TranscriberAPIBase):
        api_key = guards.require_value_with_message(
            context.transcriptor_config.transcriptor_api_key,
            "api_key is required for remote transcriber",
        )
        
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
    

def measure_audio(state: TranscriberState):
    context = MediaContext(
        input_path=state["source_path"],
        output_path=state["audio_path"],
    )
    
    action = AudioSize(context=context, runner=CommandRunner())
    result = action.execute()
    
    duration_seconds = float(result.stdout.decode().strip())
    
    return {
        "audio_duration_in_seconds": duration_seconds,
    }
    

def secondary_router(state: TranscriberState):
    audio_duration_in_seconds = guards.require_runtime_value(
        state.get("audio_duration_in_seconds"),
        "Failed measure audio in seconds",
    )
    need_correction = state.get("need_correction", False)
    
    if audio_duration_in_seconds <= 180 and need_correction:
        return "to_correction"
    
    else:
        return "not_correction"
        

def extract_hybrid_context(
    state: TranscriberState,
    runtime: WorkflowRuntime[TranscriberWorkflowContext],
) -> dict:
    context = guards.require_context(
        runtime.context,
        "Transcriber",
    )
    result = guards.require_value(
        state.get("result"),
        "result",
        "extract domain context",
    )
    
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


def correction_transcriber(
    state: TranscriberState,
    runtime: WorkflowRuntime[TranscriberWorkflowContext],
) -> dict:
    context = guards.require_context(
        runtime.context,
        "Transcriber",
    )
    result = guards.require_value(
        state.get("result"),
        "result",
        "correct transcription",
    )
    domain_context = guards.require_value(
        state.get("domain_context"),
        "domain_context",
        "correct transcription",
    )

    action = CorrectTranscription(
        llm=context.correction_llm,
        result=result,
        domain_context=domain_context,
    )

    correction_output = AIActionExecutor.run(action)
    token_usage = action.tokens_usage

    corrected_result = result.model_copy(deep=True)
    corrected_result.text = correction_output.corrected_text

    segments_by_id = {
        segment.id: segment
        for segment in corrected_result.segments
    }

    for corrected_segment in correction_output.corrected_segments:
        segment = segments_by_id.get(corrected_segment.id)

        if segment is not None:
            segment.text = corrected_segment.text

    return {
        "result": corrected_result,
        "status": "corrected",
        "human_review_reason": None,
        "input_tokens": token_usage["input_tokens"],
        "output_tokens": token_usage["output_tokens"],
        "total_tokens": token_usage["total_tokens"],
    }

# ------------------- Nodes Async --------------------------
async def aaudio_text_converter(
    state: TranscriberState,
    runtime: WorkflowRuntime[TranscriberWorkflowContext],
    ) -> dict: 
    context = guards.require_context(
        runtime.context,
        "Transcriber",
    )

    transcriptor = context.transcriptor_config.transcriptor
    temperature = (
        context.transcriptor_config.transcriptor_temperature
        if context.transcriptor_config.transcriptor_temperature is not None
        else 0.0
    )
    language=state.get("language") 
    if issubclass(transcriptor, TranscriberAPIBase):
        api_key = guards.require_value_with_message(
            context.transcriptor_config.transcriptor_api_key,
            "api_key is required for remote transcriber",
        )
        
        transcriber: TranscriberBase = transcriptor(
            audio_path=state["audio_path"],
            model_name=state["model_name"],
            language=language,
            temperature=temperature,
            api_key=api_key,
        )
        
    else:
        transcriber: TranscriberBase = transcriptor(
            audio_path=state["audio_path"],
            model_name=state["model_name"],
            language=language,
            temperature=temperature,
        )
    
    result = await transcriber.atranscribe()
    return {
        'result': result
    }
    

async def aextract_hybrid_context(
    state: TranscriberState,
    runtime: WorkflowRuntime[TranscriberWorkflowContext],
) -> dict:
    context = guards.require_context(
        runtime.context,
        "Transcriber",
    )
    result = guards.require_value(
        state.get("result"),
        "result",
        "extract domain context",
    )
    
    action = ExtractDomainContext(
        llm=context.extract_context_llm,
        result=result,
    )
    
    domain_context = await AIActionExecutor.arun(action)
    
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


async def acorrection_transcriber(
    state: TranscriberState,
    runtime: WorkflowRuntime[TranscriberWorkflowContext],
) -> dict:
    context = guards.require_context(
        runtime.context,
        "Transcriber",
    )
    result = guards.require_value(
        state.get("result"),
        "result",
        "correct transcription",
    )
    domain_context = guards.require_value(
        state.get("domain_context"),
        "domain_context",
        "correct transcription",
    )

    action = CorrectTranscription(
        llm=context.correction_llm,
        result=result,
        domain_context=domain_context,
    )

    correction_output = await AIActionExecutor.arun(action)
    token_usage = action.tokens_usage

    corrected_result = result.model_copy(deep=True)
    corrected_result.text = correction_output.corrected_text

    segments_by_id = {
        segment.id: segment
        for segment in corrected_result.segments
    }

    for corrected_segment in correction_output.corrected_segments:
        segment = segments_by_id.get(corrected_segment.id)

        if segment is not None:
            segment.text = corrected_segment.text

    return {
        "result": corrected_result,
        "status": "corrected",
        "human_review_reason": None,
        "input_tokens": token_usage["input_tokens"],
        "output_tokens": token_usage["output_tokens"],
        "total_tokens": token_usage["total_tokens"],
    }
