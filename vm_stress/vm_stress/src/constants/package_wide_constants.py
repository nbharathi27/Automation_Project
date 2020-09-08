import os
home = os.path.expanduser("~")

logfile = os.path.join(home, 'vmstress.log')

memory_default_value = 40
cpu_default_value = 40
disk_default_value = 1000

ovf_bin_path = '/usr/bin/ovftool'
