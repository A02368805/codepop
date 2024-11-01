import React, { useState, useEffect } from "react";
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import NavBar from '../components/NavBar';
import { useStripe, StripeProvider } from '@stripe/stripe-react-native';
import { useNavigation, NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

const CartPage = () => {
    const navigation = useNavigation();

    const goToCheckout = () => {
        navigation.navigate('Checkout');
      };

    return (
        <View style={styles.container}>
          <View style={styles.buttonContainer}>
            <TouchableOpacity onPress={goToCheckout} style={styles.mediumButton}>
              <Text style={styles.buttonText}>Checkout</Text>
            </TouchableOpacity>
          </View>
          <NavBar />
        </View>
      );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 0,
  },
  mediumButton: {
    margin: 20,
    padding: 15,
    backgroundColor: '#8df1d3',
    borderRadius: 10,
    alignItems: 'center',
  },
  buttonText: {
    fontSize: 16,
  },
});


export default CartPage;

