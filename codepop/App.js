import AsyncStorage from '@react-native-async-storage/async-storage';
import { NavigationContainer, useNavigation } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import * as Font from 'expo-font';
import React, { useEffect } from 'react';
import { TouchableOpacity } from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';
import AdminDash from './src/pages/AdminDash';
import AuthPage from './src/pages/AuthPage';
import CartPage from './src/pages/CartPage';
import CheckoutForm from './src/pages/CheckoutForm';
import ComplaintsPage from './src/pages/ComplaintsPage';
import CompletePage from './src/pages/CompletePage';
import CreateAccountPage from './src/pages/CreateAccountPage';
import CreateDrinkPage from './src/pages/CreateDrinkPage';
import GeneralHomePage from './src/pages/GeneralHomePage';
import ManagerDash from './src/pages/ManagerDash';
import PaymentPage from './src/pages/PaymentPage';
import PostCheckout from './src/pages/PostCheckout';
import PreferencesPage from './src/pages/PreferencesPage';
import UpdateDrink from './src/pages/UpdateDrink';

const Stack = createNativeStackNavigator();
const title = 'CodePop' 


const App = () => {
  // initialize cart list 
  const initCart = async () => {
    try{
      const checkoutList = await AsyncStorage.getItem('checkoutList')
      if (checkoutList === null){
        const initialList = [];
        await AsyncStorage.setItem("checkoutList", JSON.stringify(initialList));
      }
    }catch(error){
      console.error("error with initializing cart list", error);
    }
  };
  
  useEffect(() => {
    initCart()
  }, []);
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
      <Stack.Navigator initialRouteName="GeneralHome" screenOptions={{headerStyle: {backgroundColor: '#c8c8ee'}}}>
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
          name="ComplaintsPage"
          component={ComplaintsPage}
          options={{ title: 'ComplaintsPage' }}
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
            },
            headerRight: () => (
              <ProfileButton />
            ),}}
        />
        <Stack.Screen
          name="payment"
          component={PaymentPage}
          options={{ title: 'Payment' }}
        />
        <Stack.Screen
          name="UpdateDrink"
          component={UpdateDrink}
          options={{ title: 'UpdateDrink' }}
        />
        <Stack.Screen
          name="ManagerDash"
          component={ManagerDash}
          options={{ title: 'ManagerDash' }}
        />
        <Stack.Screen
          name="AdminDash"
          component={AdminDash}
          options={{ title: 'AdminDash' }}
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
        <Stack.Screen
          name="PostCheckout"
          component={PostCheckout}
          options={{ title: 'PostCheckout' }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
};

const ProfileButton = () => {
  const navigation = useNavigation(); // Use navigation hook

  return (
    <TouchableOpacity onPress={() => navigation.navigate('Preferences')}>
      <Icon name="person-circle-outline" size={30} color="#000" />
    </TouchableOpacity>
  );
};

export default App;
