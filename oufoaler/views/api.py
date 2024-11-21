import pandas as pd
import requests
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from oufoaler.controllers.car_controller import CarController
from oufoaler.controllers.charging_station_controller import (
    ChargingStationsController,
)
from oufoaler.controllers.itinerary_controller import ItineraryController
from oufoaler.models.api import ItineraryRequest

router = APIRouter(prefix="/api/v1", tags=["api"])

itinerary_ctrl = ItineraryController()
car_ctrl = CarController()
charging_stations_ctrl = ChargingStationsController()


@router.post("/itinerary", status_code=200, response_class=JSONResponse)
def get_itinerary(request: ItineraryRequest):
    try:
        car = car_ctrl.get_car_by_id(request.car_id)
    except ValueError as e:
        return JSONResponse(
            status_code=404, content={"status": "error", "message": str(e)}
        )
    except RuntimeError:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Internal server error"},
        )
    start_coords = request.departure
    end_coords = request.arrival

    # Step 1: Calculate itinerary
    initial_itinerary = itinerary_ctrl.get_driving_route(start_coords, end_coords)

    # Step 2: Fetch route details
    waypoints = itinerary_ctrl.extract_waypoints_from_geojson(initial_itinerary)

    # Step 3: Fetch route distance
    cumulative_distances, total_distance = itinerary_ctrl.compute_cumulative_distances(
        waypoints
    )

    # Step 4: Create a pd DataFrame
    route_df = pd.DataFrame(
        {"waypoint": waypoints, "cumulative_distance_km": cumulative_distances}
    )

    # Step 5: Calculate SoC per km
    soc_per_km = car_ctrl.calculate_soc_per_km(car)

    # Step 6: Calculate max distance without charging
    max_distance_without_charging = car_ctrl.calculate_max_distance_without_charging(
        request.soc_start, request.soc_min, soc_per_km
    )

    # Step 7: Check if charging is necessary
    if max_distance_without_charging >= total_distance:
        return JSONResponse(
            status_code=200,
            content={
                "status": "ok",
                "itinerary": initial_itinerary,
                "recharge_stops": [],
                "total_charging_time_minutes": 0,
            },
        )
    else:
        session = requests.Session()

        # Fetch charging stations near the route
        stations = charging_stations_ctrl.find_charging_stations_near_route(
            waypoints, car, session
        )

        # Compute positions of stations along the route
        stations_df = itinerary_ctrl.compute_station_positions_along_route(
            stations, waypoints
        )

        # Plan recharge stops
        try:
            recharge_stops = itinerary_ctrl.plan_recharge_stops(
                route_df,
                stations_df,
                request.soc_start,
                request.soc_min,
                request.soc_max,
                soc_per_km,
            )
        except Exception as e:
            return JSONResponse(
                status_code=422,
                content={
                    "status": "error",
                    "message": "No accessible charging stations found before reaching minimum battery level.",
                },
            )

        total_charging_time = itinerary_ctrl.calculate_total_charging_time(
            recharge_stops, car, request.soc_min, request.soc_max
        )
        charging_stations_waypoints = [
            tuple([station["xlongitude"], station["ylatitude"]])
            for station in recharge_stops
        ]

        final_itinerary_waypoints = itinerary_ctrl.get_driving_route(
            start_coords, end_coords, charging_stations_waypoints
        )
        # Prepare response
        return JSONResponse(
            status_code=200,
            content={
                "status": "ok",
                "itinerary": final_itinerary_waypoints,
                "recharge_stops": charging_stations_waypoints,
                "total_charging_time_minutes": total_charging_time,
            },
        )
