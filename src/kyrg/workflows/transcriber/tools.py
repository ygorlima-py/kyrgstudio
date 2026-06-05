from kyrg.workflows.transcriber.state import TranscriberState
from langchain_core.tools import tool

@tool
def correct_transcription_tool(state: TranscriberState):
    ...

@tool
def request_human_review_tool(state: TranscriberState):
    ...

@tool
def accept_transcription_tool(state: TranscriberState):
    ...