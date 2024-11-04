import React from 'react';
import { View, Text } from 'react-native';
import NavBar from '../components/NavBar';

const PaymentPage = () => {
  return (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
      <Text>Payment Page</Text>
      <NavBar />
    </View>
  );
};

export default PaymentPage;