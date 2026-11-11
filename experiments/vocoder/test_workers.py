import json
import random
from bench import Worker, OUT

results = {}
for name in ['opendmr','blip25']:
    worker = Worker(name)
    try:
        rejected = 0
        for operation, size in [('E',0),('E',1),('E',319),('E',321),('D',0),('D',8),('D',10)]:
            try:
                worker.request(operation,bytes(size))
            except ValueError:
                rejected += 1
            else:
                raise AssertionError('invalid size accepted')
        assert rejected == 7
        worker.request('R')
        encoded,_,_ = worker.request('E',bytes(320))
        worker.request('D',encoded)
        for position in range(72):
            changed = bytearray(encoded)
            changed[position//8] ^= 1 << (7-position%8)
            worker.request('R')
            worker.request('D',changed)
        rng = random.Random(7)
        for _ in range(100):
            worker.request('D',bytes(rng.getrandbits(8) for _ in range(9)))
        worker.request('R')
        worker.request('D',worker.request('E',bytes(320))[0])
        results[name]={'invalidLengthsRejected':rejected,'singleBitPerturbationsNoCrash':72,'randomFramesNoCrash':100,'resetAndResume':True,'fecCorrectness':'not asserted; no independent reference'}
    finally:
        worker.close()
(OUT/'worker-tests.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results))
