import resource, subprocess, sys, os, time
t = time.time()
p = subprocess.run(['nice', '-n', '5', 'python3', 'src/render_keyframe.py'], env=dict(os.environ, F669_OUT=os.path.abspath('work/det')), capture_output=True, text=True)
ru = resource.getrusage(resource.RUSAGE_CHILDREN)
print('exit', p.returncode, 'wall %.1fs' % (time.time() - t), 'peak RSS %.2f GB' % (ru.ru_maxrss / 1048576))
print(p.stderr[-300:])
