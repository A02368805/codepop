// Web stub for @stripe/stripe-react-native
import React from 'react';

export const StripeProvider = ({ children }) => children;
export const useStripe = () => ({
  initPaymentSheet: async () => ({ error: null }),
  presentPaymentSheet: async () => ({ error: null }),
  confirmPayment: async () => ({ error: null }),
});
export const CardField = () => null;
export default {};
