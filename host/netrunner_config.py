"""Pure handoff configuration validation; no transport, credentials or execution.

A valid configuration is not deployment eligibility or receiver qualification.
AP/client credentials remain owned by the host; this module accepts none.
"""
from __future__ import annotations
SCHEMA = 'ascent.netrunner.usb_handoff.v1'
FIELDS = frozenset(('schema', 'enabled', 'usb_timeout_seconds', 'wifi_mode'))

class HandoffConfigError(ValueError):
    pass

def defaults() -> dict:
    return {'schema': SCHEMA, 'enabled': False, 'usb_timeout_seconds': 60, 'wifi_mode': 'AP'}

def validate(value: dict | None) -> dict:
    """Normalize a local draft; validity is never deployment eligibility."""
    if value is None:
        return defaults()
    if not isinstance(value, dict):
        raise HandoffConfigError('USB handoff settings must be an object')
    if set(value) - FIELDS:
        raise HandoffConfigError('Unknown USB handoff setting')
    result = dict(defaults(), **value)
    if result['schema'] != SCHEMA:
        raise HandoffConfigError('Unknown USB handoff settings version')
    if type(result['enabled']) is not bool:
        raise HandoffConfigError('Enabled must be true or false')
    timeout = result['usb_timeout_seconds']
    if type(timeout) is not int or not 5 <= timeout <= 600:
        raise HandoffConfigError('USB connection timeout must be 5..600 whole seconds')
    if result['wifi_mode'] not in ('AP', 'CLIENT'):
        raise HandoffConfigError('Wi-Fi mode must be AP or CLIENT')
    return result

def receiver_policy_config(value: dict | None) -> dict:
    """Values for the unconnected C policy API, not device commands."""
    config = validate(value)
    return {'enabled': config['enabled'], 'mode': config['wifi_mode'], 'usb_timeout_ms': config['usb_timeout_seconds'] * 1000, 'handoff_timeout_ms': 60000, 'restore_timeout_ms': 30000, 'max_sample_age_ms': 1500}
