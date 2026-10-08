cd /tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/rnd/hybridplane
export MAPSDIR=maps_v2
nice -n 5 python3 tools/make_linen.py && nice -n 5 python3 tools/make_king.py 16 && nice -n 5 python3 tools/make_knight.py
python3 -c "
import cv2, numpy as np
for n in ['king_normal','knight_normal','ghost_normal','linen_normal','ground_var']:
    a=cv2.imread('maps_v2/'+n+'.png', cv2.IMREAD_UNCHANGED).astype(np.float32)/65535
    r=np.random.default_rng(1); d=(r.random(a.shape)-r.random(a.shape))/255
    cv2.imwrite('maps_v2/'+n+'8.png', np.clip((a+d)*255+0.5,0,255).astype(np.uint8))
"
echo MAPS_V2_DONE
