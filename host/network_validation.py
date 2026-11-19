"""Trusted-host network input validation, never execution or credential storage.

Channel syntax does not establish regulatory/device availability. No receiver
profiles, routes, transport or command builders are included.
"""
from __future__ import annotations

class NetrunnerError(RuntimeError):

    def __init__(self, code: str, message: str, evidence: dict | None=None):
        super().__init__(message)
        self.code, self.evidence = (code, evidence or {})
AP_ADDRESS = '192.168.0.1'
AP_NETMASK = '255.255.255.0'
AP_DHCP_START = '192.168.0.20'
AP_DHCP_END = '192.168.0.254'
AP_DEFAULT_CHANNEL = 6
SSID_MAX = 32
PSK_MIN, PSK_MAX = (8, 63)

def _validate_ssid_value(ssid) -> str:
    """1..32 bytes, printable, no newline.

    It becomes a line in a config file, so a newline would let an operator add
    arbitrary hostapd directives by typing them into the SSID box. Checked here
    rather than escaped at the point of use.
    """
    if not isinstance(ssid, str) or not ssid:
        raise NetrunnerError('SSID_REQUIRED', 'an SSID is required')
    raw = ssid.encode('utf-8')
    if len(raw) > SSID_MAX:
        raise NetrunnerError('SSID_TOO_LONG', f'an SSID is at most {SSID_MAX} bytes; this is {len(raw)}')
    if any((ord(c) < 32 or ord(c) == 127 for c in ssid)):
        raise NetrunnerError('SSID_INVALID', 'an SSID cannot contain control characters')
    if ssid.strip() != ssid:
        raise NetrunnerError('SSID_INVALID', 'an SSID cannot begin or end with a space')
    return ssid

def validate_passphrase(psk) -> str:
    """WPA2-PSK: 8..63 printable ASCII, which is the standard's own range."""
    if not isinstance(psk, str) or not psk:
        raise NetrunnerError('PASSPHRASE_REQUIRED', 'a passphrase is required')
    if not PSK_MIN <= len(psk) <= PSK_MAX:
        raise NetrunnerError('PASSPHRASE_LENGTH', f'a WPA2 passphrase is {PSK_MIN} to {PSK_MAX} characters; this is {len(psk)}')
    if any((ord(c) < 32 or ord(c) > 126 for c in psk)):
        raise NetrunnerError('PASSPHRASE_INVALID', 'a WPA2 passphrase must be printable ASCII')
    return psk

def validate_channel(channel) -> int:
    if channel is None:
        return AP_DEFAULT_CHANNEL
    if isinstance(channel, bool) or not isinstance(channel, int) or channel not in tuple(range(1, 14)) + tuple(range(36, 145, 4)) + (149, 153, 157, 161, 165):
        raise NetrunnerError('CHANNEL_UNSUPPORTED', 'Choose a valid 2.4 or 5 GHz Wi-Fi channel; the receiver must also report it available for AP hosting.')
    return channel

def default_ap_net() -> dict:
    """The AP network an operator gets if they set nothing. Exposed in the
    document so the UI can prefill the fields with the real defaults rather than
    hardcoding them a second time."""
    return {'address': AP_ADDRESS, 'netmask': AP_NETMASK, 'dhcp_start': AP_DHCP_START, 'dhcp_end': AP_DHCP_END}

def _validate_ap_network_shape(*, address=AP_ADDRESS, netmask=AP_NETMASK, dhcp_start=AP_DHCP_START, dhcp_end=AP_DHCP_END) -> dict:
    """Normalize caller-supplied AP addressing; no network/device operation."""
    import ipaddress
    try:
        ip = ipaddress.IPv4Address(str(address))
    except ValueError:
        raise NetrunnerError('AP_ADDRESS_INVALID', f'{address!r} is not an IPv4 address') from None
    try:
        net = ipaddress.IPv4Network(f'{ip}/{netmask}', strict=False)
    except (ValueError, ipaddress.NetmaskValueError):
        raise NetrunnerError('AP_NETMASK_INVALID', f'{netmask!r} is not a valid netmask') from None
    try:
        start = ipaddress.IPv4Address(str(dhcp_start))
        end = ipaddress.IPv4Address(str(dhcp_end))
    except ValueError:
        raise NetrunnerError('DHCP_RANGE_INVALID', f'the DHCP range {dhcp_start!r}..{dhcp_end!r} is not a pair of IPv4 addresses') from None
    for label, a in (('start of the DHCP range', start), ('end of the DHCP range', end)):
        if a not in net:
            raise NetrunnerError('DHCP_RANGE_OUT_OF_SUBNET', f'the {label} ({a}) is not in the {net} subnet the access point serves')
    if int(start) > int(end):
        raise NetrunnerError('DHCP_RANGE_EMPTY', f'the DHCP range start ({start}) is after its end ({end})')
    if int(start) <= int(ip) <= int(end):
        raise NetrunnerError('AP_ADDRESS_IN_POOL', f"the access point's own address ({ip}) is inside its DHCP pool ({start}..{end}); it must sit outside the pool")
    return {'address': str(ip), 'netmask': str(net.netmask), 'dhcp_start': str(start), 'dhcp_end': str(end)}

def reject_management_subnet_overlap(network, management_addresses):
    """An AP subnet must not replace the route carrying this management link."""
    import ipaddress
    subnet = ipaddress.IPv4Network(network['address'] + '/' + network['netmask'], strict=False)
    for address in management_addresses:
        if not address:
            continue
        try:
            overlaps = ipaddress.IPv4Address(address) in subnet
        except ipaddress.AddressValueError:
            continue
        if overlaps:
            raise NetrunnerError('AP_MANAGEMENT_SUBNET_OVERLAP', 'The Wi-Fi subnet overlaps this receiver’s USB management link. Choose a different Wi-Fi subnet before applying.')


def validate_ssid(value):
    try:
        return _validate_ssid_value(value)
    except UnicodeError:
        raise NetrunnerError('SSID_INVALID', 'An SSID must be valid UTF-8 text') from None


def validate_ap_network(**values):
    """Reject unusable AP/DHCP endpoints; this is not deployment eligibility."""
    import ipaddress
    result = _validate_ap_network_shape(**values)
    subnet = ipaddress.IPv4Network(result['address'] + '/' + result['netmask'], strict=False)
    forbidden = ('0.0.0.0/8', '127.0.0.0/8', '224.0.0.0/4', '240.0.0.0/4')
    if any(subnet.overlaps(ipaddress.IPv4Network(block)) for block in forbidden):
        raise NetrunnerError('AP_SUBNET_UNUSABLE', 'The AP subnet includes non-unicast or loopback addresses')
    endpoints = [ipaddress.IPv4Address(result[name]) for name in ('address', 'dhcp_start', 'dhcp_end')]
    if any(value in (subnet.network_address, subnet.broadcast_address) for value in endpoints):
        raise NetrunnerError('AP_HOST_UNUSABLE', 'The AP and DHCP endpoints must be usable host addresses')
    return result
