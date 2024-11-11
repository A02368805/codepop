import AsyncStorage from '@react-native-async-storage/async-storage';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import React, { useEffect, useState } from 'react';
import { Alert, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { BASE_URL } from '../../ip_address';
import NavBar from '../components/NavBar';
import SeasonalCarousel from '../components/SeasonalCarousel';

const GeneralHomePage = () => {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [name, setName] = useState(null);
  const navigation = useNavigation();

  // Check login status when the screen gains focus
  useFocusEffect(
    React.useCallback(() => {
      const checkLoginStatus = async () => {
        try {
          const storedName = await AsyncStorage.getItem('first_name');
          const token = await AsyncStorage.getItem('userToken');
          if (token && storedName) {
            setIsLoggedIn(true);  // User is logged in
            setName(storedName);  // Set username for display
          } else {
            setIsLoggedIn(false);  // No user is logged in
          }
        } catch (error) {
          console.error('Error checking login status:', error);
        }
      };
  
      checkLoginStatus();
    }, [])  // The empty array ensures this only runs when the screen is focused
  );

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

  // Logout function
  const handleLogout = async () => {
    try {
      // Send logout request to the backend
      const token = await AsyncStorage.getItem('userToken');
      const response = await fetch(`${BASE_URL}/backend/auth/logout/`, {
        method: 'POST',
        headers: {
          'Authorization': `Token ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.status === 200) {
        // Clear AsyncStorage
        await AsyncStorage.removeItem('userToken');
        await AsyncStorage.removeItem('userId');
        await AsyncStorage.removeItem('first_name');
        
        setIsLoggedIn(false);
        setName(null);
        
        Alert.alert('Logout successful!');
      } else {
        Alert.alert('Logout failed, please try again.');
      }
    } catch (error) {
      console.error('Error during logout:', error);
      Alert.alert('Logout failed, please try again later.');
    }
  };

  // Login button press
  const goToLoginPage = () => {
    navigation.navigate('Auth');  // Navigate to the login page
  };

  // Generate drinks button press
  const generateDrinks = () => {
    console.log('generating drinks...')
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      {/* If logged in, display the username and Logout button, otherwise display Login button */}
      {isLoggedIn ? (
        <>
          {/* Conditionally render the "Hello <username>" if username exists */}
          {name ? <Text style={styles.greeting}>Hello {name}!</Text> : null}

          {/* The main title */}
          <Text style={styles.title}>Welcome to the CodePop App!</Text>
          <SeasonalCarousel style={styles.carousel}/>
          <View style={styles.buttonContainer}>
            <TouchableOpacity onPress={generateDrinks} style={styles.mediumButton}>
              <Text style={styles.buttonText}>Generate Drinks</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={handleLogout} style={styles.mediumButton}>
              <Text style={styles.buttonText}>Logout</Text>
            </TouchableOpacity>
          </View>
        </>
      ) : (
        <>
          <SeasonalCarousel style={styles.carousel}/>
          <View style={styles.buttonContainer}>
            <TouchableOpacity onPress={generateDrinks} style={styles.mediumButton}>
            <Text style={styles.buttonText}>Generate Drinks</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={goToLoginPage} style={styles.mediumButton}>
              <Text style={styles.buttonText}>Login</Text>
            </TouchableOpacity>
          </View>
        </>
      )}
      <NavBar />
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 0,
    backgroundColor: '#c0ffe7',
  },
  contentContainer: {
    flexGrow: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  mediumButton: {
    margin: 10,
    padding: 15,
    backgroundColor: '#D30C7B',
    borderRadius: 10,
    alignItems: 'center',
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 2, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 3,
  },
  buttonText: {
    fontSize: 16,
    color: 'white',
  },
  greeting: {
    fontSize: 32,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  carousel: {
    margin: 0,
    padding: 0,
  },
  title: {
    fontSize: 22,
  }
});

export default GeneralHomePage;
