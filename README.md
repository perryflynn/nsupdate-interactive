# Interactive nsupdate

This script allows to interactively edit DNS records
with [RFC2136](https://tools.ietf.org/html/rfc2136),
a HMAC key and `nsupdate`.

## Requirements

- `dig`
- `nsupdate`
- `diff`
- `colordiff`
- `named-checkzone`
- A HMAC key which is allowed to perform `update` and `transfer` to a DNS zone

### Install packages on Ubuntu

```sh
apt install dnsutils diffutils colordiff bind9utils
```

### `named-checkzone` was not found but package is installed

On Debian `named-checkzone` is located in `/usr/sbin`. As normal user
you need to add the path to your `$PATH` variable or create a synlink
in `/usr/bin` so that the Shell and the Tool can find the executable.

## Parameters

```txt
usage: nsupdate-interactive.py [-h] --zone ZONE [--dnsserver DNSSERVER]

nsupdate-interactive

optional arguments:
  -h, --help            show this help message and exit
  --zone ZONE
  --dnsserver DNSSERVER
```

## How it work

```sh
HMAC=hmac-sha256:my-awesome-keyname:THEKEYINBASE64FORMAT
./nsupdate-interactive.py --zone example.com
```

The script will detect the authoritative name server of the specified
zone by its SOA record and will generate a pretty formatted zone file.
The file will be opened in `$EDITOR` (fallback is `nano`) afterwards.

After saving the file it will show a diff:

```diff
--- nsupdate_ns1.example.com_example.com_20200926T222019Z.org	2020-09-26 22:20:19.369097326 +0200
+++ nsupdate_ns1.example.com_example.com_20200926T222019Z.new	2020-09-26 22:20:33.768947883 +0200
@@ -49,7 +49,7 @@
 ;; Create new records
 ;; Feel free to add/modify records here
 update add                  example.com.   900  IN  TXT   "v=spf1 +mx -all"
-update add                  example.com.   900  IN  TXT   "Hello Nerds, how are you going?"
+update add                  example.com.   900  IN  TXT   "Hello Nerds, how are you going? :-)"
 update add                  example.com.  3600  IN  MX    10 example.com.
 update add                  example.com.  3600  IN  AAAA  ::1
 update add                  example.com.  3600  IN  A     127.0.0.1
```

If the diff is approved with hitting `ENTER`, the script will use
the diff to generate a `nsupdate` batch file and send it to
the nameserver.

The diff and the generated nsupdate batch file are saved as text files
in the current working directory.
