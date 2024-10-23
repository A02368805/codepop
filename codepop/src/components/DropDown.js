import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, FlatList, Modal } from 'react-native';

const DropDown = ({ options, onSelect }) => {
  const [isVisible, setIsVisible] = useState(false); // Control drop-down visibility
  const [selectedValue, setSelectedValue] = useState(null); // Hold the selected value

  const handleSelect = (option) => {
    setSelectedValue(option);
    onSelect(option);
    setIsVisible(false); // Close the drop-down after selecting
  };

  return (
    <View style={styles.container}>
      {/* Button to open dropdown */}
      <TouchableOpacity style={styles.dropdownButton} onPress={() => setIsVisible(!isVisible)}>
        <Text style={styles.dropdownButtonText}>
          {selectedValue ? selectedValue.label : 'Select an option'}
        </Text>
      </TouchableOpacity>

      {/* Modal to display dropdown options */}
      {isVisible && (
        <Modal transparent={true} animationType="fade">
          <TouchableOpacity
            style={styles.overlay}
            onPress={() => setIsVisible(false)} // Close modal if user taps outside
          >
            <View style={styles.dropdownMenu}>
              <FlatList
                data={options}
                keyExtractor={(item) => item.value.toString()}
                renderItem={({ item }) => (
                  <TouchableOpacity
                    style={styles.dropdownItem}
                    onPress={() => handleSelect(item)}
                  >
                    <Text style={styles.dropdownItemText}>{item.label}</Text>
                  </TouchableOpacity>
                )}
              />
            </View>
          </TouchableOpacity>
        </Modal>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    margin: 20,
  },
  dropdownButton: {
    padding: 15,
    backgroundColor: '#ddd',
    borderRadius: 5,
  },
  dropdownButtonText: {
    fontSize: 16,
  },
  overlay: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
  },
  dropdownMenu: {
    width: '80%',
    backgroundColor: 'white',
    borderRadius: 8,
    padding: 10,
  },
  dropdownItem: {
    padding: 15,
  },
  dropdownItemText: {
    fontSize: 16,
  },
});

export default DropDown;
