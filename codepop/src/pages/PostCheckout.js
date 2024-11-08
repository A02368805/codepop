import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, Image } from 'react-native';
import NavBar from '../components/NavBar';

// todo
// add geolocation tracking map
  // use googles geolocation API: https://developers.google.com/maps/documentation/javascript/examples/map-geolocation#maps_map_geolocation-javascript
// add timer from drink creation
// add rating stars to add to drink object
// add randomly generated code for locker combination
// clear the cart list

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

  return (
    <View style={styles.container}>
      <Image 
        source={require('../../assets/map.png')}
        style={styles.image}
        resizeMode="contain"
      />
      <Text>Timer until drink completion</Text>
      <Text>{minutes}:{seconds}</Text>
      {timeLeft === 0 && <Text>Your drink is ready!</Text>}
      <Text>Option to rate drink</Text>
      <Text>Locker combo: {lockerCombo}</Text>
      <NavBar />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1, 
    justifyContent: 'center', 
    alignItems: 'center',
  },
  image: {
    width: 150,
    height: 150,
    alignSelf: 'center',
    marginVertical: 10,
  },
});

export default PostCheckout;