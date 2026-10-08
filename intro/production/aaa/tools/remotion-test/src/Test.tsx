import React from 'react';
import {AbsoluteFill, Audio, Img, staticFile, useCurrentFrame, interpolate} from 'remotion';
export const Test: React.FC = () => {
  const frame = useCurrentFrame();
  const src = staticFile(`frames/f_${String(frame).padStart(4, '0')}.png`);
  const scale = interpolate(frame, [0, 59], [1, 1.08]);
  return (
    <AbsoluteFill style={{backgroundColor: 'black'}}>
      <Img src={src} style={{width: '100%', height: '100%', transform: `scale(${scale})`}} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{fontSize: 140, color: '#f3e3b5', fontFamily: 'serif', textShadow: '0 4px 20px #000', opacity: interpolate(frame, [0, 20], [0, 1], {extrapolateRight: 'clamp'})}}>CHRONICA {frame}</div>
      </AbsoluteFill>
      {/* audio offset: start 10 s into the mp3 (startFrom is in frames; deprecated alias of trimBefore) */}
      <Audio src={staticFile('audio.mp3')} startFrom={300} />
    </AbsoluteFill>
  );
};
