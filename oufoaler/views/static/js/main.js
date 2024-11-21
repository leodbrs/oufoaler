// Initialize the map
var map;

// Step 1: Define custom icons at the top of main.js
const markerIcons = {
    departure: L.icon({
        iconUrl: 'https://maps.google.com/mapfiles/ms/icons/green-dot.png',
        iconSize: [32, 32],
        iconAnchor: [16, 32],
        popupAnchor: [0, -32]
    }),
    arrival: L.icon({
        iconUrl: 'https://maps.google.com/mapfiles/ms/icons/red-dot.png',
        iconSize: [32, 32],
        iconAnchor: [16, 32],
        popupAnchor: [0, -32]
    }),
    charging: L.icon({
        iconUrl: 'https://maps.google.com/mapfiles/ms/icons/orange-dot.png',
        iconSize: [32, 32],
        iconAnchor: [16, 32],
        popupAnchor: [0, -32]
    })
};

// Function to initialize the map
function initializeMap(latitude, longitude) {
    map = L.map('map').setView([latitude, longitude], 13);

    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);
}

// Use Geolocation API to center the map on the user's city
if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
        (position) => {
            const { latitude, longitude } = position.coords;
            // Initialize and center your map using these coordinates
            initializeMap(latitude, longitude);
        },
        (error) => {
            console.error('Error obtaining location:', error);
            // Fallback to default location (e.g., France)
            initializeMap(46.2276, 2.2137);
        }
    );
} else {
    console.error('Geolocation is not supported by this browser.');
    // Fallback to default location
    initializeMap(46.2276, 2.2137);
}

// Rest of your JavaScript code...

// Update displayed value for sliders
function updateSliderValue(sliderId, valueId) {
    const slider = document.getElementById(sliderId);
    const valueSpan = document.getElementById(valueId);
    valueSpan.textContent = slider.value;
    slider.addEventListener('input', function() {
        valueSpan.textContent = this.value;
    });
}

// Initialize slider values
updateSliderValue('soc_start', 'soc_start_value');
updateSliderValue('soc_min', 'soc_min_value');
updateSliderValue('soc_max', 'soc_max_value');

// Display car image based on selected car
function updateCarImage() {
    const carSelect = document.getElementById('car_id');
    const selectedOption = carSelect.options[carSelect.selectedIndex];
    const imageUrl = selectedOption.getAttribute('data-image');
    const carImageElement = document.querySelector('#car-image img');
    if (imageUrl) {
        carImageElement.src = imageUrl;
        carImageElement.alt = `Image of ${selectedOption.textContent}`;
    } else {
        carImageElement.src = "{{ url_for('static', path='/img/vehicule-placeholder.png') }}";
        carImageElement.alt = 'No image available';
    }
}

// Initialize car image
updateCarImage();

// Update car image when selection changes
document.getElementById('car_id').addEventListener('change', updateCarImage);

// Toggle sliders visibility
const toggleSlidersButton = document.getElementById('toggle-sliders');
const slidersContainer = document.getElementById('sliders-container');
let slidersVisible = false;

toggleSlidersButton.addEventListener('click', function() {
    slidersVisible = !slidersVisible;
    if (slidersVisible) {
        slidersContainer.classList.remove('hidden');
        toggleSlidersButton.textContent = 'Hide Advanced Options';
    } else {
        slidersContainer.classList.add('hidden');
        toggleSlidersButton.textContent = 'Show Advanced Options';
    }
});

// Functions for address suggestions
async function fetchSuggestions(query) {
    const response = await fetch(`https://api-adresse.data.gouv.fr/search/?q=${encodeURIComponent(query)}`);
    const data = await response.json();
    return data.features.map(feature => feature.properties.label);
}

function handleSuggestions(inputElement, suggestionsContainer) {
    inputElement.addEventListener("input", async function () {
        const query = this.value;

        // Start fetching suggestions only if the query is longer than 3 characters
        if (query.length > 3) {
            const results = await fetchSuggestions(query);

            // Clear the suggestions container
            suggestionsContainer.innerHTML = "";

            // Add suggestions to the container
            if (results.length > 0) {
                results.forEach(result => {
                    const suggestionItem = document.createElement("li");
                    suggestionItem.textContent = result;

                    suggestionItem.addEventListener("click", function () {
                        inputElement.value = result;
                        suggestionsContainer.innerHTML = "";
                        suggestionsContainer.classList.add('hidden');
                    });

                    suggestionsContainer.appendChild(suggestionItem);
                });

                // Display the suggestions container
                suggestionsContainer.classList.remove('hidden');
            } else {
                suggestionsContainer.classList.add('hidden'); // Hide the suggestions container
            }
        } else {
            suggestionsContainer.innerHTML = "";
            suggestionsContainer.classList.add('hidden');
        }
    });

    // Hide suggestions when clicking outside
    document.addEventListener('click', function(event) {
        if (!inputElement.contains(event.target) && !suggestionsContainer.contains(event.target)) {
            suggestionsContainer.innerHTML = "";
            suggestionsContainer.classList.add('hidden');
        }
    });
}

