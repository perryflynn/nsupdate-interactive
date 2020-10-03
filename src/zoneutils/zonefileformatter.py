class ZoneFileFormatter:

    def __init__(self):
        self.columns = 6
        self.columnalign = [ 1, -1, 1, 1, -1, 0 ]
        self.header = [ '; Name', 'TTL', 'Class', 'Type', 'Prio', 'Content' ]
        self.separator = '    '

    def format(self, zonefile):
        """ Prettify a zone file """

        lengths = self._get_columnlengths(zonefile)

        yield f'; <<>> DiG {zonefile.digversion} <<>> @{zonefile.nameserver} -t AXFR {zonefile.zone}'
        yield ''

        record_groups = self._get_groups(zonefile)
        record_prio = self._get_record_priorities(zonefile)
        records = sorted(zonefile.records, key=lambda x: self._record_sorter(x, record_prio))

        yield self._format_line(lengths, self.header)

        previous_group = None
        for record in records:
            group = next(filter(lambda x: record.dnsName in x['items'], record_groups))['mapname']
            if previous_group is not None and group != previous_group:
                yield ''

            yield self._format_line(lengths, record.as_array())
            previous_group = group

        yield ''
        yield ';; EOF'

    def _record_sorter(self, x, record_prio):
        reversename = '.'.join(x.dnsName.split('.')[::-1])
        typeprio = record_prio.index(x.dnsType)
        dnsprio = x.dnsPrio if x.dnsPrio else 0

        return (reversename, typeprio, dnsprio)

    def _get_record_priorities(self, zonefile):
        """ Define sorting priority for record types """

        record_prio = [ 'SOA', 'NS', 'CAA', 'A', 'AAAA', 'MX', 'SRV' ]
        for record in zonefile.records:
            if record.dnsType not in record_prio:
                record_prio.append(record.dnsType)

        return record_prio


    def _get_groups(self, zonefile):
        """ Group records in zone file by 3rd level domains """

        groups = []
        for record in zonefile.records:

            mapname = record.dnsName
            parts = record.dnsName.split('.')
            if len(parts) > 3:
                mapname = '.'.join(parts[-4:])

            group = None
            groupfilter = list(filter(lambda x: x['mapname'] == mapname, groups))
            if len(groupfilter) > 0:
                group = groupfilter[0]
                group['items'].append(record.dnsName)
            else:
                group = { 'mapname': mapname, 'items': [ record.dnsName ] }
                groups.append(group)

        return groups

    def _get_columnlengths(self, zonefile, includeheader=True):
        """ Get largest string for each column """

        columnlengths = [  ]
        for i in range(0, self.columns):
            maxlength = max(map(lambda x: len(str(x.get_by_index(i))), zonefile.records))

            if includeheader:
                maxlength = maxlength if maxlength > len(self.header[i]) else len(self.header[i])

            columnlengths.append(maxlength)

        return columnlengths

    def _format_line(self, widths, record):
        """ Write padded record into the batch file """

        line = ''

        for i in range(0, self.columns):
            coltxt = record[i]
            if coltxt is None:
                coltxt = ''
            else:
                coltxt = str(coltxt)

            if self.columnalign[i] == -1:
                coltxt = coltxt.rjust(widths[i], ' ')
            elif self.columnalign[i] == 1:
                coltxt = coltxt.ljust(widths[i], ' ')

            line = line + coltxt+('' if i >= len(self.columnalign) - 1 else self.separator)

        return line
