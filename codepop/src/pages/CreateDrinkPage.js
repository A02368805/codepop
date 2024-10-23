import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import NavBar from '../components/NavBar';
import DropDown from '../components/DropDown'
import { useNavigation } from '@react-navigation/native';
import Icon from 'react-native-vector-icons/Ionicons';


const CreateDrinkPage = () => {
  const options = [
    {label: 'Sodas', value: 'pepsi'},
    {label: 'Syrups', value: 'vanilla'},
    {label: 'Juice', value: 'lime'},
  ];
  const handleOptionSelect = (selectedOption) => {
    console.log(selectedOption , ' Added to drink object');
  };
  return (
    <View style={styles.wholePage}>
      <Text>Drink GIF goes here</Text>
      <TouchableOpacity style={styles.button}>
      <Text style={styles.buttonText}>Add to Cart</Text>
      </TouchableOpacity>
      <Text>Search bar for ingredients</Text>
      <DropDown options={options} onSelect={handleOptionSelect}/>
      <NavBar />
    </View>
  );
};

const styles = StyleSheet.create({
  wholePage: {
    flex: 1, 
    justifyContent: 'center', 
    alignItems: 'center'
  },
  button: {
    backgroundColor: '#D30C7B', // pink background
    paddingVertical: 10, // Vertical padding
    paddingHorizontal: 10, // Horizontal padding
    borderRadius: 8, // Rounded corners
    alignItems: 'center', // Center text
    justifyContent: 'center', // Center vertically
    elevation: 3, // Shadow for Android
    shadowColor: '#000', // Shadow for iOS
    shadowOffset: { width: 2, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 3,
  }

});

export default CreateDrinkPage;