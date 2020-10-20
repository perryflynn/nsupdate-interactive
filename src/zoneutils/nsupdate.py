from zoneutils import zonefile
from typing import List, Iterator

class NsUpdate:
    """ Generate nsupdate batch files """

    def __init__(self, add: List[zonefile.Record] = [], delete: List[zonefile.Record] = []):
        self.add = add
        self.delete = delete

    def get_nsupdate_batch(self, nameserver: str, zone: str) -> Iterator[str]:
        """ Create a nsupdate batch file """

        # SOA records must not be deleted
        itemsdelete = filter(lambda x: x.dnsType != 'SOA', self.delete)

        # SOA records always as the last operation
        itemsadd = sorted(self.add, key=lambda x: 1 if x.dnsType == 'SOA' else 0)

        yield '; nsupdate batch file'
        yield ''
        yield f'server {nameserver}'
        yield f'zone {zone}'

        for mode, block in [ ('del', itemsdelete), ('add', itemsadd) ]:
            for change in block:
                yield f'update {mode} {str(change)}'

        yield ''
        yield '; EOF'


def from_diff(diff: str, addchar: str = '> ', delchar: str = '< ') -> NsUpdate:
    """ Create changeset from a zone file diff """

    add = []
    delete = []

    for line in diff.split('\n'):
        line = line.strip()
        if len(line) > 1:
            # delete requests
            if line.startswith(delchar):
                temp = zonefile.from_string(line[len(delchar):])
                if temp:
                    delete.append(temp)
            # create requests
            elif line.startswith(addchar):
                temp = zonefile.from_string(line[len(addchar):])
                if temp:
                    add.append(temp)

    return NsUpdate(add, delete)
