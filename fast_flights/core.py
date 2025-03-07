from typing import List, Literal, Optional
from itertools import groupby
from operator import attrgetter
from datetime import datetime, timedelta

from selectolax.lexbor import LexborHTMLParser, LexborNode

from .schema import Flight, Result
from .flights_impl import FlightData, Passengers
from .filter import TFSData
from .fallback_playwright import fallback_playwright_fetch
from .primp import Client, Response


def fetch(params: dict) -> Response:
    client = Client(impersonate="chrome_126", verify=False)
    res = client.get("https://www.google.com/travel/flights", params=params)
    assert res.status_code == 200, f"{res.status_code} Result: {res.text_markdown}"
    return res


def get_flights_from_filter(
    filter: TFSData,
    currency: str = "",
    *,
    mode: Literal["common", "fallback", "force-fallback", "local"] = "common",
) -> Result:
    data = filter.as_b64()

    params = {
        "tfs": data.decode("utf-8"),
        "hl": "en",
        "tfu": "EgQIABABIgA",
        "curr": currency,
    }

    if mode in {"common", "fallback"}:
        try:
            res = fetch(params)
        except AssertionError as e:
            if mode == "fallback":
                res = fallback_playwright_fetch(params)
            else:
                raise e

    elif mode == "local":
        from .local_playwright import local_playwright_fetch

        res = local_playwright_fetch(params)

    else:
        res = fallback_playwright_fetch(params)

    try:
        return parse_response(res)
    except RuntimeError as e:
        if mode == "fallback":
            return get_flights_from_filter(filter, mode="force-fallback")
        raise e


def get_flights(
    *,
    flight_data: List[FlightData],
    trip: Literal["round-trip", "one-way", "multi-city"],
    passengers: Passengers,
    seat: Literal["economy", "premium-economy", "business", "first"],
    fetch_mode: Literal["common", "fallback", "force-fallback", "local"] = "common",
    max_stops: Optional[int] = None,
) -> Result:
    return get_flights_from_filter(
        TFSData.from_interface(
            flight_data=flight_data,
            trip=trip,
            passengers=passengers,
            seat=seat,
            max_stops=max_stops,
        ),
        mode=fetch_mode,
    )


def parse_response(
    r: Response, *, dangerously_allow_looping_last_item: bool = False
) -> Result:
    class _blank:
        def text(self, *_, **__):
            return ""

        def iter(self):
            return []

    blank = _blank()

    def safe(n: Optional[LexborNode]):
        return n or blank

    parser = LexborHTMLParser(r.text)
    flights = []

    for i, fl in enumerate(parser.css('div[jsname="IWWDBc"], div[jsname="YdtKid"]')):
        is_best_flight = i == 0

        for item in fl.css("ul.Rk10dc li")[
            : (None if dangerously_allow_looping_last_item or i == 0 else -1)
        ]:
            # Flight name
            name = safe(item.css_first("div.sSHqwe.tPgKwe.ogfYpf span")).text(
                strip=True
            )

            # Get departure & arrival time
            dp_ar_node = item.css("span.mv1WYe div")
            try:
                departure_time = dp_ar_node[0].text(strip=True)
                arrival_time = dp_ar_node[1].text(strip=True)
            except IndexError:
                # sometimes this is not present
                departure_time = ""
                arrival_time = ""

            # Get arrival time ahead
            time_ahead = safe(item.css_first("span.bOzv6")).text()

            # Get duration
            duration = safe(item.css_first("li div.Ak5kof div")).text()

            # Get flight stops
            stops = safe(item.css_first(".BbR8Ec .ogfYpf")).text()

            # Get delay
            delay = safe(item.css_first(".GsCCve")).text() or None

            # Get prices
            price = safe(item.css_first(".YMlIz.FpEdX")).text() or "0"

            # Stops formatting
            try:
                stops_fmt = 0 if stops == "Nonstop" else int(stops.split(" ", 1)[0])
            except ValueError:
                stops_fmt = "Unknown"

            flights.append(
                {
                    "is_best": is_best_flight,
                    "name": name,
                    "departure": " ".join(departure_time.split()),
                    "arrival": " ".join(arrival_time.split()),
                    "arrival_time_ahead": time_ahead,
                    "duration": duration,
                    "stops": stops_fmt,
                    "delay": delay,
                    "price": price.replace(",", ""),
                }
            )

    current_price = safe(parser.css_first("span.gOatQ")).text()
    if not flights:
        raise RuntimeError("No flights found:\n{}".format(r.text_markdown))

    return Result(current_price=current_price, flights=[Flight(**fl) for fl in flights])


