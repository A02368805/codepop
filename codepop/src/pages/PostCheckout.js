import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, Image, Button, TouchableOpacity, FlatList } from 'react-native';
import NavBar from '../components/NavBar';
import RatingCarosel from '../components/RatingCarosel';
import Icon from 'react-native-vector-icons/FontAwesome';
import AsyncStorage from '@react-native-async-storage/async-storage';
import GeoMap from '../components/map';
import { BASE_URL } from '../../ip_address';

// todo
// add geolocation tracking map
  // use googles geolocation API: https://developers.google.com/maps/documentation/javascript/examples/map-geolocation#maps_map_geolocation-javascript
// fix bug in carosel so that only one of each drink shows up
// add im here button

// test card number: 4242 4242 4242 4242
  // enter a date in the future like 12/34
  // for everything else, just add random numbers

const PostCheckout = () => {
  const [lockerCombo, setLockerCombo] = useState('');
  const [timeLeft, setTimeLeft] = useState(60);
  const [purchasedDrinks, setPurchasedDrinks] = useState([]);

  // get the list of drinks from the cartlist
  useEffect(() => {
    const fetchPurchasedDrinks = async () => {
      try {
        const storedDrinks = await AsyncStorage.getItem("purchasedDrinks");
        console.log(storedDrinks)
        const parsedDrinks = storedDrinks ? JSON.parse(storedDrinks) : [];
        setPurchasedDrinks(parsedDrinks);
      } catch (error) {
        console.error("Error fetching purchased drinks:", error);
      }
    };
  
    fetchPurchasedDrinks();
  }, []);

  useEffect(() => {
    // Generate locker combo only when the component mounts
    handleLockerCombo();
  }, []); // Empty dependency array ensures it runs only once

  useEffect(() => {
    if(lockerCombo !== ''){
      updateLockerCombo();
    }
  }, [lockerCombo]);

  useEffect(() => {
    // Start countdown timer
    if (timeLeft > 0) {
      const timerId = setInterval(() => {
        setTimeLeft((prevTime) => prevTime - 1);
      }, 1000);
  
      // Clear the interval when the timer reaches 0
      return () => clearInterval(timerId);
    }else{
      completeOrder();
    }
  }, [timeLeft]);

  const completeOrder = async () => {
    const orderNum = await AsyncStorage.getItem("orderNum");
    await fetch(`${BASE_URL}/backend/orders/${orderNum}/`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        OrderStatus: 'completed',
      }),
    });
  }
  

  const handleLockerCombo = () => {
    // Generate a random 5-digit locker combination
    let combo = '';
    for (let i = 0; i < 5; i++) {
      const digit = Math.floor(Math.random() * 10); // Generates a number between 0 and 9
      combo += digit.toString();
    }
    setLockerCombo(combo);
  };

  const updateLockerCombo = async () => {
    const orderNum = await AsyncStorage.getItem("orderNum");
    await fetch(`${BASE_URL}/backend/orders/${orderNum}/`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        LockerCombo: lockerCombo,
      }),
    });
    console.log("Set Locker Combo To:", lockerCombo);
  };

  // Convert timeLeft to minutes and seconds format
  const minutes = String(Math.floor(timeLeft / 60)).padStart(2, '0');
  const seconds = String(timeLeft % 60).padStart(2, '0');

  return (
    <View style={styles.container}>
      <View style={styles.padding}>
        {/* Map Image Box */}
        <View style={[styles.section, styles.mapSection]}>
          {/* <GeoMap/> */}
          <Image 
            source={require('../../assets/map.png')}
            style={styles.image}
            resizeMode="contain"
          />
        </View>

        {/* Rating Box */}
        <View style={[styles.section, styles.ratingSection]}>
          <Text style={styles.ratingLabel}>Liked any of your drinks?</Text>
          <RatingCarosel purchasedDrinks={purchasedDrinks} />
        </View>

        {/* Horizontal Container for Timer and Locker Combo */}
        <View style={styles.timerAndLockerContainer}>
          <View style={[styles.section, styles.timerSection]}>
            <Text style={styles.heading}>Drink ready in:</Text>
            <Text style={styles.timer}>
              {minutes}:{seconds}
            </Text>
            {timeLeft === 0 && <Text style={styles.successMessage}>Your drink is ready!</Text>}
          </View>

          <View style={[styles.section, styles.lockerComboSection]}>
            <Text style={styles.lockerCombo}>Locker combo: {lockerCombo}</Text>
          </View>
        </View>

      </View>
      <NavBar />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1, 
    backgroundColor: '#8DF1D3', 
  },
  padding: {
    padding: 10,
  },
  section: {
    width: '100%',
    // padding: 5,
    marginBottom: 15,
    borderRadius: 8,
    alignItems: 'center',
  },
  timerAndLockerContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  timerSection: {
    backgroundColor: '#C6C8EE',
    flex: 1,
    marginRight: 10,
  },
  lockerComboSection: {
    backgroundColor: '#F92758',
    flex: 1,
    marginLeft: 10,
  },
  mapSection: {
    backgroundColor: '#D30C7B', 
  },
  ratingSection: {
    backgroundColor: '#FFA686', 
  },
  heading: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
    marginVertical: 5,
  },
  timer: {
    fontSize: 30,
    fontWeight: 'bold',
    color: '#FFA686',
    marginVertical: 5,
  },
  successMessage: {
    fontSize: 15,
    fontWeight: '500',
    color: '#8DF1D3', 
    marginVertical: 10,
  },
  ratingLabel: {
    fontSize: 15,
    fontWeight: '600',
    color: '#333',
    margin: 10,
  },
  lockerCombo: {
    fontSize: 20,
    fontWeight: '900',
    color: '#333',
    marginTop: 20,
    marginBottom: 20,
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
