import sys, time; sys.path.insert(0,'.')
from emb.scene import build
sc=build(force=True)
print({k:(v.shape if hasattr(v,'shape') else v) for k,v in sc['canvas'].items()})
print('fib0',sc['fib0']['P'].shape,'fib1',sc['fib1']['P'].shape)
