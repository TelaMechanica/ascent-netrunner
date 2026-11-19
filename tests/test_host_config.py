"""Independent validation contracts; no connected receiver or credentials."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'host'))
import netrunner_config as config


class ConfigurationContract(unittest.TestCase):
    def test_default_is_disabled_and_observations_are_independent(self):
        first = config.defaults()
        self.assertFalse(first['enabled'])
        first['enabled'] = True
        self.assertFalse(config.defaults()['enabled'])
        self.assertFalse(config.validate(None)['enabled'])

    def test_seconds_to_milliseconds_at_both_limits(self):
        for seconds in (5, 60, 600):
            with self.subTest(seconds=seconds):
                result = config.receiver_policy_config({'enabled': True, 'usb_timeout_seconds': seconds, 'wifi_mode': 'CLIENT'})
                self.assertEqual(result['usb_timeout_ms'], seconds * 1000)
                self.assertEqual(result['mode'], 'CLIENT')
                self.assertEqual(result['handoff_timeout_ms'], 60000)
                self.assertEqual(result['restore_timeout_ms'], 30000)
                self.assertEqual(result['max_sample_age_ms'], 1500)

    def test_invalid_timeout_does_not_coerce_boolean_float_or_text(self):
        for value in (True, False, 4, 601, -1, 0, 5.0, '60', None):
            with self.subTest(value=value):
                with self.assertRaises(config.HandoffConfigError):
                    config.validate({'usb_timeout_seconds': value})

    def test_enable_requires_an_actual_boolean(self):
        for value in (0, 1, 'true', None):
            with self.subTest(value=value):
                with self.assertRaises(config.HandoffConfigError):
                    config.validate({'enabled': value})

    def test_credentials_commands_and_qualification_have_no_second_owner(self):
        for name in ('ssid', 'password', 'passphrase', 'command', 'gpio', 'device_name', 'hardware', 'qualified'):
            with self.subTest(name=name):
                with self.assertRaises(config.HandoffConfigError):
                    config.validate({name: 'synthetic-value'})
        self.assertFalse(hasattr(config, 'document'))
        self.assertFalse(hasattr(config, 'DEVICE'))
        self.assertFalse(hasattr(config, 'HARDWARE'))

    def test_schema_and_mode_are_explicit(self):
        for value in ('OFF', 'ap', None, 'AP; reboot'):
            with self.subTest(value=value):
                with self.assertRaises(config.HandoffConfigError):
                    config.validate({'wifi_mode': value})
        with self.assertRaises(config.HandoffConfigError):
            config.validate({'schema': 'unknown-version'})

    def test_validation_does_not_mutate_configuration_or_keep_unknown_fields(self):
        request = {'enabled': True, 'wifi_mode': 'AP'}
        result = config.validate(request)
        self.assertEqual(request, {'enabled': True, 'wifi_mode': 'AP'})
        self.assertEqual(set(result), {'schema', 'enabled', 'wifi_mode', 'usb_timeout_seconds'})
        result['enabled'] = False
        self.assertTrue(request['enabled'])


if __name__ == '__main__':
    unittest.main()
