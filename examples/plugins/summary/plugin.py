"""Owned example: a descriptive annotation, never a vulnerability diagnosis."""
def analyze(snapshot):
    registers = snapshot.get('registers', {})
    available = sum(value is not None for value in registers.values())
    return {'api_version': 1, 'annotations': [{'message':
        'Selected snapshot contains {} available registers; no write coverage inferred.'.format(available)}]}
