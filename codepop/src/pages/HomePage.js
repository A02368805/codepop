import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import NavBar from '../components/NavBar';

const HomePage = () => {
  const [name, setName] = useState(null); // State to store the username

  useEffect(() => {
    // Retrieve the username from AsyncStorage when the component mounts
    const checkUserLogin = async () => {
      try {
        const storedName = await AsyncStorage.getItem('first_name');
        if (storedName) {
          setName(storedName); // If a username is found, set it in the state
        }
      } catch (error) {
        console.error('Error retrieving username:', error);
      }
    };

    checkUserLogin(); // Call the function when the component mounts
  }, []);

  return (
    <View style={styles.container}>
      {/* Conditionally render the "Hello <username>" if username exists */}
      {name ? <Text style={styles.greeting}>Hello {name}!</Text> : null}

      {/* The main title */}
      <Text style={styles.title}>Welcome to the CodePop App!</Text>

      {/* NavBar component */}
      <NavBar />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 0,
  },
  greeting: {
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
  },
});

export default HomePage;
