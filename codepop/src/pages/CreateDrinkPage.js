import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, TextInput, ScrollView } from 'react-native';
import NavBar from '../components/NavBar';
import DropDown from '../components/DropDown';
import { useNavigation } from '@react-navigation/native';
import { sodaOptions, syrupOptions, juiceOptions } from '../components/Ingredients';
import {BASE_URL} from '../../ip_address'
import AsyncStorage from '@react-native-async-storage/async-storage';

// to do:
// create drink gif
// generate drink from AI

const CreateDrinkPage = () => {
  const navigation = useNavigation();
  const [searchText, setSearchText] = useState('');
  const [openDropdown, setOpenDropdown] = useState({
    sodas: false,
    syrups: false,
    juices: false,
  });

  // variables to add to drink object
  const [SodaUsed, setSoda] = useState([]);
  const [SyrupsUsed, setSyrups] = useState([]);
  const [AddIns, setAddIns] = useState([]);
  const [selectedSize, setSize] = useState(null);
  const [selectedIce, setIce] = useState(null);
  

  const addToCart = async () => {
    try {
      const token = await AsyncStorage.getItem('userToken');
  
      const response = await fetch(`${BASE_URL}/backend/drinks/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Token ${token}`,
        },
        body: JSON.stringify({ 
          Name: "Drink in User Cart",  // Example name for the drink
          SodaUsed: SodaUsed,  // Default value if SodaUsed is null
          SyrupsUsed: SyrupsUsed,
          AddIns: AddIns,
          Price: 2.00,
          User_Created: true,    // Assuming the user is creating the drink
          Size: selectedSize,
          Ice: selectedIce,
        })
      });
  
      if (!response.ok) {
        throw new Error(`Failed to add drink. Status: ${response.status}`);
      }
      // add drink item (the drinks ID) to the checkout list from App.js
      try{
        // gets list of out of storage on your phone
        cartList = await AsyncStorage.getItem("checkoutList");
        const currentList = cartList ? JSON.parse(cartList) : [];
        // takes the response (what we get after we create a drink) and extracts the drinkID
        const data = await response.json();
        const drinkID = data.DrinkID;
        // add the drinkID to the checkoutList
        const updatedList = [...currentList, drinkID]
        // Saves the checkoutlist back into the storage on the phone
        await AsyncStorage.setItem('checkoutList', JSON.stringify(updatedList));
      }catch (error){
        console.log(error)
      }

      navigation.navigate('Cart');
    } catch (error) {
      console.error('Error adding drink to cart:', error);
    }
  };  
  

  const handleSizeSelection = (size) => {
    setSize(size);
  };
  
  const handleIceSelection = (ice) => {
    setIce(ice);
  };

  const handleSodaSelection = (soda) => {
    setSoda((prevSodas) => {
      if (prevSodas.includes(soda)) {
        // If soda is already selected, remove it
        return prevSodas.filter((item) => item !== soda);
      } else {
        // Otherwise, add the soda to the list
        return [...prevSodas, soda];
      }
    });
  };
  
  
  const handleSyrupSelection = (syrup) => {
    setSyrups((prevSyrups) => {
      if (prevSyrups.includes(syrup)) {
        // If soda is already selected, remove it
        return prevSyrups.filter((item) => item !== syrup);
      } else {
        // Otherwise, add the soda to the list
        return [...prevSyrups, syrup];
      }
    });
  };

  const handleAddInSelection = (addIn) => {
    setAddIns((prevAdd) => {
      if (prevAdd.includes(addIn)) {
        // If soda is already selected, remove it
        return prevAdd.filter((item) => item !== addIn);
      } else {
        // Otherwise, add the soda to the list
        return [...prevAdd, addIn];
      }
    });
  };
  
  // search and list stiff
  const filterOptions = (options = []) => {
    return options.filter((option) =>
      option.label.toLowerCase().includes(searchText.toLowerCase())
    );
  };

  const handleSearch = (text) => {
    setSearchText(text);
    setOpenDropdown({
      sodas: !!text,
      syrups: !!text,
      juices: !!text,
    });
  };
  
  // function for generate drink button which generates a drink with AI
  const GenerateAI = () => {
    // logic to generate an AI drink
  };

  return (
    <View style={styles.wholePage}>

      <ScrollView style={styles.padding}>
      <View style={styles.rowContainer}>
        {/* Size buttons on the left */}
        <View style={styles.buttonContainerLeft}>
          {['16oz', '24oz', '32oz'].map((size) => (
            <TouchableOpacity
              key={size}
              onPress={() => handleSizeSelection(size)}
              style={[
                styles.circularButton,
                selectedSize === size && styles.circularButtonSelected,
              ]}
            >
              <Text style={[styles.buttonText, selectedSize === size && styles.selectedButtonText]}>
                {size}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        
        <View style={styles.graphicContainer}>
          {/* Drink graphic in the center */}
          <Text style={styles.drinkGraphicText}>Drink GIF goes here</Text>
          {/* {gifUrl && <Image source={{ uri: gifUrl }} style={styles.gifImage} />} */}

          {/* Button to generate drinks */}
          <TouchableOpacity onPress={GenerateAI} style={styles.button}>
            <Text style={styles.buttonText}>Generate Drink</Text>
          </TouchableOpacity>
        </View>

        {/* Ice buttons on the right */}
        <View style={styles.buttonContainerRight}>
          {['No Ice', 'Light', 'Regular', 'Extra'].map((ice) => (
            <TouchableOpacity
              key={ice}
              onPress={() => handleIceSelection(ice)}
              style={[
                styles.circularButton,
                selectedIce === ice && styles.circularButtonSelected,
              ]}
            >
              <Text style={[styles.buttonText, selectedIce === ice && styles.selectedButtonText]}>{ice}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Button to add to cart */}
      <TouchableOpacity onPress={addToCart} style={styles.button}>
        <Text style={styles.buttonText}>Add to Cart</Text>
      </TouchableOpacity>

      {/* Search Input */}
      <TextInput
        placeholder="Search ingredients"
        style={styles.searchInput}
        value={searchText}
        onChangeText={handleSearch}
      />

      {/* Dropdowns */}
      <View style={styles.navBarSpace}>
        <DropDown 
          title="Sodas" 
          options={filterOptions(sodaOptions)} 
          onSelect={handleSodaSelection} 
          isOpen={openDropdown.sodas}
          setOpen={() => setOpenDropdown(prev => ({ ...prev, sodas: !prev.sodas }))}
        />
        <DropDown 
          title="Syrups" 
          options={filterOptions(syrupOptions)} 
          onSelect={handleSyrupSelection} 
          isOpen={openDropdown.syrups}
          setOpen={() => setOpenDropdown(prev => ({ ...prev, syrups: !prev.syrups }))}
        />
        <DropDown 
          title="Juices" 
          options={filterOptions(juiceOptions)} 
          onSelect={handleAddInSelection} 
          isOpen={openDropdown.juices}
          setOpen={() => setOpenDropdown(prev => ({ ...prev, juices: !prev.juices }))}
        />
      </View>
      </ScrollView>
      <NavBar/>
    </View>
  );
};

const styles = StyleSheet.create({
  wholePage: {
    flex: 1,
    backgroundColor: '#FFA686',
    // padding: 10,
  },
  padding: {
    padding: 10,
  },
  navBarSpace: {
    marginBottom: 80,
  },
  rowContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 10, // Add padding on sides
    flex: 1,
  },
  buttonContainerLeft: {
    flexDirection: 'column',
    alignItems: 'flex-start',
    justifyContent: 'space-around',
    width: '30%', // Adjust width as needed
  },
  buttonContainerRight: {
    flexDirection: 'column',
    alignItems: 'flex-end',
    justifyContent: 'space-around',
    width: '30%', // Adjust width as needed
  },
  graphicContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    flex: 1, // Center the graphic
  },
  drinkGraphicText: {
    fontSize: 20,
    fontWeight: 'bold',
    textAlign: 'center',
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
  },
  circularButton: {
    width: 60,
    height: 60,
    borderRadius: 30,
    borderWidth: 2,
    borderColor: '#D30C7B',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#F92758',
    margin: 5,
  },
  circularButtonSelected: {
    borderColor: '#8DF1D3',
    backgroundColor: '#E8F5E9',
  },
  selectedButtonText: {
    color: '#000', // Black color for selected text
  },
  searchInput: {
    height: 40,
    borderColor: '#ddd',
    borderWidth: 3,
    paddingHorizontal: 10,
    width: '80%',
    marginVertical: 15,
    borderRadius: 5,
    alignSelf: 'center', // Center the search input
  },
});

export default CreateDrinkPage;
