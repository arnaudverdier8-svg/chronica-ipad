import React from 'react';
import {Composition} from 'remotion';
import {Test} from './Test';
export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="Test" component={Test} durationInFrames={60} fps={30} width={2560} height={1440} />
  </>
);
