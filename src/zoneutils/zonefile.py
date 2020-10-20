import re
from typing import Union
from datetime import datetime, timezone

RESOURCE_CLASSES = [ 'ANY', 'IN', 'CH', 'HS', 'CS' ]
RESOURCE_TYPE_RGX = re.compile(r"^[A-Z0-9]+$")
RECORD_WITHPRIO_RGX = re.compile(r"^\s*?(?P<host>[^;\s]+\.)\s+(?P<ttl>[0-9]+)\s+(?P<class>[^\s]+)\s+(?P<type>MX|SRV)(?:\s+(?P<prio>[0-9]+))?\s+(?P<content>.+)$", re.M | re.S)
RECORD_RGX = re.compile(r"^\s*?(?P<host>[^;\s]+\.)\s+(?P<ttl>[0-9]+)\s+(?P<class>[^\s]+)\s+(?P<type>(?:(?!TSIG|SRV|MX))[^\s]+)\s+(?P<content>.+)$", re.M | re.S)
DIG_ABOUT_RGX = re.compile(r"^\s*?^;\s+<<>>\s+DiG\s+(?P<digversion>[0-9.]+)[^<\s]*?\s+<<>>\s+@(?P<ns>[^\s]+)\s+-y\s+(?P<keytype>[^\s+]+)\s-t\s+AXFR\s+(?P<zone>[^\s]+)\s*?$", re.M | re.S)
SOACONTENT_RGX = re.compile(r"^\s*?(?P<primarydns>[^\s]+)\s+(?P<contact>[^\s]+)\s+(?P<serial>[0-9]+)\s+(?P<refresh>[0-9]+)\s+(?P<retry>[0-9]+)\s+(?P<expire>[0-9]+)\s+(?P<minttl>[^\s]+)\s*?$", re.M)


class ZoneRecordSyntaxError(Exception): pass
class InvalidZoneTypeError(Exception): pass


class Record(object):
    """ Represents one single record in a zone file """

    def __init__(self, dnsName=None, dnsTtl=3600, dnsClass='IN', dnsType=None, dnsPrio=None, dnsContent=None):
        self.dnsName = dnsName
        self.dnsTtl = dnsTtl
        self.dnsClass = dnsClass
        self.dnsType = dnsType
        self.dnsPrio = dnsPrio
        self.dnsContent = dnsContent

        if not self.dnsName.endswith('.'):
            self.dnsName = self.dnsName + '.'

        if self.dnsTtl < 0:
            raise ZoneRecordSyntaxError(f'{self.dnsTtl} is not a valid ttl')

        if not RESOURCE_TYPE_RGX.match(self.dnsType):
            raise ZoneRecordSyntaxError(f'{self.dnsType} is not a valid resource type')

        if self.dnsClass not in RESOURCE_CLASSES:
            raise ZoneRecordSyntaxError(f'{self.dnsClass} is not a valid record class')

    def as_array(self) -> list:
        """ Get record as list """

        return [
            self.dnsName,
            self.dnsTtl,
            self.dnsClass,
            self.dnsType,
            self.dnsPrio,
            self.dnsContent
        ]

    def get_by_index(self, index: int) -> Union[int, str]:
        """ Get record field by index """

        if index >= 0 and index < len(self.as_array()):
            return self.as_array()[index]

        return None

    def __str__(self) -> str:
        """ Convert record data back into a zone file record """

        prio = ' '+self.dnsPrio if self.dnsPrio else ''
        return f'{self.dnsName} {self.dnsTtl} {self.dnsClass} {self.dnsType}{prio} {self.dnsContent}'

    def __eq__(self, other):
        """ Compare with other record """

        if not isinstance(other, Record):
            raise NotImplementedError()

        return self.dnsName == other.dnsName and self.dnsTtl == other.dnsTtl \
            and self.dnsClass == other.dnsClass and self.dnsType == other.dnsType \
            and self.dnsPrio == other.dnsPrio and self.dnsContent == other.dnsContent


