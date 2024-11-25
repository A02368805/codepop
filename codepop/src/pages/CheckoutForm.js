import { useState } from 'react';
import { Alert } from 'react-native';
import { useStripe } from '@stripe/stripe-react-native';
import { BASE_URL } from '../../ip_address';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useNavigation } from '@react-navigation/native';

// todo
  // test the removeAllDrinks function

export default function CheckoutForm(totalPrice) {
  const navigation = useNavigation();
  const [drinks, setDrinks] = useState([]);

  const { initPaymentSheet, presentPaymentSheet } = useStripe();
  const [loading, setLoading] = useState(false);

  const fetchPaymentSheetParams = async () => {
    const response = await fetch(`${BASE_URL}/backend/create-payment-intent/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount: totalPrice }), // amount in cents
    });
    const { paymentIntent, ephemeralKey, customer } = await response.json();
    return { paymentIntent, ephemeralKey, customer };
  };

  const initializePaymentSheet = async () => {
    const { paymentIntent, ephemeralKey, customer } = await fetchPaymentSheetParams();
    const { error } = await initPaymentSheet({
      merchantDisplayName: "Example, Inc.",
      customerId: customer,
      customerEphemeralKeySecret: ephemeralKey,
      paymentIntentClientSecret: paymentIntent,
      allowsDelayedPaymentMethods: true,
    });
    if (!error) setLoading(true);
    else Alert.alert("Error", error.message);
  };

  // function to remove all drinks from cart list after sucessful checkout
  const removeAllDrinks = async () => {
    try {
      const cartList = await AsyncStorage.getItem('checkoutList');
      const currentList = cartList ? JSON.parse(cartList) : [];
      const token = await AsyncStorage.getItem('userToken');

      // loop through cart list
      for (let i = 0; i < currentList.length; i++) {
        // Delete the drink from the backend database
        await fetch(`${BASE_URL}/backend/drinks/${currentList[i]}/`, {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Token ${token}`,
          },
        });
        // Update the local state to remove the drink from the cart page
        const updatedDrinks = drinks.filter(data => data.DrinkID !== drinkId);
        setDrinks(updatedDrinks);
    
        // Update the AsyncStorage to remove the drink ID from the checkout list
        const updatedList = currentList.filter(item => item !== currentList[i]);
        await AsyncStorage.setItem("checkoutList", JSON.stringify(updatedList));
      }

      console.log("cart cleared sucessfully");
      
    } catch (error) {
      console.error('Error removing drinks from cart:', error);
    }
  };

  const openPaymentSheet = async () => {
    const { error } = await presentPaymentSheet();
    if (error) Alert.alert(`Error code: ${error.code}`, error.message);
    else 
      Alert.alert('Success', 'Your order is confirmed!');
      // navigate to ratings and geolocation page
      navigation.navigate('PostCheckout');
      // call removeAllDrinks page
      removeAllDrinks();
  };

  return { initializePaymentSheet, openPaymentSheet, loading };
}