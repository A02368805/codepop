import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, Image, Button, TouchableOpacity } from 'react-native';
import NavBar from '../components/NavBar';

// todo
// add geolocation tracking map
  // use googles geolocation API: https://developers.google.com/maps/documentation/javascript/examples/map-geolocation#maps_map_geolocation-javascript
// add timer from drink creation
// add rating stars to add to drink object
// add randomly generated code for locker combination
// clear the cart list


// test card number: 4242 4242 4242 4242
  // enter a date in the future like 12/34
  // for everything else, just add random numbers

const PostCheckout = () => {
  const [lockerCombo, setLockerCombo] = useState('');
  const [timeLeft, setTimeLeft] = useState(60);

  useEffect(() => {
    // Generate locker combo when the component mounts
    handleLockerCombo();

    // Start countdown timer
    if (timeLeft > 0) {
      const timerId = setInterval(() => {
        setTimeLeft((prevTime) => prevTime - 1);
      }, 1000);

      // Clear the interval when the timer reaches 0
      return () => clearInterval(timerId);
    }
  }, [timeLeft]);

  const handleLockerCombo = () => {
    // Generate a random 5-digit locker combination
    let combo = '';
    for (let i = 0; i < 5; i++) {
      const digit = Math.floor(Math.random() * 10); // Generates a number between 0 and 9
      combo += digit.toString();
    }
    setLockerCombo(combo);
  };

  // Convert timeLeft to minutes and seconds format
  const minutes = String(Math.floor(timeLeft / 60)).padStart(2, '0');
  const seconds = String(timeLeft % 60).padStart(2, '0');

  const handleDrinkRating = () => {
    // add logic to add a drink rating to the drink object
  };

  return (
    <View style={styles.container}>
      {/* Map Image Box */}
      <View style={[styles.section, styles.mapSection]}>
        <Image 
          source={require('../../assets/map.png')}
          style={styles.image}
          resizeMode="contain"
        />
      </View>

      {/* Timer Box */}
      <View style={[styles.section, styles.timerSection]}>
        <Text style={styles.heading}>Timer until drink completion</Text>
        <Text style={styles.timer}>
          {minutes}:{seconds}
        </Text>
        {timeLeft === 0 && <Text style={styles.successMessage}>Your drink is ready!</Text>}
      </View>

      {/* Rating Box */}
      <View style={[styles.section, styles.ratingSection]}>
        <Text style={styles.ratingLabel}>Option to rate drink:</Text>

        <TouchableOpacity onPress={handleDrinkRating} style={styles.button}>
        <Text style={styles.buttonText}>Add to Cart</Text>
      </TouchableOpacity>
      </View>

      {/* Locker Combo Box */}
      <View style={[styles.section, styles.lockerComboSection]}>
        <Text style={styles.lockerCombo}>Locker combo: {lockerCombo}</Text>
      </View>

      {/* NavBar */}
      <NavBar />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1, 
    justifyContent: 'center', 
    alignItems: 'center',
    backgroundColor: '#8DF1D3', // Light background for consistency
    padding: 20,
  },
  section: {
    width: '100%',
    padding: 15,
    marginBottom: 15,
    borderRadius: 8,
  },
  mapSection: {
    backgroundColor: '#D30C7B', 
  },
  timerSection: {
    backgroundColor: '#C6C8EE', 
  },
  ratingSection: {
    backgroundColor: '#FFA686', 
  },
  lockerComboSection: {
    backgroundColor: '#F92758', 
  },
  heading: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginVertical: 10,
  },
  timer: {
    fontSize: 30,
    fontWeight: 'bold',
    color: '#FFA686',
    marginVertical: 10,
  },
  successMessage: {
    fontSize: 18,
    fontWeight: '500',
    color: '#8DF1D3', 
    marginVertical: 10,
  },
  ratingLabel: {
    fontSize: 18,
    fontWeight: '500',
    color: '#333',
    marginTop: 20,
  },
  lockerCombo: {
    fontSize: 18,
    fontWeight: '500',
    color: '#333',
    marginTop: 20,
    marginBottom: 30,
  },
  image: {
    width: 200,
    height: 200,
    alignSelf: 'center',
    marginVertical: 20,
  },
  button: {
    backgroundColor: '#D30C7B',
    paddingVertical: 10,
    paddingHorizontal: 10,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 2, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 3,
    marginVertical: 5,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
  }
});

export default PostCheckout;
