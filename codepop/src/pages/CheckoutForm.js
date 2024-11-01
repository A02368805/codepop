import React, { useState, useEffect } from "react";
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { StripeProvider, CardField, useConfirmPayment } from '@stripe/stripe-react-native';
import { BASE_URL } from '../../ip_address';

export default function CheckoutForm({ navigation }) {
  const [clientSecret, setClientSecret] = useState(null);
  const { confirmPayment, loading } = useConfirmPayment();

  // Fetch the client secret from your backend when the component mounts
  useEffect(() => {
    fetchClientSecret();
  }, []);

  const fetchClientSecret = async () => {
    try {
      const response = await fetch(`${BASE_URL}/backend/create-payment-intent/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount: 1000 }), // Set amount here
      });
      const { clientSecret } = await response.json();
      setClientSecret(clientSecret);
    } catch (error) {
      console.error('Error fetching client secret:', error);
    }
  };

  const handlePayment = async () => {
    if (!clientSecret) return;
    const { error, paymentIntent } = await confirmPayment(clientSecret, {
      paymentIntentClientSecret: clientSecret,
    });
    if (error) {
      console.error('Payment confirmation error:', error.message);
    } else if (paymentIntent) {
      navigation.navigate('Complete');
    }
  };

  return (
    <StripeProvider publishableKey="pk_test_51QEDP7HwEWxwIyaLoeRGprLwnn6Fj7jZljzxglWudPSTSe6sMyFPAjHZsnMOy1HuwZhUYT9JGZbOsxhXxkFTJp9700JSZTZKIz">
      <View style={styles.container}>
        {clientSecret && (
          <>
            <CardField
              postalCodeEnabled={true}
              placeholder={{ number: '4242 4242 4242 4242' }}
              cardStyle={styles.cardField}
              style={styles.cardContainer}
              onCardChange={(cardDetails) => console.log(cardDetails)}
            />
            <TouchableOpacity onPress={handlePayment} style={styles.button}>
              <Text style={styles.buttonText}>
                {loading ? 'Processing...' : 'Complete Payment'}
              </Text>
            </TouchableOpacity>
          </>
        )}
      </View>
    </StripeProvider>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', padding: 16 },
  cardContainer: { height: 50, marginVertical: 30 },
  cardField: { backgroundColor: '#FFFFFF' },
  button: { backgroundColor: '#007AFF', padding: 12, borderRadius: 5 },
  buttonText: { color: '#FFFFFF', fontWeight: 'bold', textAlign: 'center' },
});