// Attach suggestion handlers to the input fields
const departureInput = document.getElementById('departure_address');
const departureSuggestions = document.getElementById('departure_suggestions');
handleSuggestions(departureInput, departureSuggestions);

const arrivalInput = document.getElementById('arrival_address');
const arrivalSuggestions = document.getElementById('arrival_suggestions');
handleSuggestions(arrivalInput, arrivalSuggestions);

// Step 2: Update the form submission handler to use new icons
document.getElementById('itinerary-form').addEventListener('submit', async function(event) {
    event.preventDefault();


    showLoader();
    // Get form values
    const car_id = document.getElementById('car_id').value;
    const soc_start = parseFloat(document.getElementById('soc_start').value);
    const soc_min = parseFloat(document.getElementById('soc_min').value);
    const soc_max = parseFloat(document.getElementById('soc_max').value);
    const departure_address = document.getElementById('departure_address').value;
    const arrival_address = document.getElementById('arrival_address').value;

    try {
        // Geocode addresses
        const departure = await geocodeAddress(departure_address);
        const arrival = await geocodeAddress(arrival_address);

        // Validate coordinates
        if (!departure || isNaN(departure.lat) || isNaN(departure.lon)) {
            throw new Error('Invalid departure coordinates');
        }
        if (!arrival || isNaN(arrival.lat) || isNaN(arrival.lon)) {
            throw new Error('Invalid arrival coordinates');
        }

        // Prepare payload
        const payload = {
            car_id: car_id,
            soc_start: soc_start,
            soc_min: soc_min,
            soc_max: soc_max,
            departure: departure,
            arrival: arrival
        };

        // Send payload to API
        const response = await fetch('/api/v1/itinerary', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`API Error ${response.status}`);
        }

        const data = await response.json();

        if (data.status !== 'ok') {
            throw new Error('Error from API: ' + JSON.stringify(data));
        }

        // Display total charging time
        document.getElementById('result').innerHTML = `<p class="text-lg font-medium">Total Charging Time: ${data.total_charging_time_minutes} minutes</p>`;

        // Clear existing layers (except the base tile layer)
        map.eachLayer(function(layer){
            if (layer instanceof L.Marker || layer instanceof L.Polyline || layer instanceof L.GeoJSON) {
                map.removeLayer(layer);
            }
        });

        // Add GeoJSON route
        const routeGeoJSON = L.geoJSON(data.itinerary, {
            style: {
                color: 'blue',
                weight: 4,
                opacity: 0.8
            }
        }).addTo(map);

        // Add markers for used charging stations
        const recharge_stops = data.recharge_stops;

        if (recharge_stops && recharge_stops.length > 0) {
            recharge_stops.forEach(stop => {
                let lat, lon;

                // Check if stop is an array [lon, lat]
                if (Array.isArray(stop) && stop.length >= 2) {
                    lon = parseFloat(stop[0]);
                    lat = parseFloat(stop[1]);
                } else if (stop.xlongitude && stop.ylatitude) {
                    // If stop is an object with xlongitude and ylatitude properties
                    lon = parseFloat(stop.xlongitude);
                    lat = parseFloat(stop.ylatitude);
                } else {
                    console.error('Invalid format for recharge stop:', stop);
                    return;
                }

                if (isNaN(lat) || isNaN(lon)) {
                    console.error('Invalid coordinates for recharge stop:', stop);
                    return;
                }

                const marker = L.marker([lat, lon], { 
                    icon: markerIcons.charging 
                }).addTo(map);

                marker.bindPopup('Charging Station');
            });
        }

        // Add departure marker
        const departureMarker = L.marker(
            [departure.lat, departure.lon], 
            { icon: markerIcons.departure }
        ).addTo(map);
        departureMarker.bindPopup('Departure: ' + departure_address);

        // Add arrival marker
        const arrivalMarker = L.marker(
            [arrival.lat, arrival.lon], 
            { icon: markerIcons.arrival }
        ).addTo(map);
        arrivalMarker.bindPopup('Arrival: ' + arrival_address);

        // Fit map to bounds
        const bounds = routeGeoJSON.getBounds();
        bounds.extend([departure.lat, departure.lon]);
        bounds.extend([arrival.lat, arrival.lon]);
        map.fitBounds(bounds);

    } catch (error) {
        console.error(error);
        alert('An error occurred: ' + error.message);
    }
    finally {
        hideLoader();
    }
});
// Function to geocode an address
async function geocodeAddress(address) {
    const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(address)}`;
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`HTTP Error ${response.status} when requesting ${address}`);
    }
    const data = await response.json();
    if (data.length > 0) {
        const lat = parseFloat(data[0].lat);
        const lon = parseFloat(data[0].lon);
        if (isNaN(lat) || isNaN(lon)) {
            throw new Error(`Invalid coordinates for address: ${address}`);
        }
        return { lat, lon };
    } else {
        throw new Error(`Address not found: ${address}`);
    }
}

function showLoader() {
    document.getElementById('loader-overlay').style.display = 'flex';
}

function hideLoader() {
    document.getElementById('loader-overlay').style.display = 'none';
}
