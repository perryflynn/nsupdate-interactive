import re

RESOURCE_CLASSES = [ 'ANY', 'IN', 'CH', 'HS', 'CS' ]
RESOURCE_TYPE_RGX = re.compile(r"^[A-Z0-9]+$")
RECORD_WITHPRIO_RGX = re.compile(r"^\s*?(?P<host>[^;\s]+\.)\s+(?P<ttl>[0-9]+)\s+(?P<class>[^\s]+)\s+(?P<type>MX|SRV)(?:\s+(?P<prio>[0-9]+))?\s+(?P<content>.+)$", re.M | re.S)
RECORD_RGX = re.compile(r"^\s*?(?P<host>[^;\s]+\.)\s+(?P<ttl>[0-9]+)\s+(?P<class>[^\s]+)\s+(?P<type>(?:(?!TSIG|SRV|MX))[^\s]+)\s+(?P<content>.+)$", re.M | re.S)
DIG_ABOUT_RGX = re.compile(r"^\s*?^;\s+<<>>\s+DiG\s+(?P<digversion>[0-9.]+)[^<\s]*?\s+<<>>\s+@(?P<ns>[^\s]+)\s+-y\s+(?P<keytype>[^\s+]+)\s-t\s+AXFR\s+(?P<zone>[^\s]+)\s*?$", re.M | re.S)


class ZoneRecordSyntaxError(Exception): pass


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

    def as_array(self):
        return [
            self.dnsName,
            self.dnsTtl,
            self.dnsClass,
            self.dnsType,
            self.dnsPrio,
            self.dnsContent
        ]

    def get_by_index(self, index):
        if index >= 0 and index < len(self.as_array()):
            return self.as_array()[index]

        return None

    def __str__(self):
        prio = ' '+self.dnsPrio if self.dnsPrio else ''
        return f'{self.dnsName} {self.dnsTtl} {self.dnsClass} {self.dnsType}{prio} {self.dnsContent}'

    @staticmethod
    def from_string(recordstr):
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

    def __init__(self, zonefilestr):
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
            r = Record.from_string(line)

            if r and (soa == False or r.dnsType != 'SOA'):
                self.records.append(r)

                if soa == False and r.dnsType == 'SOA':
                    soa = True
