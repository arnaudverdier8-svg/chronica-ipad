import struct,sys,zstandard,glob,os
def unrscc(d):
    assert d[:4]==b'RSCC'
    mode,bs,total=struct.unpack('<III',d[4:16])
    nb=(total+bs-1)//bs
    sizes=struct.unpack('<%dI'%nb,d[16:16+4*nb])
    p=16+4*nb; out=bytearray()
    dc=zstandard.ZstdDecompressor()
    for i,s in enumerate(sizes):
        blk=d[p:p+s]; p+=s
        want=min(bs,total-len(out))
        out+=dc.decompress(blk,max_output_size=want)
    assert len(out)==total,(len(out),total)
    return bytes(out)
if __name__=='__main__':
    for fn in sorted(glob.glob('*.glb.scn')):
        r=unrscc(open(fn,'rb').read())
        open(fn.replace('.scn','.rsrc'),'wb').write(r)
        print(fn,len(r),r[:4])
