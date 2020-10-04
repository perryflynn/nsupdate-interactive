import subprocess
from typing import Tuple

def create_process(cmd: str) -> subprocess.CompletedProcess:
    """ Execute a command """

    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

def dig_zonetransfer(ns: str, hmac: str, zone: str) -> Tuple[bool, str]:
    """ Perform zone transfer to get the full list of all records in the zone """

    cmd = [ 'dig', '@'+ns, '-y', hmac, '-t', 'AXFR', zone ]
    proc = create_process(cmd)
    diglines = proc.stdout.decode('UTF-8-sig')

    return (proc.returncode == 0, diglines)

def diff(file1: str, file2: str) -> Tuple[bool, str]:
    """ Diff two text files """

    cmd = [ 'diff', '--ignore-space-change', '--suppress-common-lines', '-Nau', file1, file2 ]
    proc = create_process(cmd)

    return (proc.returncode == 1, proc.stdout.decode('UTF-8-sig'))

def diff_minimal(file1: str, file2: str) -> Tuple[bool, str]:
    """ Diff two text files and shows just the changed lines """

    cmd = [ 'diff', '--ignore-space-change', '--suppress-common-lines', file1, file2 ]
    proc = create_process(cmd)

    return (proc.returncode == 1, proc.stdout.decode('UTF-8-sig'))

def colorize_diff(diffstr: str) -> Tuple[bool, str]:
    """ Colorize a diff """

    proc = subprocess.run(['colordiff'], stdout=subprocess.PIPE, input=diffstr, encoding='UTF-8-sig')
    return (proc.returncode == 0, proc.stdout)

def checkzone(zone: str, file: str) -> Tuple[bool, str]:
    """ Check syntax of a zone file """

    cmd = [ 'named-checkzone', '-i', 'local', zone, file ]
    proc = create_process(cmd)

    return (proc.returncode == 0, proc.stdout.decode('UTF-8-sig'))

def nsupdate(hmac: str, filename: str) -> Tuple[bool, str]:
    """ Perform the nsupdate with a batch file """

    cmd = [ 'nsupdate', '-y', hmac, filename ]
    proc = create_process(cmd)

    return ( proc.returncode == 0, proc.stdout.decode('UTF-8-sig'))
