# ASCENT Netrunner

This repository publishes the standalone source subset and host checks.
An installable Widget Manager package and receiver qualification are pending.
Real captures, prebuilt binaries, credential files and private bootstrap are excluded.
Run python3 -I run_host_checks.py --output <fresh-directory>.


This local source subset also contains a pure handoff configuration validator.
It accepts no network credentials or device commands and performs no file/device
I/O. Receiver profiles, qualification claims and deployment adapters are excluded.
Run its independent host checks with `python3 -m unittest discover -s tests`.
The native policy checks remain `python3 run_host_checks.py --output <fresh-dir>`.
This is not a complete widget, installer, hardware qualification or release.


The network input module validates caller-provided SSID/passphrase/channel and
IPv4 AP/DHCP fields locally. It does not store credentials, issue commands, change
routes or establish hardware/regulatory eligibility. It excludes receiver profiles
and routing integrations. Compared with the original host helper, this candidate
rejects unusable subnet/endpoints and normalizes invalid UTF-8 SSIDs to a typed
refusal. Original engineering runtime files remain unchanged; adoption is pending.

## MAX receiver build candidate

The build uses WPA Supplicant 2.10 and libnl-tiny at commit
`40493a655d8caa2ccf5206dde1e733abe2920432`. Place the pinned archives in the
input directory as `wpa-2.10.tar.gz` and `libnl-tiny-40493a65.tar.gz`.

```sh
mkdir /tmp/netrunner-max-build
bash receiver/build-max.sh /tmp/netrunner-inputs /tmp/netrunner-max-build /usr/bin/aarch64-linux-gnu-gcc
python3 receiver/package-max.py /tmp/netrunner-max-build/bin /tmp/netrunner-max.zip
```

The build retains the libraries, WPA build objects and configuration used for
relinking. The archive contains the two Wi-Fi executables and the ASCENT
channel probe. It uses static linkage and requires receiver qualification
before replacing the MAX binaries built against receiver-provided libraries.
