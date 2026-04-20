from pathlib import Path

from promptbranch import ChatGPTServiceClient, ConversationStateStore
from promptbranch_cli import _cli_command_name, make_parser
from promptbranch_service_client import ChatGPTServiceClient as DirectClient
from promptbranch_state import ConversationStateStore as DirectStore


def test_promptbranch_primary_import_surface():
    assert ChatGPTServiceClient is DirectClient
    assert ConversationStateStore is DirectStore


def test_parser_prog_defaults_to_promptbranch(monkeypatch):
    monkeypatch.setattr('sys.argv', ['promptbranch'])
    parser = make_parser()
    assert parser.prog == 'promptbranch'
    assert _cli_command_name('promptbranch') == 'promptbranch'


def test_cli_command_name_is_promptbranch():
    assert _cli_command_name('promptbranch') == 'promptbranch'
    

def test_new_internal_files_exist():
    repo = Path(__file__).resolve().parents[1]
    for rel in [
        'promptbranch_cli.py',
        'promptbranch_container_api.py',
        'promptbranch_service_client.py',
        'promptbranch_state.py',
        'promptbranch_automation/service.py',
        'promptbranch_browser_auth/client.py',
    ]:
        assert (repo / rel).exists(), rel
