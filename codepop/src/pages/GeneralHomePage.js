import React, { useState } from 'react';
import { View, Text, Button, StyleSheet, Dimensions } from 'react-native';
import NavBar from '../components/NavBar';
import { useNavigation } from '@react-navigation/native';
import { TouchableOpacity } from 'react-native';

const { width: screenWidth } = Dimensions.get('window');

const drinks = [
  { id: 1, name: 'Mojito', description: 'Refreshing mint and lime cocktail' },
  { id: 2, name: 'Pina Colada', description: 'Tropical coconut and pineapple drink' },
  { id: 3, name: 'Margarita', description: 'Classic tequila cocktail' },
];

const GeneralHomePage = () => {
  const [currentIndex, setCurrentIndex] = useState(0);

  const navigation = useNavigation();

  const generateDrinks = () => {
    console.log('Generating drinks...');
  };

  const createAccount = () => {
    console.log('Navigating to account creation...');
    navigation.navigate('Auth');
  };

  return (
    <View style={styles.container}>
      <View style={styles.buttonContainer}>
        <TouchableOpacity onPress={generateDrinks} style={styles.mediumButton}>
          <Text style={styles.buttonText}>Generate Drinks</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={createAccount} style={styles.mediumButton}>
          <Text style={styles.buttonText}>Create Account</Text>
        </TouchableOpacity>
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
  carouselItem: {
    backgroundColor: '#fff',
    borderRadius: 10,
    height: 250,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
  },
  drinkName: {
    fontSize: 24,
    fontWeight: 'bold',
  },
  drinkDescription: {
    fontSize: 16,
    textAlign: 'center',
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
  }
});

export default GeneralHomePage;
