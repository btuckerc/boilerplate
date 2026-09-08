"""Exercise accounting and send guards in a temporary project, never on a printer."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import ledger


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root/'plate.3mf').write_bytes(b'test-only-plate')
        self.state = {'schema':1,'revision':0,'run':'first','updated_at':ledger.now(),
                      'parts':{'arc':{'label':'Arc','required':12},'rib':{'label':'Rib','required':6},'key':{'label':'Key','required':12}},
                      'plates':{'plate-01':{'parts':{'arc':12,'rib':6},'file':'plate.3mf','sha256':hashlib.sha256(b'test-only-plate').hexdigest()},
                                'plate-02':{'parts':{'key':12},'file':'plate.3mf','sha256':hashlib.sha256(b'test-only-plate').hexdigest()}},
                      'production_order':['plate-01','plate-02'],'jobs':{},'printer':{},'events':[],
                      'runs':[],'notes':[],'calibration':{'evidence':'Test fit passed'}}
        self.serial = 0

    def tearDown(self):
        self.temp.cleanup()

    def event(self, kind, **values):
        self.serial += 1
        event = {'id':str(self.serial),'type':kind,'evidence':'test observation',**values}
        changed = copy.deepcopy(self.state)
        result = ledger.apply_event(changed, event, self.root)
        self.state = changed
        return event, result

    def ready(self):
        self.event('observe',state='idle')
        self.event('bed_clear')

    def start(self):
        self.ready()
        self.event('reserve',job='j1',plate='plate-01')

    def finish(self):
        self.start()
        self.event('observe',state='finished',job='j1',job_status='finished')

    def test_reservation_is_single_use_and_active_blocks(self):
        self.start()
        self.assertIsNone(self.state['printer']['bed_clear'])
        self.assertEqual(ledger.next_step(self.state)['action'],'check_active_job')
        with self.assertRaises(ValueError):
            self.event('reserve',job='j2',plate='plate-01')

    def test_cannot_send_without_fresh_idle_clear_bed(self):
        with self.assertRaises(ValueError): self.event('reserve',job='j1',plate='plate-01')
        self.ready()
        self.state['printer']['bed_clear']['at']='2000-01-01T00:00:00+00:00'
        with self.assertRaises(ValueError): self.event('reserve',job='j1',plate='plate-01')
        self.ready()
        self.state['printer']['observation']['state']='printing'
        with self.assertRaises(ValueError): self.event('reserve',job='j1',plate='plate-01')

    def test_completion_requires_physical_inspection(self):
        self.finish()
        self.assertEqual(ledger.inventory(self.state)['arc'],0)
        self.assertEqual(ledger.next_step(self.state)['action'],'inspect_parts')
        self.event('inspect',job='j1',good={'arc':12})
        self.assertEqual(ledger.next_step(self.state)['action'],'inspect_parts')

    def test_partial_reprint_and_later_breakage(self):
        self.finish()
        self.event('inspect',job='j1',good={'arc':12,'rib':5},bad={'rib':1})
        self.assertEqual(ledger.next_step(self.state)['parts'],{'rib':1})
        self.event('add_plate',plate='one-rib',parts={'rib':1},file='plate.3mf')
        self.assertEqual(ledger.next_step(self.state)['plate'],'one-rib')
        self.ready()
        with self.assertRaises(ValueError): self.event('reserve',job='j2',plate='plate-01')
        self.event('reserve',job='j2',plate='one-rib')
        self.event('observe',state='finished',job='j2',job_status='finished')
        self.event('inspect',job='j2',good={'rib':1})
        self.assertEqual(ledger.next_step(self.state)['plate'],'plate-02')
        self.event('inspect',job='j2',bad={'rib':1})
        self.assertEqual(ledger.remaining(self.state)['rib'],1)

    def test_idempotent_absolute_counts_and_invalid_counts(self):
        self.finish()
        event, _ = self.event('inspect',job='j1',good={'arc':12,'rib':6})
        self.assertFalse(ledger.apply_event(self.state,event,self.root))
        self.event('inspect',job='j1',good={'arc':12,'rib':6})
        self.assertEqual(ledger.inventory(self.state)['arc'],12)
        for bad in [{'arc':13},{'arc':-1},{'unknown':1},{'rib':1.5}]:
            with self.assertRaises(ValueError): self.event('inspect',job='j1',good=bad)
        with self.assertRaises(ValueError):
            ledger.apply_event(self.state,{**event,'good':{'arc':1}},self.root)

    def test_changed_file_rejected(self):
        self.ready()
        (self.root/'plate.3mf').write_bytes(b'changed')
        with self.assertRaises(ValueError): self.event('reserve',job='j1',plate='plate-01')

    def test_reset_preserves_busy_printer_and_history(self):
        self.start()
        self.event('reset',new_run='second')
        self.assertEqual(ledger.next_step(self.state)['action'],'check_active_job')
        self.event('observe',state='finished',job='j1',job_status='finished')
        self.event('inspect',job='j1',good={'arc':12,'rib':6})
        self.assertEqual(ledger.inventory(self.state)['arc'],0)
        self.assertEqual(ledger.next_step(self.state)['action'],'automation_paused')
        self.event('control',enabled=True)
        self.assertEqual(ledger.next_step(self.state)['plate'],'plate-01')
        self.assertIsNone(self.state['printer']['bed_clear'])
        self.assertEqual(self.state['runs'][0]['id'],'first')

    def test_complete_stops(self):
        self.finish()
        self.event('inspect',job='j1',good={'arc':12,'rib':6})
        self.ready()
        self.event('reserve',job='j2',plate='plate-02')
        self.event('observe',state='finished',job='j2',job_status='finished')
        self.event('inspect',job='j2',good={'key':12})
        self.assertEqual(ledger.next_step(self.state)['action'],'kit_complete')

    def test_validation_subset_keeps_send_guards(self):
        self.event('add_plate',plate='one-rib',parts={'rib':1},file='plate.3mf')
        with self.assertRaises(ValueError):
            self.event('reserve',job='test',plate='one-rib',purpose='validation_test')
        self.ready()
        with self.assertRaises(ValueError):
            self.event('reserve',job='test',plate='one-rib')
        self.event('reserve',job='test',plate='one-rib',purpose='validation_test')
        self.assertIsNone(self.state['printer']['bed_clear'])
        with self.assertRaises(ValueError):
            self.event('reserve',job='duplicate',plate='one-rib',purpose='validation_test')
        self.event('observe',state='finished',job='test',job_status='finished')
        with self.assertRaises(ValueError):
            self.event('reserve',job='uninspected',plate='one-rib',purpose='validation_test')
        self.event('inspect',job='test',good={'rib':1})
        self.assertEqual(ledger.remaining(self.state)['rib'],5)
        self.assertEqual(ledger.next_step(self.state)['parts'],{'arc':12,'rib':5})
        self.event('add_plate',plate='wrong-plate',parts={'key':1},file='plate.3mf')
        self.ready()
        with self.assertRaises(ValueError):
            self.event('reserve',job='wrong',plate='wrong-plate',purpose='validation_test')

    def test_cli_archive_reset_retry(self):
        path=self.root/'print_tracking/ledger.json'
        ledger.atomic_json(path,self.state)
        cmd=[sys.executable,str(Path(ledger.__file__).resolve()),'--project',str(self.root),'reset','--event-id','reset-one','--evidence','start from scratch']
        subprocess.run(cmd,check=True,capture_output=True)
        once=json.loads(path.read_text())
        subprocess.run(cmd,check=True,capture_output=True)
        twice=json.loads(path.read_text())
        self.assertEqual(once,twice)
        self.assertEqual(json.loads((path.parent/'history/revision-000000.json').read_text()),self.state)
        self.assertTrue((path.parent/'STATUS.md').exists())

if __name__=='__main__':
    unittest.main()
