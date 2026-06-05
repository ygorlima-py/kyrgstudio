from kyrg.workflows.transcriber.state import TranscriberState
from kyrg.editor import MediaContext, CommandRunner
from kyrg.editor.audio import ExtractAudio, ConvertToWhisperFormat
from kyrg.transcribers.base import TranscriberAPIBase
from kyrg.workflows.transcriber.agent import TranscriptionAgent
from kyrg.workflows.transcriber.tools import (
    accept_transcription_tool,
    correct_transcription_tool,
    request_human_review_tool,
)

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
    
    if issubclass(transcriber_class, TranscriberAPIBase):
        api_key = state["api_key"]
        
        if api_key is None:
            raise ValueError("api_key is required for remote transcriber")
        
        transcriber = transcriber_class(
            audio_path=state["audio_path"],
            model_name=state["model_name"],
            language=state["language"],
            temperature=state["temperature"],
            api_key=api_key,
        )
        
    else:
        transcriber = transcriber_class(
            audio_path=state["audio_path"],
            model_name=state["model_name"],
            language=state["language"],
            temperature=state["temperature"],
        )
    
    result = transcriber.transcribe()
    return {
        'result': result
    }
    
def extract_hybrid_context(state: TranscriberState) -> dict:
    ...


