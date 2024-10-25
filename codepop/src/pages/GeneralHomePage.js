import React, { useEffect, useState } from 'react';
import { View, Text, Button, StyleSheet, Dimensions, TouchableOpacity, Alert } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import NavBar from '../components/NavBar';
import { BASE_URL } from '../../ip_address';

const { width: screenWidth } = Dimensions.get('window');

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
    <View style={styles.container}>
      {/* If logged in, display the username and Logout button, otherwise display Login button */}
      <View style={styles.buttonContainer}>
        <TouchableOpacity onPress={generateDrinks} style={styles.mediumButton}>
          <Text style={styles.buttonText}>Generate Drinks</Text>
        </TouchableOpacity>

        {isLoggedIn ? (
          <>
            <TouchableOpacity onPress={handleLogout} style={styles.mediumButton}>
              <Text style={styles.buttonText}>Logout</Text>
            </TouchableOpacity>
          </>
        ) : (
          <TouchableOpacity onPress={goToLoginPage} style={styles.mediumButton}>
            <Text style={styles.buttonText}>Login</Text>
          </TouchableOpacity>
        )}
      </View>
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
  mediumButton: {
    margin: 20,
    padding: 15,
    backgroundColor: '#8df1d3',
    borderRadius: 10,
    alignItems: 'center',
  },
  buttonText: {
    fontSize: 16,
  },
  greeting: {
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 10,
  },
});

export default GeneralHomePage;
