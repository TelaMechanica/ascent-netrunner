"""Independent network input contracts; no sockets, receiver or credential store."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'host'))
import network_validation as network


def documented(**changes):
    return dict(address='192.0.2.1',netmask='255.255.255.0',dhcp_start='192.0.2.20',dhcp_end='192.0.2.254',**changes)


class NetworkInputContract(unittest.TestCase):
    def rejected(self, code, **changes):
        values=documented();values.update(changes)
        with self.assertRaises(network.NetrunnerError) as result:network.validate_ap_network(**values)
        self.assertEqual(result.exception.code,code)

    def test_valid_network_is_normalized_without_mutating_the_request(self):
        values=documented();before=dict(values);result=network.validate_ap_network(**values)
        self.assertEqual(values,before);self.assertEqual(result,values)
        result['address']='198.51.100.1';self.assertEqual(values,before)

    def test_dhcp_pool_must_be_ordered_in_subnet_and_exclude_the_router(self):
        self.rejected('DHCP_RANGE_OUT_OF_SUBNET',dhcp_end='198.51.100.20')
        self.rejected('DHCP_RANGE_EMPTY',dhcp_start='192.0.2.30',dhcp_end='192.0.2.20')
        self.rejected('AP_ADDRESS_IN_POOL',dhcp_start='192.0.2.1')

    def test_router_and_pool_cannot_use_network_or_broadcast_endpoints(self):
        for change in ({'address':'192.0.2.0'},{'address':'192.0.2.255'},
                       {'address':'192.0.2.200','dhcp_start':'192.0.2.0','dhcp_end':'192.0.2.100'},{'dhcp_end':'192.0.2.255'}):
            with self.subTest(change=change):self.rejected('AP_HOST_UNUSABLE',**change)

    def test_non_unicast_loopback_and_overbroad_subnets_are_refused(self):
        for prefix in ['0.0.0','127.0.0','224.0.0','240.0.0']:
            values={'address':prefix+'.1','netmask':'255.255.255.0','dhcp_start':prefix+'.20','dhcp_end':prefix+'.30'}
            with self.subTest(prefix=prefix),self.assertRaises(network.NetrunnerError) as result:
                network.validate_ap_network(**values)
            self.assertEqual(result.exception.code,'AP_SUBNET_UNUSABLE')
        self.rejected('AP_SUBNET_UNUSABLE',netmask='0.0.0.0')

    def test_management_subnet_overlap_remains_a_separate_required_guard(self):
        values=network.validate_ap_network(**documented())
        with self.assertRaises(network.NetrunnerError) as result:
            network.reject_management_subnet_overlap(values,['192.0.2.50'])
        self.assertEqual(result.exception.code,'AP_MANAGEMENT_SUBNET_OVERLAP')
        network.reject_management_subnet_overlap(values,['198.51.100.2'])

    def test_ssid_byte_limits_and_injection_refusals(self):
        self.assertEqual(network.validate_ssid('Ж'*16),'Ж'*16)
        for value in ['', ' ', ' leading', 'trailing ', 'a\nmode=0', 'a\x00b', 'Ж'*17, '\ud800']:
            with self.subTest(value=repr(value)),self.assertRaises(network.NetrunnerError):network.validate_ssid(value)

    def test_passphrases_are_local_inputs_and_errors_do_not_echo_them(self):
        self.assertEqual(network.validate_passphrase('fixture-passphrase'),'fixture-passphrase')
        for value in ['', 'short', 'synthetic\nsecret', 'Ж'*10, 'x'*64]:
            with self.subTest(length=len(value)),self.assertRaises(network.NetrunnerError) as result:
                network.validate_passphrase(value)
            if value:self.assertNotIn(value,str(result.exception))

    def test_channel_syntax_is_not_a_device_availability_claim(self):
        for channel in [1,6,11,36,149,165]:self.assertEqual(network.validate_channel(channel),channel)
        for channel in [True,False,0,14,35,166,'6',6.0]:
            with self.subTest(channel=channel),self.assertRaises(network.NetrunnerError):network.validate_channel(channel)
        self.assertFalse(hasattr(network,'mode_commands_for'))
        self.assertFalse(hasattr(network,'cot_source_policy'))
        self.assertFalse(hasattr(network,'ap_start_steps'))


if __name__=='__main__':unittest.main()
