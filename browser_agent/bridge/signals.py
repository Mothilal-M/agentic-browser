"""Qt signals for thread-safe communication between agent and UI."""

from PyQt6.QtCore import QObject, pyqtSignal


class AgentSignals(QObject):
    assistant_text = pyqtSignal(str)
    assistant_message_complete = pyqtSignal(str)
    tool_call_started = pyqtSignal(str, str)    # tool_name, args_json
    tool_result_received = pyqtSignal(str, str)  # tool_name, result_text
    thinking_update = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    agent_busy = pyqtSignal(bool)
    help_requested = pyqtSignal(object)
    task_status_changed = pyqtSignal(str, str)
