import React, { useState } from 'react';
import { TouchableOpacity } from 'react-native';
import { View, TextInput, Button, Text, StyleSheet } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Alert } from 'react-native';
import {BASE_URL} from '../../ip_address'

const AuthPage = ({ navigation }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [token, setToken] = useState(null);
  const [message, setMessage] = useState('');

  const handleRegister = async () => {
    // Registration logic... Go to CreateAccountPage
    navigation.navigate('CreateAccount');
  };

  const handleLogin = async () => {
    try {
      // Send credentials to Django backend
      const response = await fetch(`${BASE_URL}/backend/auth/login/`, {
          method: 'POST',
          headers: {
              'Content-Type': 'application/json',
          },
          body: JSON.stringify({ username, password }),
      });

      if (response.status === 200) {
          const data = await response.json();
          const token = data.token; // Get token from response

          // Store the token, username, and user ID in AsyncStorage
          await AsyncStorage.setItem('userToken', data.token);
          await AsyncStorage.setItem('userId', data.user_id.toString());  // Store user ID as string
          await AsyncStorage.setItem('first_name', data.first_name);
        
          Alert.alert('Login successful!');
          navigation.navigate('Home'); // Navigate to Home screen on success
      } else {
          Alert.alert('Invalid credentials, please try again.');
      }
    } catch (error) {
      console.error(error);
      Alert.alert('Login failed. Please try again later.');
    }
  };

  return (
    <View style={styles.container}>
      <TextInput
        placeholder="Username"
        value={username}
        onChangeText={setUsername}
        style={styles.input}
      />
      <TextInput
        placeholder="Password"
        value={password}
        secureTextEntry
        onChangeText={setPassword}
        style={styles.input}
      />
      <View style={styles.buttonContainer}>
        <TouchableOpacity style={styles.mediumButton} onPress={handleRegister}>
          <Text style={styles.buttonText}>Create Account</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.mediumButton} onPress={handleLogin}>
          <Text style={styles.buttonText}>Login</Text>
        </TouchableOpacity>
      </View>
      {token && <Text>Your token: {token}</Text>}
      {message && <Text>{message}</Text>}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  input: {
    marginBottom: 10,
    borderWidth: 1,
    padding: 5,
    width: '100%',
  },
  buttonContainer: {
    flexDirection: 'row',
  },
  mediumButton: {
    margin: 10,
    padding: 15,
    backgroundColor: '#8df1d3',
    borderRadius: 10,
    alignItems: 'center',
  },
  buttonText: {
    fontSize: 16,
  }
});

export default AuthPage;
