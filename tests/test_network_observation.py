import subprocess
import unittest

from host.network_observation import PREFIX, SECTIONS, command, parse


class NetworkObservationTest(unittest.TestCase):
    def setUp(self):
        self.probes = {name: f'printf "{name}\\n"' for name in SECTIONS}
        self.reply = subprocess.check_output(
            ['sh', '-c', command(self.probes)], text=True, timeout=3)

    def test_complete_read_round_trips_all_probe_outputs(self):
        self.assertEqual(parse(self.reply, self.probes), {
            probe: {'stdout': name} for name, probe in self.probes.items()
        })

    def test_partial_duplicate_and_failed_reads_are_rejected(self):
        for reply in (self.reply.replace(f'{PREFIX} COMPLETE\n', ''),
                      self.reply + self.reply,
                      self.reply.replace(f'{PREFIX} END tools 0',
                                         f'{PREFIX} END tools 1')):
            with self.subTest(reply=reply), self.assertRaises(ValueError):
                parse(reply, self.probes)

    def test_missing_profile_probe_is_rejected_before_execution(self):
        self.probes.pop('startup')
        with self.assertRaises(ValueError):
            command(self.probes)
