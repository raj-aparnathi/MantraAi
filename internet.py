"""
internet.py – Mantra AI v1.0
Weather, news, and Wikipedia lookups.

API keys (optional – features gracefully degrade):
  - OpenWeatherMap: data/config.json → api_keys.openweathermap
  - NewsAPI:        data/config.json → api_keys.newsapi
  - Wikipedia: no key required
"""

import requests
import wikipedia

import config
from utils import log, normalize, contains_any, extract_after


class Internet:

    WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
    NEWS_URL    = "https://newsapi.org/v2/top-headlines"

    # ── Weather ────────────────────────────────────────────────────────────────

    def get_weather(self, city: str | None = None) -> str:
        """Fetch current weather for `city` (falls back to config default)."""
        if not config.OPENWEATHER_API_KEY:
            return (
                "Weather is unavailable. Please add your OpenWeatherMap API key "
                "to data/config.json."
            )

        city = city or config.DEFAULT_CITY
        params = {
            "q":     city,
            "appid": config.OPENWEATHER_API_KEY,
            "units": config.WEATHER_UNITS,
        }
        try:
            resp = requests.get(self.WEATHER_URL, params=params, timeout=8)
            resp.raise_for_status()
            data = resp.json()
            desc     = data["weather"][0]["description"].capitalize()
            temp     = round(data["main"]["temp"])
            feels    = round(data["main"]["feels_like"])
            humidity = data["main"]["humidity"]
            unit_sym = "°C" if config.WEATHER_UNITS == "metric" else "°F"
            log.info(f"Weather fetched for {city}: {desc}, {temp}{unit_sym}")
            return (
                f"The weather in {city} is {desc}. "
                f"Temperature is {temp}{unit_sym}, feels like {feels}{unit_sym}. "
                f"Humidity is {humidity} percent."
            )
        except requests.HTTPError as e:
            if resp.status_code == 404:
                return f"I couldn't find weather data for '{city}'. Please check the city name."
            log.error(f"Weather API HTTP error: {e}")
            return "Sorry, I couldn't fetch the weather right now."
        except requests.RequestException as e:
            log.error(f"Weather request error: {e}")
            return "I'm having trouble connecting to the weather service."

    # ── News ───────────────────────────────────────────────────────────────────

    def get_news(self, count: int = 5) -> str:
        """Fetch top news headlines."""
        if not config.NEWSAPI_KEY:
            return (
                "News is unavailable. Please add your NewsAPI key "
                "to data/config.json."
            )

        params = {
            "apiKey":   config.NEWSAPI_KEY,
            "country":  "us",
            "pageSize": count,
        }
        try:
            resp = requests.get(self.NEWS_URL, params=params, timeout=8)
            resp.raise_for_status()
            articles = resp.json().get("articles", [])
            if not articles:
                return "I couldn't find any news at the moment."

            headlines = [a["title"].split(" - ")[0] for a in articles[:count] if a.get("title")]
            intro = f"Here are the top {len(headlines)} headlines. "
            numbered = " ".join(
                f"Number {i}: {h}." for i, h in enumerate(headlines, 1)
            )
            log.info(f"Fetched {len(headlines)} news headlines.")
            return intro + numbered
        except Exception as e:
            log.error(f"News error: {e}")
            return "Sorry, I couldn't fetch the news right now."

    # ── Wikipedia ──────────────────────────────────────────────────────────────

    def search_wikipedia(self, query: str) -> str:
        """Search Wikipedia and return a 2-sentence summary."""
        if not query:
            return "What would you like to search on Wikipedia?"
        try:
            wikipedia.set_lang("en")
            summary = wikipedia.summary(query, sentences=2, auto_suggest=True)
            log.info(f"Wikipedia summary fetched for: '{query}'")
            return summary
        except wikipedia.exceptions.DisambiguationError as e:
            first = e.options[0] if e.options else query
            return self.search_wikipedia(first)
        except wikipedia.exceptions.PageError:
            return f"I couldn't find a Wikipedia article about '{query}'."
        except Exception as e:
            log.error(f"Wikipedia error: {e}")
            return "Sorry, I had trouble searching Wikipedia."

    # ── Command Router ─────────────────────────────────────────────────────────

    def parse_and_execute(self, text: str) -> str | None:
        """Route internet commands. Returns spoken response or None."""
        t = normalize(text)

        # Weather
        if contains_any(t, ["weather", "temperature", "forecast"]):
            # Try to extract city name
            city = None
            for kw in ["weather in", "weather for", "temperature in"]:
                city_part = extract_after(t, kw)
                if city_part:
                    city = city_part.strip()
                    break
            return self.get_weather(city)

        # News
        if contains_any(t, ["news", "headlines", "latest news", "top stories"]):
            return self.get_news()

        # Wikipedia
        if contains_any(t, ["wikipedia", "search wikipedia", "tell me about",
                             "what is", "who is", "who was", "what was"]):
            for kw in ["search wikipedia for", "tell me about", "what is",
                       "who is", "who was", "what was", "wikipedia"]:
                query = extract_after(t, kw)
                if query:
                    return self.search_wikipedia(query)

        return None


# ── Quick self-test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    inet = Internet()
    print(inet.search_wikipedia("Python programming language"))
    # These need API keys:
    # print(inet.get_weather("Mumbai"))
    # print(inet.get_news())
