"""Read-only AppImage runtime checks in dedicated Distrobox test containers."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CASES = {
 'arch': ('couchpad-qa-arch', 'docker.io/library/archlinux:latest'),
 'debian': ('couchpad-qa-debian13', 'docker.io/library/debian:13'),
 'ubuntu': ('couchpad-qa-ubuntu2604', 'docker.io/library/ubuntu:26.04'),
 'fedora': ('couchpad-qa-fedora44', 'registry.fedoraproject.org/fedora:44'),
}

def main():
 artifact = ROOT/'dist/CouchPad-0.1.0b1-x86_64.AppImage'
 if not artifact.is_file():
  raise SystemExit('AppImage ausente em dist/: execute tools/build_appimage.py primeiro')
 env = os.environ.copy(); env.update(DBX_CONTAINER_MANAGER='podman', SHELL='/bin/bash')
 work = ROOT/'.build/distrobox'; (work/'logs').mkdir(parents=True,exist_ok=True)
 for slug in (sys.argv[1:] or CASES):
  name,image = CASES[slug]
  home = work/'homes'/slug; home.mkdir(parents=True,exist_ok=True)
  exists = subprocess.run(['podman','container','exists',name]).returncode == 0
  if not exists:
   subprocess.run(['distrobox','create','--yes','--no-entry','--name',name,'--image',image,
                   '--home',str(home),'--volume',f'{ROOT / "dist"}:/opt/couchpad-beta:ro'],env=env,check=True)
  command = r'''
set +e
printf 'COUCHPAD_QA_OS='
. /etc/os-release
printf '%s\n' "$PRETTY_NAME"
printf 'COUCHPAD_QA_LIBC='
getconf GNU_LIBC_VERSION
/opt/couchpad-beta/CouchPad-0.1.0b1-x86_64.AppImage --appimage-extract-and-run --version
printf 'COUCHPAD_QA_VERSION_EXIT=%s\n' "$?"
/opt/couchpad-beta/CouchPad-0.1.0b1-x86_64.AppImage --appimage-extract-and-run --runtime-check
printf 'COUCHPAD_QA_RUNTIME_EXIT=%s\n' "$?"
'''
  result = subprocess.run(['distrobox','enter','--no-tty','--clean-path','--no-workdir','--name',name,
                           '--','bash','-c',command],env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  (work/'logs'/f'{slug}-runtime.log').write_text(result.stdout)
  record={'container':name,'image':image,'distrobox_exit':result.returncode,'checks':{},'errors':[]}
  for line in result.stdout.splitlines():
   if line.startswith('COUCHPAD_QA_'):
    key,value=line.removeprefix('COUCHPAD_QA_').split('=',1)
    record['checks'][key.lower()]=value
   if any(text in line for text in ('not found','No such file','GLIBC_','error while loading','Traceback','Failed to')):
    record['errors'].append(line)
   if line.startswith('{') and '"frozen"' in line:
    try: record['runtime']=json.loads(line)
    except ValueError: pass
  (work/f'{slug}-results.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
  print(json.dumps(record,ensure_ascii=False,indent=2),flush=True)

if __name__ == '__main__': main()
