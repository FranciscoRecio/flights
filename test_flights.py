from fast_flights import create_filter, get_flights_from_filter, FlightData, Passengers
from datetime import datetime, timedelta

def test_common():
    """Test common mode (direct HTTP request)"""
    future_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
    
    filter = create_filter(
        flight_data=[
            FlightData(
                date=future_date,
                from_airport="LAX",  # Los Angeles
                to_airport="JFK",    # New York
            )
        ],
        trip="one-way",
        passengers=Passengers(adults=2, children=1, infants_in_seat=0, infants_on_lap=0),
        seat="economy",
        max_stops=1,
    )
    print("\n=== Common Mode Test (Direct HTTP) ===")
    print("Base64 encoded filter:")
    print(filter.as_b64().decode("utf-8"))
    print("\nResults:")
    print(get_flights_from_filter(filter, mode="common"))

def test_force_fallback():
    """Test force-fallback mode (remote Playwright)"""
    future_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
    
    filter = create_filter(
        flight_data=[
            FlightData(
                date=future_date,
                from_airport="LAX",
                to_airport="JFK",
            )
        ],
        trip="one-way",
        passengers=Passengers(adults=2, children=1, infants_in_seat=0, infants_on_lap=0),
        seat="economy",
        max_stops=1,
    )
    print("\n=== Force-Fallback Mode Test (Remote Playwright) ===")
    print("Base64 encoded filter:")
    print(filter.as_b64().decode("utf-8"))
    print("\nResults:")
    print(get_flights_from_filter(filter, mode="force-fallback"))

if __name__ == "__main__":
    print("Starting flight search tests...")
    print("(Testing both direct HTTP and remote Playwright methods)")
    
    test_common()         # Test direct HTTP request
    test_force_fallback() # Test remote Playwright
    
    print("\nTests completed!") 