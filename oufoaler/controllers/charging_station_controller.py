import json
import math
from typing import List

import requests
from shapely import Polygon, box, unary_union

from oufoaler.controllers.itinerary_controller import ItineraryController
from oufoaler.models.car import Car


class ChargingStationsController:
    def simplify_geometry(self, area):
        simplified_geom = area.simplify(0.01)
        return simplified_geom

    def round_coordinates(self, area, decimal_places=3):
        def round_point(coords):
            return tuple(round(coord, decimal_places) for coord in coords)

        if area.geom_type == "Polygon":
            exterior = [round_point(pt) for pt in area.exterior.coords]
            interiors = [
                [round_point(pt) for pt in interior.coords]
                for interior in area.interiors
            ]
            rounded_geom = Polygon(exterior, interiors)
        elif area.geom_type == "MultiPolygon":
            rounded_geom = unary_union(
                [self.round_coordinates(p, decimal_places) for p in area.geoms]
            )
        else:
            rounded_geom = area
        return rounded_geom

    def fetch_charging_stations(
        self, area: str, car: Car, session: requests.Session
    ) -> List[dict]:
        """Fetch charging stations from the API for the given search area."""
        stations = []
        offset = 0
        total_count = 1
        where_clause = (
            f"type_prise like '*T2*' AND "
            f"within(geo_point_borne, geom'{area}') AND "
            f"puiss_max <= {car.power}"
        )

        try:
            while offset < total_count:
                params = {
                    "select": "*",
                    "where": where_clause,
                    "limit": 100,
                    "offset": offset,
                }
                response = session.get(
                    "https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/bornes-irve/records",
                    params=params,
                    timeout=60,
                )
                response.raise_for_status()
                data = response.json()
                batch = data.get("results", [])
                stations.extend(batch)
                total_count = data.get("total_count", 0)
                offset += 100
        except requests.exceptions.HTTPError as http_err:
            raise http_err
        except requests.exceptions.RequestException as req_err:
            raise req_err
        except json.JSONDecodeError as json_err:
            raise json_err
        except Exception as e:
            raise e
        return stations

    def split_polygon_into_grid(
        self, buffered_projected: Polygon, grid_size: int
    ) -> List[Polygon]:
        minx, miny, maxx, maxy = buffered_projected.bounds
        grid_polygons = []
        x_steps = math.ceil((maxx - minx) / grid_size)
        y_steps = math.ceil((maxy - miny) / grid_size)

        for i in range(x_steps):
            for j in range(y_steps):
                grid_minx = minx + i * grid_size
                grid_miny = miny + j * grid_size
                grid_maxx = min(grid_minx + grid_size, maxx)
                grid_maxy = min(grid_miny + grid_size, maxy)
                grid_cell = box(grid_minx, grid_miny, grid_maxx, grid_maxy)
                sub_polygon = buffered_projected.intersection(grid_cell)
                if not sub_polygon.is_empty:
                    grid_polygons.append(sub_polygon)
        return grid_polygons

    def find_charging_stations_near_route(
        self, waypoints: list, car: Car, session: requests.Session
    ) -> List[dict]:
        BUFFER_DISTANCE = 20000  # in meters
        SUB_POLYGON_SIZE = 300000  # in meters

        itinerary_ctrl = ItineraryController()

        # Step 1: Create LineString from the points
        line = itinerary_ctrl.create_linestring_from_points(waypoints)
        if not line:
            raise ValueError("Failed to create LineString from waypoints.")

        # Step 2: Project to metric CRS (EPSG:3857) for buffering
        line_proj = itinerary_ctrl.project_geometry(line)
        if not line_proj:
            raise ValueError("Failed to project LineString.")

        # Step 3: Buffer the LineString
        buffered = line_proj.buffer(BUFFER_DISTANCE)

        # Step 4: Re-project back to WGS84 (EPSG:4326)
        buffered_wgs84 = itinerary_ctrl.project_geometry(
            buffered, src_crs="epsg:3857", dst_crs="epsg:4326"
        )
        if not buffered_wgs84:
            raise ValueError("Failed to reproject buffered polygon to WGS84.")

        buffered_wgs84 = self.simplify_geometry(buffered_wgs84)
        buffered_wgs84 = self.round_coordinates(buffered_wgs84)

        # Step 5: Project buffered polygon to metric CRS (EPSG:3857)
        buffered_projected = itinerary_ctrl.project_geometry(
            buffered_wgs84, src_crs="epsg:4326", dst_crs="epsg:3857"
        )
        if not buffered_projected:
            raise ValueError("Failed to project buffered polygon to metric CRS.")

        # Step 6: Split buffered polygon into sub-polygons
        if not isinstance(buffered_projected, Polygon):
            raise ValueError("Expected a Polygon geometry")
        sub_polygons_projected = self.split_polygon_into_grid(
            buffered_projected, SUB_POLYGON_SIZE
        )

        if not sub_polygons_projected:
            raise ValueError("No sub-polygons created. Check buffer and grid size.")

        # Step 7: Re-project sub-polygons back to WGS84
        sub_polygons_wgs84 = [
            itinerary_ctrl.project_geometry(
                sub_poly, src_crs="epsg:3857", dst_crs="epsg:4326"
            )
            for sub_poly in sub_polygons_projected
            if sub_poly and not sub_poly.is_empty
        ]

        # Step 8: Fetch charging stations for each sub-polygon
        all_stations = []
        for sub_poly in sub_polygons_wgs84:
            wkt = sub_poly.wkt
            stations = self.fetch_charging_stations(wkt, car, session)
            all_stations.extend(stations)

        # Deduplicate stations based on 'id_station'
        unique_stations = {
            station.get("id_station"): station
            for station in all_stations
            if station.get("id_station")
        }

        return list(unique_stations.values())
