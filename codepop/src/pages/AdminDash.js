import React from 'react';
import { View, Text } from 'react-native';
import NavBar from '../components/NavBar';

const AdminDash = () => {
  return (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
      <Text>Admin Dashboard</Text>
      <NavBar />
    </View>
  );
};

export default AdminDash;