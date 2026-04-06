// Web stub for react-native-maps
import React from 'react';
import { View, Text } from 'react-native';

const MapView = ({ children, style }) => (
  React.createElement(View, { style: [{ backgroundColor: '#e0e0e0', alignItems: 'center', justifyContent: 'center' }, style] },
    React.createElement(Text, null, 'Map not available on web'),
    children
  )
);

export const Marker = () => null;
export const PROVIDER_GOOGLE = 'google';
export default MapView;
