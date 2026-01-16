#!/bin/bash
# Test script to add a location for Julius Tetteh

# First, get the access token (you'll need to login first)
# Replace with actual token or add login logic

TOKEN="YOUR_ACCESS_TOKEN_HERE"

# Add a primary location
curl -X POST http://localhost:8000/api/farms/locations/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "gps_address_string": "GA-0123-4567",
    "region": "Greater Accra",
    "district": "Accra Metro",
    "constituency": "Odododiodoo",
    "community": "James Town",
    "land_size_acres": 2.5,
    "land_ownership_status": "Owned",
    "road_accessibility": "All Year",
    "nearest_landmark": "Near James Town Police Station"
  }'
