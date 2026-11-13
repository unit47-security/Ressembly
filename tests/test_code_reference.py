import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from ressembly import code_reference as cr

class CodeReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.binary=Path(self.temp.name)/'owned.elf'
        data=bytearray(256); data[:7]=b'\x7fELF\x02\x01\x01'
        struct.pack_into('<HHIQQQIHHHHHH',data,16,2,62,1,0x400080,64,0,0,64,56,1,64,0,0)
        struct.pack_into('<IIQQQQQQ',data,64,1,5,0,0x400000,0,len(data),len(data),4096)
        data[128:144]=bytes(range(16)); self.data=bytes(data); self.binary.write_bytes(data)
        self.reference=dict(schema='ressembly.code-reference.v1',module_sha256=hashlib.sha256(data).hexdigest(),
            file_offset=128,elf_virtual_address=0x400080,runtime_pc=0x55550080,mapping_start=0x55550000,
            mapping_end=0x55551000,mapping_offset=0,file_bytes_hex=data[128:144].hex(),run_id='boot:pid:start')
    def test_mapping_aslr_and_offset(self):
        self.assertEqual(cr.validate(self.reference,self.binary)['elf_virtual_address'],0x400080)
        other=dict(self.reference,runtime_pc=0x66660080,mapping_start=0x66660000,mapping_end=0x66661000)
        self.assertEqual(cr.validate(other,self.binary)['file_offset'],128)
    def test_inconsistent_build_range_bytes_rejected(self):
        for key,value in [('module_sha256','0'*64),('file_offset',129),('elf_virtual_address',0),
                          ('runtime_pc',1),('mapping_offset',4),('file_bytes_hex','00'*16),
                          ('runtime_pc',True),('file_offset',128.0),('run_id','')]:
            with self.subTest(key=key),self.assertRaises(ValueError): cr.validate(dict(self.reference,**{key:value}),self.binary)
    def test_non_executable_and_ambiguous_refused(self):
        data=bytearray(self.data); struct.pack_into('<I',data,68,4)
        with self.assertRaises(ValueError): cr.virtual_address(bytes(data),128)
        with self.assertRaises(ValueError): cr.virtual_address(self.data,len(self.data))
    def test_virtual_segment_overflow_rejected(self):
        data=bytearray(self.data); struct.pack_into('<Q',data,80,2**64-1)
        with self.assertRaisesRegex(ValueError,'overflows'):
            cr.virtual_address(bytes(data),128)

    def test_build_modification_detected(self):
        self.binary.write_bytes(self.data[:-1]+b'x')
        with self.assertRaisesRegex(ValueError,'hash'): cr.validate(self.reference,self.binary)

if __name__=='__main__': unittest.main()
