"""Usage: python3 scripts/show-marker-history.py CAPTURE.json. Read-only renderer."""
import json
import sys
with open(sys.argv[1]) as stream:
    capture = json.load(stream)
if capture.get('schema') != 'ressembly.marker-history.v1':
    raise SystemExit('Unsupported capture schema')
print('Explicit target markers; partial coverage; byte differences are not write events.')
print('Run:', capture['metadata'].get('run_id', 'unknown'))
print('Status:', capture['metadata'].get('acquisition_status', 'unknown'))
for event in capture['events']:
    print('#{} {} address={} object={} changed={} error={}'.format(
        event['sequence'], event['kind'], hex(event['address']) if 'address' in event else '?',
        event.get('object_id'), event.get('changed_offsets'), event.get('error')))
