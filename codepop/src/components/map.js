import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, PermissionsAndroid, Platform } from 'react-native';
// import MapView, { Marker } from 'react-native-maps';
// import Geolocation from 'react-native-geolocation-service';

// make sure to run npm install react-native-maps in the VE for this to work ... I think

const GeoMap = () => {
    // const [region, setRegion] = useState({
    //     latitude: 37.7749, // Default to San Francisco
    //     longitude: -122.4194,
    //     latitudeDelta: 0.01,
    //     longitudeDelta: 0.01,
    //   });

    //   const requestLocationPermission = async () => {
    //     if (Platform.OS === 'android') {
    //       const granted = await PermissionsAndroid.request(
    //         PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION
    //       );
    //       return granted === PermissionsAndroid.RESULTS.GRANTED;
    //     }
    //     return true; // iOS permissions are handled via plist
    //   };

    // useEffect(() => {
    //     const getLocation = async () => {
    //       const hasPermission = await requestLocationPermission();
    //       if (!hasPermission) return;
    
    //       Geolocation.getCurrentPosition(
    //         (position) => {
    //           const { latitude, longitude } = position.coords;
    //           setRegion({
    //             ...region,
    //             latitude,
    //             longitude,
    //           });
    //         },
    //         (error) => {
    //           console.error("Error getting location:", error);
    //         },
    //         { enableHighAccuracy: true, timeout: 15000, maximumAge: 10000 }
    //       );
    //     };
    
    //     getLocation();
    //   }, []);

    // return(
    //     <MapView
    //         style={styles.map}
    //         region={region}
    //         showsUserLocation
    //         followsUserLocation
    //       >
    //         <Marker coordinate={{ latitude: region.latitude, longitude: region.longitude }} />
    //     </MapView>       
    // );
};

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: '#8DF1D3' },
    padding: { padding: 10 },
    section: { width: '100%', marginBottom: 15, borderRadius: 8, alignItems: 'center' },
    mapSection: { height: 300, overflow: 'hidden', borderRadius: 8 },
    map: { width: '100%', height: '100%' },
    ratingSection: { backgroundColor: '#FFA686' },
    timerAndLockerContainer: { flexDirection: 'row', justifyContent: 'space-between' },
    timerSection: { backgroundColor: '#C6C8EE', flex: 1, marginRight: 10 },
    lockerComboSection: { backgroundColor: '#F92758', flex: 1, marginLeft: 10 },
    heading: { fontSize: 20, fontWeight: 'bold', color: '#333' },
    timer: { fontSize: 30, fontWeight: 'bold', color: '#FFA686' },
    successMessage: { fontSize: 15, color: '#8DF1D3' },
    ratingLabel: { fontSize: 15, fontWeight: '600', color: '#333' },
    lockerCombo: { fontSize: 20, fontWeight: '900', color: '#333' },
  });

  export default GeoMap;
  