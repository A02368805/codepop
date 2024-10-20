// src/pages/DrinkPage.js

import React, { useState } from 'react';
import { View, Text, Button, StyleSheet, Dimensions } from 'react-native';
// import Carousel from 'react-native-snap-carousel';
import NavBar from '../components/NavBar';
// import NavBar from '../components/NavBar';

const { width: screenWidth } = Dimensions.get('window');

const drinks = [
  { id: 1, name: 'Mojito', description: 'Refreshing mint and lime cocktail' },
  { id: 2, name: 'Pina Colada', description: 'Tropical coconut and pineapple drink' },
  { id: 3, name: 'Margarita', description: 'Classic tequila cocktail' },
];

const GeneralHomePage = () => {
  const [currentIndex, setCurrentIndex] = useState(0);

//   const renderDrinkItem = ({ item }) => (
//     <View style={styles.carouselItem}>
//       <Text style={styles.drinkName}>{item.name}</Text>
//       <Text style={styles.drinkDescription}>{item.description}</Text>
//     </View>
//   );

  const generateDrinks = () => {
    console.log('Generating drinks...');
  };

  const createAccount = () => {
    console.log('Navigating to account creation...');
  };

  return (
    <View style={styles.container}>
      {/* <Carousel
        data={drinks}
        renderItem={renderDrinkItem}
        sliderWidth={screenWidth}
        itemWidth={screenWidth * 0.8}
        onSnapToItem={(index) => setCurrentIndex(index)}
      /> */}
      <Button title="Generate Drinks" onPress={generateDrinks} />
      <Button title="Create Account" onPress={createAccount} />
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
    elevation: 3, // For Android shadow
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
});

export default GeneralHomePage;



// src/screens/HomeScreen.js

// import React from 'react';
// import { View, Text, StyleSheet } from 'react-native';
// import NavBar from '../components/NavBar';

// const GeneralHomePage = () => {
//   return (
//     <View style={styles.container}>
//       <Text style={styles.title}>Welcome to the Soda App!</Text>
//       {/* Add more content here */}
//       <NavBar />
//     </View>
//   );
// };

// const styles = StyleSheet.create({
//   container: {
//     flex: 1,
//     justifyContent: 'center',
//     alignItems: 'center',
//     padding: 0,
//   },
//   title: {
//     fontSize: 24,
//     fontWeight: 'bold',
//   },
// });

// export default GeneralHomePage;
