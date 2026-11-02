"""Exercise the actual setup firmware function with isolated command stubs, without reinstalling setup."""
import os
from pathlib import Path
import subprocess

from kerf import fwcheck as W

ROOT = Path(__file__).resolve().parents[1]


def test_setup_gives_arduino_its_supported_proxy_setting(tmp_path):
    body = (ROOT/'setup.sh').read_text(encoding='utf-8').split('fw_tools() {',1)[1].split('\n}\nfw_tools ||',1)[0]
    cli = tmp_path/'.cache/arduino/bin/arduino-cli'
    cli.parent.mkdir(parents=True)
    cli.write_text('#!/bin/sh\nprintf "%s" "$ARDUINO_NETWORK_PROXY" > "$PROXY_CAPTURE"\necho "arduino-cli Version: 1.3.1 Commit: test"\n', encoding='utf-8')
    cli.chmod(0o755)
    (tmp_path/'.cache/arduino/data/packages/arduino/hardware/avr/1.8.6').mkdir(parents=True)
    user = tmp_path/'.cache/arduino/user'
    user.mkdir()
    (user/'.kerf-libs').write_text(' '.join(W.LIBS)+'\n',encoding='utf-8')
    stubs = tmp_path/'stubs'
    stubs.mkdir()
    for name,src in {'uname':'echo Linux-x86_64' , 'apt-get':'exit 0'}.items():
        # uname -s/-m is used as a pair, and uname without arguments selects the Linux install branch.
        if name=='uname':src='if [ "$1" = "-s" ]; then echo Linux; elif [ "$1" = "-m" ]; then echo x86_64; else echo Linux; fi'
        f=stubs/name;f.write_text('#!/bin/sh\n'+src+'\n',encoding='utf-8');f.chmod(0o755)
    env={**os.environ,'PATH':str(stubs)+os.pathsep+os.environ['PATH'],'HTTPS_PROXY':'http://proxy.example:8080',
         'PROXY_CAPTURE':str(tmp_path/'proxy.txt')}
    env.pop('ARDUINO_NETWORK_PROXY',None)
    for explicit, expected in [(None,'http://proxy.example:8080'),('http://explicit.example:3128','http://explicit.example:3128'),('','')]:
        if explicit is not None:env['ARDUINO_NETWORK_PROXY']=explicit
        r=subprocess.run(['bash','-c','set -eu\nfw_tools() {'+body+'\n}\nfw_tools'],cwd=tmp_path,env=env,capture_output=True,text=True,timeout=15)
        assert r.returncode==0,r.stdout+r.stderr
        assert (tmp_path/'proxy.txt').read_text(encoding='utf-8')==expected
