from __future__ import annotations
import json
from pathlib import Path
import pytest
from promptbranch_release_engine import ReleaseContractError, load_contract, plan

ROOT=Path(__file__).resolve().parents[1]

def test_tracked_contract_is_valid_and_plan_is_read_only():
    contract=load_contract(ROOT)
    payload=plan(ROOT,contract)
    assert payload['ok'] is True
    assert payload['status']=='planned_read_only'
    assert payload['safety']['planning_mutated_state'] is False
    assert '.pb_profile' in payload['preserve']
    assert '.promptbranch-repo.json' in payload['preserve']
    assert [p['operation'] for p in payload['phases']]==['validate','test','build','verify','publish','adopt','verify_current']

def test_unknown_fields_fail_closed(tmp_path: Path):
    data=json.loads((ROOT/'.promptbranch-release.json').read_text())
    data['unknown']=True
    (tmp_path/'.promptbranch-release.json').write_text(json.dumps(data))
    with pytest.raises(ReleaseContractError,match='unknown fields'):
        load_contract(tmp_path)

def test_path_traversal_fails_closed(tmp_path: Path):
    data=json.loads((ROOT/'.promptbranch-release.json').read_text())
    data['artifact']['path']='../escape.zip'
    (tmp_path/'.promptbranch-release.json').write_text(json.dumps(data))
    with pytest.raises(ReleaseContractError,match='without traversal'):
        load_contract(tmp_path)

def test_shell_commands_are_rejected(tmp_path: Path):
    data=json.loads((ROOT/'.promptbranch-release.json').read_text())
    data['operations']['validate'][0]['argv']=['bash','-lc','true']
    (tmp_path/'.promptbranch-release.json').write_text(json.dumps(data))
    with pytest.raises(ReleaseContractError,match='may not invoke a shell'):
        load_contract(tmp_path)
