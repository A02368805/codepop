import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';

const DropDown = ({ title, options = [], onSelect, isOpen, setOpen}) => {
  // const [isOpen, setIsOpen] = useState(false);
  const [selectedItems, setSelectedItems] = useState({});

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
                  selectedItems[option.value] && styles.circularButtonSelected,
                ]}
                onPress={() => toggleItemSelection(option.value)}
              >
                <Text style={styles.buttonText}>{option.value}</Text>
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
    borderColor: '#6FD9BB',
    backgroundColor: '#C8E6C9',
    padding: 18,
    width: '100%',
    borderWidth: 2,
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
    backgroundColor: '#FF6685',
  },
  buttonContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
  },
  circularButton: {
    width: 60,
    height: 60,
    borderRadius: 30,
    borderWidth: 1,
    borderColor: '#ddd',
    alignItems: 'center',
    justifyContent: 'center',
    margin: 5,
    backgroundColor: '#FFA686',
    shadowColor: '#000',
    shadowOffset: { width: 3, height: 3 },
    shadowOpacity: 0.4,
    shadowRadius: 3,
    elevation: 5, // For Android
  },
  circularButtonSelected: {
    borderColor: '#8DF1D3',
    backgroundColor: '#8DF1D3',
    shadowColor: '#8DF1D3',
    shadowOffset: { width: 1, height: 1 },
    shadowOpacity: 0.6,
    shadowRadius: 2,
  },
  buttonText: {
    color: '#444',
    fontSize: 10,
    fontWeight: 'bold',
  },
});

export default DropDown;
