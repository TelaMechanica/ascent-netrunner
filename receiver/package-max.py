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


BASIC_FILES = {
    '8188fu.ko': 'bba7c6739bb4839821c336255714439849b453d0b94197f4b32847422ce85ee1',
    'busybox': '3f278e53cfd24c4ea0a2bdd148a53bd974e1cb6e79904562d5a7d1b451c465bc',
    'hostapd': 'c6b43d30f51ebcdd98bdd57491520925deb0df08c3b538c7953fdcd039eeffa7',
    'hostapd_cli': '4623a4c9e37d48119feefd0ae9d228ac0fbe2b401045f7ff8d4243f8b9089a70',
}
PROFILE_PINS = {'pro-18.21.10': PRO_FILES, 'classic-gnd485-19.2.14': BASIC_FILES}


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('build_directory', type=Path)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--profile', choices=('max', *PROFILE_PINS), default='max')
    args = parser.parse_args()
    expected = PROFILE_PINS.get(args.profile)
    blobs = {name: (args.build_directory / name).read_bytes() for name in (expected or FILES)}
    digests = {name: sha256(data).hexdigest() for name, data in blobs.items()}
    if expected is not None and digests != expected:
        parser.error(f'{args.profile} packaging requires its reviewed binary inventory')
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
