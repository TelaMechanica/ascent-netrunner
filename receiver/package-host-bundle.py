"""Build an offline candidate by updating the host code in a reviewed bundle."""

from argparse import ArgumentParser
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
INPUT_SHA256 = '73917b484603d23cd04382be8ec49170390a45f7979dbe0a5333599454d0790f'
HOST_ENTRY = 'host/netrunner_observation.py'


def build(source, output):
    data = source.read_bytes()
    if sha256(data).hexdigest() != INPUT_SHA256:
        raise ValueError('Unexpected NetRunner qualification input digest')
    with ZipFile(BytesIO(data)) as original:
        entries = original.namelist()
        if entries.count(HOST_ENTRY) != 1:
            raise ValueError('The NetRunner host entry is missing or repeated')
        host = (ROOT / 'host/network_observation.py').read_bytes()
        with ZipFile(output, 'x') as archive:
            for name in sorted(entries):
                payload = host if name == HOST_ENTRY else original.read(name)
                archive.writestr(ZipInfo(name), payload, compress_type=ZIP_DEFLATED)
    return sha256(output.read_bytes()).hexdigest()


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('qualification_input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(build(args.qualification_input, args.output))
