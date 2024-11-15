import React, { useState } from 'react';
import { View, StyleSheet, TouchableOpacity, FlatList } from 'react-native';
import Icon from 'react-native-vector-icons/FontAwesome';

const StarRating = ({ onRatingSelected }) => {
  const [rating, setRating] = useState(0);

  const handleRating = (star) => {
    setRating(star);
    onRatingSelected(star);  // Pass the selected rating to the parent component
  };

  const renderStar = ({ item: star }) => {
    return (
      <TouchableOpacity onPress={() => handleRating(star)}>
        <Icon
          name="star"
          size={40}
          color={star <= rating ? '#D30C7B' : '#ffff'}  // Filled if <= rating, otherwise grey
          style={styles.star}
        />
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
      <FlatList
        data={[1, 2, 3, 4, 5]}
        renderItem={renderStar}
        keyExtractor={(star) => star.toString()}
        horizontal
        contentContainerStyle={styles.starContainer}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
  },
  starContainer: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  star: {
    marginHorizontal: 5,
  },
});

export default StarRating;
