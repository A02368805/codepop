import React from 'react';
import { View, Text } from 'react-native';
import NavBar from '../components/NavBar';

const CreateDrinkPage = () => {
  return (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
      <Text>Create Drink Screen</Text>
      <NavBar />
    </View>
  );
};

export default CreateDrinkPage;