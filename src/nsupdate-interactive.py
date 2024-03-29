#!/usr/bin/python3

import os
import sys
import re
import argparse
import subprocess
import shlex
import shutil
import datetime
import textwrap
from zoneutils import zonefile, zonefileformatter, nsupdate, utils
from pprint import pprint


SLUG_RGX = re.compile(r"[^a-zA-Z0-9_]")
DEFAULT_IGNORE_RRTYPES = [ 'DNSKEY', 'RRSIG', 'NSEC', 'TYPE65534', 'CDS', 'CDNSKEY' ]


def parse_args():
    """ Parse command line arguments """

    parser = argparse.ArgumentParser(
        description='nsupdate-interactive', 
        formatter_class=argparse.RawDescriptionHelpFormatter, 
        epilog=textwrap.dedent(f'''\
            Per default, the following RR types will be ignored:
            {', '.join(DEFAULT_IGNORE_RRTYPES)}

            Author: Christian Blechert <christian@serverless.industries>
            Website: https://github.com/perryflynn/nsupdate-interactive
            ''')
        )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--zone', type=str, help='The zone name', metavar='example.com')
    group.add_argument('--get-zone-slug', type=str, help='Slugify a zone name for hmac key envs', metavar='example.com')
    
    parser.add_argument('--dnsserver', type=str, required=False, help='DNS server to use', metavar='ns1.example.com')
    parser.add_argument('--ignore-rrtype', action='append', required=False, help='Ignore RR types, can be used multiple times', metavar='RRSIG')

    return parser.parse_args()


def check_dependencies(editor: str):
    """ Check for binaries which are required for this script """

    binaries = [ editor, 'nsupdate', 'dig', 'diff', 'colordiff', 'named-checkzone' ]
    binarymissing = False
    for binary in binaries:
        if shutil.which(binary) is None:
            binarymissing = True
            print("The program '"+binary+"' is required to use this script")

    if binarymissing:
        sys.exit(1)


def domain_slugify(domain: str) -> str:
    idn = domain.encode('idna').decode('utf-8-sig')
    return SLUG_RGX.sub('_', idn).upper().strip()


def press(what: str):
    input(f"Press ENTER to {what}, CTRL+C to abort.")


def main():
    """ Main function of the script"""

    # get editor
    editor = os.environ.get('EDITOR', 'nano')

    # check for dependend programs
    check_dependencies(editor)

    # parse arguments
    args = parse_args()

    # ignore rrtypes default
    if (not args.ignore_rrtype) or len(args.ignore_rrtype) < 1:
        args.ignore_rrtype = DEFAULT_IGNORE_RRTYPES

    args.ignore_rrtype = list(map(lambda x: x.upper().strip(), args.ignore_rrtype))

    # print domain slug
    if args.get_zone_slug:
        print(f"HMAC_{domain_slugify(args.get_zone_slug)}")
        sys.exit(0)

    # get hmac key
    zone_varname = f"HMAC_{domain_slugify(args.zone)}"
    hmackey = os.environ.get('HMAC', os.environ.get(zone_varname))

    if hmackey is None:
        print("Environment variable 'HMAC' is required.")
        sys.exit(1)

    # find nameserver if no one is defined
    if not args.dnsserver:
        args.dnsserver = utils.dig_get_authoritative_server(args.zone)

        if args.dnsserver:
            print(f"Found dns server by SOA record: {args.dnsserver}")
        else:
            print("There was no '--dnsserver' option defined and we are unable")
            print("to find the authoritative name server by SOA record.")
            sys.exit(1)

    # base filename
    ts = datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'Z'
    filename = 'nsupdate_'+utils.sanitize_for_filesystem(args.dnsserver)+'_'+utils.sanitize_for_filesystem(args.zone)+'_'+ts+'.{0}.db'

    # get zone records by calling dig
    digstr = utils.dig_zonetransfer(args.dnsserver, hmackey, args.zone)

    if digstr[2] == utils.ZonetransferResult.KEYINVALID:
        print(digstr[1])
        print("Invalid HMAC key provided or HMAC key was denied by DNS server.")
        sys.exit(1)
    elif digstr[2] == utils.ZonetransferResult.FAILED:
        print(digstr[1])
        print("Transfer failed.")
        print("Maybe a typo in zone name or dns server address?")
        print("Or the HMAC doesn't have the permission to access the given dns zone.")
        sys.exit(1)
    elif digstr[0] == False:
        print("dig failed:")
        print(digstr[1])
        sys.exit(1)

    records = zonefile.ZoneFile(digstr[1])

    if len(records.records) < 1:
        print("Unable to find any records in the DNS zone.")
        print("There must be at least a SOA record.")
        print("Maybe a typo in the zone name or dns server address?")
        print("Or something wrong with your permissions?")
        sys.exit(1)

    # create zone files for diff and editing
    formatter = zonefileformatter.ZoneFileFormatter(args.ignore_rrtype)

    for version in [ 'org', 'new' ]:
        formatter.save(filename.format(version), records)

    # edit and check syntax
    haserrors = True
    while haserrors:
        # open text editor
        subprocess.call([ editor, filename.format('new') ])

        # check syntax
        checkresult = utils.checkzone(args.zone, filename.format('new'))
        if checkresult[0]:
            haserrors = False
        else:
            print("Found syntax errors in zone file:")
            print(checkresult[1])
            press('correct the zone file')

    # show a diff between work copy and original
    diffresult = utils.diff(filename.format('org'), filename.format('new'))
    if diffresult[0] == False:
        print("No changes made. Exit.")
        os.remove(filename.format('org'))
        os.remove(filename.format('new'))
        sys.exit(0)

    # update soa serial
    originalsoa = zonefile.SoaRecord(next(filter(lambda x: x.dnsType=='SOA', records.records)))
    newrecords = zonefile.load(filename.format('new'))
    editedsoa = zonefile.SoaRecord(next(filter(lambda x: x.dnsType=='SOA', newrecords.records)))

    if originalsoa == editedsoa:
        # update serial with the classic date format
        editedsoa.apply_default_serialincrease()

        # write zone file and redo diff
        formatter.save(filename.format('new'), newrecords)
        diffresult = utils.diff(filename.format('org'), filename.format('new'))

    print(utils.colorize_diff(diffresult[1])[1])

    # write diff into a patch file
    with open(filename.format('patch'), 'w+') as f:
        f.write(diffresult[1])

    # ask befort continue with nsupdate
    press('send the changes to the nameserver')

    # create nsupdate batch file
    minidiff = utils.diff_minimal(filename.format('org'), filename.format('new'))[1]
    nsupdater = nsupdate.from_diff(minidiff)
    nsupdatestr = '\n'.join(list(nsupdater.get_nsupdate_batch(args.dnsserver, args.zone)))

    with open(filename.format('batch'), 'w+') as f:
        f.write(nsupdatestr)

    # execute nsupdate
    updateresult = utils.nsupdate(hmackey, filename.format('batch'))

    if updateresult[0] == False:
        print("nsupdate failed:")
        print(updateresult[1])
        sys.exit(1)


# start main function
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # catch exception when script was canceled by CTRL+C
        pass
