import React from 'react';
import { View, Text } from 'react-native';
import NavBar from '../components/NavBar';

const UpdateDrink = () => {
  return (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
      <Text>UpdateDrink page</Text>
      <NavBar />
    </View>
  );
};

export default UpdateDrink;