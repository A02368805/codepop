import React from 'react';
import { View, Text } from 'react-native';
import NavBar from '../components/NavBar';

const ManagerDash = () => {
  return (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
      <Text>Manager Dashboard</Text>
      <NavBar />
    </View>
  );
};

export default ManagerDash;