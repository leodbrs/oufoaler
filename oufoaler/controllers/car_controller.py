import requests
from fastapi.logger import logger

from oufoaler.config import config
from oufoaler.models.car import Car


class CarController:
    def __init__(self) -> None:
        self._cars_cache: list[Car] = list()

    def get_cars(self) -> list[Car]:
        url = "https://api.chargetrip.io/graphql"
        headers = {
            "Content-Type": "application/json",
            "x-client-id": config.chargetrip_client_id,
            "x-app-id": config.chargetrip_app_id,
        }

        body = '{"query":"query vehicleListAll { vehicleList { id naming { make model version edition chargetrip_version } drivetrain { type } connectors { standard power max_electric_power time speed } adapters { standard power max_electric_power time speed } battery { usable_kwh full_kwh } body { seats } availability { status } range { chargetrip_range { best worst } } media { image { id type url height width thumbnail_url thumbnail_height thumbnail_width } brand { id type url height width thumbnail_url thumbnail_height thumbnail_width } video { id url } } routing { fast_charging_support } connect { providers } } }"}'

        try:
            response = requests.post(url, headers=headers, data=body)
            response.raise_for_status()
            response_data = response.json()
            # logger.debug(f"GraphQL API Response: {response_data}")
            if "errors" in response_data:
                error_message = response_data["errors"][0]["message"]
                logger.error(f"GraphQL API Error: {error_message}")
                raise RuntimeError(f"Failed to fetch cars: {error_message}")

            exclude_ids = {"63ef773bc7ac42e426e66301", "63d3e0ce44bd322626dd23f8"}

            cars = []
            for car in response_data.get("data", {}).get("vehicleList", []):
                if car["id"] in exclude_ids:
                    continue

                p_max = 0.0
                for connector in car["connectors"]:
                    p_max = max(p_max, connector["max_electric_power"])

                cars.append(
                    Car(
                        id=car["id"],
                        make=car["naming"]["make"],
                        model=car["naming"]["model"],
                        version=car["naming"]["chargetrip_version"],
                        power=p_max,
                        battery_capacity=float(car["battery"]["usable_kwh"]),
                        range_best=float(car["range"]["chargetrip_range"]["best"]),
                        range_worst=float(car["range"]["chargetrip_range"]["worst"]),
                        image=car["media"]["image"]["url"],
                    )
                )
            self._cars_cache = cars
            return cars
        except Exception as e:
            raise RuntimeError(f"Failed to fetch cars: {str(e)}") from e

    def calculate_soc_per_km(self, car: Car) -> float:
        try:
            average_range = (car.range_best + car.range_worst) / 2
            if average_range == 0:
                raise ZeroDivisionError("Average range cannot be zero.")
            soc_per_km = 100.0 / average_range
            return soc_per_km
        except (TypeError, ZeroDivisionError) as e:
            print(f"Error calculating soc_per_km: {e}")
            return 0.0

    def calculate_max_distance_without_charging(
        self, soc_start: float, soc_min: float, soc_per_km: float
    ) -> float:
        try:
            if soc_per_km == 0:
                raise ValueError("soc_per_km cannot be zero.")
            max_distance = (soc_start - soc_min) / soc_per_km
            return max_distance
        except (TypeError, ValueError) as e:
            print(f"Error calculating max distance: {e}")
            return 0.0

    def get_car_by_id(self, car_id: str) -> Car:
        # Force cars fetch if cache is empty
        if self._cars_cache.__len__() == 0:
            self.get_cars()

        print(self._cars_cache)
        # Find car in cache
        car = next((car for car in self._cars_cache if car.id == car_id), None)
        if not car:
            raise ValueError(f"Car with id {car_id} not found")

        return car
