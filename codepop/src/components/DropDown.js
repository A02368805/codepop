import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';

const DropDown = ({ title, options = [], onSelect, isOpen, setOpen}) => {
  // const [isOpen, setIsOpen] = useState(false);
  const [selectedItems, setSelectedItems] = useState({});

  const toggleDropdown = () => {
    setIsOpen(!isOpen);
  };

  const toggleItemSelection = (item) => {
    setSelectedItems((prevSelectedItems) => ({
      ...prevSelectedItems,
      [item]: !prevSelectedItems[item],
    }));
    onSelect(item);
  };

  return (
    <View style={styles.container}>
      <TouchableOpacity onPress={setOpen} style={[
        styles.collapsible,
        isOpen && styles.collapsibleOpen,
      ]}>
        <Text style={styles.collapsibleText}>{title}</Text>
        <Icon name={isOpen ? "caret-up-outline" : "caret-down-outline"} size={24} color="#000" />
      </TouchableOpacity>
      {isOpen && options.length > 0 && (
        <View style={styles.content}>
          <View style={styles.buttonContainer}>
            {options.map((option) => (
              <TouchableOpacity
                key={option.value}
                style={[
                  styles.circularButton,
                  selectedItems[option.label] && styles.circularButtonSelected,
                ]}
                onPress={() => toggleItemSelection(option.label)}
              >
                <Text style={styles.buttonText}>{option.label}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
  },
  collapsible: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderColor: '#8DF1D3',
    backgroundColor: '#E8F5E9',
    padding: 18,
    width: '100%',
    borderWidth: 1,
  },
  collapsibleText: {
    color: '#444',
    fontSize: 15,
    textAlign: 'left',
  },
  collapsibleOpen: {
    backgroundColor: '#C6C8EE',
  },
  content: {
    padding: 18,
    backgroundColor: '#F92758',
  },
  buttonContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  circularButton: {
    width: 60,
    height: 60,
    borderRadius: 30,
    borderWidth: 2,
    borderColor: '#ddd',
    alignItems: 'center',
    justifyContent: 'center',
    margin: 5,
    backgroundColor: '#fff',
  },
  circularButtonSelected: {
    borderColor: '#8DF1D3',
    backgroundColor: '#E8F5E9',
  },
  buttonText: {
    color: '#444',
    fontSize: 12,
  },
  carat: {
    marginLeft: 10,
  },
});

export default DropDown;
