from dotenv import load_dotenv

from oufoaler.models.settings import Settings

load_dotenv()
config = Settings()  # type: ignore
