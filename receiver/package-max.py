"""Create a deterministic Netrunner MAX archive and its release file pins."""
from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

FILES = ('ascent_wifi_channels', 'wpa_cli', 'wpa_supplicant')


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('build_directory', type=Path)
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    blobs = {name: (args.build_directory / name).read_bytes() for name in FILES}
    with ZipFile(args.archive, 'x') as package:
        for name, data in blobs.items():
            entry = ZipInfo(name)
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            package.writestr(entry, data, compress_type=ZIP_DEFLATED, compresslevel=9)
    print(json.dumps({
        'sha256': sha256(args.archive.read_bytes()).hexdigest(),
        'files': {name: sha256(data).hexdigest() for name, data in blobs.items()},
    }, indent=2))


if __name__ == '__main__':
    main()
