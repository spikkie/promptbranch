from __future__ import annotations
import json,sys,zipfile
from pathlib import Path
from promptbranch_artifacts import ArtifactRegistry,ArtifactRecord
from promptbranch_cli import make_parser,_candidate_protocol_selection
from promptbranch_full_integration_test import DockerServiceAdapter
from promptbranch_release_state_machine import SubprocessReleaseExecutor,build_machine_from_args

def test_selected_protocol_reply_is_origin_authority():
 c={"conversation_id":"legacy","answer_id":"legacy-a","selected_protocol_reply":{"conversation_url":"https://chatgpt.com/g/g-p-demo/c/exact","conversation_id":"exact","answer_id":"exact-a","request_id":"r"}}
 x=_candidate_protocol_selection(c); assert x["conversation_id"]=="exact" and x["answer_id"]=="exact-a"

def test_registry_origin_validation(tmp_path):
 r=ArtifactRegistry(tmp_path/'r');r.initialize(); rec=ArtifactRecord(path=str(tmp_path/'repo_v0.1.2.zip'),filename='repo_v0.1.2.zip',kind='adopted_release',version='v0.1.2',repo_path=None,repo_id='repo',sha256='a'*64,size_bytes=1,file_count=1,created_at='2026-08-10T00:00:00Z',source_ref='repo_v0.1.2.zip',project_url='https://chatgpt.com/g/g-p-demo/project',origin_conversation_url='https://chatgpt.com/g/g-p-demo/c/c1',origin_conversation_id='c1');r.add(rec); bad=rec.to_dict();bad['origin_conversation_id']='x';assert 'must exactly match' in r._record_validation_error(bad)

def test_parser_options():
 p=make_parser(); assert p.parse_args(['artifact','bind-conversation','--repo','repo','--version','v0.1.2','--conversation-url','https://chatgpt.com/g/g-p-demo/c/c1']).artifact_command=='bind-conversation'; assert p.parse_args(['test','full','--ask-conversation-url','https://chatgpt.com/g/g-p-demo/c/c1']).ask_conversation_url.endswith('/c/c1')

def test_pinned_chat_derives_matching_project(): assert DockerServiceAdapter._project_url_for_conversation('https://chatgpt.com/g/g-p-base/c/c1','https://chatgpt.com/g/g-p-gen/project')=='https://chatgpt.com/g/g-p-base/project'

def _zip(path):
 with zipfile.ZipFile(path,'w') as z:
  for n,b in {'VERSION':'v0.1.127.1.1\n','pyproject.toml':'[project]\nname="promptbranch"\nversion="0.1.127.1.1"\n','promptbranch_version.py':'PACKAGE_VERSION="0.1.127.1.1"\n','promptbranch_cli.py':'# x\n','README.md':'x\n','.promptbranch-release.json':'{}\n','.promptbranch-repo.json':'{"repo_id":"repo"}\n','promptbranch_release_state_machine.py':'# x\n','run_chatgpt_service.sh':'#!/bin/sh\n','docker/run-chatgpt-service-in-container.sh':'#!/bin/sh\n','docker-compose.chatgpt-service.yml':'services: {}\n','Dockerfile':'FROM scratch\n'}.items(): z.writestr(n,b)
 return path

def test_candidate_registration_binds_origin(tmp_path):
 repo=tmp_path/'repo';repo.mkdir(); a=_zip(tmp_path/'repo_v0.1.127.1.1.zip'); chat='https://chatgpt.com/g/g-p-demo/c/candidate'; m=build_machine_from_args(repo_root=repo,profile_dir=repo/'.pb_profile',artifact=a,version='v0.1.127.1.1',baseline_version='v0.1.126.1.1.1.1.3',until='candidate-registered',artifact_conversation_url=chat); payload,code=m.run();assert code==0;reg=json.loads((repo/'.pb_profile/artifact_candidates.json').read_text());assert reg['candidates'][0]['selected_protocol_reply']['conversation_url']==chat

def test_candidate_test_blocks_missing_baseline_origin(tmp_path):
 repo=tmp_path/'repo';repo.mkdir();a=_zip(tmp_path/'repo_v0.1.127.1.1.zip');m=build_machine_from_args(repo_root=repo,profile_dir=repo/'.pb_profile',artifact=a,version='v0.1.127.1.1',baseline_version='v0.1.126.1.1.1.1.3');e=SubprocessReleaseExecutor();e.current_status=lambda machine,record:{'ok':True,'result':{'repos':{'repo':{'registry_current':{'version':'v0.1.126.1.1.1.1.3'}}}}};res=e.run_tests(m,{'artifact':{'sha256':'a'*64},'evidence':{'RUNTIME_PREPARED':{}},'active_test_attempt':{'retry_number':1}});assert res['failure_code']=='baseline_artifact_conversation_provenance_missing' and res['test_subprocess_executed'] is False


def _origin_record_for_project_identity(*, project_url: str, origin_url: str):
    return ArtifactRecord(
        path="/tmp/repo_v0.1.2.zip",
        filename="repo_v0.1.2.zip",
        kind="adopted_release",
        version="v0.1.2",
        repo_path=None,
        repo_id="repo",
        sha256="a" * 64,
        size_bytes=1,
        file_count=1,
        created_at="2026-08-10T00:00:00Z",
        source_ref="repo_v0.1.2.zip",
        project_url=project_url,
        origin_conversation_url=origin_url,
        origin_conversation_id=origin_url.rstrip("/").split("/c/", 1)[-1],
    ).to_dict()


def test_registry_origin_accepts_slugged_conversation_for_unslugged_project(tmp_path):
    registry = ArtifactRegistry(tmp_path / "r")
    project_id = "g-p-6a43ea5129508191be8c8ebcf9fc7391"
    record = _origin_record_for_project_identity(
        project_url=f"https://chatgpt.com/g/{project_id}/project",
        origin_url=f"https://chatgpt.com/g/{project_id}-promptbranch3/c/6a78783b-3e00-83eb-8dc1-1e814fcf2a59",
    )
    assert registry._record_validation_error(record) is None


def test_registry_origin_accepts_unslugged_conversation_for_slugged_project(tmp_path):
    registry = ArtifactRegistry(tmp_path / "r")
    project_id = "g-p-6a43ea5129508191be8c8ebcf9fc7391"
    record = _origin_record_for_project_identity(
        project_url=f"https://chatgpt.com/g/{project_id}-promptbranch3/project",
        origin_url=f"https://chatgpt.com/g/{project_id}/c/6a78783b-3e00-83eb-8dc1-1e814fcf2a59",
    )
    assert registry._record_validation_error(record) is None


def test_registry_origin_rejects_different_canonical_project_identity(tmp_path):
    registry = ArtifactRegistry(tmp_path / "r")
    record = _origin_record_for_project_identity(
        project_url="https://chatgpt.com/g/g-p-6a43ea5129508191be8c8ebcf9fc7391/project",
        origin_url="https://chatgpt.com/g/g-p-7b43ea5129508191be8c8ebcf9fc7392-promptbranch3/c/6a78783b-3e00-83eb-8dc1-1e814fcf2a59",
    )
    assert registry._record_validation_error(record) == "origin conversation must belong to the artifact project"
