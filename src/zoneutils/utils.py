import subprocess

def create_process(cmd):
    """ Execute a command """

    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

def dig_zonetransfer(ns, hmac, zone):
    """ Perform zone transfer to get the full list of all records in the zone """

    cmd = [ 'dig', '@'+ns, '-y', hmac, '-t', 'AXFR', zone ]
    proc = create_process(cmd)
    diglines = proc.stdout.decode('UTF-8-sig')

    return (proc.returncode == 0, diglines)

def diff(file1, file2):
    """ Diff two text files """

    cmd = [ 'diff', '-Nau', file1, file2 ]
    proc = create_process(cmd)

    return (proc.returncode == 1, proc.stdout.decode('UTF-8-sig'))

def diff_minimal(file1, file2):
    """ Diff two text files and shows just the changed lines """

    cmd = [ 'diff', "--old-group-format=-%<", "--new-group-format=+%>", "--unchanged-group-format=", file1, file2 ]
    proc = create_process(cmd)

    return (proc.returncode == 1, proc.stdout.decode('UTF-8-sig'))

def checkzone(zone, file):
    """ Check syntax of a zone file """

    cmd = [ 'named-checkzone', '-i', 'local', zone, file ]
    proc = create_process(cmd)

    return (proc.returncode == 0, proc.stdout.decode('UTF-8-sig'))

def nsupdate(hmac, filename):
    """ Perform the nsupdate with a batch file """

    cmd = [ 'nsupdate', '-y', hmac, filename ]
    proc = create_process(cmd)

    return ( proc.returncode == 0, proc.stdout.decode('UTF-8-sig'))
