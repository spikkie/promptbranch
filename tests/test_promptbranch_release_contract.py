from __future__ import annotations
import json
import tomllib
from pathlib import Path
import pytest
from promptbranch_release_engine import ReleaseContractError, execute, load_contract, plan

ROOT=Path(__file__).resolve().parents[1]

def test_tracked_contract_is_valid_and_plan_is_read_only():
    contract=load_contract(ROOT)
    payload=plan(ROOT,contract)
    assert payload['ok'] is True
    assert payload['status']=='planned_read_only'
    assert payload['safety']['planning_mutated_state'] is False
    assert '.pb_profile' in payload['preserve']
    assert '.promptbranch-repo.json' in payload['preserve']
    assert [p['operation'] for p in payload['phases']]==['validate','test','build','verify','publish','adopt','verify_current','rollback']

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


def test_release_engine_is_declared_as_installed_module():
    data=tomllib.loads((ROOT/'pyproject.toml').read_text(encoding='utf-8'))
    modules=data['tool']['setuptools']['py-modules']
    assert 'promptbranch_release_engine' in modules


def test_tracked_contract_uses_sole_version_authority_for_release_identity():
    data=json.loads((ROOT/'.promptbranch-release.json').read_text(encoding='utf-8'))
    version=(ROOT/'VERSION').read_text(encoding='utf-8').strip()
    artifact=f"chatgpt_claudecode_workflow-2_{version}.zip"
    assert data['version_authority']=={'path':'VERSION','format':'plain'}
    assert data['artifact']['path']=='chatgpt_claudecode_workflow-2_{version}.zip'
    serialized=json.dumps(data)
    assert version not in serialized
    resolved=load_contract(ROOT)
    assert resolved['artifact']['path']==artifact
    for steps in resolved['operations'].values():
        for step in steps:
            for arg in step['argv']:
                assert '{version}' not in arg
                assert '{artifact}' not in arg
                if isinstance(arg,str) and arg.endswith('.zip'):
                    assert arg==artifact
                if isinstance(arg,str) and arg.startswith('v0.'):
                    assert arg==version


def test_tracked_contract_has_no_selectable_python_authority():
    data=json.loads((ROOT/'.promptbranch-release.json').read_text(encoding='utf-8'))
    assert 'PROMPTBRANCH_RELEASE_VALIDATION_PYTHON' not in data['environment']
    assert 'PROMPTBRANCH_CANDIDATE_PYTHON' not in data['environment']


def test_release_engine_enforces_launcher_python_with_poisoned_path(tmp_path: Path, monkeypatch):
    data=json.loads((ROOT/'.promptbranch-release.json').read_text(encoding='utf-8'))
    data['operations']['validate']=[{
        'id':'env-probe',
        'argv':['python3','-c','pass'],
        'timeout_seconds':30,
    }]
    (tmp_path/'.promptbranch-release.json').write_text(json.dumps(data), encoding='utf-8')
    (tmp_path/'.promptbranch-repo.json').write_text('{}\n', encoding='utf-8')
    (tmp_path/'VERSION').write_text((ROOT/'VERSION').read_text(encoding='utf-8'), encoding='utf-8')
    (tmp_path/'.pb_profile').mkdir()
    contract=load_contract(tmp_path)
    poisoned_path='/foreign/pytest-8/bin:/usr/bin'
    monkeypatch.setenv('PATH', poisoned_path)
    observed={}

    class Result:
        returncode=0
        stdout=''
        stderr=''

    def fake_runner(argv, *, cwd, env, text, capture_output, timeout, check):
        observed['argv']=argv
        observed['env']=dict(env)
        return Result()

    result=execute(tmp_path, contract, 'validate', runner=fake_runner)
    assert result['ok'] is True
    assert observed['env']['PATH'] == poisoned_path
    authority=str(Path(__import__('sys').executable).absolute())
    assert observed['argv'][0] == authority
    assert 'PROMPTBRANCH_RELEASE_VALIDATION_PYTHON' not in observed['env']
    assert 'PROMPTBRANCH_CANDIDATE_PYTHON' not in observed['env']


def test_release_engine_routes_pb_contract_step_through_same_python(tmp_path: Path, monkeypatch):
    data=json.loads((ROOT/'.promptbranch-release.json').read_text(encoding='utf-8'))
    data['operations']['publish']=[{
        'id':'pb-probe',
        'argv':['pb','--version'],
        'timeout_seconds':30,
    }]
    (tmp_path/'.promptbranch-release.json').write_text(json.dumps(data), encoding='utf-8')
    (tmp_path/'.promptbranch-repo.json').write_text('{}\n', encoding='utf-8')
    (tmp_path/'VERSION').write_text((ROOT/'VERSION').read_text(encoding='utf-8'), encoding='utf-8')
    (tmp_path/'.pb_profile').mkdir()
    (tmp_path/'promptbranch_cli.py').write_text('print("ok")\n', encoding='utf-8')
    contract=load_contract(tmp_path)
    artifact=tmp_path/contract['artifact']['path']
    artifact.write_bytes(b'not-a-zip')
    observed={}
    class Result:
        returncode=0
        stdout=''
        stderr=''
    def fake_runner(argv, *, cwd, env, text, capture_output, timeout, check):
        observed['argv']=argv
        observed['env']=dict(env)
        return Result()
    # Publish will fail artifact verification because the test artifact is not a ZIP,
    # but command resolution occurs first and is the invariant under test.
    execute(tmp_path, contract, 'publish', runner=fake_runner)
    authority=str(Path(__import__('sys').executable).absolute())
    assert observed['argv'][:3] == [authority, '-m', 'promptbranch.cli']
    assert 'PROMPTBRANCH_RELEASE_VALIDATION_PYTHON' not in observed['env']
    assert 'PROMPTBRANCH_CANDIDATE_PYTHON' not in observed['env']
