# Interactive nsupdate

This script allows to interactively edit DNS records
with [RFC2136](https://tools.ietf.org/html/rfc2136),
a HMAC key and `nsupdate`.

## Requirements

- `dig`
- `nsupdate`
- `diff`
- A HMAC key which is allowed to perform `update` and `transfer` to a DNS zone

## How it work

```sh
HMAC=hmac-sha256:my-awesome-keyname:THEKEYINBASE64FORMAT
./nsupdate-interactive.py --dnsserver ns1.example.com --zone example.com
```

The script will now generate a "delete all and add all again" batch file
for `nsupdate` and will open it in `$EDITOR` (fallback is `nano`).

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
`nsupdate` to execute the updates on the nameserver.

The patch is saved as a file in the current working directory.
