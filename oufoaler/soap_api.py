import requests
from spyne import (
    Application,
    Array,
    ComplexModel,
    Float,
    Integer,
    ServiceBase,
    Unicode,
    rpc,
)
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication


# SOAP Models
class CoordinatesModel(ComplexModel):
    lat = Float
    lon = Float


class ItinerarySummaryModel(ComplexModel):
    distance = Float
    duration = Float


class StepModel(ComplexModel):
    distance = Float
    duration = Float
    type = Integer
    instruction = Unicode
    name = Unicode
    exit_number = Integer(min_occurs=0)
    way_points = Array(Integer)


class SegmentModel(ComplexModel):
    distance = Float
    duration = Float
    steps = Array(StepModel)


class FeaturePropertiesModel(ComplexModel):
    segments = Array(SegmentModel)
    summary = ItinerarySummaryModel
    way_points = Array(Integer)


class FeatureModel(ComplexModel):
    properties = FeaturePropertiesModel


class ItineraryModel(ComplexModel):
    features = Array(FeatureModel)


class ItineraryResponseModel(ComplexModel):
    status = Unicode
    message = Unicode
    total_charging_time_minutes = Float
    itinerary = ItineraryModel
    recharge_stops = Array(CoordinatesModel)


class ItineraryRequestModel(ComplexModel):
    car_id = Unicode
    soc_start = Float
    soc_min = Float
    soc_max = Float
    departure_lat = Float
    departure_lon = Float
    arrival_lat = Float
    arrival_lon = Float


# SOAP Service
class ItineraryService(ServiceBase):
    @rpc(ItineraryRequestModel, _returns=ItineraryResponseModel)
    def get_itinerary(ctx, request):
        # Transform SOAP request to REST request
        rest_payload = {
            "car_id": request.car_id,
            "soc_start": request.soc_start,
            "soc_min": request.soc_min,
            "soc_max": request.soc_max,
            "departure": {"lat": request.departure_lat, "lon": request.departure_lon},
            "arrival": {"lat": request.arrival_lat, "lon": request.arrival_lon},
        }

        # Call REST API
        try:
            response = requests.post(
                "http://localhost:8000/api/v1/itinerary", json=rest_payload
            )
            data = response.json()

            # Transform REST response to SOAP response

            # Build recharge_stops
            recharge_stops_data = data.get("recharge_stops", [])
            recharge_stops = []
            for coord in recharge_stops_data:
                lon, lat = coord
                recharge_stops.append(CoordinatesModel(lat=lat, lon=lon))

            # Build itinerary
            features_data = data["itinerary"]["features"]
            features = []
            for feature_data in features_data:
                properties_data = feature_data["properties"]
                segments_data = properties_data.get("segments", [])
                summary_data = properties_data.get("summary", {})
                way_points_data = properties_data.get("way_points", [])

                # Build segments
                segments = []
                for segment_data in segments_data:
                    steps_data = segment_data.get("steps", [])
                    steps = []
                    for step_data in steps_data:
                        step = StepModel(
                            distance=step_data.get("distance"),
                            duration=step_data.get("duration"),
                            type=step_data.get("type"),
                            instruction=step_data.get("instruction"),
                            name=step_data.get("name"),
                            exit_number=step_data.get("exit_number"),
                            way_points=step_data.get("way_points", []),
                        )
                        steps.append(step)

                    segment = SegmentModel(
                        distance=segment_data.get("distance"),
                        duration=segment_data.get("duration"),
                        steps=steps,
                    )
                    segments.append(segment)

                # Build summary
                summary = ItinerarySummaryModel(
                    distance=summary_data.get("distance"),
                    duration=summary_data.get("duration"),
                )

                # Build properties
                properties = FeaturePropertiesModel(
                    segments=segments,
                    summary=summary,
                    way_points=way_points_data,
                )

                # Build feature
                feature = FeatureModel(properties=properties)

                features.append(feature)

            itinerary = ItineraryModel(features=features)

            return ItineraryResponseModel(
                status=data.get("status", "error"),
                message=data.get("message", ""),
                total_charging_time_minutes=data.get("total_charging_time_minutes", 0),
                itinerary=itinerary,
                recharge_stops=recharge_stops,
            )
        except Exception as e:
            return ItineraryResponseModel(
                status="error", message=str(e), total_charging_time_minutes=0
            )


# Create SOAP Application
soap_app = Application(
    [ItineraryService],
    tns="itinerary",
    in_protocol=Soap11(validator="lxml"),
    out_protocol=Soap11(),
)

# WSGI Application
wsgi_app = WsgiApplication(soap_app)
