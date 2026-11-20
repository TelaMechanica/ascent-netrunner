# ASCENT Netrunner

This repository publishes the standalone source subset and host checks.
Standalone Widget Manager releases are pending. See the receiver status below.
Real captures, prebuilt binaries, credential files and private bootstrap are excluded.
Run python3 -I run_host_checks.py --output <fresh-directory>.


This local source subset also contains a pure handoff configuration validator.
It accepts no network credentials or device commands and performs no file/device
I/O. Receiver-specific support is listed below.
Run its independent host checks with `python3 -m unittest discover -s tests`.
The native policy checks remain `python3 run_host_checks.py --output <fresh-dir>`.
This is not a complete widget, installer, hardware qualification or release.


The network input module validates caller-provided SSID/passphrase/channel and
IPv4 AP/DHCP fields locally. It does not store credentials, issue commands, change
routes or establish hardware/regulatory eligibility. Compared with the original host helper, this candidate
rejects unusable subnet/endpoints and normalizes invalid UTF-8 SSIDs to a typed
refusal. Original engineering runtime files remain unchanged; adoption is pending.

## Receiver status

| Receiver | Integrated behavior and standalone status |
| --- | --- |
| Basic / Classic VRX | Integrated AC+ has a separate, time-limited guarded AP workflow for an exact Basic / Classic profile. Standalone packaging and a full AP/client/off lifecycle are pending. |
| VRX Pro | Integrated AC+ bench evidence covers AP, client, and off on firmware 18.21.10. The Pro radio profile and command builders are included in `host/pro_radio.py`. Standalone packaging and Widget Manager lifecycle qualification are pending. |
| VRX MAX | The standalone MAX build candidate is below. Its archive and Widget Manager lifecycle still require on-device qualification. |

### MAX receiver build candidate

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