class SoaRecord(object):
    """ Special functionality for SOA records """

    def __init__(self, record: Record):
        self.record = record
        match = SOACONTENT_RGX.match(self.record.dnsContent)

        if self.record.dnsType != 'SOA' or not match:
            raise InvalidZoneTypeError(f'Record type must be SOA')

        self.soaPrimaryDns = match.group('primarydns')
        self.soaContact = match.group('contact')
        self.soaSerial = int(match.group('serial'))
        self.soaRefresh = int(match.group('refresh'))
        self.soaRetry = int(match.group('retry'))
        self.soaExpire = int(match.group('expire'))
        self.soaTtl = int(match.group('minttl'))

    def update_soa_content(self):
        """ Update content from soa properties """

        self.record.dnsContent = f'{self.soaPrimaryDns} {self.soaContact} {self.soaSerial} {self.soaRefresh} {self.soaRetry} {self.soaExpire} {self.soaTtl}'

    def apply_default_serialincrease(self):
        """ Apply date-style serial if this style is used """

        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        todaystr = now.strftime('%Y%m%d')

        # we assume date-style serial when
        # its parsable into datetime and not older than 5 years
        try:
            datepart = str(self.soaSerial)[0:8]
            serialdate = datetime.strptime(datepart, '%Y%m%d').replace(tzinfo=timezone.utc)

            if now >= serialdate and (now - serialdate).total_seconds() < 86400 * 365 * 5 and todaystr != datepart:
                self.soaSerial = int(f'{todaystr}00')
        except Exception:
            pass

        self.soaSerial += 1

    def __setattr__(self, prop, val):
        """ Trigger content update when a soa property is changed """

        super().__setattr__(prop, val)

        # ensure the update is only executed when all soa properties are available
        soafields = [ 'soaPrimaryDns', 'soaContact', 'soaSerial', 'soaRefresh', 'soaRetry', 'soaExpire', 'soaTtl' ]
        allset = len(list(filter(lambda x: x == False, map(lambda x: hasattr(self, x), soafields)))) < 1

        if allset and prop in soafields:
            self.update_soa_content()

    def __eq__(self, other):
        """ Compare with other SOA record instance """

        if not isinstance(other, SoaRecord):
            raise NotImplementedError()

        return super().__eq__(other) and self.soaPrimaryDns == other.soaPrimaryDns \
            and self.soaContact == other.soaContact and self.soaSerial == other.soaSerial \
            and self.soaRefresh == other.soaRefresh and self.soaRetry == other.soaRetry \
            and self.soaExpire == other.soaExpire and self.soaTtl == other.soaTtl


def from_string(recordstr: str) -> Record:
    """ Create record from zone file line """

    match = RECORD_WITHPRIO_RGX.match(recordstr)

    if match is None:
        match = RECORD_RGX.match(recordstr)

    if match:
        return Record(
            dnsName=match.group('host'),
            dnsTtl=int(match.group('ttl')),
            dnsClass=match.group('class'),
            dnsType=match.group('type'),
            dnsPrio=int(match.group('prio')) if 'prio' in match.groupdict().keys() else None,
            dnsContent=match.group('content')
        )

    return None


class ZoneFile:
    """ Represents all records from a AXFR query executed by dig """

    def __init__(self, zonefilestr: str):
        self.digversion = None
        self.nameserver = None
        self.zone = None
        self.querykeytype = None
        self.records = []

        info = DIG_ABOUT_RGX.match(zonefilestr)
        if info:
            self.digversion = info.group('digversion')
            self.nameserver = info.group('ns')
            self.zone = info.group('zone')
            self.querykeytype = info.group('keytype')

        soa = False
        for line in zonefilestr.split('\n'):
            r = from_string(line)

            if r and (soa == False or r.dnsType != 'SOA'):
                self.records.append(r)

                if soa == False and r.dnsType == 'SOA':
                    soa = True


def load(zonefile: str) -> ZoneFile:
    """ Load zone from a text file """

    with open(zonefile, 'r') as f:
        return ZoneFile(f.read())
