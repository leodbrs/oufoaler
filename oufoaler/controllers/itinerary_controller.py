import openrouteservice
import openrouteservice.directions
import openrouteservice.geocode
import pandas as pd
import pyproj
from geopy.distance import geodesic
from shapely import LineString, Point
from shapely.ops import transform

from oufoaler.config import config
from oufoaler.models.api import Coordinates
from oufoaler.models.car import Car


class ItineraryController:
    def __init__(self) -> None:
        self.client = openrouteservice.Client(key=config.openrouteservice_api_key)

    def get_driving_route(
        self,
        start: Coordinates,
        end: Coordinates,
        waypoints: list[tuple[float, float]] = [],
    ) -> dict:
        """Get the driving route between two points."""

        start_coords = [start.lon, start.lat]
        end_coords = [end.lon, end.lat]

        if len(waypoints) > 0:
            coordinates = [start_coords, *waypoints, end_coords]
        else:
            coordinates = [start_coords, end_coords]

        print(coordinates)
        response = openrouteservice.directions.directions(
            client=self.client,
            coordinates=coordinates,
            profile="driving-car",
            format="geojson",
        )
        return response

    def extract_waypoints_from_geojson(self, itinerary) -> list[tuple[float, float]]:
        """Extract waypoints from the GeoJSON itinerary."""
        waypoints = []
        for feature in itinerary["features"]:
            geometry = feature["geometry"]
            if geometry["type"] == "LineString":
                waypoints.extend(geometry["coordinates"])
        return waypoints

    def compute_cumulative_distances(self, waypoints) -> tuple[list[float], float]:
        cumulative_distances = [0.0]
        total_distance = 0.0
        for i in range(1, len(waypoints)):
            distance = geodesic(waypoints[i - 1][::-1], waypoints[i][::-1]).kilometers
            total_distance += distance
            cumulative_distances.append(total_distance)
        return cumulative_distances, total_distance

    def create_linestring_from_points(self, waypoints):
        line = LineString(waypoints)
        return line

    def project_geometry(self, geom, src_crs="epsg:4326", dst_crs="epsg:3857"):
        transformer = pyproj.Transformer.from_crs(
            src_crs, dst_crs, always_xy=True
        ).transform
        projected_geom = transform(transformer, geom)
        return projected_geom

    def compute_station_positions_along_route(self, df_stations, waypoints):
        route_line = LineString(waypoints)

        # Define UTM zone based on the centroid
        centroid = route_line.centroid
        utm_zone = int((centroid.x + 180) / 6) + 1
        is_northern = centroid.y >= 0

        utm_crs = pyproj.CRS.from_dict(
            {
                "proj": "utm",
                "zone": utm_zone,
                "south" if not is_northern else "north": True,
                "ellps": "WGS84",
                "units": "m",
                "no_defs": True,
            }
        )

        project_to_utm = pyproj.Transformer.from_crs(
            "epsg:4326", utm_crs, always_xy=True
        ).transform

        route_line_utm = transform(project_to_utm, route_line)

        valid_stations = []
        for station in df_stations:
            try:
                station_point = Point(
                    float(station.get("xlongitude")),
                    float(station.get("ylatitude")),
                )

                station_point_utm = transform(project_to_utm, station_point)

                distance_along_route_m = route_line_utm.project(station_point_utm)

                distance_along_route_km = distance_along_route_m / 1000.0

                station["distance_along_route_km"] = float(distance_along_route_km)
                valid_stations.append(station)
            except Exception as e:
                print(f"Error computing distance for station: {e}")

        df_stations = pd.DataFrame(valid_stations)
        df_stations = df_stations.dropna(subset=["distance_along_route_km"])
        df_stations = df_stations.sort_values("distance_along_route_km").reset_index(
            drop=True
        )

        return df_stations

    def plan_recharge_stops(
        self, df_route, df_stations, soc_start, soc_min, soc_max, soc_per_km
    ):
        recharge_stops = []
        current_soc = soc_start
        total_distance = df_route["cumulative_distance_km"].iloc[-1]

        last_recharge_distance = 0.0
        current_position = 0.0

        df_stations["puiss_max"] = pd.to_numeric(
            df_stations["puiss_max"], errors="coerce"
        )
        df_stations = df_stations.dropna(subset=["puiss_max"])
        df_stations = df_stations[df_stations["puiss_max"] > 0]

        while current_position < total_distance:
            max_reachable_distance = (
                last_recharge_distance + (current_soc - soc_min) / soc_per_km
            )

            if max_reachable_distance >= total_distance:
                break

            accessible_stations = df_stations[
                (df_stations["distance_along_route_km"] > current_position)
                & (df_stations["distance_along_route_km"] <= max_reachable_distance)
            ]

            if accessible_stations.empty:
                raise Exception(
                    "No accessible charging station before reaching SoC_min."
                )

            high_power_stations = accessible_stations[
                accessible_stations["puiss_max"] >= 50.0
            ]

            if not high_power_stations.empty:
                next_stop = high_power_stations.iloc[-1]
            else:
                next_stop = accessible_stations.iloc[-1]

            recharge_stops.append(next_stop)

            last_recharge_distance = next_stop["distance_along_route_km"]
            current_soc = soc_max

            current_position = last_recharge_distance

        return recharge_stops

    def calculate_total_charging_time(self, recharge_stops, car: Car, soc_min, soc_max):
        """
        Calculate total charging time for all stops in minutes.

        Args:
            recharge_stops (list): List of charging station dictionaries
            vehicle_params (dict): Vehicle parameters including battery capacity and SoC settings

        Returns:
            int: Total charging time in minutes
        """
        total_charging_time_hours = 0.0

        battery_capacity = car.battery_capacity  # kWh
        soc_to_charge = soc_max - soc_min  # percentage

        for stop in recharge_stops:
            # Get charging power in kW, default to 0 if not available
            charger_power = float(stop.get("puiss_max", 0.0))

            if charger_power > 0:
                # Calculate energy needed in kWh
                energy_needed = (soc_to_charge / 100.0) * battery_capacity

                # Calculate charging time in hours
                charging_time = energy_needed / charger_power
                total_charging_time_hours += charging_time

        # Convert to minutes and round to nearest minute
        total_charging_time_minutes = int(round(total_charging_time_hours * 60))
        return total_charging_time_minutes
