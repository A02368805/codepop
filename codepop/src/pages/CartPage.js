import React from 'react';
import { View, Text } from 'react-native';
import NavBar from '../components/NavBar';

const CartPage = () => {
  return (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
      <Text>Cart Screen</Text>
      <NavBar />
    </View>
  );
};

export default CartPage;