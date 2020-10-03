from zoneutils import zonefile

class NsUpdate:
    """ Generate nsupdate batch files """

    def __init__(self, add=[], delete=[]):
        self.add = add
        self.delete = delete

    def get_nsupdate_batch(self, nameserver, zone):
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

    @staticmethod
    def from_diff(diff, addchar='+', delchar='-'):
        """ Create changeset from a zone file diff """

        add = []
        delete = []

        for line in diff.split('\n'):
            line = line.strip()
            if len(line) > 1:
                if line[0] == addchar:
                    add.append(zonefile.Record.from_string(line[1:]))
                elif line[0] == delchar:
                    delete.append(zonefile.Record.from_string(line[1:]))

        return NsUpdate(add, delete)
