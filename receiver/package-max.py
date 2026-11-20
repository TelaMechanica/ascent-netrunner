"""Create a deterministic NetRunner archive and its release file pins."""
from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

FILES = ('ascent_wifi_channels', 'wpa_cli', 'wpa_supplicant')
PRO_FILES = {
    'ascent_wifi_channels': '081b5d0ab400fd163d6b9bc33c7233f68b5c0767a3a15ba180ab25614334bfe4',
    'wpa_cli': '3b1e5969dfa2b5b2248d5c480c4f5fbdc5df4df7e89fa168e39c3bd22de52720',
    'wpa_supplicant': '72d568262a0f440267a364a189f7c5ccf9a7e36b5b68aff4ae408daa795bb25a',
}


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('build_directory', type=Path)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--profile', choices=('max', 'pro-18.21.10'), default='max')
    args = parser.parse_args()
    blobs = {name: (args.build_directory / name).read_bytes() for name in FILES}
    digests = {name: sha256(data).hexdigest() for name, data in blobs.items()}
    if args.profile == 'pro-18.21.10' and digests != PRO_FILES:
        parser.error('Pro packaging requires the reviewed client tools for firmware 18.21.10')
    with ZipFile(args.archive, 'x') as package:
        for name, data in blobs.items():
            entry = ZipInfo(name)
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            package.writestr(entry, data, compress_type=ZIP_DEFLATED, compresslevel=9)
    print(json.dumps({
        'sha256': sha256(args.archive.read_bytes()).hexdigest(),
        'files': digests,
        **({'profile': args.profile} if args.profile != 'max' else {}),
    }, indent=2))


if __name__ == '__main__':
    main()