def _parse_duration(duration: str) -> int:
    """Convert duration string to minutes for sorting"""
    try:
        hours, minutes = duration.replace(" hr ", ":").replace(" min", "").split(":")
        return int(hours) * 60 + int(minutes)
    except (ValueError, AttributeError):
        return float('inf')  # Return infinity for invalid durations


def _get_sort_key(sort_method: Literal["best", "price", "duration"]):
    """Returns the appropriate sort key function based on sort method"""
    if sort_method == "best":
        return lambda f: (not f.is_best, float(f.price.replace("$", "").replace(",", "")), _parse_duration(f.duration))
    elif sort_method == "price":
        return lambda f: float(f.price.replace("$", "").replace(",", ""))
    else:  # duration
        return lambda f: _parse_duration(f.duration)


def _sort_and_limit_flights(flights: List[Flight], sort_method: str, limit: int = 5) -> List[Flight]:
    """Sort flights by given method and return top N results"""
    return sorted(flights, key=_get_sort_key(sort_method))[:limit]


def get_top_sorted_flights(
    *,
    flight_data: List[FlightData],
    trip: Literal["round-trip", "one-way", "multi-city"],
    passengers: Passengers,
    seat: Literal["economy", "premium-economy", "business", "first"],
    fetch_mode: Literal["common", "fallback", "force-fallback", "local"] = "common",
    max_stops: Optional[int] = None,
    sort_method: Literal["best", "price", "duration"] = "best",
) -> Result:
    # Get all flights first
    result = get_flights(
        flight_data=flight_data,
        trip=trip,
        passengers=passengers,
        seat=seat,
        fetch_mode=fetch_mode,
        max_stops=max_stops,
    )
    
    # Group flights by number of stops
    flights_by_stops = {}
    for stops, flights in groupby(sorted(result.flights, key=attrgetter("stops")), key=attrgetter("stops")):
        # Sort flights within each stop group and take top 5
        flights_by_stops[stops] = _sort_and_limit_flights(list(flights), sort_method)
    
    # Combine all top flights
    top_flights = []
    for stops in sorted(flights_by_stops.keys()):
        top_flights.extend(flights_by_stops[stops])
    
    return Result(current_price=result.current_price, flights=top_flights)


def get_best_flights_across_dates(
    *,
    start_date: datetime,
    end_date: datetime,
    from_airport: str,
    to_airport: str,
    trip: Literal["round-trip", "one-way", "multi-city"],
    passengers: Passengers,
    seat: Literal["economy", "premium-economy", "business", "first"],
    fetch_mode: Literal["common", "fallback", "force-fallback", "local"] = "common",
    max_stops: Optional[int] = None,
    sort_method: Literal["best", "price", "duration"] = "best",
) -> Result:
    """Get best flights across a date range (maximum 5 days)"""
    # Validate date range
    date_diff = (end_date - start_date).days
    if date_diff < 0:
        raise ValueError("end_date must be after start_date")
    if date_diff > 5:
        raise ValueError("Maximum date range is 5 days")
    
    # Collect flights for each date
    all_flights = []
    price_levels = []  # Track all price levels
    
    current_date = start_date
    while current_date <= end_date:
        flight_data = [
            FlightData(
                date=current_date.strftime("%Y-%m-%d"),
                from_airport=from_airport,
                to_airport=to_airport,
            )
        ]
        
        # Get top flights for this date
        result = get_top_sorted_flights(
            flight_data=flight_data,
            trip=trip,
            passengers=passengers,
            seat=seat,
            fetch_mode=fetch_mode,
            max_stops=max_stops,
            sort_method=sort_method,
        )
        
        # Track price levels
        price_levels.append(result.current_price)
            
        # Add date information to flights
        for flight in result.flights:
            flight.date = current_date.strftime("%Y-%m-%d")
        
        all_flights.extend(result.flights)
        current_date += timedelta(days=1)
    
    # Sort all flights and take top 5 overall
    best_flights = _sort_and_limit_flights(all_flights, sort_method)
    
    # Determine overall price level (use the most common level, defaulting to the lowest)
    if "low" in price_levels:
        overall_price = "low"
    elif "typical" in price_levels:
        overall_price = "typical"
    else:
        overall_price = "high"
    
    return Result(current_price=overall_price, flights=best_flights)
