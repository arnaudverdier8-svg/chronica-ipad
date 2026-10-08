# usage: python3 timeit.py LOG -- cmd...  ; prints wall, user, sys CPU of the child tree, max RSS
import sys, subprocess, time, resource
log = sys.argv[1]; cmd = sys.argv[sys.argv.index('--')+1:]
t = time.time()
with open(log, 'w') as f:
    rc = subprocess.call(cmd, stdout=f, stderr=subprocess.STDOUT)
w = time.time() - t
r = resource.getrusage(resource.RUSAGE_CHILDREN)
msg = f'TIMEIT rc={rc} wall={w:.1f}s user={r.ru_utime:.1f}s sys={r.ru_stime:.1f}s cpu={r.ru_utime+r.ru_stime:.1f}s maxrss={r.ru_maxrss/1024:.0f}MB avg_cores={(r.ru_utime+r.ru_stime)/w:.2f}'
with open(log, 'a') as f: f.write(msg + '\n')
print(msg)
