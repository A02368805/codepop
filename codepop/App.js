import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import * as Font from 'expo-font';
import React, { useEffect } from 'react';
import AuthPage from './src/pages/AuthPage';
import CartPage from './src/pages/CartPage';
import CreateAccountPage from './src/pages/CreateAccountPage';
import CreateDrinkPage from './src/pages/CreateDrinkPage';
import GeneralHomePage from './src/pages/GeneralHomePage';
import CompletePage from './src/pages/CompletePage';
import CheckoutForm from './src/pages/CheckoutForm';
import PreferencesPage from './src/pages/PreferencesPage';

const Stack = createNativeStackNavigator();
const title = 'CodePop' 

const App = () => {
  useEffect(() => {
    const loadFonts = async () => {
        await Font.loadAsync({
            'CherryBombOne': require('./assets/fonts/CherryBombOne-Regular.ttf'), // Adjust path as necessary
        });
    };

    loadFonts();
  }, []);

  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="GeneralHome">
        <Stack.Screen 
          name="Auth" 
          component={AuthPage} 
          options={{ 
            title: title, 
            headerTitleStyle: {
              // fontFamily: 'CherryBombOne',
          },}}
        />
        <Stack.Screen
          name="CreateAccount"
          component={CreateAccountPage}
          options={{ 
            title: title,
            headerTitleStyle: {
              // fontFamily: 'CherryBombOne',
          },}}
        />
        <Stack.Screen
          name="Cart"
          component={CartPage}
          options={{ 
            title: title, 
            headerTitleStyle: {
              // fontFamily: 'CherryBombOne',
          },}}        
        />
        <Stack.Screen
          name="CreateDrink"
          component={CreateDrinkPage}
          options={{ 
            title: title, 
            headerTitleStyle: {
              // fontFamily: 'CherryBombOne',
          },}}        
        />
        <Stack.Screen
          name="Preferences"
          component={PreferencesPage}
          options={{ 
            title: title, 
            headerTitleStyle: {
              // fontFamily: 'CherryBombOne',
            },}}        
        />
        <Stack.Screen
          name="GeneralHome"
          component={GeneralHomePage}
          options={{ 
            title: title, 
            headerTitleStyle: {
              // fontFamily: 'CherryBombOne',
          },}}
        />
        <Stack.Screen
          name="Complete"
          component={CompletePage}
          options={{ title: 'Complete' }}
        />
        <Stack.Screen
          name="Checkout"
          component={CheckoutForm}
          options={{ title: 'Checkout Form' }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
};

export default App;
