import __main__ as _m; R = _m.R
exec(open(os.path.join(W, 'bench.py')).read())
bench([dict(fuzz=False, halo=0.0, ao=0.0), dict(fuzz=False, halo=1.0), dict(fuzz=True, halo=0.0), dict(fuzz=True, halo=1.0)], 'bench2.png')
