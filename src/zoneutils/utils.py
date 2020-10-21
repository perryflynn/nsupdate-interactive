import subprocess
from typing import Tuple
from enum import Enum
import re
from zoneutils import zonefile

TSIG_EXISTS_RGX = re.compile(r"^\s*[^\s]+\s+[^\s]+\s+ANY\s+TSIG\s+[^\s]+\s+[^\s]+\s+[^\s]+\s+[^\s]+\s+[^\s]+\s+[^\s]+\s+NOERROR\s+[^\s]+\s*$", re.M)
TRANSFER_FAILED_RGX = re.compile(r"^\s*;\s+Transfer\s+failed.\s*$", re.M)

class ZonetransferResult(Enum):
    OK = 0,
    KEYINVALID = 1,
    FAILED = 2

def create_process(cmd: str) -> subprocess.CompletedProcess:
    """ Execute a command """

    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

def dig_get_authoritative_server(zone: str) -> str:
    """ Get domains authoritative name server by SOA record """

    cmd = [ 'dig', '-t', 'SOA', zone ]
    proc = create_process(cmd)
    diglines = proc.stdout.decode('UTF-8-sig')

    if proc.returncode == 0:
        # find SOA record and return primary DNS server
        records = zonefile.ZoneFile(diglines)
        rawsoa = list(filter(lambda x: x.dnsType == 'SOA', records.records))

        if len(rawsoa) > 0:
            soa = zonefile.SoaRecord(rawsoa[0])
            return soa.soaPrimaryDns

    return None

def dig_zonetransfer(ns: str, hmac: str, zone: str) -> Tuple[bool, str, ZonetransferResult]:
    """ Perform zone transfer to get the full list of all records in the zone """

    cmd = [ 'dig', '@'+ns, '-y', hmac, '-t', 'AXFR', zone ]
    proc = create_process(cmd)
    diglines = proc.stdout.decode('UTF-8-sig')

    # check for errors
    result = ZonetransferResult.OK

    if not TSIG_EXISTS_RGX.search(diglines):
        result = ZonetransferResult.KEYINVALID

    elif TRANSFER_FAILED_RGX.search(diglines):
        result = ZonetransferResult.FAILED

    return (proc.returncode == 0 and result == ZonetransferResult.OK, diglines, result)

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
