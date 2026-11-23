"""Frame the existing NetRunner read probes and verify their complete reply."""

PREFIX = 'ASCENT_NETWORK_OBSERVATION_V1'
SECTIONS = ('interfaces', 'ap', 'channels', 'forwarding',
            'hardware', 'tools', 'client', 'startup')


def command(probes):
    """Combine trusted profile-specific read commands into one observation."""
    if probes.keys() != set(SECTIONS):
        raise ValueError('Incomplete network observation probe set')
    parts = []
    for name in SECTIONS:
        parts.append(
            f"printf '\\n{PREFIX} BEGIN {name}\\n'; ( {probes[name]}\n); "
            f"nr_read_rc=$?; printf '\\n{PREFIX} END {name} %s\\n' \"$nr_read_rc\""
        )
    return ';\n'.join(parts) + f";\nprintf '{PREFIX} COMPLETE\\n'"


def parse(text, probes):
    """Accept the existing output format only after every probe completes."""
    if probes.keys() != set(SECTIONS):
        raise ValueError('Incomplete network observation probe set')
    values = {}
    name = None
    lines = []
    complete = False
    for line in (text or '').splitlines():
        if line.startswith(PREFIX + ' '):
            words = line.split()
            if words == [PREFIX, 'COMPLETE']:
                if name is not None or values.keys() != probes.keys() or complete:
                    raise ValueError('Incomplete or duplicate network observation')
                complete = True
            elif len(words) == 3 and words[1] == 'BEGIN':
                if complete or name is not None or words[2] not in probes or words[2] in values:
                    raise ValueError('Unexpected network section')
                name = words[2]
                lines = []
            elif len(words) == 4 and words[1] == 'END':
                if complete or name != words[2] or words[3] != '0':
                    raise ValueError('Network section did not complete')
                values[name] = '\n'.join(lines).strip()
                name = None
            else:
                raise ValueError('Malformed network observation marker')
        elif name is not None:
            lines.append(line)
        elif line.strip():
            raise ValueError('Unexpected network observation data')
    if not complete:
        raise ValueError('Network observation completion missing')
    return {probes[key]: {'stdout': value} for key, value in values.items()}
