import React from 'react';
import { View, StyleSheet } from 'react-native';

const Gif = ({ layers, height = 250, width = 150 }) => {
  return (
    <View style={styles.container}>
      {/* Straw positioned above the drink container */}
      {/* <View style={styles.straw}></View> */}
      <View style={[styles.straw, { height: height * 0.84 }]}></View>
      
      {/* Drink container */}
      <View style={[
          styles.gifContainer,
          {
            height, // Use height prop
            width,  // Use width prop
          },
        ]}>
        {/* Render layers stacked from the bottom */}
        {layers.map((layer, index) => (
          <View
            key={index}
            style={[
              styles.layer,
              { 
                backgroundColor: layer.color, 
                height: `${layer.height}%`, 
                bottom: `${index * (100 / layers.length)}%`,  // Stack from bottom
              },
            ]}
          />
        ))}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
  },
  straw: {
    position: 'absolute',
    top: 10, // Position the straw above the cup
    left: '50%',
    width: 10,
    height: 210,
    backgroundColor: '#8DF1D3',  // Straw color
    borderRadius: 5,
    transform: [{ translateX: -5 }],  // Center the straw horizontally
    zIndex: 1, // Ensure straw appears on top of the drink container
  },
  gifContainer: {
    // width: 150,  // Top width of the cup 150
    // height: 250, //250
    marginTop:30,
    borderWidth: 1,
    borderTopColor: '#FFA686',
    borderLeftColor: 'black',
    borderBottomLeftRadius: 40,  // Smaller radius on bottom-left
    borderBottomRightRadius: 40,  // Smaller radius on bottom-right
    overflow: 'hidden',
    position: 'relative',  // For absolute positioning of layers
    backgroundColor: '#FFA686', // Cup background color
    justifyContent: 'flex-end', // Position layers at the bottom
  },
  layer: {
    position: 'absolute',
    width: '100%',
    bottom: 0, // Start layers stacking from the bottom of the cup
  },
});

export default Gif;