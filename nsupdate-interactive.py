#!/usr/bin/python3

import os
import sys
import re
import argparse
import subprocess
import shlex
import shutil
import datetime


class DiffNoChangeError(Exception): pass


def parse_args():
    """ Parse command line arguments """
    parser = argparse.ArgumentParser(description='ExDiff')

    parser.add_argument('--zone', type=str, required=True)
    parser.add_argument('--dnsserver', type=str, required=True)

    return parser.parse_args()


def create_process(cmd):
    """ Execute a command """
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )


def dig_zonetransfer(dns_server, key, zone):
    """ Perform zone transfer to get the full list of all records in the zone """
    cmd = [ 'dig', '@'+dns_server, '-y', key, '-t', 'AXFR', zone ]
    proc = create_process(cmd)

    if proc.returncode != 0:
        raise Exception("Unexapected return code "+str(proc.returncode))

    return proc.stdout.decode('UTF-8')


def nsupdate(key, filename):
    """ Perform the nsupdate with a batch file """
    cmd = [ 'nsupdate', '-y', key, filename ]
    proc = create_process(cmd)

    if proc.returncode != 0:
        raise Exception("Unexapected return code "+str(proc.returncode))

    return proc.stdout.decode('UTF-8')


def diff(file1, file2):
    """ Diff two text files """
    cmd = [ 'diff', '-Naur', file1, file2 ]
    proc = create_process(cmd)

    if proc.returncode != 1:
        raise DiffNoChangeError("Unexapected return code "+str(proc.returncode))

    return proc.stdout.decode('UTF-8')


def get_columnlengths(digmatches):
    """ Get largest string for each column """
    columnlengths = [ -1 ]
    for i in range(1, 5):
        columnlengths.append(max(map(lambda x: len(x.group(i)), digmatches)))
    return columnlengths


def write_columns(file, widths, aligns, match):
    """ Write padded record into the batch file """
    for i in range(1, 6):
        coltxt = match.group(i)
        if aligns[i] == -1:
            coltxt = coltxt.rjust(widths[i], ' ')
        elif aligns[i] == 1:
            coltxt = coltxt.ljust(widths[i], ' ')

        file.write(coltxt+('' if i >= 5 else '  '))


def main():
    """ Main function of the script"""

    # get editor
    editor = os.environ.get('EDITOR', 'nano')

    # get hmac key
    hmackey = os.environ.get('HMAC')

    if hmackey is None:
        print("Environment variable 'HMAC' is required.")
        sys.exit(1)

    # parse arguments
    args = parse_args()

    # check for dependend programs
    binaries = [ editor, 'nsupdate', 'dig', 'diff' ]
    binarymissing = False
    for binary in binaries:
        if shutil.which(binary) is None:
            binarymissing = True
            print("The program '"+binary+"' is requied to use this script")

    if binarymissing:
        sys.exit(1)

    # base filename
    ts = datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'Z'
    filename = 'nsupdate_'+args.dnsserver+'_'+args.zone+'_'+ts+'.{0}'

    # record selector
    # it excludes some record types
    record_rgx = re.compile(r"^(?P<host>[^;\s]+\.)\s+(?P<ttl>[0-9]+)\s+(?P<class>[^\s]+)\s+(?P<type>(?:(?!SOA|TSIG))[^\s]+)\s+(?P<value>.+)$", re.I | re.M)

    # get zone records by calling dig
    dig = dig_zonetransfer(args.dnsserver, hmackey, args.zone)
    dig_lines = list(record_rgx.finditer(dig, 1))

    # calculate column widths to pad the columns
    columnalign = [ 0, -1, -1, 1, 1, 0 ]
    columnlengths = get_columnlengths(dig_lines)

    # create nsupdate batch file
    with open(filename.format('org'), 'w+') as f:

        # header
        f.write(';; nsupdate batch file generated at '+datetime.datetime.now().isoformat()+'\n')
        f.write(';; Zone: '+args.zone+'\n')

        f.write('\n')
        f.write('server '+args.dnsserver+'\n')
        f.write('\n')

        # delete list
        # all existing records to delete them
        f.write(';; Delete existing records\n')
        f.write(';; In the most cases you don\'t want to modify this lines\n')
        for line in dig_lines:
            f.write('update del ')
            write_columns(f, columnlengths, columnalign, line)
            f.write('\n')

        f.write('\n')

        # add list
        # all existing records to add them again
        f.write(';; Create new records\n')
        f.write(';; Feel free to add/modify records here\n')
        for line in dig_lines:
            f.write('update add ')
            write_columns(f, columnlengths, columnalign, line)
            f.write('\n')

        f.write('\n')

        # footer
        f.write('send\n')
        f.write('\n')
        f.write('; EOF\n')

    # create a working copy and open the editor
    shutil.copyfile(filename.format('org'), filename.format('new'))
    subprocess.call([ editor, filename.format('new') ])

    # show a diff between work copy and original
    diffresult = None
    try:
        diffresult = diff(filename.format('org'), filename.format('new'))
    except DiffNoChangeError:
        print("No changes made. Exit.")
        os.remove(filename.format('org'))
        os.remove(filename.format('new'))
        sys.exit(0)

    print(diffresult)

    with open(filename.format('patch'), 'w+') as f:
        f.write(diffresult)

    # ask befort continue with nsupdate
    input("Press Enter to continue...")

    # start nsupdate and process modified batch file
    print("Perform nsupdate...")
    print(nsupdate(hmackey, filename.format('new')))


# start main function
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # catch exception when script was canceled by CTRL+C
        pass
