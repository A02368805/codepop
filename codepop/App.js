import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import React from 'react';
import AuthPage from './src/pages/AuthPage';
import HomePage from './src/pages/HomePage';
import CartPage from './src/pages/CartPage';
import CreateDrinkPage from './src/pages/CreateDrinkPage';
import PreferencesPage from './src/pages/PreferencesPage';
import GeneralHomePage from './src/pages/GeneralHomePage';
import CreateAccountPage from './src/pages/CreateAccountPage';

const Stack = createNativeStackNavigator();
const title = 'CodePop' 

const App = () => {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="GeneralHome">
        <Stack.Screen 
          name="Auth" 
          component={AuthPage} 
        />
        <Stack.Screen
          name="CreateAccount"
          component={CreateAccountPage}
          options={{ title: 'Create Account'}}
        />
        <Stack.Screen 
          name="Home" 
          component={HomePage} 
          options={{ title: 'Home' }} 
        />
        <Stack.Screen
          name="Cart"
          component={CartPage}
          options={{ title: 'Cart' }}
        />
        <Stack.Screen
          name="CreateDrink"
          component={CreateDrinkPage}
          options={{ title: 'Create Drink' }}
        />
        <Stack.Screen
          name="Preferences"
          component={PreferencesPage}
          options={{ title: 'Preferences' }}
        />
        <Stack.Screen
          name="GeneralHome"
          component={GeneralHomePage}
          options={{ title: 'General Home' }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
};

export default App;
