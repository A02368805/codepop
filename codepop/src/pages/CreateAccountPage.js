import React, { useState } from 'react';
import { View, TextInput, Button, Text, StyleSheet } from 'react-native';
import axios from 'axios';
import {BASE_URL} from '../../ip_address'


const CreateAccountPage = ({ navigation }) => {
    const [first_name, setFirstname] = useState('');
    const [username, setUsername] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [message, setMessage] = useState('');

    const handleRegister = async () => {
    try {
      const response = await fetch(`${BASE_URL}/backend/auth/register/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ first_name, username, password, email })
      });
      navigation.navigate('Auth');
    } catch (error) {
        console.log(error);
      setMessage('Error registering user.');
    }
  };

  return (
    <View style={styles.container}>
        <TextInput placeholder="First Name" onChangeText={setFirstname} />
        <TextInput placeholder="Username" onChangeText={setUsername} />
        <TextInput placeholder="Email" onChangeText={setEmail} keyboardType="email-address" />
        <TextInput placeholder="Password" onChangeText={setPassword} secureTextEntry />
        <Button title="Create Account" onPress={handleRegister} />
        {message ? <Text>{message}</Text> : null}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    padding: 16,
  },
});

export default CreateAccountPage;
