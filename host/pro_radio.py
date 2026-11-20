"""Exact Pro18.21.10 radio executor inputs; admission remains with the authenticated host.

Shared MAX access architecture does not select the radio GPIO or driver.
Bench provenance is recorded separately from integrated AC qualification.
"""
DEVICE='Ascent_VRX_pro'
FIRMWARE='Ascent_VRX_Pro_18_21_10'
HARDWARE='Ascent-VRX-Pro-V3.0-1.0'
GPIO=105
DRIVER='/lib/modules/RTL8189FU.ko'
DRIVER_SHA256='80fcb62724d243f6dc89d2ef812865e3c769d234b3d055e0fdb84a0d54b15609'
MODULE='RTL8189FU'


def client_deconfigure_command():
    # The stock hook removes the DHCP address and only wlan0-tagged DNS rows.
    # Run in the same SSH exchange as stopping the client: in the first live
    # positive trial new SSH connections stalled after the supplicant stopped.
    # The retest with this stock hook completed every subsequent off step.
    return ('if [ -d /sys/class/net/wlan0 ]; then '
            'interface=wlan0 /usr/share/udhcpc/default.script deconfig || exit 1; fi')


def matches(device_name,firmware):
    return device_name==DEVICE and firmware==FIRMWARE


def preflight_command():
    return ("test \"$(uname -r)\" = 5.10.198 && "
            "grep -Fxq BOARD_TYPE=VRX_PRO /etc/app.version && "
            "grep -Fxq APP_VERSION=18.21.10 /etc/app.version && "
            "test -x /usr/share/udhcpc/default.script && "
            f'test "$(sha256sum {DRIVER} | cut -d\' \' -f1)" = {DRIVER_SHA256}')


def radio_prepare_steps():
    return [
        {'step':'VERIFY_PRO_RADIO_PROFILE','describe':'Check the exact Pro firmware and stock driver','command':preflight_command()},
        {'step':'POWER_RADIO','describe':'Power the Pro Wi-Fi radio if it is off',
         'command':f'[ -d /sys/class/gpio/gpio{GPIO} ] || echo {GPIO} > /sys/class/gpio/export; '
                   f'if [ "$(cat /sys/class/gpio/gpio{GPIO}/value 2>/dev/null)" != 1 ] || '
                   f'[ "$(cat /sys/class/gpio/gpio{GPIO}/direction 2>/dev/null)" != out ]; then '
                   f'echo high > /sys/class/gpio/gpio{GPIO}/direction || exit 1; sleep 1; fi'},
        {'step':'LOAD_DRIVER','describe':'Load the stock Pro driver and verify wlan0 ownership',
         'command':f'if ! grep -q "^{MODULE} " /proc/modules; then insmod {DRIVER} || exit 1; fi; '
                   'nr_pro_wait=0; while [ ! -d /sys/class/net/wlan0 ] && [ "$nr_pro_wait" -lt 10 ]; do '
                   'sleep 1; nr_pro_wait=$((nr_pro_wait+1)); done; '
                   f'test "$(basename "$(readlink -f /sys/class/net/wlan0/device/driver/module)")" = {MODULE}'},
    ]


def radio_unload_command():
    return (f'if grep -q "^{MODULE} " /proc/modules; then rmmod {MODULE} || exit 1; fi; '
            f'! grep -q "^{MODULE} " /proc/modules')


def ap_configuration(conf):
    # Pro's observed adapter is 2.4 GHz. Channel permission still comes from
    # its own driver, not the MAX's discovered capabilities.
    rows=conf.splitlines()
    channel=int(next(x.split('=',1)[1] for x in rows if x.startswith('channel=')))
    if not 1<=channel<=13:
        from .network_validation import NetrunnerError
        raise NetrunnerError('CHANNEL_NOT_AVAILABLE','This Pro radio requires an available 2.4 GHz channel.')
    rows=[x for x in rows if not x.startswith('ht_capab=')]
    rows.append('ht_capab=[SHORT-GI-20]')
    return '\n'.join(rows)+'\n'
