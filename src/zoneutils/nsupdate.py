from zoneutils import zonefile
from typing import List, Iterator

class NsUpdate:
    """ Generate nsupdate batch files """

    def __init__(self, add: List[zonefile.Record] = [], delete: List[zonefile.Record] = []):
        self.add = add
        self.delete = delete

    def get_nsupdate_batch(self, nameserver: str, zone: str) -> Iterator[str]:
        """ Create a nsupdate batch file """

        yield '; nsupdate batch file'
        yield ''
        yield f'server {nameserver}'
        yield f'zone {zone}'

        for mode, block in [ ('del', self.delete), ('add', self.add) ]:
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
            if line.startswith(delchar):
                delete.append(zonefile.from_string(line[len(delchar):]))
            elif line.startswith(addchar):
                add.append(zonefile.from_string(line[len(addchar):]))

    return NsUpdate(add, delete)
