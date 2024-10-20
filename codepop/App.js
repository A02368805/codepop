// src/App.js

import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import React from 'react';
import AuthPage from './src/pages/AuthPage';
import HomePage from './src/pages/HomePage';
import CartPage from './src/pages/CartPage';
import CreateDrinkPage from './src/pages/CreateDrinkPage';
import PreferencesPage from './src/pages/PreferencesPage';
import GeneralHomePage from './src/pages/GeneralHomePage';

const Stack = createNativeStackNavigator();

const App = () => {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="Home">
        <Stack.Screen 
          name="Auth" 
          component={AuthPage} 
          options={{ title: 'Login/Register' }} 
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

// import React, { useState } from 'react';
// import { View, TextInput, Button, Text, StyleSheet } from 'react-native';

// const App = () => {
//   const [username, setUsername] = useState('');
//   const [password, setPassword] = useState('');
//   const [token, setToken] = useState(null);
//   const [message, setMessage] = useState('');

//   // Single variable to store the base URL
//   const BASE_URL = 'http://172.20.5.200:8000'; // Replace with your actual backend URL

//   const handleRegister = async () => {
//     try {
//       const response = await fetch(`${BASE_URL}/backend/auth/register/`, {
//         method: 'POST',
//         headers: {
//           'Content-Type': 'application/json',
//         },
//         body: JSON.stringify({
//           username,
//           password,
//           first_name: 'FirstName',
//           last_name: 'LastName',
//         }),
//       });
//       const data = await response.json();
//       if (response.ok) {
//         setMessage('User created successfully! You can now login.');
//       } else {
//         setMessage(`Error: ${data.detail || 'Registration failed'}`);
//       }
//     } catch (error) {
//       setMessage('Error registering user');
//       console.error(error);
//     }
//   };

//   const handleLogin = async () => {
//     try {
//       const response = await fetch(`${BASE_URL}/backend/auth/login/`, {
//         method: 'POST',
//         headers: {
//           'Content-Type': 'application/json',
//         },
//         body: JSON.stringify({
//           username,
//           password,
//         }),
//       });
//       const data = await response.json();
//       if (response.ok) {
//         setToken(data.token); // Token will be stored here
//         setMessage('Logged in successfully!');
//       } else {
//         setMessage(`Login failed: ${data.detail || 'Invalid credentials'}`);
//       }
//     } catch (error) {
//       setMessage('Login failed');
//       console.error(error);
//     }
//   };

//   return (
//     <View style={styles.container}>
//       <TextInput
//         placeholder="Username"
//         value={username}
//         onChangeText={setUsername}
//         style={styles.input}
//       />
//       <TextInput
//         placeholder="Password"
//         value={password}
//         secureTextEntry
//         onChangeText={setPassword}
//         style={styles.input}
//       />
//       <Button title="Register" onPress={handleRegister} />
//       <Button title="Login" onPress={handleLogin} />
//       {token && <Text>Your token: {token}</Text>}
//       {message && <Text>{message}</Text>}
//     </View>
//   );
// };

// const styles = StyleSheet.create({
//   container: {
//     flex: 1,
//     justifyContent: 'center', // Center vertically
//     alignItems: 'center',     // Center horizontally
//     padding: 20,
//   },
//   input: {
//     marginBottom: 10,
//     borderWidth: 1,
//     padding: 5,
//     width: '100%',            // Adjust input width to be full width
//   },
// });

// export default App;