import React, { useState } from 'react';
import { TouchableOpacity } from 'react-native';
import { View, TextInput, Button, Text, StyleSheet } from 'react-native';

const AuthPage = ({ navigation }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [token, setToken] = useState(null);
  const [message, setMessage] = useState('');

  const BASE_URL = 'http://192.168.1.83:8000'; // Your backend URL

  const handleRegister = async () => {
    // Registration logic...
  };

  const handleLogin = async () => {
    // Login logic...
    // If login is successful, navigate to Home screen
    // if (response.ok) {
    navigation.navigate('Home'); // Navigate to Home screen on success
    // }
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
