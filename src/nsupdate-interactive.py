#!/usr/bin/python3

import os
import sys
import re
import argparse
import subprocess
import shlex
import shutil
import datetime
from zoneutils import zonefile, zonefileformatter, nsupdate, utils


def parse_args():
    """ Parse command line arguments """

    parser = argparse.ArgumentParser(description='ExDiff')

    parser.add_argument('--zone', type=str, required=True)
    parser.add_argument('--dnsserver', type=str, required=True)

    return parser.parse_args()


def check_dependencies(editor):
    """ Check for binaries which are required for this script """

    binaries = [ editor, 'nsupdate', 'dig', 'diff', 'named-checkzone' ]
    binarymissing = False
    for binary in binaries:
        if shutil.which(binary) is None:
            binarymissing = True
            print("The program '"+binary+"' is required to use this script")

    if binarymissing:
        sys.exit(1)


def press(what):
    input(f"Press ENTER to {what}, CTRL+C to abort.")


def main():
    """ Main function of the script"""

    # get editor
    editor = os.environ.get('EDITOR', 'nano')

    # check for dependend programs
    check_dependencies(editor)

    # get hmac key
    hmackey = os.environ.get('HMAC')

    if hmackey is None:
        print("Environment variable 'HMAC' is required.")
        sys.exit(1)

    # parse arguments
    args = parse_args()

    # base filename
    ts = datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'Z'
    filename = 'nsupdate_'+args.dnsserver+'_'+args.zone+'_'+ts+'.{0}.db'

    # get zone records by calling dig
    digstr = utils.dig_zonetransfer(args.dnsserver, hmackey, args.zone)
    if digstr[0] == False:
        print("dig failed:")
        print(digstr[1])
        sys.exit(1)

    records = zonefile.ZoneFile(digstr[1])

    # create zone textfile
    formatter = zonefileformatter.ZoneFileFormatter()
    with open(filename.format('org'), 'w+') as f:
        for line in formatter.format(records):
            f.write(f'{line}\n')

    # create a working copy
    shutil.copyfile(filename.format('org'), filename.format('new'))

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

    print(diffresult[1])

    # write diff into a patch file
    with open(filename.format('patch'), 'w+') as f:
        f.write(diffresult[1])

    # ask befort continue with nsupdate
    press('send the changes to the nameserver')

    # create nsupdate batch file
    minidiff = utils.diff_minimal(filename.format('org'), filename.format('new'))[1]
    nsupdater = nsupdate.NsUpdate.from_diff(minidiff)
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