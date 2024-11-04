import React, { useState } from 'react';
import GIF from 'gif.js';


  const generateGif = (selectedIngredients, size, ice) => {
    
    const gif = new GIF({
      workers: 2,
      quality: 10,
    });
    // Create frames based on selected ingredients, size, and ice amount
    selectedIngredients.forEach((ingredient) => {
      const frame = document.createElement('canvas'); // Use canvas to draw each frame
      const context = frame.getContext('2d');
      
      // Draw on the canvas (example)
      context.fillStyle = 'white';
      context.fillRect(0, 0, frame.width, frame.height);
      context.fillStyle = 'black';
      context.font = '20px Arial';
      context.fillText(`${size} ${ingredient} with ${ice}`, 10, 30); // Example text

      gif.addFrame(context, { delay: 500 });
    });

    gif.on('finished', (blob) => {
      const url = URL.createObjectURL(blob);
      // Set the GIF URL in the state to display it
      setGifUrl(url);
    });

    gif.render();
  };