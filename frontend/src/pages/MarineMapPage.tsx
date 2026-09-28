import React from 'react';
import { MarineMap } from '../components/map/MarineMap';

interface MarineMapPageProps {
  onAskAboutLocation?: (lat: number, lon: number) => void;
}

export const MarineMapPage: React.FC<MarineMapPageProps> = ({ onAskAboutLocation }) => {
  return (
    <div
      style={{
        width: '100%',
        height: 'calc(100vh - var(--nav-height))',
        position: 'relative',
        backgroundColor: '#07101c',
      }}
    >
      <MarineMap onAskAboutLocation={onAskAboutLocation} />
    </div>
  );
};
