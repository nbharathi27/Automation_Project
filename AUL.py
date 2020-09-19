#!/usr/bin/python
import subprocess

iso = sys.argv[1]
ip=sys.argv[2]
pwd=sys.argv[3]

cmd = ['/opt/ft/sbin/ft-install', iso, '-n', '-N', '-H', ip, '-p', pwd]
popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True)
for stdout_line in iter(popen.stdout.readline, ""):
    yield stdout_line
popen.stdout.close()
return_code = popen.wait()
if return_code:
    raise subprocess.CalledProcessError(return_code, cmd)
