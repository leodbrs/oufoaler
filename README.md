# Oufoaler

**Oufoaler** is an intelligent route planner for electric vehicle (EV) drivers, helping you plan journeys with optimal charging stops.

## Technologies

- **Language:** Python 3.10+
- **Backend:** FastAPI
- **Frontend:** Leaflet.js, Tailwind CSS
- **Geospatial:** PyProj, Shapely, GeoPy
- **Routing:** OpenRouteService
- **Data:** Pandas, Pydantic
- **Tools:** Poetry, Taskfile

## Getting Started

### Requirements

- **Python:** 3.10 or higher
- **Poetry:** For managing dependencies

### Installation

1. **Clone the Repository**

   ```bash
   git clone <repository-url>
   cd oufoaler
   ```

2. **Install Dependencies**

   ```bash
   poetry install
   ```

3. **Set Up Environment Variables**

   Create a `.env` file in the project root:

   ```
   OUFOALER_LOGGING_LEVEL=INFO
   OUFOALER_OPENROUTESERVICE_API_KEY=your_openrouteservice_api_key
   OUFOALER_CHARGETRIP_CLIENT_ID=your_chargetrip_client_id
   OUFOALER_CHARGETRIP_APP_ID=your_chargetrip_app_id
   ```

   _Replace the placeholders with your actual API keys and credentials._

## Running the App

### Development

Start the development server with hot-reloading:

```bash
task development
```

### Production

Run the app in production mode:

```bash
task production
```

Access the app at [http://localhost:8000](http://localhost:8000).

## API Documentation

Explore the API using these links:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Deployment

Oufoaler can be deployed on:

- **Azure Web Apps:** Check `main_oufoaler.yml` for settings.
- **Vercel:** See `vercel.json` for configuration.
